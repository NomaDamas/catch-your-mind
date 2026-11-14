"""Prospective numeric fixture graph; no claim of real source/model evidence."""
from copy import deepcopy
from itertools import permutations
from benchmarks.recording_native_schema import digest
from benchmarks.perception_comparison import plan_digest
from test_recording_runtime_native import runtime_declarations
from test_matched_source_exposure import declarations
from test_recording_financial import adapters
from test_recording_settlement import scenario


def prospective(count=24):
    d,l,bundles=runtime_declarations();u=d['runtime_policy'];original=bundles['original']
    p=deepcopy(d['plan']);p['comparison']['tasks']=[]
    _,g,k,e=declarations(count);g['groups']=[];sources={};records=[];policies=[]
    tasks=[]
    for n in range(count):
        rid='recording-%02d'%n;bundle=deepcopy(original);bundle['manifest']['recording_id']=rid
        task=deepcopy(original['tasks'][0]);task['task_id']=str(n)
        task['input']={'question':'original fixture question '+str(n)};task['input_sha256']=digest(task['input']);tasks.append(task)
        ptask=deepcopy(d['plan']['comparison']['tasks'][0]);ptask.update(id=str(n),input_sha256=task['input_sha256'])
        p['comparison']['tasks'].append(ptask);bundle['tasks']=[task]
        bundle['profiles'].update(recording_id=rid,source_manifest_sha256=digest(bundle['manifest']))
        sources[rid]=bundle
        records.append(dict(recording_id=rid,source_manifest_sha256=digest(bundle['manifest']),tasks_sha256=digest([task]),
            profiles_sha256=digest(bundle['profiles']),task_ids=[str(n)],duration_ns=bundle['manifest']['duration_ns']))
        upstream=deepcopy(u['recordings'][0]);upstream.update({key:records[-1][key] for key in
            ('recording_id','source_manifest_sha256','tasks_sha256','profiles_sha256')});policies.append(upstream)
        source=bundle['manifest']['sources'][0]
        g['groups'].append(dict(recording_id=rid,source_manifest_sha256=digest(bundle['manifest']),tasks_sha256=digest([task]),
            exposure_duration_ns=bundle['manifest']['duration_ns'],sources=[dict(source_id=source['source_id'],sensor_id=source['sensor_id'],
                original_stream_epoch=source['stream_epoch'],format=source['format'],calibration_id=None,record_count=1,
                record_inventory_sha256=digest(bundle['manifest']['records']),counter_contract='attempted_equals_captured_plus_dropped')],
            availability_sha256=digest(bundle['manifest']['availability']),arm_order=list(tuple(permutations('ABC'))[n%6])))
    psha=plan_digest(p);g['comparison_plan_sha256']=psha
    for stream in k['streams']:
        group=next(row for row in g['groups'] if row['recording_id']==stream['recording_id'])
        stream.update(source_manifest_sha256=group['source_manifest_sha256'],exposure_duration_ns=group['exposure_duration_ns'])
    k.update(comparison_plan_sha256=psha,recordings_sha256=digest(g))
    l.update(comparison_plan_sha256=psha)
    e.update(comparison_plan_sha256=psha,recordings_sha256=digest(g),latency_policy_sha256=digest(l),accounting_policy_sha256=digest(k))
    scenarios=[];rows=[];invocations=[]
    for group_index,group in enumerate(g['groups']):
        for arm in group['arm_order']:
            invocation=len(invocations);sid=group['recording_id']+'-'+arm
            invocations.append(dict(ordinal=invocation,recording_index=group_index,arm=arm,stream_id=sid))
            charge=scenario();charge.update(invoice_id='original-'+sid,stream_id=sid,resource_id='resource-'+sid,
                source_quantity=dict(numerator=10 if arm=='A' else 7 if arm=='B' else 6,denominator=1),
                quantity=10 if arm=='A' else 7 if arm=='B' else 6,billed_atomic=10 if arm=='A' else 7 if arm=='B' else 6)
            charge['components']={'other':charge['billed_atomic']};charge['operation_key'].update(invocation_ordinal=invocation,binding_index=0)
            scenarios.append(charge);rows.append(dict(invocation_ordinal=invocation,lane_id='answer',call_ordinal=0,
                text='actual synthetic fixture answer',usage=None,synthetic_receipt_sha256=digest(charge)))
    responses=dict(schema_version=1,kind='fixture_completions',rows=rows)
    u.update(schema_version=2,evaluation_mode='matched_source_exposure_full_lifetime_v2',comparison_plan_sha256=psha,
        latency_policy_sha256=digest(l),accounting_policy_sha256=digest(k),numeric_policy_sha256=digest(e),recordings=policies)
    u['adapters'][0]['config'].update(responses_sha256=digest(responses),settlement='synthetic_explicit')
    for arm in u['arms']:
        first=arm['recording_policies'][0];arm['recording_policies']=[]
        for record in records:
            policy=deepcopy(first);policy['recording_id']=record['recording_id'];arm['recording_policies'].append(policy)
    c=d['collection'];c.update(comparison_plan_sha256=psha,runtime_policy_sha256=digest(u),recordings=records,invocations=invocations)
    c['capacity'].update(max_entries_per_run=4,max_reservations_per_run=16,max_events_per_run=64,max_chunks_per_run=8)
    for arm in c['arms']:
        arm['config_sha256']=digest(p['systems'][arm['arm']])
        for binding in arm['provider_bindings']:
            if binding['operation_kinds']==['semantic']:binding['config_sha256']=digest(u['adapters'][0]['config'])
    q=d['scope_protocol'];q.update(schema_version=2,collection_sha256=digest(c),comparison_plan_sha256=psha,
        stream_protocol_sha256=digest(k),recording_reconciliation_sha256=digest(e),retain_financial_documents=True,scopes=[])
    for inv in invocations:
        task=tasks[inv['recording_index']]
        q['scopes'].extend([dict(invocation_ordinal=inv['ordinal'],scope_index=0,scope_kind='stream',task_id=None,input_sha256=None),
            dict(invocation_ordinal=inv['ordinal'],scope_index=1,scope_kind='task',task_id=task['task_id'],input_sha256=task['input_sha256'])])
    i=d['instrumentation_protocol'];i.update(schema_version=3,collection_sha256=digest(c),scope_protocol_sha256=digest(q))
    f=adapters();fdoc=dict(schema_version=1,kind='recording_financial_adapters',adapters=list(f.adapters))
    ds=[]
    for record in records:
        bundle=sources[record['recording_id']]
        ds.append(dict(plan=p,runtime_policy=u,collection=c,scope_protocol=q,instrumentation_protocol=i,
            source_manifest=bundle['manifest'],tasks=bundle['tasks'],profiles=bundle['profiles'],stream_protocol=k))
    return ds,l,sources,dict(opportunities=g,exposure_policy=e,financial_adapter_inventory=fdoc),responses,scenarios
