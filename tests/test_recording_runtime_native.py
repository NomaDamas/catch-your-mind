"""Runtime profile entrypoint is separate from unchanged legacy admission."""
from copy import deepcopy
import unittest
from recording_native_fixtures import declarations, rehash
from test_recording_runtime_contract import fixture
from benchmarks.recording_native_schema import digest, validate_recording_scope_protocol
from benchmarks.recording_runtime_native import validate_runtime_scope_protocol


def runtime_declarations():
    u,p,l,bundles=fixture();bundle=bundles['original']
    # Build the native scope/collection graph from these exact originals.
    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory(dir='.') as path:d=declarations(Path(path))
    d.update(plan=p,runtime_policy=u,source_manifest=bundle['manifest'],tasks=bundle['tasks'],profiles=bundle['profiles'])
    c=d['collection'];c['runtime_policy_sha256']=digest(u)
    c['recordings']=[dict(recording_id='original',source_manifest_sha256=digest(bundle['manifest']),
        tasks_sha256=digest(bundle['tasks']),profiles_sha256=digest(bundle['profiles']),
        task_ids=[t['task_id'] for t in bundle['tasks']],duration_ns=bundle['manifest']['duration_ns'])]
    for arm,policy in zip(c['arms'],u['arms']):
        bindings=[]
        for index,lane in enumerate(policy['lanes']):
            bindings.append(dict(binding_id=lane['binding_id'],provider='test.fixture',model_revision='1',
                role='text_llm' if lane['role']=='text_answer' else 'small_vlm',
                config_sha256=digest(u['adapters'][0]['config']),source_ids=['camera'],
                entry_boundary='async_client_callback',operation_kinds=['semantic'],semantic_lane=index))
        if arm['arm']!='A':
            bindings.append(dict(binding_id='vision',provider='fixture.bgr',model_revision='1',role='signal',
                config_sha256='d'*64,source_ids=['camera'],entry_boundary='in_process_backend',
                operation_kinds=['process'],semantic_lane=None))
        arm['provider_bindings']=bindings
        arm['config_sha256']=digest(p['systems'][arm['arm']])
    q=d['scope_protocol'];q['scopes']=[]
    for inv in c['invocations']:
        n=inv['ordinal'];q['scopes'].append(dict(invocation_ordinal=n,scope_index=0,scope_kind='stream',task_id=None,input_sha256=None))
        q['scopes'].extend(dict(invocation_ordinal=n,scope_index=i,scope_kind='task',task_id=t['task_id'],input_sha256=t['input_sha256'])
            for i,t in enumerate(bundle['tasks'],1))
    rehash(d)
    return d,l,bundles


class RuntimeNative(unittest.TestCase):
    def test_original_runtime_profiles_are_explicit_and_legacy_stays_strict(self):
        d,l,bundles=runtime_declarations()
        with self.assertRaises(ValueError):validate_recording_scope_protocol(d)
        checked=validate_runtime_scope_protocol(d,latency_policy=l,source_bundles=bundles)
        self.assertEqual(checked,d)
        for mutation in (
            lambda value:value['collection']['arms'][0]['provider_bindings'][0].update(model_revision='other'),
            lambda value:value['collection']['arms'][1]['provider_bindings'][0].update(config_sha256='0'*64),
            lambda value:value['collection']['arms'][2]['provider_bindings'].pop(),
        ):
            changed=deepcopy(d);mutation(changed);rehash(changed)
            with self.assertRaises(ValueError):validate_runtime_scope_protocol(changed,latency_policy=l,source_bundles=bundles)

    def test_altered_original_bundle_is_rejected_even_when_profile_shape_is_valid(self):
        d,l,bundles=runtime_declarations();other=deepcopy(bundles)
        other['original']['tasks'][0]['input']['question']='different question'
        with self.assertRaises(ValueError):validate_runtime_scope_protocol(d,latency_policy=l,source_bundles=other)
