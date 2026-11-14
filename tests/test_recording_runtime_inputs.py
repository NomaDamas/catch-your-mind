"""Owned metadata loader; actual fixed files, descriptors and cancellation."""
import asyncio
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from benchmarks.recording_native_schema import CAPS,digest,encoded
from benchmarks.recording_runtime_inputs import OwnedRuntimeInputs,RuntimeInputReceipt
import benchmarks.recording_runtime_inputs as inputs
from test_recording_runtime_contract import fixture as policy_fixture


def fixture(root,count=20):
    u,p,l,bundles=policy_fixture();base=next(iter(bundles.values()))
    original=deepcopy(p['comparison']['tasks'][0]);p['comparison']['tasks']=[]
    arms=deepcopy(u['arms']);u['recordings']=[]
    for arm in arms:arm['recording_policies']=[]
    allbundles={};crows=[]
    budget=dict(unit='fixture',pricing_revision='1',ceiling=100,max_calls=256,max_inflight=4,receipt_limit=128)
    config=dict(delay_ms=0)
    responses=dict(schema_version=1,kind='fixture_completions',rows=[])
    u['adapters'][0]['config']['responses_sha256']=digest(responses)
    for n in range(count):
        rid=f'original-{n}';bundle=deepcopy(base);bundle['manifest']['recording_id']=rid
        task=deepcopy(bundle['tasks'][0]);task['task_id']=str(n);bundle['tasks']=[task]
        plan_task=deepcopy(original);plan_task['id']=str(n);plan_task['input_sha256']=task['input_sha256'];p['comparison']['tasks'].append(plan_task)
        profiles=bundle['profiles'];profiles['recording_id']=rid;profiles['source_manifest_sha256']=digest(bundle['manifest'])
        declaration=deepcopy(policy_fixture()[0]['recordings'][0]);declaration.update(recording_id=rid,source_manifest_sha256=digest(bundle['manifest']),tasks_sha256=digest(bundle['tasks']))
        for a,arm in zip(profiles['arms'],arms):
            a['deliveries'][0]['config_sha256']=None if a['arm']=='A' else digest(config)
            policy=deepcopy(policy_fixture()[0]['arms']['ABC'.index(arm['arm'])]['recording_policies'][0]);policy['recording_id']=rid
            policy['deliveries']=deepcopy(a['deliveries']);arm['recording_policies'].append(policy)
            for controller in arm['controllers']:controller['budget_sha256']=digest(budget)
        declaration['profiles_sha256']=digest(profiles);u['recordings'].append(declaration);allbundles[rid]=bundle
        crows.append(dict(recording_id=rid,source_manifest_sha256=digest(bundle['manifest']),tasks_sha256=digest(bundle['tasks']),profiles_sha256=digest(profiles),task_ids=[str(n)],duration_ns=bundle['manifest']['duration_ns']))
    u['arms']=arms;u['comparison_plan_sha256']=digest(p);l['comparison_plan_sha256']=digest(p);u['latency_policy_sha256']=digest(l)
    collection=dict(schema_version=2,kind='recording_collection',comparison_plan_sha256=digest(p),runtime_policy_sha256=digest(u),recordings=crows,arms=[],invocations=[],capacity=dict(CAPS,max_entries_per_run=4,max_events_per_run=64,max_chunks_per_run=8))
    for arm in arms:
        bs=[]
        for n,lane in enumerate(arm['lanes']):
            bs.append(dict(binding_id=lane['binding_id'],provider='test.fixture',model_revision='1',role='text_llm' if lane['role']=='text_answer' else 'small_vlm',config_sha256=digest(u['adapters'][0]['config']),source_ids=['camera'],entry_boundary='async_client_callback',operation_kinds=['semantic'],semantic_lane=n))
        if arm['arm']!='A':bs.append(dict(binding_id='vision',provider='fixture.bgr',model_revision='1',role='signal',config_sha256=digest(config),source_ids=['camera'],entry_boundary='in_process_backend',operation_kinds=['process'],semantic_lane=None))
        collection['arms'].append(dict(arm=arm['arm'],config_sha256=digest(p['systems'][arm['arm']]),provider_bindings=bs))
    for n in range(count):
        for arm in 'ABC':collection['invocations'].append(dict(ordinal=len(collection['invocations']),recording_index=n,arm=arm,stream_id=f'stream-{n}-{arm}'))
    scopes=[]
    for inv in collection['invocations']:
        scopes.extend([dict(invocation_ordinal=inv['ordinal'],scope_index=0,scope_kind='stream',task_id=None,input_sha256=None),dict(invocation_ordinal=inv['ordinal'],scope_index=1,scope_kind='task',task_id=str(inv['recording_index']),input_sha256=p['comparison']['tasks'][inv['recording_index']]['input_sha256'])])
    q=dict(schema_version=1,kind='recording_scope_protocol',collection_sha256=digest(collection),comparison_plan_sha256=digest(p),stream_protocol_sha256=None,allocation_protocol_sha256=None,recording_reconciliation_sha256=None,cost_card_sha256=None,retention_policy='explicit_external_evaluation_hashes',retain_financial_documents=False,scopes=scopes)
    i=dict(schema_version=2,kind='recording_instrumentation',scope_protocol_sha256=digest(q),collection_sha256=digest(collection),hello_timeout_ms=1000,close_timeout_ms=1000,fd_environment_key='GAMST_RECORDING_FD_V2')
    def file(path,value):
        data=encoded(value)+b'\n';target=root/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
        return dict(path=path,file_sha256=hashlib.sha256(data).hexdigest(),bytes=len(data))
    configref=file('configurations/000.json',config);responseref=file('responses/000.json',responses);file('budgets/000.json',budget)
    assets=dict(schema_version=1,kind='recording_runtime_assets',assets=[dict(asset_id='vision-config',kind='provider_config',path=configref['path'],sha256=configref['file_sha256'],bytes=configref['bytes']),dict(asset_id='fixture-responses',kind='fixture_responses',path=responseref['path'],sha256=responseref['file_sha256'],bytes=responseref['bytes'])],dependencies=[],resident_state=[])
    documents=dict(policy=u,plan=p,latency=l,collection=collection,scopes=q,instrumentation=i,assets=assets)
    for key,value in documents.items():file('runtime/'+key+'.json',value)
    index=dict(schema_version=1,kind='recording_runtime_input_sources',collection_sha256=digest(collection),runtime_policy_sha256=digest(u),recordings=[])
    for n,(rid,bundle) in enumerate(allbundles.items()):
        row=dict(recording_id=rid,recording_index=n)
        for kind in ('manifest','tasks','profiles'):row[kind]=file(f'recordings/{n:02}/{kind}.json',bundle[kind])
        payload=root/f'recordings/{n:02}/payload';payload.mkdir();(payload/'frame.bin').write_bytes(bytes(32*32*3))
        index['recordings'].append(row)
    file('runtime/source-bundles.json',index)
    selected=None
    for inv in collection['invocations']:
        execution=dict(schema_version=1,kind='recording_execution',runtime_policy_sha256=digest(u),collection_sha256=digest(collection),scope_protocol_sha256=digest(q),instrumentation_protocol_sha256=digest(i),invocation_ordinal=inv['ordinal'],recording_index=inv['recording_index'],arm=inv['arm'],stream_id=inv['stream_id'],execution_namespace='execution-'+str(inv['ordinal']),cache_namespace='cache-'+str(inv['ordinal']),asset_inventory_sha256=digest(assets))
        file(f"invocations/{inv['ordinal']:02}/execution.json",execution)
        if inv['ordinal']==0:selected=execution
    return digest(selected)


def numeric_fixture(root):
    fixture(root,20)
    from test_matched_source_exposure import declarations
    _,g,k,e=declarations(20)
    from test_recording_financial import adapters
    f=dict(schema_version=1,kind='recording_financial_adapters',adapters=[dict(a) for a in adapters().adapters])
    docs={str(path.relative_to(root)):json.loads(path.read_bytes()) for path in root.rglob('*.json')}
    u=docs['runtime/policy.json'];c=docs['runtime/collection.json'];p=docs['runtime/plan.json'];q=docs['runtime/scopes.json'];i=docs['runtime/instrumentation.json']
    # The synthetic fixture keeps20 distinct original manifest identities and
    # exactly the same original tasks; no tasks become independent recordings.
    g['comparison_plan_sha256']=digest(p)
    for n,(group,original) in enumerate(zip(g['groups'],c['recordings'])):
        m=docs[f'recordings/{n:02}/manifest.json'];tasks=docs[f'recordings/{n:02}/tasks.json']
        group.update(recording_id=original['recording_id'],source_manifest_sha256=digest(m),tasks_sha256=digest(tasks),exposure_duration_ns=m['duration_ns'],availability_sha256=digest(m['availability']),arm_order=['A','B','C'])
        group['sources']=[]
        for source in m['sources']:
            records=[r for r in m['records'] if r['source_id']==source['source_id']]
            group['sources'].append(dict(source_id=source['source_id'],sensor_id=source['sensor_id'],original_stream_epoch=source['stream_epoch'],format=source['format'],calibration_id=source['calibration_id'],record_count=len(records),record_inventory_sha256=digest(records),counter_contract='attempted_equals_captured_plus_dropped'))
    k.update(comparison_plan_sha256=digest(p),recordings_sha256=digest(g))
    for n,inv in enumerate(c['invocations']):
        row=k['streams'][n];original=c['recordings'][inv['recording_index']]
        row.update(stream_id=inv['stream_id'],recording_id=original['recording_id'],source_manifest_sha256=original['source_manifest_sha256'],exposure_duration_ns=original['duration_ns'],execution_namespace='execution-'+str(n),cache_namespace='cache-'+str(n))
    e.update(comparison_plan_sha256=digest(p),recordings_sha256=digest(g),latency_policy_sha256=digest(docs['runtime/latency.json']),accounting_policy_sha256=digest(k))
    u.update(schema_version=2,accounting_policy_sha256=digest(k),numeric_policy_sha256=digest(e),evaluation_mode='matched_source_exposure_full_lifetime_v2')
    c['runtime_policy_sha256']=digest(u)
    q.update(schema_version=2,collection_sha256=digest(c),stream_protocol_sha256=digest(k),recording_reconciliation_sha256=digest(e))
    i.update(schema_version=3,collection_sha256=digest(c),scope_protocol_sha256=digest(q))
    docs.update({'runtime/accounting.json':k,'runtime/opportunities.json':g,'runtime/exposure.json':e,'runtime/financial-adapters.json':f})
    docs['runtime/source-bundles.json'].update(collection_sha256=digest(c),runtime_policy_sha256=digest(u))
    for n in range(len(c['invocations'])):
        docs[f'invocations/{n:02}/execution.json'].update(runtime_policy_sha256=digest(u),collection_sha256=digest(c),scope_protocol_sha256=digest(q),instrumentation_protocol_sha256=digest(i))
    for path,value in docs.items():(root/path).write_bytes(encoded(value)+b'\n')
    return digest(docs['invocations/00/execution.json'])


class Inputs(unittest.IsolatedAsyncioTestCase):
    def root(self):
        directory=tempfile.TemporaryDirectory(dir='.');self.addCleanup(directory.cleanup)
        root=Path(directory.name).absolute();root.chmod(0o700);return root

    async def test_twenty_original_recordings_and_same_native_originals(self):
        root=self.root();expected=fixture(root)
        async with await OwnedRuntimeInputs.open(str(root),expected_execution_sha256=expected,invocation_ordinal=0) as owned:
            self.assertEqual(len(owned.receipt.source_bundles()),20)
            self.assertEqual(owned.receipt.documents()['runtime/plan.json']['comparison']['min_pairs'],20)
            self.assertEqual(owned.workspace_bytes,128*owned.metadata_bytes)
            self.assertLess(owned.workspace_bytes,256*1024**2)
            self.assertEqual(owned.receipt.identities['execution_sha256'],expected)
            declarations=owned.receipt.declarations();self.assertEqual(declarations['source_manifest']['recording_id'],'original-0')
            mapping=dict(plan='runtime/plan.json',collection='runtime/collection.json',scope_protocol='runtime/scopes.json',instrumentation_protocol='runtime/instrumentation.json',runtime_policy='runtime/policy.json',source_manifest='recordings/00/manifest.json',tasks='recordings/00/tasks.json',profiles='recordings/00/profiles.json')
            owned.validate_native_paths({k:str(root/v) for k,v in mapping.items()})
            fd=owned.duplicate_payload_root('original-0')
            try:self.assertFalse(os.get_inheritable(fd));self.assertEqual(os.fstat(fd).st_ino,(root/'recordings/00/payload').stat().st_ino)
            finally:os.close(fd)
            with self.assertRaises(TypeError):RuntimeInputReceipt(owned)
        self.assertEqual(owned.workspace_bytes,0)
        with self.assertRaises(RuntimeError):owned.receipt.documents()

    async def test_fifo_ancestor_symlink_and_extra_metadata_reject_without_decode(self):
        root=self.root();fixture(root,1);fifo=root/'runtime/extra.json';os.mkfifo(fifo)
        with patch.object(inputs,'_decode',side_effect=AssertionError('parsed unsafe file')):
            with self.assertRaises(ValueError):await OwnedRuntimeInputs.open(str(root),expected_execution_sha256='a'*64,invocation_ordinal=0)
        fifo.unlink();alias=root/'alias';alias.symlink_to(root/'runtime',target_is_directory=True)
        with self.assertRaises(OSError):await OwnedRuntimeInputs.open(str(alias),expected_execution_sha256='a'*64,invocation_ordinal=0)
        alias.unlink();(root/'runtime/unlisted.json').write_text('{}\n')
        with self.assertRaises(ValueError):await OwnedRuntimeInputs.open(str(root),expected_execution_sha256='a'*64,invocation_ordinal=0)

    async def test_metadata_mutation_and_noncanonical_bytes_reject(self):
        root=self.root();expected=fixture(root,1);original=inputs._read;done=False
        def mutated(fd,path,identity):
            nonlocal done
            data=original(fd,path,identity)
            if not done:
                done=True;(root/path).write_bytes(data)
            return data
        with patch.object(inputs,'_read',side_effect=mutated):
            with self.assertRaisesRegex(ValueError,'mutated'):await OwnedRuntimeInputs.open(str(root),expected_execution_sha256=expected,invocation_ordinal=0)
        p=root/'runtime/plan.json';p.write_bytes(b' '+p.read_bytes())
        with self.assertRaisesRegex(ValueError,'canonical'):await OwnedRuntimeInputs.open(str(root),expected_execution_sha256=expected,invocation_ordinal=0)

    async def test_cancel_joins_actual_read_before_closing_owned_fds(self):
        root=self.root();expected=fixture(root,1);entered=threading.Event();release=threading.Event();original=inputs._read
        def blocked(*args):entered.set();release.wait(5);return original(*args)
        with patch.object(inputs,'_read',side_effect=blocked):
            task=asyncio.create_task(OwnedRuntimeInputs.open(str(root),expected_execution_sha256=expected,invocation_ordinal=0))
            self.assertTrue(await asyncio.to_thread(entered.wait,2));task.cancel();await asyncio.sleep(0);task.cancel()
            self.assertFalse(task.done());release.set()
            with self.assertRaises(asyncio.CancelledError):await task
        self.assertTrue(release.is_set())

    async def test_joint_workspace_and_lexical_depth_reject_before_json_conversion(self):
        root=self.root();path=root/'recordings/00/manifest.json';path.parent.mkdir(parents=True)
        path.write_bytes(b' '*(2*1024**2+1))
        with patch.object(inputs,'_decode',side_effect=AssertionError('decoded before joint quota')):
            with self.assertRaisesRegex(ValueError,'workspace'):await OwnedRuntimeInputs.open(str(root),expected_execution_sha256='a'*64,invocation_ordinal=0)
        with patch.object(inputs.json,'loads',side_effect=AssertionError('decoded before lexical bound')):
            with self.assertRaisesRegex(ValueError,'lexical depth'):inputs._decode(b'['*33+b']'*33+b'\n')

    async def test_native_same_content_alias_and_extra_payload_are_rejected(self):
        root=self.root();expected=fixture(root,1)
        async with await OwnedRuntimeInputs.open(str(root),expected_execution_sha256=expected,invocation_ordinal=0) as owned:
            d=owned.receipt.declarations();mapping=dict(plan='runtime/plan.json',collection='runtime/collection.json',scope_protocol='runtime/scopes.json',instrumentation_protocol='runtime/instrumentation.json',runtime_policy='runtime/policy.json',source_manifest='recordings/00/manifest.json',tasks='recordings/00/tasks.json',profiles='recordings/00/profiles.json')
            paths={k:str(root/v) for k,v in mapping.items()}
            alias=root/'runtime/copied-plan.json';alias.write_bytes((root/'runtime/plan.json').read_bytes());paths['plan']=str(alias)
            with self.assertRaisesRegex(ValueError,'same original'):owned.validate_native_paths(paths)
            alias.unlink()
        (root/'recordings/00/payload/unlisted.bin').write_bytes(b'x')
        with self.assertRaisesRegex(ValueError,'unlisted original payload'):await OwnedRuntimeInputs.open(str(root),expected_execution_sha256=expected,invocation_ordinal=0)

    async def test_prospective_numeric_inputs_require_exact_financial_adapter_inventory(self):
        root=self.root();expected=numeric_fixture(root)
        async with await OwnedRuntimeInputs.open(str(root),expected_execution_sha256=expected,invocation_ordinal=0) as owned:
            self.assertEqual(owned.receipt.declarations()['scope_protocol']['schema_version'],2)
            self.assertEqual(owned.receipt.documents()['runtime/instrumentation.json']['schema_version'],3)
            self.assertEqual(len(owned.receipt.source_bundles()),20)
        (root/'runtime/financial-adapters.json').unlink()
        with self.assertRaisesRegex(ValueError,'numeric original inputs'):await OwnedRuntimeInputs.open(str(root),expected_execution_sha256=expected,invocation_ordinal=0)
