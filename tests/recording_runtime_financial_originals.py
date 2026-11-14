"""Explicit F1 invoice/finality originals over already joined actual runs.

Test-only authority. This deliberately signs no real invoice and changes no
runtime receipt, native event or controller history. Every actual entry is billed.
"""
from copy import deepcopy
from pathlib import Path
import time

from benchmarks.recording_financial import digest,decode,claim_sha256,ratio
from benchmarks.recording_native_schema import digest as original_digest
from benchmarks.recording_native_validation import iter_canonical_operations
from benchmarks.recording_runtime_finance import finalize_financial_runs
from test_recording_financial import invoice


def financial_originals(joined,manifest,documents,output,store):
    runs=finalize_financial_runs(joined,manifest,documents=documents)
    p=documents['runtime/plan.json'];u=documents['runtime/policy.json'];c=documents['runtime/collection.json']
    q=documents['runtime/scopes.json'];k=documents['runtime/accounting.json'];e=documents['runtime/exposure.json']
    f=documents['runtime/financial-adapters.json'];output=Path(output)
    sources=[];evidences=[];operations=[];costs=[];lanes=[];finalities=[];lifetimes=[];coverages=[];assessments=[]
    perrun=[];settlement_ordinal=0
    for typed,run in zip(joined,runs):
        inv=run.invocation_ordinal;directory=output/f'runs/{inv:02}'
        coverage=store.write(f'ledger/coverage-{inv:03}.json',typed.source_coverage);coverages.append(coverage)
        life={name:getattr(run,name) for name in ('execution_sha256','run_inventory_sha256','stream_id','clock_domain',
            'activation_started_ns','child_spawn_started_ns','playback_anchor_ns','source_finished_ns',
            'child_cleanup_finished_ns','process_reaped_ns','parent_resources_closed_ns','external_work_closed','worker_inventory_sha256')}
        anchor=dict(monotonic_ns=time.monotonic_ns(),unix_ns=time.time_ns())
        life.update(schema_version=2,kind='recording_observed_lifetime',utc_anchor=dict(anchor,evidence_sha256=digest(anchor)),
            resource_intervals=coverage,coverage_sha256=run.source_coverage_sha256,state='closed')
        lifetimes.append(store.write(f'ledger/lifetime-{inv:03}.json',life))
        native=list(iter_canonical_operations(typed.native_index));ranks={};localops=[];localdocs=[];positions=[]
        settlement_by_instance={row['instance']:row for row in typed.controller_settlements}
        # Original child evidence is already validated by the typed join. Preserve
        # content-addressed invoice originals and copy SDK receipts by global alias.
        child_evidence={}
        for path in sorted((directory/'financial/evidence').glob('evidence-*.json')):
            value=decode(path.read_bytes());child_evidence[value['owner_instance']]=value
        for op in native:
            binding=op['binding_index'];rank=ranks.get(binding,0);ranks[binding]=rank+1
            instance=op['instance'];settled=settlement_by_instance.get(instance)
            if op['role'] in ('text_llm','small_vlm','strong_vlm'):
                if settled is None or instance not in child_evidence:raise ValueError('actual semantic SDK charge missing')
                evidence=deepcopy(child_evidence[instance]);source=decode((directory/evidence['source_document']['path']).read_bytes())
                source_ref=store.write_invoice(source)
                if source_ref!=evidence['source_document']:raise ValueError('original SDK source changed during copy')
                evidence_ref=store.write(f'financial/evidence/evidence-{len(evidences):06}.json',evidence)
                receipt_ref=store.write(f'financial/settlements/receipt-{settlement_ordinal:06}.json',settled);settlement_ordinal+=1
            else:
                # Frozen F1 callback-only fixture meter: one original tick for
                # every entered source process, including failed callbacks.
                source=invoice();source.update(account_scope='s',invoice_id=f'process-{inv}-{binding}-{rank}',currency_unit='fixture')
                line=source['lines'][0];line.update(line_id='l',stream_id=run.stream_id,component_id='perception',
                    resource_id='r-'+str(inv),lane_id='perception',operation_key=dict(invocation_ordinal=inv,binding_index=binding,call_ordinal=rank),
                    service_event_ns=op['entered_monotonic_ns'],source_quantity=ratio(1),quantity=1,billed_atomic=1)
                source_ref=store.write_invoice(source)
                evidence=dict(schema_version=1,kind='recording_financial_evidence',adapter_id='fixture',adapter_inventory_sha256=digest(f),
                    origin='synthetic_fixture',source_document=source_ref,provider=source['provider'],revision=source['revision'],
                    account_scope=source['account_scope'],invoice_id=source['invoice_id'],line_id='l',
                    claim_sha256=claim_sha256(source['provider'],source['account_scope'],source['invoice_id'],'l'),owner_instance=instance,
                    stream_id=run.stream_id,quantities=dict(perception=ratio(1)),billed_atomic=1,currency='USD',currency_unit='fixture',
                    service_start_ns=None,service_end_ns=None,service_event_ns=line['service_event_ns'],
                    observed_received_ns=time.monotonic_ns(),finality_evidence_sha256=None)
                evidence_ref=store.write(f'financial/evidence/evidence-{len(evidences):06}.json',evidence);receipt_ref=None
            line=source['lines'][0];sources.append(dict(source_document=source_ref));localdocs.append(source_ref['file_sha256']);evidences.append(evidence)
            row=dict(instance=instance,invocation_ordinal=inv,binding_index=binding,entry_ordinal=op['entry_ordinal'],
                status='settled',basis='original_line',evidence=evidence_ref,controller_settlement=receipt_ref,meter_lane=None)
            operations.append(row);localops.append(row);positions.append(len(costs))
            costs.append(dict(stream_id=run.stream_id,component_id=line['component_id'],resource_id=line['resource_id'],lane_id=line['lane_id'],
                start_ns=line['service_start_ns'],end_ns=line['service_end_ns'],event_ns=line['service_event_ns'],
                identity=dict(kind='invoice',provider=source['provider'],revision=source['revision'],account_scope=source['account_scope'],
                    invoice_id=source['invoice_id'],document_sha256=source_ref['file_sha256'],line_id=line['line_id']),
                source_quantity=line['source_quantity'],quantity=line['quantity'],status='settled',billed_amount=line['billed_atomic'],
                evidence_sha256=op['evidence_sha256'],operation_instance=instance,lifecycle_work_ref=None,
                received_ns=evidence['observed_received_ns'],financial_evidence_sha256=digest(evidence)))
        perrun.append((run,localops,sorted(localdocs),positions))
        for receipt in typed.task_receipts:
            task=next(task for task in p['comparison']['tasks'] if task['id']==receipt['task_id'])
            assessments.append(dict(task_id=receipt['task_id'],input_sha256=receipt['input_sha256'],invocation_ordinal=inv,
                parent_receipt_sha256=digest(receipt),answer_sha256=receipt['answer_sha256'],quality_score=1,
                correct_critical_facts=task['critical_facts']))
    # Native identities make actual runtime rows larger than small arithmetic
    # fixtures. Keep pages within the original64KiB bound as well as128 rows.
    from benchmarks.recording_financial import encode
    pages=[];pending=[]
    for row in costs:
        if pending and (len(pending)==128 or len(encode(dict(schema_version=2,kind='recording_cost_lines',
                page_ordinal=len(pages),previous_page_sha256='0'*64,entries=[*pending,row]),1024**2,newline=True))>65536):
            pages.append(pending);pending=[]
        pending.append(row)
    if pending:pages.append(pending)
    costrefs=[];locators=[];previous=None
    for ordinal,rows in enumerate(pages):
        page=dict(schema_version=2,kind='recording_cost_lines',page_ordinal=ordinal,previous_page_sha256=previous,entries=rows)
        ref=store.write(f'ledger/cost-{ordinal:06}.json',page);costrefs.append(ref);previous=ref['file_sha256']
        locators.extend(dict(cost_page=ref,entry_index=n) for n in range(len(rows)))
    for run,localops,localdocs,positions in perrun:
        lane=dict(stream_id=run.stream_id,component_id='perception',resource_id='r-'+str(run.invocation_ordinal),lane_id='perception',
            window_start_ns=run.activation_started_ns,window_end_ns=run.parent_resources_closed_ns,status='closed',
            cost_line_inventory=store.write_index('line-locators',[locators[pos] for pos in positions]),
            work_inventory_sha256=run.worker_inventory_sha256)
        lanes.append(lane)
        finality=dict(schema_version=1,kind='synthetic_recording_finality',evidence_class='fixture',authority='gamst.synthetic_invoice_fixture_v1',
            execution_sha256=run.execution_sha256,stream_id=run.stream_id,accounting_policy_sha256=digest(k),source_document_sha256=localdocs,
            operation_inventory_sha256=digest(sorted(localops,key=lambda row:row['entry_ordinal'])),lane_closure_inventory_sha256=digest([lane]),
            service_end_ns=run.parent_resources_closed_ns,issued_ns=time.monotonic_ns(),state='final_no_further_charges')
        finalities.append(dict(finality=store.write(f'financial/finality/finality-{run.invocation_ordinal:06}.json',finality)))
    fin=dict(schema_version=1,kind='recording_financial_inventory',exposure_policy_sha256=digest(e),accounting_policy_sha256=digest(k),
        financial_adapter_inventory_sha256=digest(f),collection_sha256=original_digest(c),source_documents=store.write_index('source',sources),
        evidence_pages=store.write_index('evidence',evidences),operation_pages=store.write_index('operations',operations),
        lane_closure_pages=store.write_index('lanes',lanes),finality=store.write_index('finality',finalities),state='complete')
    finref=store.write('ledger/financial-inventory.json',fin);closures=[];seal=0
    for (run,localops,_,_),finality in zip(perrun,finalities):
        seal=time.monotonic_ns()
        closure=dict(schema_version=1,kind='recording_financial_closure',execution_sha256=run.execution_sha256,stream_id=run.stream_id,
            accounting_policy_sha256=digest(k),financial_adapter_inventory_sha256=digest(f),operational_end_ns=run.parent_resources_closed_ns,
            cutoff_ns=run.parent_resources_closed_ns,sealed_ns=seal,operation_count=len(localops),known_settled_operations=len(localops),
            unresolved_operations=0,required_lane_count=1,closed_lane_count=1,pending_line_count=0,unknown_component_count=0,
            external_finality_refs=[finality['finality']],financial_inventory_sha256=digest(fin),state='closed')
        closures.append(store.write(f'ledger/closure-{run.invocation_ordinal:03}.json',closure))
    closure_ref=store.write('ledger/closures.json',dict(schema_version=1,kind='recording_financial_closures',closures=closures))
    ledger=dict(schema_version=2,kind='recording_lifetime_ledger',accounting_policy_sha256=digest(k),exposure_policy_sha256=digest(e),
        runtime_policy_sha256=original_digest(u),collection_sha256=original_digest(c),scope_protocol_sha256=original_digest(q),comparison_plan_sha256=original_digest(p),
        reviewer='explicit-synthetic-fixture',source_evidence_sha256=digest([r.source_coverage for r in joined]),lifetimes=lifetimes,
        coverage=coverages,entry_pages=costrefs,financial_inventory=finref,closure=closure_ref)
    genesis=dict(schema_version=1,kind='recording_validity_entry',exposure_policy_sha256=digest(e),ledger_sha256=digest(ledger),sequence=0,
        previous_sha256=None,notice=None,state='sealed',observed_ns=seal)
    genref=store.write('ledger/validity-000000.json',genesis)
    checkpoint=dict(schema_version=1,kind='recording_validity_checkpoint',exposure_policy_sha256=digest(e),ledger_sha256=digest(ledger),
        tail_sha256=genref['file_sha256'],tail_sequence=0,reviewed_as_of_ns=time.monotonic_ns(),reviewer='external-fixture',review_method_sha256='b'*64)
    assessment=dict(schema_version=1,kind='recording_assessment',comparison_plan_sha256=original_digest(p),runtime_policy_sha256=original_digest(u),
        collection_sha256=original_digest(c),execution_inventory_sha256=original_digest(manifest),reviewer='explicit-synthetic-fixture',rubric_sha256='d'*64,
        measurement_protocol_sha256='e'*64,source_evidence_sha256=digest([r.task_rows for r in joined]),rows=assessments)
    return dict(store=store,ledger=ledger,financial_inventory=fin,validity_checkpoint=checkpoint,
        expected_ledger_sha256=digest(ledger),expected_checkpoint_sha256=digest(checkpoint),validity_entries=[(genref,genesis)],late_notices={},
        assessment=assessment,expected_assessment_sha256=original_digest(assessment))
