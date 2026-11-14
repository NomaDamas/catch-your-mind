"""Explicit runtime-v2 declaration entrypoints; legacy native APIs stay strict.

These validators do not activate providers, certify assets or constitute the
owned-input admission receipt. Actual activation also requires source/asset,
clock, joint memory/artifact and fixed child transport preflight.
"""
from .recording_native_schema import (_validate_scope_protocol_common, digest,
    snapshot, keys)
from .recording_runtime_contract import validate_runtime_policy


def validate_runtime_scope_protocol(declarations, *, latency_policy, source_bundles):
    d=snapshot(declarations)
    if 'runtime_policy' not in d:raise ValueError('original runtime policy required')
    policy=validate_runtime_policy(d['runtime_policy'],comparison_plan=d['plan'],
        latency_policy=latency_policy,source_bundles=source_bundles)
    if policy.document()['schema_version']!=1:
        raise ValueError('U2 requires prospective numeric declaration validation')
    d=_validate_scope_protocol_common(d,runtime_profiles=True)
    c=d['collection'];u=policy.document()
    if c['runtime_policy_sha256']!=policy.sha256:
        raise ValueError('original collection must bind the validated runtime policy')
    if len(c['recordings'])!=len(u['recordings']):raise ValueError('complete original runtime recordings required')
    for original,upstream in zip(c['recordings'],u['recordings']):
        for field in ('recording_id','source_manifest_sha256','tasks_sha256','profiles_sha256'):
            if original[field]!=upstream[field]:raise ValueError('runtime recording order/identity differs from collection')
    _validate_runtime_bindings(d,u)
    return d


def _validate_runtime_bindings(d,u):
    for arm,policy in zip(d['collection']['arms'],u['arms']):
        if arm['arm']!=policy['arm']:raise ValueError('original ABC arm order required')
        bindings={b['binding_id']:b for b in arm['provider_bindings']}
        adapters={a['adapter_id']:a for a in u['adapters']}
        expected=set()
        for lane in policy['lanes']:
            bid=lane['binding_id'];expected.add(bid)
            if bid not in bindings:raise ValueError('missing original semantic provider binding')
            binding=bindings[bid];adapter=adapters[lane['adapter_id']]
            role='text_llm' if lane['role']=='text_answer' else 'strong_vlm' if lane['role']=='fill_strong' else 'small_vlm'
            boundary='process_adapter' if adapter['implementation']=='smolvlm_process_v1' else 'async_client_callback'
            if (binding['provider'],binding['model_revision'],binding['role'],binding['entry_boundary'],binding['operation_kinds']) != (
                    adapter['provider'],adapter['model_revision'],role,boundary,['semantic']):
                raise ValueError('actual semantic adapter differs from original binding')
            if binding['semantic_lane']!=policy['lanes'].index(lane):
                raise ValueError('semantic lane ordinal differs from frozen policy')
            # Adapter config identity is canonical, not a provider/model alias.
            if adapter['implementation']!='smolvlm_process_v1' and binding['config_sha256']!=digest(adapter['config']):
                raise ValueError('semantic adapter configuration digest mismatch')
        for recording in policy['recording_policies']:
            for delivery in recording['deliveries']:
                if delivery['binding_id'] is not None:expected.add(delivery['binding_id'])
            fill=recording['fill_chain']
            if fill is not None:
                # The direct fill computation binding is resolved by its fixed
                # source/backend identity, never guessed from callback timing.
                fill_bindings=[b for b in bindings.values() if b['operation_kinds']==['process'] and
                    b['entry_boundary']=='in_process_backend' and b['config_sha256']==fill['fill_config_sha256'] and
                    fill['source_id'] in b['source_ids']]
                if len(fill_bindings)!=1:raise ValueError('one exact direct fill computation binding required')
                expected.add(fill_bindings[0]['binding_id'])
        if expected!=set(bindings):raise ValueError('unused or missing original runtime provider binding')
