"""Real recorded fill measurement/reinspection/strong path; model text is synthetic."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from recording_abc_fixtures import build_runtime_fixture,installed_dependencies
from benchmarks.recording_runtime_inputs import OwnedRuntimeInputs
from benchmarks.recording_runtime_artifacts import RecordingRuntimeArtifacts,validate_fill_case
from benchmarks.recording_native_writer import RecordingNativeWriter,ArtifactBudget
from benchmarks.recording_native_schema import run_context
from benchmarks.recording_runtime_native import preflight_runtime_collection
from benchmarks.recording_evaluation import RecordingEvaluationSession
from benchmarks.recording_arm_runtime import RecordingArmRuntime


@unittest.skipUnless(all(importlib.util.find_spec(n) for n in ('numpy','cv2')),
                     'existing optional vision dependencies required')
class FillRuntime(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):cls.dependencies=installed_dependencies()

    async def test_actual_recorded_small_retry_strong_preserves_unknown_liability(self):
        with tempfile.TemporaryDirectory(dir='.') as temporary:
            root=Path(temporary).resolve();(root/'inputs').mkdir()
            f=build_runtime_fixture(root/'inputs',count=24,duration_ns=2_000_000_000,
                task_snapshot_ns=1_500_000_000,include_fill=True,dependency_evidence=self.dependencies)
            preflight=preflight_runtime_collection([f.declarations(n) for n in range(24)],
                latency_policy=f.documents['runtime/latency.json'],source_bundles=f.source_bundles)
            self.assertLess(preflight['predicted_artifact_bytes'],4*1024**3)
            ordinal=2
            inputs=await OwnedRuntimeInputs.open(str(f.root),expected_execution_sha256=f.execution_sha256s[ordinal],invocation_ordinal=ordinal)
            d=inputs.receipt.declarations()
            artifacts=await RecordingRuntimeArtifacts.open(root/'arm',f.documents['invocations/02/execution.json'],
                budget=ArtifactBudget(),retain_evaluation_artifacts=True)
            writer=await RecordingNativeWriter.open(artifacts.output/'native',run_context(d,'a'*64,ordinal))
            owner=RecordingEvaluationSession.from_runtime_frozen(d,writer,
                latency_policy=f.documents['runtime/latency.json'],source_bundles=f.source_bundles,
                run_nonce='a'*64,execution_ordinal=ordinal,retain_evaluation_hashes=True)
            runtime=None
            try:
                runtime=await RecordingArmRuntime.open(inputs,owner=owner,artifacts=artifacts)
                received=[]
                async def playback(*args):pass
                async def answer(*args):received.append(args)
                try:await runtime.start(playback_started=playback,answer_ready=answer)
                except Exception as error:
                    self.fail(f'{error}: failures={runtime.failures}, perception={runtime.perception.failures}, tasks={runtime.task_runtime.result_values}')
                cases=list((artifacts.output/'fill').glob('case-*.json'))
                self.assertEqual(len(cases),1)
                case=json.loads(cases[0].read_bytes());validate_fill_case(case,artifacts.execution_sha256)
                self.assertEqual(case['outcome'],'resolved_under_rule')
                self.assertEqual([r['stage'] for r in case['stages']],['initial','reinspection','strong'])
                self.assertTrue(all(r['operation_instance'] for r in case['stages']))
                self.assertEqual(len({r['operation_instance'] for r in case['stages']}),3)
                self.assertEqual(case['stages'][1]['predecessor_instance'],case['stages'][0]['operation_instance'])
                self.assertEqual(case['stages'][2]['predecessor_instance'],case['stages'][1]['operation_instance'])
                budget=runtime.controllers['fill'].snapshot()['budget']
                self.assertEqual(budget['spent_known'],0)
                self.assertEqual(budget['reserved_liability'],15)
                self.assertEqual(budget['unresolved_dispatched'],3)
                self.assertEqual(len(received),1)
                self.assertEqual(runtime.task_runtime.result_values[0]['status'],'answer')
            finally:
                if runtime is not None:await runtime.close()
                await owner.close();await artifacts.abort();await inputs.close()
            self.assertTrue(runtime.human.closed)
