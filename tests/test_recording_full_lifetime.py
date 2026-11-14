"""Whole 24-group financial traversal retains every failed original arm."""
import tempfile
from pathlib import Path
import unittest

from benchmarks.recording_financial import FinancialArtifacts,claim_sha256,digest,ratio
from benchmarks.recording_lifetime_ledger import validate_lifetime_ledger
from benchmarks.recording_exposure_report import compare_quality_latency,reconcile_exposure
from benchmarks.perception_comparison import plan_digest
from test_matched_source_exposure import declarations
from test_recording_financial import adapters,invoice
from test_recording_lifetime_ledger import runview,lifetime
from test_recording_exposure_report import quality_fixture


def incomplete_collection(store,count=24):
    plan,g,k,e=declarations(count);f=adapters()
    fdoc=dict(schema_version=1,kind='recording_financial_adapters',adapters=list(f.adapters))
    u=dict(schema_version=2,evaluation_mode='matched_source_exposure_full_lifetime_v2',
        numeric_policy_sha256=digest(e),accounting_policy_sha256=digest(k))
    c=dict(runtime_policy_sha256=digest(u),arms=[dict(arm=a,provider_bindings=[]) for a in 'ABC'])
    q=dict(schema_version=2,recording_reconciliation_sha256=digest(e),stream_protocol_sha256=digest(k),collection_sha256=digest(c))
    i=dict(schema_version=3,scope_protocol_sha256=digest(q),collection_sha256=digest(c))
    _,_,_,original_receipts=quality_fixture()
    sources=[];evidences=[];entries=[];lanes=[];runs=[];lives=[];coverages=[]
    for n,stream in enumerate(k['streams']):
        sid=stream['stream_id'];coverage=dict(stream_id=sid,actual_source_complete=False)
        covref=store.write('ledger/coverage-%03d.json'%n,coverage);coverages.append(covref)
        nonce=digest(['original failed invocation',n])
        receipts=[] if n>=len(original_receipts) else [{**original_receipts[n][1],'execution_sha256':nonce}]
        run=runview(stream['arm'],execution_sha256=nonce,parent_receipt_inventory_sha256=digest(receipts),
            invocation_ordinal=n,stream_id=sid,recording_id=stream['recording_id'],
            source_manifest_sha256=stream['source_manifest_sha256'],source_coverage_sha256=digest(coverage),
            source_comparable=False,operational_closed=False,external_work_closed=False,
            native_terminal_sha256=None,violations=('missing_native_prefix',))
        runs.append(run);life=lifetime(run);life.update(state='incomplete',resource_intervals=covref)
        lives.append(store.write('ledger/lifetime-%03d.json'%n,life))
        document=invoice();document.update(invoice_id='original-'+sid,currency_unit='USD.micro')
        line=document['lines'][0];line.update(stream_id=sid,resource_id='resource-'+sid,quantity=4,source_quantity=ratio(4),
            operation_key=dict(invocation_ordinal=n,binding_index=0,call_ordinal=0))
        source=store.write_invoice(document);sources.append(dict(source_document=source))
        owner=digest(['actual-unverified-prefix',sid]);claim=claim_sha256('fixture','study',document['invoice_id'],line['line_id'])
        evidence=dict(schema_version=1,kind='recording_financial_evidence',adapter_id='fixture',adapter_inventory_sha256=f.digest,
            origin='synthetic_fixture',source_document=source,provider='fixture',revision='v1',account_scope='study',
            invoice_id=document['invoice_id'],line_id=line['line_id'],claim_sha256=claim,owner_instance=owner,stream_id=sid,
            quantities=dict(vlm=ratio(4)),billed_atomic=4,currency='USD',currency_unit='USD.micro',service_start_ns=None,
            service_end_ns=None,service_event_ns=101,observed_received_ns=1100,finality_evidence_sha256=None)
        evidences.append(evidence)
        entries.append(dict(stream_id=sid,component_id='vlm',resource_id='resource-'+sid,lane_id='vlm',start_ns=None,end_ns=None,
            event_ns=101,identity=dict(kind='invoice',provider='fixture',revision='v1',account_scope='study',invoice_id=document['invoice_id'],
                document_sha256=source['file_sha256'],line_id=line['line_id']),source_quantity=ratio(4),quantity=4,status='settled',
            billed_amount=4,evidence_sha256='9'*64,operation_instance=owner,lifecycle_work_ref=None,received_ns=1100,
            financial_evidence_sha256=digest(evidence)))
    costpage=store.write('ledger/cost-000000.json',dict(schema_version=2,kind='recording_cost_lines',page_ordinal=0,
        previous_page_sha256=None,entries=entries))
    for n,run in enumerate(runs):
        lanes.append(dict(stream_id=run.stream_id,component_id='vlm',resource_id='resource-'+run.stream_id,lane_id='vlm',
            window_start_ns=100,window_end_ns=1000,status='unknown',work_inventory_sha256=run.worker_inventory_sha256,
            cost_line_inventory=store.write_index('line-locators',[dict(cost_page=costpage,entry_index=n)])))
    fin=dict(schema_version=1,kind='recording_financial_inventory',exposure_policy_sha256=digest(e),accounting_policy_sha256=digest(k),
        financial_adapter_inventory_sha256=f.digest,collection_sha256=digest(c),source_documents=store.write_index('source',sources),
        evidence_pages=store.write_index('evidence',evidences),operation_pages=store.write_index('operations',[]),
        lane_closure_pages=store.write_index('lanes',lanes),finality=store.write_index('finality',[]),state='incomplete')
    finref=store.write('ledger/financial-inventory.json',fin);closures=[]
    for n,run in enumerate(runs):
        closure=dict(schema_version=1,kind='recording_financial_closure',execution_sha256=run.execution_sha256,stream_id=run.stream_id,
            accounting_policy_sha256=digest(k),financial_adapter_inventory_sha256=f.digest,operational_end_ns=1000,cutoff_ns=1000,sealed_ns=1200,
            operation_count=0,known_settled_operations=0,unresolved_operations=0,required_lane_count=1,closed_lane_count=0,
            pending_line_count=0,unknown_component_count=0,external_finality_refs=[],financial_inventory_sha256=digest(fin),state='incomplete')
        closures.append(store.write('ledger/closure-%03d.json'%n,closure))
    closure_ref=store.write('ledger/closures.json',dict(schema_version=1,kind='recording_financial_closures',closures=closures))
    ledger=dict(schema_version=2,kind='recording_lifetime_ledger',accounting_policy_sha256=digest(k),exposure_policy_sha256=digest(e),
        runtime_policy_sha256=digest(u),collection_sha256=digest(c),scope_protocol_sha256=digest(q),comparison_plan_sha256=plan_digest(plan),
        reviewer='fixture',source_evidence_sha256='a'*64,lifetimes=lives,coverage=coverages,entry_pages=[costpage],financial_inventory=finref,closure=closure_ref)
    genesis=dict(schema_version=1,kind='recording_validity_entry',exposure_policy_sha256=digest(e),ledger_sha256=digest(ledger),
        sequence=0,previous_sha256=None,notice=None,state='sealed',observed_ns=1200)
    genref=store.write('ledger/validity-000000.json',genesis)
    checkpoint=dict(schema_version=1,kind='recording_validity_checkpoint',exposure_policy_sha256=digest(e),ledger_sha256=digest(ledger),
        tail_sha256=genref['file_sha256'],tail_sequence=0,reviewed_as_of_ns=1201,reviewer='external-fixture',review_method_sha256='b'*64)
    return dict(policy=k,exposure=e,runtime=u,collection=c,scope_protocol=q,instrumentation=i,observed_runs=runs,
        native_indices=[None]*len(runs),ledger=ledger,financial_inventory=fin,validity_checkpoint=checkpoint,plan=plan,
        recordings=g,adapters_document=fdoc,store=store,expected_policy_sha256=digest(k),expected_exposure_sha256=digest(e),
        expected_ledger_sha256=digest(ledger),expected_checkpoint_sha256=digest(checkpoint),validity_entries=[(genref,genesis)],late_notices={})


class WholeLifetime(unittest.TestCase):
    def test_all_twenty_four_original_groups_retained_with_known_money_and_unknown_native_prefix(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as root:
            with FinancialArtifacts(root) as store:
                args=incomplete_collection(store);validated=validate_lifetime_ledger(**args)
                self.assertEqual(len(validated.totals),72)
                self.assertEqual(sum(t.known_monetary_atomic for t in validated.totals),288)
                self.assertTrue(all(t.full_monetary_atomic is None for t in validated.totals))
                plan,_,assessment,receipts=quality_fixture()
                assessment.update(runtime_policy_sha256=digest(args['runtime']),collection_sha256=digest(args['collection']))
                for row,(_,receipt),run in zip(assessment['rows'],receipts,args['observed_runs']):
                    receipt['execution_sha256']=run.execution_sha256
                    row['parent_receipt_sha256']=digest(receipt)
                quality=compare_quality_latency(plan,assessment,receipts,expected_assessment_sha256=plan_digest(assessment))
                report=reconcile_exposure(plan,args['exposure'],args['recordings'],validated,quality,
                    runtime_policy_sha256=digest(args['runtime']),collection_sha256=digest(args['collection']),
                    scope_protocol_sha256=digest(args['scope_protocol']),instrumentation_protocol_sha256=digest(args['instrumentation']),
                    execution_inventory_sha256='c'*64)
                self.assertEqual(len(report['groups']),24);self.assertEqual(report['state'],'incomplete')
                self.assertEqual(report['canonical_arm_totals']['A']['known_monetary_atomic'],96)
                self.assertIsNone(report['canonical_arm_totals']['A']['full_monetary_atomic'])
                self.assertFalse(report['comparison']['C_vs_A']['cost_gate'])
                with self.assertRaises(TypeError):validated.validity['state']='sealed'

    def test_any_known_unindexed_original_invoice_refuses_selective_success(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as root:
            with FinancialArtifacts(root) as store:
                args=incomplete_collection(store)
                extra=invoice();extra['invoice_id']='omitted-known-original';store.write_invoice(extra)
                with self.assertRaisesRegex(ValueError,'orphan/omitted'):validate_lifetime_ledger(**args)


if __name__=='__main__':unittest.main()
