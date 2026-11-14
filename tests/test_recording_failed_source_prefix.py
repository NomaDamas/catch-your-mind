"""Retained failed acquisition and financial originals remain validated."""
import asyncio
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from recording_abc_fixtures import build_runtime_fixture, installed_dependencies
from recording_runtime_numeric_fixtures import numeric_runtime_fixture
from benchmarks.recording_coordinator import _preflight, _run_one
from benchmarks.recording_runtime_inputs import OwnedRuntimeInputs
from benchmarks.recording_runtime_artifacts import read_ref
from benchmarks.recording_runtime_validation import validate_recording_run


SCRIPT = '''
import asyncio, sys
from benchmarks.recording_arm_runtime import RecordingArmRuntime
from benchmarks.recording_runtime_artifacts import RecordingRuntimeArtifacts
phase=sys.argv.pop(1)
if phase=='preflight':
    from benchmarks.owned_capture import OwnedCaptureSource
    async def refuse(*args, **kwargs): raise OSError('synthetic source preflight refusal')
    OwnedCaptureSource.preflight=refuse
original=RecordingRuntimeArtifacts.write_metadata
async def metadata(self, kind, value):
    if phase=='early' and kind=='mapping':
        # Actual acquired/provider work precedes this failed persistence.
        await asyncio.sleep(.25)
        raise OSError('synthetic mapping persistence refusal')
    return await original(self,kind,value)
RecordingRuntimeArtifacts.write_metadata=metadata
finalize=RecordingArmRuntime.finalize
async def finish(self, *args):
    if phase=='late':
        self._fail('source_failed')
        self.source_mappings_ref=None
    return await finalize(self,*args)
RecordingArmRuntime.finalize=finish
from benchmarks.recording_arm import main
raise SystemExit(main())
'''


class FailedSourcePrefix(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):cls.dependencies=installed_dependencies()

    async def test_failed_source_prefix_integrity_including_actual_u2_settlements(self):
        with tempfile.TemporaryDirectory(dir='.') as tmp:
            root=Path(tmp).resolve()
            for name in ('structural','numeric'):(root/name).mkdir()
            structural=build_runtime_fixture(root/'structural',count=20,duration_ns=1_400_000_000,
                task_snapshot_ns=900_000_000,dependency_evidence=self.dependencies)
            numeric=numeric_runtime_fixture(structural,root/'numeric')
            for ordinal,(fixture,phase) in enumerate(((structural,'early'),(numeric,'early'),(numeric,'late'),
                    (structural,'preflight'),(numeric,'preflight'))):
                inputs=await OwnedRuntimeInputs.open(str(fixture.root),expected_execution_sha256=fixture.execution_sha256s[ordinal],invocation_ordinal=ordinal)
                try:docs,bundles,declarations,_,budget=await _preflight(inputs)
                finally:await inputs.close()
                real_spawn=asyncio.create_subprocess_exec
                async def spawn(*args,**kw):return await real_spawn(args[0],'-c',SCRIPT,phase,*args[3:],**kw)
                with patch('asyncio.create_subprocess_exec',spawn):
                    _,run,token,activation=await _run_one(str(fixture.root),root/f'stage-{ordinal}',root/f'run-{ordinal}',
                        docs,bundles,declarations,budget,docs['runtime/collection.json']['invocations'][ordinal],
                        retain_financial_documents=fixture is numeric)
                directory=root/f'run-{ordinal}'
                def validate():return validate_recording_run(directory,documents=docs,source_bundles=bundles,
                    invocation_ordinal=ordinal,parent_native_inventory=token,activation_started_ns=activation)
                with self.subTest(phase=phase,numeric=fixture is numeric):
                    joined=validate()
                    self.assertEqual(run['state'],'failed')
                    self.assertFalse(joined.financial_values['source_comparable'])
                    self.assertIn('source_mapping_incomplete',joined.financial_values['violations'])
                    if phase=='preflight':
                        self.assertEqual(joined.source_coverage['actual_capture_count'],0)
                        self.assertEqual(joined.source_coverage['uninspected_count'],3)
                        self.assertEqual(joined.controller_settlements,[])
                        self.assertTrue(all(r['status']=='not_executed' for r in joined.task_receipts))
                        self.assertIsNone(run['child_summary'])
                        continue
                    self.assertGreater(joined.source_coverage['actual_capture_count'],0)
                    self.assertEqual(joined.source_coverage['mapping_sha256'],joined.native_index.terminal['mapping_sha256'])
                    if phase=='early':
                        self.assertIsNone(joined.financial_values['playback_anchor_ns'])
                        self.assertTrue(all(r['status']=='not_executed' for r in joined.task_receipts))
                    else:
                        self.assertGreater(len(joined.controller_settlements),0)
                        self.assertTrue(joined.financial_values['clock_consistent'])
                        self.assertTrue(any(r['status']=='answer' for r in joined.task_receipts))
                    # A retained journal, static declaration and financial
                    # inventory cannot bypass validation because capture is absent.
                    paths=['source/journal.jsonl','source/source-manifest.json']
                    if fixture is numeric:paths.append('source/controller-settlements.json')
                    for name in paths:
                        path=directory/name;original=path.read_bytes()
                        path.write_bytes(original+b' ')
                        try:
                            with self.assertRaises(ValueError,msg=name):validate()
                        finally:path.write_bytes(original)
                    summary=read_ref(directory,run['child_summary'])
                    self.assertIsNone(summary['capture_inventory'])
                    # Even an otherwise decoded publication cannot change the
                    # native mapping hash when no runtime mapping was persisted.
                    import benchmarks.recording_runtime_validation as validation
                    original_read=validation.read_publication;seen=[]
                    def corrupted(*args,**kwargs):
                        row,record=original_read(*args,**kwargs);seen.append(row)
                        row['source_mapping_sha256']='9'*64
                        return row,record
                    with patch.object(validation,'read_publication',corrupted):
                        if phase=='late':
                            with self.assertRaisesRegex(ValueError,'source mapping'):validate()
                        else:
                            try:validate()
                            except ValueError as error:self.assertIn('source mapping',str(error))
                    if phase=='late':self.assertTrue(seen)


if __name__=='__main__':unittest.main()
