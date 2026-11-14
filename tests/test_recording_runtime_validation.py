"""Original source/native/parent ownership joins; no actual model claims."""
import asyncio
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from recording_abc_fixtures import build_runtime_fixture, installed_dependencies
from benchmarks.recording_coordinator import _preflight, _run_one
from benchmarks.recording_runtime_inputs import OwnedRuntimeInputs
from benchmarks.recording_runtime_validation import ValidatedRecordingRun, validate_recording_run


class OriginalRunJoin(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls.dependencies = installed_dependencies()

    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir='.')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        for name in ('inputs', 'stage', 'runs'):
            (self.root / name).mkdir()
        self.fixture = build_runtime_fixture(self.root / 'inputs', count=20,
            duration_ns=2_000_000_000, dependency_evidence=self.dependencies)
        self.inputs = await OwnedRuntimeInputs.open(str(self.fixture.root),
            expected_execution_sha256=self.fixture.execution_sha256s[0], invocation_ordinal=0)
        self.addAsyncCleanup(self.inputs.close)
        self.docs, self.bundles, self.declarations, _, self.budget = await _preflight(self.inputs)

    async def run_one(self, *, spawn_failure=False):
        args = (str(self.fixture.root), self.root / 'stage/00', self.root / 'runs/00',
            self.docs, self.bundles, self.declarations, self.budget,
            self.docs['runtime/collection.json']['invocations'][0])
        if spawn_failure:
            with patch('asyncio.create_subprocess_exec', side_effect=OSError('fixture spawn refusal')):
                self.result = await _run_one(*args,retain_financial_documents=False)
        else:
            self.child_output=[]
            async def capture(stream,maximum):
                data=bytearray()
                while True:
                    block=await stream.read(65536)
                    if not block:break
                    if len(data)<maximum:data.extend(block[:maximum-len(data)])
                self.child_output.append(bytes(data).decode('utf-8','replace'))
            with patch('benchmarks.recording_coordinator._drain',capture):
                self.result = await _run_one(*args,retain_financial_documents=False)
        return self.result

    def validate(self, *, inventory=None, documents=None):
        _, _, token, activation = self.result
        return validate_recording_run(self.root / 'runs/00', documents=self.docs if documents is None else documents,
            source_bundles=self.bundles, invocation_ordinal=0,
            parent_native_inventory=token if inventory is None else inventory,
            activation_started_ns=activation)

    async def test_failed_spawn_keeps_original_arm_unknown_prefix_and_receipt_floor(self):
        await self.run_one(spawn_failure=True)
        joined = self.validate()
        self.assertIsNone(joined.native_index)
        self.assertIsNone(joined.financial_values['native_terminal_sha256'])
        self.assertEqual(len(joined.task_receipts), len(self.declarations[0]['tasks']))
        for key in ('source_comparable', 'operational_closed', 'external_work_closed'):
            self.assertFalse(joined.financial_values[key])
        self.assertIn('missing_native_prefix', joined.financial_values['violations'])
        self.assertEqual(joined.controller_settlements, [])
        copy = joined.execution
        copy['arm'] = 'B'
        self.assertEqual(joined.execution['arm'], 'A')
        with self.assertRaises(TypeError):
            self.validate(inventory=dict(self.result[2]))
        with self.assertRaises(TypeError):
            ValidatedRecordingRun({}, {}, [], {}, {}, [], None)
        changed = deepcopy(self.docs)
        changed['invocations/00/execution.json']['execution_namespace'] = 'different'
        with self.assertRaises(ValueError):
            self.validate(documents=changed)

    async def test_actual_child_source_sdk_native_response_and_parent_receipt_join(self):
        _, run, token, _ = await self.run_one()
        self.assertEqual(run['state'], 'closed', (run,self.child_output))
        joined = self.validate()
        self.assertIsNotNone(joined.native_index)
        self.assertTrue(joined.financial_values['source_comparable'])
        self.assertTrue(joined.financial_values['operational_closed'])
        self.assertEqual(joined.financial_values['native_terminal_sha256'], token['terminal_sha256'])
        self.assertEqual(joined.task_receipts[0]['status'], 'answer')
        self.assertEqual(joined.controller_settlements, [])
        # Answer text cannot stand in for a different actual SDK/native result.
        import json
        path = self.root / 'runs/00/requests/request-000000.json'
        original = path.read_bytes()
        changed = json.loads(original)
        changed['sdk_result']['usage'] = dict(input_tokens=1,output_tokens=1,cached_input_tokens=0)
        from benchmarks.recording_native_schema import encoded
        path.write_bytes(encoded(changed) + b'\n')
        with self.assertRaises(ValueError):
            self.validate()
        path.write_bytes(original)
        source = self.root / 'runs/00/source/mapping-records.json'
        original = source.read_bytes()
        changed = json.loads(original)
        changed[0]['timestamp_ms'] += 1
        source.write_bytes(encoded(changed))
        with self.assertRaises(ValueError):
            self.validate()
        source.write_bytes(original)


if __name__ == '__main__':
    unittest.main()
