"""Prospective F1 originals for the actual owned ABC runtime (test-only).

Creates a second immutable input tree. The structural source tree, payloads,
questions and capture schedules are never rewritten. No real money/model claim.
"""
from copy import deepcopy
import hashlib
from pathlib import Path

from benchmarks.recording_native_schema import digest, encoded
from benchmarks.recording_runtime_finance import validate_runtime_charge_scenarios
from recording_abc_fixtures import RuntimeFixture
from test_matched_source_exposure import declarations
from test_recording_financial import adapters
from test_recording_settlement import scenario


def numeric_runtime_fixture(original, root):
    root = Path(root).resolve()
    if not root.is_dir() or root.is_symlink() or any(root.iterdir()):
        raise ValueError('empty caller-owned destination required')
    root.chmod(0o700)
    docs=deepcopy(original.documents);u=docs['runtime/policy.json'];c=docs['runtime/collection.json']
    p=docs['runtime/plan.json'];l=docs['runtime/latency.json'];q=docs['runtime/scopes.json'];i=docs['runtime/instrumentation.json']
    _,g,k,e=declarations(len(c['recordings']));g['comparison_plan_sha256']=digest(p);g['groups']=[]
    for n,record in enumerate(c['recordings']):
        bundle=original.source_bundles[record['recording_id']];m=bundle['manifest']
        g['groups'].append(dict(recording_id=record['recording_id'],source_manifest_sha256=digest(m),
            tasks_sha256=digest(bundle['tasks']),exposure_duration_ns=m['duration_ns'],sources=[dict(
                source_id=s['source_id'],sensor_id=s['sensor_id'],original_stream_epoch=s['stream_epoch'],
                format=s['format'],calibration_id=s['calibration_id'],record_count=len(rows),
                record_inventory_sha256=digest(rows),counter_contract='attempted_equals_captured_plus_dropped')
                for s in m['sources'] for rows in [[r for r in m['records'] if r['source_id']==s['source_id']]]],
            availability_sha256=digest(m['availability']),arm_order=[v['arm'] for v in c['invocations'] if v['recording_index']==n]))
    k.update(comparison_plan_sha256=digest(p),recordings_sha256=digest(g),currency_unit='fixture',rate_revision='1')
    # F1 explicitly charges every callback (semantic and signal) as perception.
    # Other ten-category requirements remain frozen explicit fixture N/A, never
    # a real machine-cost assertion or an inferred zero from process success.
    for component in k['components']:
        component['coverage']='event' if component['id']=='perception' else 'interval'
    k['streams']=[]
    for inv in c['invocations']:
        record=c['recordings'][inv['recording_index']];ordinal=inv['ordinal']
        k['streams'].append(dict(stream_id=inv['stream_id'],recording_id=record['recording_id'],arm=inv['arm'],
            source_manifest_sha256=record['source_manifest_sha256'],exposure_duration_ns=record['duration_ns'],
            execution_namespace='execution-'+str(ordinal),cache_namespace='cache-'+str(ordinal),isolation_policy_sha256='4'*64,
            requirements={comp['id']:dict(state='required' if comp['id']=='perception' else 'not_applicable',
                reason_code='synthetic_callback_only_fixture',justification_sha256=None if comp['id']=='perception' else '5'*64,
                lanes=[dict(resource_id='r-'+str(ordinal),lane_id='perception',coverage='whole_lifetime',
                    lifecycle_binding_id=None)] if comp['id']=='perception' else []) for comp in k['components']}))
    f=dict(schema_version=1,kind='recording_financial_adapters',adapters=list(adapters().adapters))
    k['financial_adapter_inventory_sha256']=digest(f)
    e.update(comparison_plan_sha256=digest(p),recordings_sha256=digest(g),latency_policy_sha256=digest(l),
             accounting_policy_sha256=digest(k),financial_adapter_inventory_sha256=digest(f))
    # max lateness is frozen up front; no capture timestamp is retimed to fit.
    e['source_policy']['max_acquisition_lateness_ns']=100_000_000
    responses=docs['responses/000.json'];scenarios=[]
    for row in responses['rows']:
        inv=c['invocations'][row['invocation_ordinal']];arm=next(a for a in u['arms'] if a['arm']==inv['arm'])
        lane=next(a for a in arm['lanes'] if a['lane_id']==row['lane_id'])
        bindings=next(a['provider_bindings'] for a in c['arms'] if a['arm']==inv['arm'])
        bi=next(n for n,b in enumerate(bindings) if b['binding_id']==lane['binding_id'])
        charge=scenario();amount=10 if inv['arm']=='A' else 1
        charge.update(account_scope='s',invoice_id=f"i-{inv['ordinal']}-{bi}-{row['call_ordinal']}",line_id='l',
            stream_id=inv['stream_id'],component_id='perception',resource_id='r-'+str(inv['ordinal']),lane_id='perception',
            currency_unit='fixture',pricing_revision='1',source_quantity=dict(numerator=amount,denominator=1),
            quantity=amount,billed_atomic=amount,components={'other':amount},
            operation_key=dict(invocation_ordinal=inv['ordinal'],binding_index=bi,call_ordinal=row['call_ordinal']))
        row['synthetic_receipt_sha256']=digest(charge);scenarios.append(charge)
    scenario_doc=dict(schema_version=1,kind='recording_synthetic_charge_scenarios',scenarios=scenarios)
    adapter=u['adapters'][0];adapter['config'].update(responses_sha256=digest(responses),settlement='synthetic_explicit')
    u.update(schema_version=2,evaluation_mode='matched_source_exposure_full_lifetime_v2',
             numeric_policy_sha256=digest(e),accounting_policy_sha256=digest(k))
    for arm in c['arms']:
        for binding in arm['provider_bindings']:
            if binding['operation_kinds']==['semantic']:binding['config_sha256']=digest(adapter['config'])
    c.update(runtime_policy_sha256=digest(u))
    # Joint declaration is conservative for this no-audio three-frame fixture;
    # all reservations/events/chunks remain collection bounded, never reset.
    c['capacity'].update(max_entries_per_run=8,max_reservations_per_run=16,max_events_per_run=128,max_chunks_per_run=4)
    q.update(schema_version=2,collection_sha256=digest(c),stream_protocol_sha256=digest(k),
             recording_reconciliation_sha256=digest(e),retain_financial_documents=True)
    i.update(schema_version=3,collection_sha256=digest(c),scope_protocol_sha256=digest(q),hello_timeout_ms=10000)
    docs.update({'runtime/accounting.json':k,'runtime/opportunities.json':g,'runtime/exposure.json':e,
                 'runtime/financial-adapters.json':f,'runtime/charge-scenarios.json':scenario_doc})
    validate_runtime_charge_scenarios(scenario_doc,runtime_policy=u,collection=c,responses=[responses],
        accounting_policy=k,financial_adapter_inventory=f)
    assets=docs['runtime/assets.json']
    for asset in assets['assets']:
        if asset['path']=='responses/000.json':
            data=encoded(responses)+b'\n';asset.update(sha256=hashlib.sha256(data).hexdigest(),bytes=len(data))
    docs['runtime/source-bundles.json'].update(collection_sha256=digest(c),runtime_policy_sha256=digest(u))
    shas=[]
    for inv in c['invocations']:
        execution=docs[f"invocations/{inv['ordinal']:02}/execution.json"]
        execution.update(runtime_policy_sha256=digest(u),collection_sha256=digest(c),scope_protocol_sha256=digest(q),
                         instrumentation_protocol_sha256=digest(i),asset_inventory_sha256=digest(assets))
        shas.append(digest(execution))
    for path,value in docs.items():
        target=root/path;target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('xb') as out:out.write(encoded(value)+b'\n')
    for n,record in enumerate(c['recordings']):
        for row in original.source_bundles[record['recording_id']]['manifest']['records']:
            path=f"recordings/{n:02}/payload/{row['payload_path']}";data=(original.root/path).read_bytes()
            if len(data)!=row['payload_bytes'] or hashlib.sha256(data).hexdigest()!=row['payload_sha256']:
                raise ValueError('original payload changed')
            target=root/path;target.parent.mkdir(parents=True,exist_ok=True)
            with target.open('xb') as out:out.write(data)
    return RuntimeFixture(root,tuple(shas),docs,deepcopy(original.source_bundles),original.dependency_inventory)
