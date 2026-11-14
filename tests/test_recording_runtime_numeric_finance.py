"""Actual original recordings plus prospective synthetic financial closure."""
import asyncio
from copy import deepcopy
import hashlib
from pathlib import Path
import tempfile
import unittest

from recording_abc_fixtures import build_runtime_fixture,installed_dependencies
from recording_runtime_numeric_fixtures import numeric_runtime_fixture
from benchmarks.recording_runtime_inputs import OwnedRuntimeInputs
from benchmarks.recording_coordinator import _preflight
from benchmarks.recording_native_schema import encoded


class RuntimeNumericFinance(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):cls.dependencies=installed_dependencies()

    async def test_original_twenty_groups_scenarios_and_joint_admission(self):
        with tempfile.TemporaryDirectory(dir='.') as tmp:
            root=Path(tmp).resolve();(root/'structural').mkdir();(root/'numeric').mkdir()
            original=build_runtime_fixture(root/'structural',count=20,duration_ns=1_400_000_000,
                task_snapshot_ns=900_000_000,dependency_evidence=self.dependencies)
            original_hashes={str(p.relative_to(original.root)):hashlib.sha256(p.read_bytes()).hexdigest()
                for p in original.root.rglob('*') if p.is_file()}
            fixture=numeric_runtime_fixture(original,root/'numeric')
            scenarios=fixture.documents['runtime/charge-scenarios.json']
            self.assertEqual(len(scenarios['scenarios']),100)
            self.assertLessEqual(len(encoded(scenarios))+1,65536)
            self.assertEqual(fixture.source_bundles,original.source_bundles)
            self.assertEqual(original_hashes,{str(p.relative_to(original.root)):hashlib.sha256(p.read_bytes()).hexdigest()
                for p in original.root.rglob('*') if p.is_file()})
            async with await OwnedRuntimeInputs.open(str(fixture.root),expected_execution_sha256=fixture.execution_sha256s[0],invocation_ordinal=0) as inputs:
                docs,bundles,declarations,bounds,budget=await _preflight(inputs)
                self.assertEqual(len(declarations),20)
                self.assertEqual(len(bounds),60)
                self.assertEqual(docs['runtime/plan.json']['comparison']['min_pairs'],20)
                self.assertLess(budget.used,4*1024**3)


if __name__=='__main__':unittest.main()
