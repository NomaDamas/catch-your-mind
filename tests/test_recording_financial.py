import copy
from fractions import Fraction
import hashlib
import os
from pathlib import Path
import tempfile
import unittest

from benchmarks.recording_financial import (ADAPTER,AUTHORITY,FinancialArtifacts,
    INPUT_GRAMMAR,OUTPUT_GRAMMAR,claim_sha256,decode,digest,encode,iter_financial_rows,
    ratio,rational,validate_adapters,validate_financial_evidence,validate_invoice)
from benchmarks.matched_source_exposure import compare_costs


def invoice():
    return dict(schema_version=1,kind='synthetic_recording_invoice',evidence_class='fixture',
        authority=AUTHORITY,provider='fixture',revision='v1',account_scope='study',invoice_id='invoice-1',
        currency='USD',currency_unit='microUSD',lines=[dict(line_id='line-1',stream_id='stream-A',
        component_id='vlm',resource_id='resource-A',lane_id='vlm',
        operation_key=dict(invocation_ordinal=0,binding_index=3,call_ordinal=0),
        service_start_ns=None,service_end_ns=None,service_event_ns=101,
        source_quantity=ratio(2),quantity=2,billed_atomic=4)])


def adapters():
    document = dict(schema_version=1,kind='recording_financial_adapters',adapters=[dict(
        adapter_id='fixture',implementation=ADAPTER,implementation_sha256='a'*64,
        provider='fixture',revision='v1',evidence_class='fixture',
        input_schema_sha256=digest(INPUT_GRAMMAR),output_schema_sha256=digest(OUTPUT_GRAMMAR),
        closure_capability='explicit_original_lines_and_finality')])
    return validate_adapters(document,expected_sha256=digest(document))


class RecordingFinancial(unittest.TestCase):
    def test_strict_original_invoice_and_claim_identity(self):
        document = invoice(); before = copy.deepcopy(document)
        self.assertEqual(validate_invoice(document),document)
        self.assertEqual(document,before)
        self.assertEqual(claim_sha256('fixture','study','invoice-1','line-1'),
            digest(['gamst.recording.claim.v1','fixture','study','invoice-1','line-1']))
        for key,value in (('evidence_class','real'),('authority','provider'),('schema_version',True)):
            bad = copy.deepcopy(document); bad[key] = value
            with self.subTest(key=key),self.assertRaises(ValueError): validate_invoice(bad)
        bad = copy.deepcopy(document); bad['lines'].append(bad['lines'][0])
        with self.assertRaises(ValueError): validate_invoice(bad)

    def test_duplicate_nonfinite_float_and_integer_lexemes_reject_before_conversion(self):
        for data in (b'{"a":1,"a":2}',b'{"a":NaN}',b'{"a":1.0}',
                     ('{"a":'+'9'*79+'}').encode(),b'\xff'):
            with self.subTest(data=data[:30]),self.assertRaises(ValueError): decode(data)

    def test_rational_output_uses_256_bits_and_requires_reduced(self):
        value = Fraction(10_000_000*3600*10**9,60_000_000_001)
        self.assertGreater(value.numerator,2**63-1)
        self.assertEqual(rational(ratio(value)),value)
        for value in (dict(numerator=2,denominator=2),dict(numerator=True,denominator=1),
                      dict(numerator=2**256,denominator=1),dict(numerator=1,denominator=0)):
            with self.subTest(value=value),self.assertRaises(ValueError): rational(value)

    def test_only_shipped_synthetic_adapter_grammar(self):
        self.assertEqual(adapters().get('fixture')['evidence_class'],'fixture')
        with self.assertRaises(ValueError): adapters().get('openai')

    def test_exact_evidence_preserves_original_line(self):
        document = invoice(); adapter = adapters()
        data = encode(document,newline=True)
        ref = dict(path='financial/source/source-'+hashlib.sha256(data).hexdigest()+'.json',
                   file_sha256=hashlib.sha256(data).hexdigest(),bytes=len(data))
        evidence = dict(schema_version=1,kind='recording_financial_evidence',adapter_id='fixture',
            adapter_inventory_sha256=adapter.digest,origin='synthetic_fixture',source_document=ref,
            provider='fixture',revision='v1',account_scope='study',invoice_id='invoice-1',line_id='line-1',
            claim_sha256=claim_sha256('fixture','study','invoice-1','line-1'),owner_instance='b'*64,
            stream_id='stream-A',quantities=dict(vlm=ratio(2)),billed_atomic=4,currency='USD',
            currency_unit='microUSD',service_start_ns=None,service_end_ns=None,service_event_ns=101,
            observed_received_ns=200,finality_evidence_sha256=None)
        self.assertEqual(validate_financial_evidence(evidence,adapters=adapter,invoice=document,source_reference=ref),evidence)
        for key,value in (('origin','external_original'),('billed_atomic',0),('claim_sha256','c'*64)):
            bad = copy.deepcopy(evidence); bad[key] = value
            with self.subTest(key=key),self.assertRaises(ValueError):
                validate_financial_evidence(bad,adapters=adapter,invoice=document,source_reference=ref)

    def test_bounded_exclusive_pages_and_exact_reader(self):
        with tempfile.TemporaryDirectory() as root:
            with FinancialArtifacts(root) as store:
                ref = store.write_invoice(invoice())
                self.assertEqual(store.read(ref),invoice())
                with self.assertRaises(ValueError): store.write_invoice(invoice())
                rows = [dict(source_document=ref) for _ in range(300)]
                index = store.write_index('source',rows)
                self.assertEqual(index['page_count'],3)
                self.assertEqual(list(iter_financial_rows(store,'source',index)),rows)
                empty = store.write_index('finality',[])
                self.assertEqual(list(iter_financial_rows(store,'finality',empty)),[])
                bad = copy.deepcopy(index); bad['row_count'] -= 1
                with self.assertRaises(ValueError): list(iter_financial_rows(store,'source',bad))

    def test_symlink_and_mutated_original_bytes_reject(self):
        with tempfile.TemporaryDirectory() as root:
            with FinancialArtifacts(root) as store:
                ref = store.write_invoice(invoice())
                path = Path(root,ref['path']); original = path.read_bytes()
                path.write_bytes(original.replace(b'line-1',b'line-2'))
                with self.assertRaises(ValueError): store.read(ref)
        with tempfile.TemporaryDirectory() as root:
            Path(root,'financial').symlink_to(Path(root),target_is_directory=True)
            with FinancialArtifacts(root) as store:
                with self.assertRaises(OSError): store.write_invoice(invoice())


class RecordingBootstrap(unittest.TestCase):
    def fixture(self,n=24):
        groups = [dict(recording_id='recording-%02d'%i,source_manifest_sha256='%064x'%(i+1),
                       exposure_duration_ns=(i+1)*10**9) for i in range(n)]
        totals = {g['recording_id']:{arm:dict(full_monetary_atomic=100 if arm=='A' else 70,
                    source_comparable=True,cost_complete=True) for arm in 'ABC'} for g in groups}
        policy = dict(bootstrap=dict(seed=17,repetitions=100,minimum_recordings=20))
        return policy,dict(groups=groups),totals

    def test_all_original_recordings_equal_exposure_unequal_lifetime(self):
        policy,recordings,totals = self.fixture()
        before = copy.deepcopy((policy,recordings,totals))
        result = compare_costs(policy,recordings,totals)
        self.assertTrue(result['C_vs_A']['cost_gate'])
        self.assertEqual(result['C_vs_A']['point_ratio'],ratio(Fraction(7,10)))
        self.assertEqual(result['C_vs_A']['interval95'],[ratio(Fraction(7,10))]*2)
        self.assertEqual((policy,recordings,totals),before)
        recordings['groups'].reverse()
        self.assertEqual(compare_costs(policy,recordings,totals),result)

    def test_failed_recording_not_subset_and_startup_cleanup_cost_retained(self):
        policy,recordings,totals = self.fixture()
        totals['recording-00']['C']['full_monetary_atomic'] = 10000
        self.assertFalse(compare_costs(policy,recordings,totals)['C_vs_A']['cost_gate'])
        totals['recording-00']['C'].update(full_monetary_atomic=70,cost_complete=False)
        self.assertFalse(compare_costs(policy,recordings,totals)['C_vs_A']['cost_gate'])
        totals['recording-00']['C'].update(cost_complete=True,source_comparable=False)
        self.assertFalse(compare_costs(policy,recordings,totals)['C_vs_A']['cost_gate'])
        totals.pop('recording-00')
        with self.assertRaises(ValueError): compare_costs(policy,recordings,totals)

    def test_unknown_money_never_zero_and_zero_draw_undefined(self):
        policy,recordings,totals = self.fixture()
        totals['recording-00']['C']['full_monetary_atomic'] = None
        result = compare_costs(policy,recordings,totals)['C_vs_A']
        self.assertIsNone(result['point_ratio']); self.assertIsNone(result['interval95']); self.assertFalse(result['cost_gate'])
        policy,recordings,totals = self.fixture(2)
        totals['recording-00']['A']['full_monetary_atomic'] = 0
        result = compare_costs(policy,recordings,totals)['C_vs_A']
        self.assertIsNone(result['interval95']); self.assertFalse(result['cost_gate'])


if __name__ == '__main__': unittest.main()
