"""Actual original recordings plus prospective synthetic financial closure."""
import asyncio
from contextlib import contextmanager
from copy import deepcopy
import hashlib
from pathlib import Path
import tempfile
import shutil
import unittest

from recording_abc_fixtures import build_runtime_fixture,installed_dependencies
from recording_runtime_numeric_fixtures import numeric_runtime_fixture
from benchmarks.recording_runtime_inputs import OwnedRuntimeInputs
from benchmarks.recording_coordinator import _preflight
from benchmarks.recording_native_schema import encoded


@contextmanager
def retained_failure_directory():
    """Keep originals from a failed long collection available for diagnosis."""
    root=Path(tempfile.mkdtemp(prefix='runtime-finance-',dir='.')).resolve()
    try:yield root
    except BaseException as error:
        error.add_note(f'Original collection retained at {root}') if hasattr(error,'add_note') else None
        print(f'Original collection retained at {root}',flush=True)
        raise
    else:shutil.rmtree(root) # Only this test's newly created successful fixture.


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

    async def test_actual_twenty_recording_collector_and_financial_finalizer(self):
        from benchmarks.recording_coordinator import run_recording_collection
        from benchmarks.recording_runtime_finance import reconcile_runtime_finance,finalize_financial_runs
        from benchmarks.recording_financial import FinancialArtifacts
        from recording_runtime_financial_originals import financial_originals
        asyncio.get_running_loop().slow_callback_duration=2
        with retained_failure_directory() as root:
            for name in ('structural','numeric','money'):(root/name).mkdir()
            original=build_runtime_fixture(root/'structural',count=20,duration_ns=1_400_000_000,
                task_snapshot_ns=900_000_000,dependency_evidence=self.dependencies)
            fixture=numeric_runtime_fixture(original,root/'numeric')
            collection=await run_recording_collection(str(fixture.root),root/'output',
                expected_execution_sha256=fixture.execution_sha256s[0],retain_evaluation_artifacts=True,retain_financial_documents=True)
            joined=collection['validated_runs']
            self.assertEqual(len(joined),60)
            self.assertTrue(all(run.financial_values['source_comparable'] for run in joined),
                [dict(invocation=r.financial_values['invocation_ordinal'],violations=r.financial_values['violations'],
                    failures=r.run_inventory['failure_counts']) for r in joined if not r.financial_values['source_comparable']])
            self.assertTrue(all(run.financial_values['operational_closed'] for run in joined))
            self.assertTrue(all(receipt['status']=='answer' for run in joined for receipt in run.task_receipts))
            manifest=collection['manifest']
            self.assertEqual(manifest['assessments'],[])
            original_manifest=deepcopy(manifest)
            with FinancialArtifacts(root/'money',budget=collection['artifact_budget']) as store:
                args=financial_originals(joined,manifest,fixture.documents,root/'output',store)
                validated,quality,report=reconcile_runtime_finance(joined,manifest,documents=fixture.documents,**args)
                self.assertEqual(report['state'],'complete')
                self.assertEqual(len(validated.totals),60)
                self.assertTrue(all(not total.reasons for total in validated.totals))
                self.assertTrue(report['comparison']['B_vs_A']['cost_gate'])
                self.assertTrue(report['comparison']['C_vs_A']['cost_gate'])
                self.assertFalse(report['comparison']['B_vs_A']['overall_gate'])
                self.assertFalse(report['truth_flags']['receipt_authenticity_verified'])
                self.assertEqual(manifest,original_manifest)
                # Original typed run/execution set and parent receipt authority
                # must survive collection finalization, never caller new hashes.
                for mutation in ('execution','run','receipt','path'):
                    changed=deepcopy(manifest)
                    if mutation=='execution':changed['executions'][0]['file_sha256']='9'*64
                    elif mutation=='run':changed['runs'][0]['bytes']+=1
                    elif mutation=='receipt':changed['runs'].reverse()
                    else:changed['runs'][0]['path']='runs/00/alias.json'
                    with self.subTest(mutation=mutation),self.assertRaises(ValueError):
                        finalize_financial_runs(joined,changed,documents=fixture.documents)


if __name__=='__main__':unittest.main()
