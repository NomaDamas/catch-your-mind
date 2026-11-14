"""Actual persistent source/SDK/fixture-completion composition, no model claims."""
import asyncio
from pathlib import Path
import tempfile
import unittest
from recording_abc_fixtures import build_runtime_fixture,installed_dependencies
from benchmarks.recording_runtime_inputs import OwnedRuntimeInputs
from benchmarks.recording_runtime_artifacts import RecordingRuntimeArtifacts,iter_outcome_rows
from benchmarks.recording_native_writer import RecordingNativeWriter,ArtifactBudget
from benchmarks.recording_native_schema import run_context
from benchmarks.recording_evaluation import RecordingEvaluationSession
from benchmarks.recording_arm_runtime import RecordingArmRuntime


class Arms(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):cls.dependencies=installed_dependencies()

    async def test_actual_startup_and_owned_cleanup(self):
        with tempfile.TemporaryDirectory(dir='.') as tmp:
            root=Path(tmp).resolve();(root/'inputs').mkdir()
            f=build_runtime_fixture(root/'inputs',count=20,duration_ns=2_000_000_000,dependency_evidence=self.dependencies)
            i=await OwnedRuntimeInputs.open(str(f.root),expected_execution_sha256=f.execution_sha256s[0],invocation_ordinal=0)
            d=i.receipt.declarations();a=await RecordingRuntimeArtifacts.open(root/'arm',f.documents['invocations/00/execution.json'],budget=ArtifactBudget(),retain_evaluation_artifacts=True)
            w=await RecordingNativeWriter.open(a.output/'native',run_context(d,'a'*64,0))
            o=RecordingEvaluationSession.from_runtime_frozen(d,w,latency_policy=f.documents['runtime/latency.json'],source_bundles=f.source_bundles,run_nonce='a'*64,execution_ordinal=0,retain_evaluation_hashes=True)
            r=None
            try:
                r=await RecordingArmRuntime.open(i,owner=o,artifacts=a)
                self.assertEqual(len(r.lanes),2)
                self.assertIsNone(r.clock)
                received=[]
                async def playback(*args):pass
                async def answer(*args):received.append(args)
                try:await r.start(playback_started=playback,answer_ready=answer)
                except Exception as error:self.fail(f"{error}: failures={r.failures}, perception={r.perception.failures}, results={r.task_runtime.result_values}")
                self.assertEqual(len(received),1)
                self.assertEqual(r.task_runtime.result_values[0]['status'],'answer')
                self.assertEqual(r.source.counters()[0]['captured'],3)
                self.assertFalse(r.failures)
            finally:
                if r:await r.close()
                await o.close();await a.abort();await i.close()
            self.assertTrue(r.human.closed)
            self.assertTrue(all(lane['adapter']._closed for lane in r.lanes.values()))


if __name__=='__main__':unittest.main()
