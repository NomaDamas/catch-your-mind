from pathlib import Path
import tempfile
import unittest

from benchmarks.recording_financial import FinancialArtifacts,digest,iter_financial_rows
from test_recording_financial import invoice,adapters


class FinancialBounds(unittest.TestCase):
    def test_join_memory_shared_artifact_budget_and_cross_index_aliases_are_hard_bounds(self):
        class Budget:
            def __init__(self):self.used=0
            def reserve(self,count):
                if self.used+count>10000:raise ValueError('collection byte reservation exhausted')
                self.used+=count
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as root:
            budget=Budget()
            with FinancialArtifacts(root,budget=budget) as store:
                ref=store.write_invoice(invoice());self.assertEqual(budget.used,ref['bytes'])
                index=store.write_index('source',[dict(source_document=ref)])
                self.assertEqual(len(list(iter_financial_rows(store,'source',index))),1)
                with self.assertRaisesRegex(ValueError,'aliased'):list(iter_financial_rows(store,'source',index))
                store._index_bytes=128*1024**2-1
                with self.assertRaisesRegex(ValueError,'128 MiB'):store.reserve_index({'original':'retained'})
                budget.used=10000
                with self.assertRaisesRegex(ValueError,'reservation exhausted'):store.write('ledger/coverage-000.json',{'known':True})
                self.assertFalse((Path(root)/'ledger/coverage-000.json').exists())

    def test_original_source_path_and_actual_adapter_inventory_cannot_be_mutated(self):
        a=adapters();changed=a.adapters[0];changed['provider']='forged'
        self.assertEqual(a.get('fixture')['provider'],'fixture')
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as root:
            with FinancialArtifacts(root) as store:
                with self.assertRaisesRegex(ValueError,'source filename'):
                    store.write('financial/source/source-'+'a'*64+'.json',invoice())

    def test_known_retained_late_notice_cannot_hide_behind_an_old_checkpoint(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as root:
            with FinancialArtifacts(root) as store:
                ref=store.write('ledger/validity-000000.json',{'original':'genesis'})
                store.assert_validity_inventory([],[ref])
                notice=store.write('ledger/late-000000.json',{'known':'new charge'})
                with self.assertRaisesRegex(ValueError,'omitted'):store.assert_validity_inventory([],[ref])
                store.assert_validity_inventory([notice],[ref])


if __name__=='__main__':unittest.main()
