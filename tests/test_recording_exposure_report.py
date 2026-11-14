import copy
from fractions import Fraction
import hashlib
import unittest
from decimal import localcontext

from benchmarks.recording_financial import digest,encode,decode
from benchmarks.recording_lifetime_ledger import validate_validity_chain
from benchmarks.recording_exposure_report import compare_quality_latency
from benchmarks.perception_comparison import plan_digest
from test_three_arm_comparison import fixture,run


def quality_fixture():
    plan,rows = fixture()
    assessment = dict(schema_version=1,kind='recording_assessment',comparison_plan_sha256=plan_digest(plan),
        runtime_policy_sha256='a'*64,collection_sha256='b'*64,execution_inventory_sha256='c'*64,
        reviewer='fixture',rubric_sha256='d'*64,measurement_protocol_sha256='e'*64,source_evidence_sha256='f'*64,rows=[])
    receipts = []
    for ordinal,row in enumerate(rows):
        receipt = dict(schema_version=1,kind='recording_parent_task_receipt',execution_sha256='1'*64,
            task_id=row['task_id'],input_sha256=row['input_sha256'],result_sha256='2'*64,
            received_ns=1000,failed_observed_ns=None,status='answer',failure_reason='completed',
            answer_sha256='3'*64,latency_ns=int(row['latency_ms']*10**6))
        receipts.append((row['arm'],receipt))
        assessment['rows'].append(dict(task_id=row['task_id'],input_sha256=row['input_sha256'],invocation_ordinal=ordinal%96,
            parent_receipt_sha256=digest(receipt),answer_sha256=receipt['answer_sha256'],
            quality_score=row['quality_score'],correct_critical_facts=row['correct_critical_facts']))
    return plan,rows,assessment,receipts


class QualityLatency(unittest.TestCase):
    def test_original_precision_is_independent_of_callers_decimal_context(self):
        plan,rows,assessment,receipts=quality_fixture()
        baseline=compare_quality_latency(plan,assessment,receipts,expected_assessment_sha256=plan_digest(assessment))
        with localcontext() as context:
            context.prec=2
            changed=compare_quality_latency(plan,assessment,receipts,expected_assessment_sha256=plan_digest(assessment))
        self.assertEqual(changed.reports,baseline.reports)

    def test_exact_original_math_without_fake_cost_or_usage(self):
        plan,rows,assessment,receipts = quality_fixture(); old = run(plan,rows)
        result = compare_quality_latency(plan,assessment,receipts,expected_assessment_sha256=plan_digest(assessment))
        reports = decode(result.reports,16*1024**2)
        for name,report in reports.items():
            prior = old['comparisons'][name]
            self.assertEqual(report['exact_point'],{key:prior['exact_point'][key] for key in ('latency_ratio','quality_delta')})
            self.assertEqual(report['exact_paired_bootstrap_95'],{key:prior['exact_paired_bootstrap_95'][key] for key in ('latency_ratio','quality_delta')})
            self.assertTrue(report['meets_quality_latency_gates'])
            self.assertNotIn('usage',report)
            self.assertNotIn('cost',report['gates'])

    def test_late_answer_remains_zero_quality_and_no_accepted_answer(self):
        plan,rows,assessment,receipts = quality_fixture()
        receipt = receipts[0][1]; receipt.update(status='late_answer',answer_sha256=None)
        assessment['rows'][0]['parent_receipt_sha256'] = digest(receipt)
        with self.assertRaises(ValueError):
            compare_quality_latency(plan,assessment,receipts,expected_assessment_sha256=plan_digest(assessment))
        assessment['rows'][0].update(answer_sha256=None,quality_score=0,correct_critical_facts=[])
        result = compare_quality_latency(plan,assessment,receipts,expected_assessment_sha256=plan_digest(assessment))
        self.assertIn('C_vs_A',decode(result.reports,16*1024**2))


def artifact(value,path):
    data = encode(value,newline=True)
    return dict(path=path,file_sha256=hashlib.sha256(data).hexdigest(),bytes=len(data))


class Validity(unittest.TestCase):
    def fixture(self):
        genesis = dict(schema_version=1,kind='recording_validity_entry',exposure_policy_sha256='a'*64,
            ledger_sha256='b'*64,sequence=0,previous_sha256=None,notice=None,state='sealed',observed_ns=100)
        ref = artifact(genesis,'ledger/validity-000000.json')
        checkpoint = dict(schema_version=1,kind='recording_validity_checkpoint',exposure_policy_sha256='a'*64,
            ledger_sha256='b'*64,tail_sha256=ref['file_sha256'],tail_sequence=0,reviewed_as_of_ns=101,
            reviewer='external-fixture',review_method_sha256='c'*64)
        return [(ref,genesis)],checkpoint,{}

    def check(self,entries,checkpoint,notices,expected=None):
        return validate_validity_chain(entries,checkpoint,expected_checkpoint_sha256=expected or digest(checkpoint),
            exposure_policy_sha256='a'*64,ledger_sha256='b'*64,sealed_ns=99,notices=notices)

    def test_mandatory_zero_notice_genesis_and_external_tail(self):
        entries,checkpoint,notices = self.fixture()
        self.assertEqual(self.check(entries,checkpoint,notices)['state'],'sealed')
        with self.assertRaises(ValueError): self.check([],checkpoint,notices)
        with self.assertRaises(ValueError): self.check(entries,checkpoint,notices,expected='d'*64)

    def test_late_invoice_invalidates_without_rewriting_ledger_or_genesis(self):
        entries,checkpoint,notices = self.fixture(); before = copy.deepcopy(entries)
        notice = dict(schema_version=1,kind='recording_late_cost_notice',sealed_ledger_sha256='b'*64,
            closure_sha256='c'*64,stream_id='stream-A',noticed_ns=110,
            financial_evidence=dict(path='financial/evidence/evidence-000001.json',file_sha256='d'*64,bytes=100),reason='new_charge')
        nref = artifact(notice,'ledger/late-000000.json'); notices[nref['file_sha256']] = notice
        entry = dict(schema_version=1,kind='recording_validity_entry',exposure_policy_sha256='a'*64,
            ledger_sha256='b'*64,sequence=1,previous_sha256=entries[0][0]['file_sha256'],notice=nref,state='invalidated',observed_ns=111)
        ref = artifact(entry,'ledger/validity-000001.json'); entries.append((ref,entry))
        checkpoint.update(tail_sha256=ref['file_sha256'],tail_sequence=1,reviewed_as_of_ns=112)
        self.assertEqual(self.check(entries,checkpoint,notices)['state'],'invalidated')
        self.assertEqual(entries[:1],before)
        with self.assertRaises(ValueError): self.check(entries[:1],dict(checkpoint,tail_sequence=0,tail_sha256=entries[0][0]['file_sha256']),notices)


if __name__ == '__main__': unittest.main()
