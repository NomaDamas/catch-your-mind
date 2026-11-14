"""Owned parent observations; all providers here are synthetic fixtures."""
import asyncio
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from recording_abc_fixtures import build_runtime_fixture,installed_dependencies
from benchmarks.recording_coordinator import _preflight,_run_one,_receipt,_retained_bytes
from benchmarks.recording_runtime_inputs import OwnedRuntimeInputs
from benchmarks.recording_runtime_artifacts import read_ref,iter_outcome_rows
from benchmarks.recording_native_schema import digest

class Coordinator(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):cls.dependencies=installed_dependencies()

    async def asyncSetUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir='.');self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name).resolve();(self.root/'inputs').mkdir();(self.root/'stage').mkdir();(self.root/'runs').mkdir()
        self.fixture=build_runtime_fixture(self.root/'inputs',count=20,duration_ns=2_000_000_000,task_snapshot_ns=1_500_000_000,dependency_evidence=self.dependencies)
        self.inputs=await OwnedRuntimeInputs.open(str(self.fixture.root),expected_execution_sha256=self.fixture.execution_sha256s[0],invocation_ordinal=0)
        self.addAsyncCleanup(self.inputs.close)

    async def test_actual_fixed_child_two_channels_original_import_and_parent_receipt(self):
        docs,bundles,declarations,bounds,budget=await _preflight(self.inputs)
        self.assertLess(budget.used,budget.limit)
        ref,run,inventory,activation=await _run_one(str(self.fixture.root),self.root/'stage/00',self.root/'runs/00',docs,bundles,declarations,budget,docs['runtime/collection.json']['invocations'][0],retain_financial_documents=False)
        self.assertEqual(run['state'],'closed',run)
        final=self.root/'runs/00';stage=self.root/'stage/00'
        self.assertEqual(read_ref(final,ref),run)
        receipt=read_ref(final,run['receipts'][0]);self.assertIn(receipt['status'],('answer','late_answer'))
        self.assertGreaterEqual(receipt['received_ns'],0)
        self.assertTrue(read_ref(final,run['native_inventory'])['parent_reaped'])
        self.assertTrue(run['process_reaped_ns']<=run['parent_resources_closed_ns'])
        self.assertEqual((stage/'source/journal.jsonl').read_bytes(),(final/'source/journal.jsonl').read_bytes())
        self.assertEqual((stage/'tasks/task-0000-result.json').read_bytes(),(final/'tasks/task-0000-result.json').read_bytes())
        self.assertEqual(receipt['result_sha256'],hashlib.sha256((final/'tasks/task-0000-result.json').read_bytes()).hexdigest())
        rows=list(iter_outcome_rows(final,run['channel_outcomes'],execution_sha256=digest(docs['invocations/00/execution.json']),kind='channels'))
        self.assertEqual(len(rows),4);self.assertTrue(all(row['state']=='closed' for row in rows),rows)
        self.assertGreater(_retained_bytes(self.root/'runs',budget.limit),0)

    async def test_spawn_failure_retains_parent_only_unknown_inventory_and_original_task_floor(self):
        docs,bundles,declarations,bounds,budget=await _preflight(self.inputs)
        with patch('asyncio.create_subprocess_exec',side_effect=OSError('synthetic spawn refusal')):
            ref,run,inventory,activation=await _run_one(str(self.fixture.root),self.root/'stage/00',self.root/'runs/00',docs,bundles,declarations,budget,docs['runtime/collection.json']['invocations'][0],retain_financial_documents=False)
        self.assertEqual(run['state'],'failed');self.assertIsNone(run['process_reaped_ns'])
        native=read_ref(self.root/'runs/00',run['native_inventory'])
        self.assertFalse(native['parent_reaped']);self.assertIsNone(native['terminal_sha256'])
        receipt=read_ref(self.root/'runs/00',run['receipts'][0]);task=declarations[0]['tasks'][0]
        self.assertEqual(receipt['status'],'not_executed');self.assertEqual(receipt['latency_ns'],task['deadline_ns']-task['opens_ns'])
        self.assertIsNone(receipt['received_ns'])

    async def test_cancellation_during_owned_spawn_joins_child_before_return(self):
        docs,bundles,declarations,bounds,budget=await _preflight(self.inputs)
        real=asyncio.create_subprocess_exec;spawned=asyncio.Event();children=[]
        async def held(*args,**kwargs):
            process=await real(*args,**kwargs);children.append(process);spawned.set()
            await asyncio.sleep(.05)
            return process
        with patch('asyncio.create_subprocess_exec',side_effect=held):
            task=asyncio.create_task(_run_one(str(self.fixture.root),self.root/'stage/00',self.root/'runs/00',docs,bundles,declarations,budget,docs['runtime/collection.json']['invocations'][0],retain_financial_documents=False))
            await spawned.wait();task.cancel();await asyncio.sleep(.01);task.cancel()
            with self.assertRaises(asyncio.CancelledError):await asyncio.wait_for(asyncio.shield(task),8)
        self.assertIsNotNone(children[0].returncode)
        import json
        run=json.loads((self.root/'runs/00/run-inventory.json').read_bytes())
        self.assertEqual(run['state'],'failed');self.assertIsNotNone(run['process_reaped_ns'])
        self.assertTrue(read_ref(self.root/'runs/00',run['native_inventory'])['parent_reaped'])


class Receipt(unittest.TestCase):
    def test_failure_floor_and_late_answer_keep_original_clock(self):
        task=dict(task_id='task',input_sha256='a'*64,opens_ns=20,deadline_ns=120)
        value=_receipt('b'*64,task,anchor=1000,failed_ns=1400,reason='backend_failed')
        self.assertEqual(value['latency_ns'],380)
        result=dict(status='answer',answer_sha256='c'*64)
        late=_receipt('b'*64,task,anchor=1000,result=result,result_sha256='d'*64,received_ns=1300)
        self.assertEqual(late['status'],'late_answer');self.assertEqual(late['latency_ns'],280)
        with self.assertRaises(ValueError):_receipt('b'*64,task,anchor=1000,result=result,result_sha256='d'*64,received_ns=1019)

if __name__=='__main__':unittest.main()

class ActivationPreflight(unittest.TestCase):
    def test_credentials_cannot_restore_loader_search_paths(self):
        from benchmarks.recording_coordinator import _environment
        for name in ('PYTHONPATH','PYTHONHOME','PYTHONSTARTUP','LD_PRELOAD','DYLD_INSERT_LIBRARIES',
                     'PATH','HOME','BASH_ENV','TMPDIR','GAMST_RECORDING_FD_V2','OPENSSL_CONF','VIRTUAL_ENV','HF_HOME','SSL_CERT_FILE'):
            with self.subTest(name=name),patch.dict('os.environ',{name:'synthetic-not-a-secret'},clear=True):
                with self.assertRaises(ValueError):_environment({'adapters':[{'config':{'api_key_env':name}}]})
        with patch.dict('os.environ',{'LOCAL_API_KEY':'synthetic','PYTHONPATH':'forbidden','LD_PRELOAD':'forbidden'},clear=True):
            env=_environment({'adapters':[{'config':{'api_key_env':'LOCAL_API_KEY'}}]})
        self.assertEqual(env,{'LOCAL_API_KEY':'synthetic'})

    def test_selected_smol_timeout_added_once_before_activation(self):
        from benchmarks.recording_coordinator import _startup_budget_ns
        docs={'runtime/collection.json':{'recordings':[{'recording_id':'r'}]},
              'runtime/policy.json':{'adapters':[
                  {'adapter_id':'worker','implementation':'smolvlm_process_v1','config':{'startup_timeout_ms':120000}},
                  {'adapter_id':'unused','implementation':'smolvlm_process_v1','config':{'startup_timeout_ms':120000}}],
                  'arms':[{'arm':'A','lanes':[{'lane_id':'vision','adapter_id':'worker'}],
                           'recording_policies':[{'recording_id':'r','periodic':{'lane_id':'vision'}}]}]}}
        invocation={'arm':'A','recording_index':0}
        self.assertEqual(_startup_budget_ns(docs,invocation),150_000_000_000)
        docs['runtime/policy.json']['arms'][0]['recording_policies'][0]['periodic']=None
        self.assertEqual(_startup_budget_ns(docs,invocation),30_000_000_000)


class ExplicitRetention(unittest.IsolatedAsyncioTestCase):
    async def test_omitted_consent_rejects_before_input_or_output_activation(self):
        from benchmarks.recording_coordinator import run_recording_collection
        with tempfile.TemporaryDirectory(dir='.') as temporary:
            root=Path(temporary).resolve()
            with patch.object(OwnedRuntimeInputs,'open',side_effect=AssertionError('input activation')):
                with self.assertRaises(PermissionError):
                    await run_recording_collection(root/'missing',root/'output',expected_execution_sha256='0'*64)
            self.assertFalse((root/'output').exists())

class JoinWorkspaceAdmission(unittest.TestCase):
    def test_retained_prior_runs_are_not_reset_between_invocations(self):
        from benchmarks.recording_coordinator import _admit_join_workspace
        mib=1024**2
        admitted=_admit_join_workspace(20*mib,[dict(peak_workspace_bytes=40*mib,retained_workspace_bytes=10*mib)]*6)
        self.assertEqual(admitted['peak_workspace_bytes'],110*mib)
        self.assertEqual(admitted['retained_workspace_bytes'],60*mib)
        with self.assertRaises(ValueError):_admit_join_workspace(150*mib,[dict(peak_workspace_bytes=80*mib,retained_workspace_bytes=30*mib)]*2)
        with self.assertRaises(ValueError):_admit_join_workspace(0,[dict(peak_workspace_bytes=1,retained_workspace_bytes=65*mib)]*2)
