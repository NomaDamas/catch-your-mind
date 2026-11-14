"""Actual failed-child continuation; frozen original collection is not projected."""
import asyncio
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from recording_abc_fixtures import build_runtime_fixture, installed_dependencies
from benchmarks import recording_coordinator as coordinator
from benchmarks.recording_runtime_artifacts import read_ref


class FailedCollection(unittest.IsolatedAsyncioTestCase):
    async def test_reaped_failed_first_child_retained_before_next_original_invocation(self):
        with tempfile.TemporaryDirectory(dir='.') as temporary:
            root=Path(temporary).resolve();(root/'inputs').mkdir()
            fixture=build_runtime_fixture(root/'inputs',count=20,duration_ns=2_000_000_000,
                task_snapshot_ns=1_500_000_000,dependency_evidence=installed_dependencies())
            real_spawn=asyncio.create_subprocess_exec;real_run=coordinator._run_one
            children=[];invocations=[]
            async def spawn(*args,**kwargs):
                child=await real_spawn(*args,**kwargs);children.append(child)
                if len(children)==1:
                    # This is our test's newly created recording child only.
                    child.terminate()
                return child
            async def run(*args,**kwargs):
                ordinal=args[7]['ordinal'];invocations.append(ordinal)
                if ordinal==2:raise asyncio.CancelledError('test stops after two original arms')
                return await real_run(*args,**kwargs)
            with patch('asyncio.create_subprocess_exec',spawn),patch.object(coordinator,'_run_one',run):
                with self.assertRaises(asyncio.CancelledError):
                    await coordinator.run_recording_collection(fixture.root,root/'output',
                        expected_execution_sha256=fixture.execution_sha256s[0])
            self.assertEqual(invocations,[0,1,2])
            self.assertEqual(len(children),2)
            self.assertTrue(all(child.returncode is not None for child in children))
            runs=[json.loads((root/f'output/runs/{n:02}/run-inventory.json').read_bytes()) for n in (0,1)]
            self.assertEqual(runs[0]['state'],'failed')
            self.assertIsNotNone(runs[0]['process_reaped_ns'])
            failed=read_ref(root/'output/runs/00',runs[0]['receipts'][0])
            self.assertIn(failed['status'],('failed','not_executed'))
            self.assertGreater(failed['latency_ns'],0)
            self.assertEqual(runs[1]['state'],'closed')
            answer=read_ref(root/'output/runs/01',runs[1]['receipts'][0])
            self.assertIn(answer['status'],('answer','late_answer'))
            self.assertIsNotNone(answer['received_ns'])
            self.assertFalse((root/'output/execution-inventory.json').exists())


if __name__=='__main__':unittest.main()
