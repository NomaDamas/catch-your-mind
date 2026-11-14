import copy
import hashlib
import tempfile
from pathlib import Path
import unittest

from benchmarks.recording_financial import (FinancialArtifacts,_issue_financial_run_view,
    claim_sha256,digest,encode,ratio)
from benchmarks.recording_lifetime_ledger import _validate_costs,validate_lifetime


def runview(arm='A',**overrides):
    value = dict(execution_sha256=arm.lower()*64,run_inventory_sha256='1'*64,execution_inventory_sha256='c'*64,
        parent_receipt_inventory_sha256=digest([]),invocation_ordinal='ABC'.index(arm),
        stream_id='stream-'+arm,recording_id='recording',arm=arm,source_manifest_sha256='2'*64,
        source_coverage_sha256='3'*64,source_comparable=True,task_row_inventory_sha256='4'*64,
        clock_domain='local',clock_consistent=True,activation_started_ns=100,child_spawn_started_ns=200,
        playback_anchor_ns=300,source_finished_ns=700,child_cleanup_finished_ns=800,process_reaped_ns=900,
        parent_resources_closed_ns=1000,operational_closed=True,external_work_closed=True,
        worker_inventory_sha256=digest([]),native_terminal_sha256='6'*64,
        controller_settlement_inventory_sha256=digest([]),semantic_unknown_instances=(),violations=())
    value.update(overrides)
    return _issue_financial_run_view(**value)


def lifetime(run):
    value = {key:getattr(run,key) for key in ('execution_sha256','run_inventory_sha256','stream_id','clock_domain',
        'activation_started_ns','child_spawn_started_ns','playback_anchor_ns','source_finished_ns',
        'child_cleanup_finished_ns','process_reaped_ns','parent_resources_closed_ns','external_work_closed','worker_inventory_sha256')}
    value.update(schema_version=2,kind='recording_observed_lifetime',
        utc_anchor=dict(monotonic_ns=100,unix_ns=1700000000000000000,evidence_sha256='6'*64),
        resource_intervals=dict(path='ledger/coverage-000.json',file_sha256='7'*64,bytes=10),
        coverage_sha256=run.source_coverage_sha256,state='closed')
    return value


def cost_fixture(store,*,lifecycle_owner=False):
    runs = [runview(arm) for arm in 'ABC']
    components = [dict(id=cid,category=cid,kind='monetary',unit='tick',source_unit='tick',
        atomic_per_source=ratio(1),coverage=coverage,rate_id='fixture') for cid,coverage in (('vlm','event'),('resident_idle','interval'))]
    policy = dict(components=components,rates=dict(fixture=dict(provider='fixture',revision='v1',unit='tick',per_unit='1')),streams=[])
    operations = {}; financial = dict(original_lines={},evidence={},operations={},lanes={}); entries = []; by_lane = {}
    for run in runs:
        sid = run.stream_id; resource = 'resource-'+run.arm
        policy['streams'].append(dict(stream_id=sid,requirements={cid:dict(state='required',lanes=[dict(
            resource_id=resource,lane_id=cid,coverage='whole_lifetime',lifecycle_binding_id=None)]) for cid in ('vlm','resident_idle')}))
        for ordinal,cid in enumerate(('vlm','vlm','resident_idle')):
            instance = digest([run.arm,ordinal]) if cid == 'vlm' else None
            if instance:
                operations[instance] = dict(instance=instance,invocation_ordinal=run.invocation_ordinal,binding_index=0,
                    entry_ordinal=ordinal,role='text_llm',outcome='error' if ordinal else 'ok')
                financial['operations'][instance] = dict(status='settled',basis='original_line')
            line_id = cid+'-'+str(ordinal)
            evidence = dict(claim_sha256=claim_sha256('fixture','study','invoice-'+run.arm,line_id),
                owner_instance=instance,observed_received_ns=1100,billed_atomic=1)
            original = dict(line_id=line_id,stream_id=sid,component_id=cid,resource_id=resource,lane_id=cid,
                source_quantity=ratio(1),quantity=1,service_start_ns=100 if cid=='resident_idle' else None,
                service_end_ns=1000 if cid=='resident_idle' else None,service_event_ns=400+ordinal if cid=='vlm' else None)
            ref = dict(path='financial/source/source-'+'8'*64+'.json',file_sha256='8'*64,bytes=10)
            financial['original_lines'][evidence['claim_sha256']] = (ref,dict(revision='v1'),original)
            financial['evidence'][digest(evidence)] = evidence
            line = dict(stream_id=sid,component_id=cid,resource_id=resource,lane_id=cid,
                start_ns=original['service_start_ns'],end_ns=original['service_end_ns'],event_ns=original['service_event_ns'],
                identity=dict(kind='invoice',provider='fixture',revision='v1',account_scope='study',invoice_id='invoice-'+run.arm,
                              document_sha256='8'*64,line_id=line_id),
                source_quantity=ratio(1),quantity=1,status='settled',billed_amount=1,evidence_sha256='9'*64,
                operation_instance=instance,lifecycle_work_ref=(dict(invocation_ordinal=0,worker_ordinal=0,work_ordinal=0)
                    if lifecycle_owner and run.arm=='A' and cid=='resident_idle' else None),
                received_ns=1100,financial_evidence_sha256=digest(evidence))
            by_lane.setdefault((sid,cid,resource,cid),[]).append(len(entries)); entries.append(line)
    page = dict(schema_version=2,kind='recording_cost_lines',page_ordinal=0,previous_page_sha256=None,entries=entries)
    page_ref = store.write('ledger/cost-000000.json',page)
    for key,positions in by_lane.items():
        index = store.write_index('line-locators',[dict(cost_page=page_ref,entry_index=position) for position in positions])
        financial['lanes'][key] = dict(window_start_ns=100,window_end_ns=1000,status='closed',cost_line_inventory=index,
            work_inventory_sha256=digest([]))
    return policy,runs,financial,operations,[page_ref]


class Lifetime(unittest.TestCase):
    def test_actual_lifetime_preserved_and_not_equal_to_source_duration(self):
        run = runview(); value = lifetime(run)
        self.assertEqual(validate_lifetime(value,run),value)
        value['parent_resources_closed_ns'] = 700
        with self.assertRaises(ValueError): validate_lifetime(value,run)

    def test_child_terminal_and_cancel_ack_do_not_close_work(self):
        run = runview(parent_resources_closed_ns=None,operational_closed=False,external_work_closed=False)
        value = lifetime(run)
        with self.assertRaises(ValueError): validate_lifetime(value,run)
        value['state'] = 'incomplete'
        self.assertEqual(validate_lifetime(value,run)['state'],'incomplete')

    def test_failed_cancelled_unreferenced_calls_and_resident_lifetime_all_charged(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as root:
            with FinancialArtifacts(root) as store:
                policy,runs,financial,operations,pages = cost_fixture(store)
                totals,reasons,lines = _validate_costs(store,pages,policy=policy,runs=runs,
                    lifetimes={r.stream_id:lifetime(r) for r in runs},financial=financial,operations=operations,work={})
                self.assertEqual(totals,{'stream-A':3,'stream-B':3,'stream-C':3})
                self.assertTrue(all(not value for value in reasons.values()))
                self.assertEqual(len(lines),9)

    def test_missing_actual_operation_line_and_meter_refuses_silent_cost_omission(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as root:
            with FinancialArtifacts(root) as store:
                policy,runs,financial,operations,pages = cost_fixture(store)
                operation = next(iter(operations.values())).copy(); operation['instance'] = 'f'*64
                operations['f'*64] = operation
                financial['operations']['f'*64] = dict(status='settled',basis='original_line')
                with self.assertRaises(ValueError): _validate_costs(store,pages,policy=policy,runs=runs,
                    lifetimes={r.stream_id:lifetime(r) for r in runs},financial=financial,operations=operations,work={})

    def test_operation_meter_cannot_borrow_another_run_or_unbound_overhead(self):
        for target in ('stream-B','stream-A'):
            with self.subTest(target=target),tempfile.TemporaryDirectory(dir=Path.cwd()) as root:
                with FinancialArtifacts(root) as store:
                    policy,runs,financial,operations,pages=cost_fixture(store)
                    operations['f'*64]=dict(instance='f'*64,invocation_ordinal=0,binding_index=0,entry_ordinal=2,role='motion',outcome='ok')
                    financial['operations']['f'*64]=dict(status='settled',basis='meter_lane',meter_lane=dict(
                        stream_id=target,component_id='resident_idle',resource_id='resource-'+target[-1],lane_id='resident_idle'))
                    with self.assertRaisesRegex(ValueError,'original run stream|explicit monetary lifecycle binding'):
                        _validate_costs(store,pages,policy=policy,runs=runs,lifetimes={r.stream_id:lifetime(r) for r in runs},
                            financial=financial,operations=operations,work={})

    def test_operation_meter_requires_actual_bound_work_inside_measured_interval(self):
        for variant in ('exact','other_binding','other_operation','missing_work','open_work','outside_window'):
            with self.subTest(variant=variant),tempfile.TemporaryDirectory(dir=Path.cwd()) as root:
                with FinancialArtifacts(root) as store:
                    policy,runs,financial,operations,pages=cost_fixture(store,lifecycle_owner=True)
                    lane=policy['streams'][0]['requirements']['resident_idle']['lanes'][0]
                    lane.update(coverage='observed_lifecycle',lifecycle_binding_id='motion')
                    collection=dict(arms=[dict(arm=a,provider_bindings=[dict(binding_id='motion'),dict(binding_id='other')]) for a in 'ABC'])
                    operations['f'*64]=dict(instance='f'*64,invocation_ordinal=0,binding_index=1 if variant=='other_binding' else 0,
                        entry_ordinal=2,role='motion',outcome='ok')
                    financial['operations']['f'*64]=dict(status='settled',basis='meter_lane',meter_lane=dict(
                        stream_id='stream-A',component_id='resident_idle',resource_id='resource-A',lane_id='resident_idle'))
                    interval=dict(binding=0,parent_entry_ordinal=3 if variant=='other_operation' else 2,work_ordinal=0,worker_ordinal=0,
                        started_ns=90 if variant=='outside_window' else 400,ended_ns=None if variant=='open_work' else 500,
                        clock_domain='host_monotonic_ns')
                    work={(0,0,0):interval}
                    financial['lanes']['stream-A','resident_idle','resource-A','resident_idle']['work_inventory_sha256']=digest([interval])
                    if variant=='missing_work':interval['parent_entry_ordinal']=None
                    call=lambda:_validate_costs(store,pages,policy=policy,runs=runs,lifetimes={r.stream_id:lifetime(r) for r in runs},
                        financial=financial,operations=operations,work=work,collection=collection)
                    if variant in ('other_binding','outside_window'):
                        with self.assertRaisesRegex(ValueError,'binding/resource|excludes actual'):call()
                    else:
                        totals,reasons,_=call()
                        self.assertEqual(totals,{'stream-A':3,'stream-B':3,'stream-C':3})
                        self.assertEqual(not reasons['stream-A'],variant=='exact')
                        if variant in ('other_operation','missing_work'):self.assertIn('unmeasured_operation_work',reasons['stream-A'])
                        if variant=='open_work':self.assertIn('unclosed_operation_work',reasons['stream-A'])

    def test_required_proxy_never_establishes_monetary_accounting(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as root:
            with FinancialArtifacts(root) as store:
                policy,runs,financial,operations,pages = cost_fixture(store)
                # A monetary original line cannot be relabeled as measuredproxy.
                policy['components'][0]['kind'] = 'proxy'
                with self.assertRaises(ValueError): _validate_costs(store,pages,policy=policy,runs=runs,
                    lifetimes={r.stream_id:lifetime(r) for r in runs},financial=financial,operations=operations,work={})


if __name__ == '__main__': unittest.main()
