import copy
import itertools
import unittest

from benchmarks.recording_financial import digest,ratio
from benchmarks.matched_source_exposure import (EXPOSURE_LIMITS,FAILURE_POLICY,SOURCE_POLICY,TARGETS,
    validate_accounting_policy,validate_exposure_policy,validate_recording_opportunities)
from benchmarks.perception_comparison import plan_digest
from benchmarks.stream_cost_ledger import CATEGORIES
from test_three_arm_comparison import fixture
from test_recording_financial import adapters


def declarations(n=24):
    plan,rows = fixture(); f = adapters()
    g = dict(schema_version=1,kind='matched_recording_opportunities',comparison_plan_sha256=plan_digest(plan),groups=[])
    orders = tuple(itertools.permutations('ABC'))
    for i in range(n):
        g['groups'].append(dict(recording_id='recording-%02d'%i,source_manifest_sha256='%064x'%(i+1),
            tasks_sha256='1'*64,exposure_duration_ns=1000000000,sources=[dict(source_id='camera',sensor_id='camera-1',
                original_stream_epoch='epoch-1',format='bgr8_hwc',calibration_id=None,record_count=1,
                record_inventory_sha256='2'*64,counter_contract='attempted_equals_captured_plus_dropped')],
            availability_sha256='3'*64,arm_order=list(orders[i%6])))
    components = [dict(id=c,category=c,kind='monetary',unit='tick',source_unit='tick',
        atomic_per_source=ratio(1),coverage='event' if c=='vlm' else 'interval',rate_id='fixture') for c in CATEGORIES]
    k = dict(schema_version=2,kind='recording_lifetime_accounting',comparison_plan_sha256=plan_digest(plan),
        recordings_sha256=digest(g),financial_adapter_inventory_sha256=f.digest,boundary='full_attributable_arm_lifetime',
        currency='USD',currency_unit='USD.micro',rate_revision='v1',invoice_rounding='line_atomic_half_even',isolation='isolated_arms',
        components=components,rates=dict(fixture=dict(provider='fixture',revision='v1',unit='tick',per_unit='1')),streams=[],
        closure=dict(admission_end='source_duration_and_original_task_deadlines',cost_boundary_end='all_attributable_work_closed',
            settlement_wait_ms=0,seal='external_finality_or_incomplete',late_invoice='immutable_invalidate_no_rewrite',
            amendments='unsupported',deadline_clock='same_host_monotonic_ns'),limits=copy.deepcopy(EXPOSURE_LIMITS))
    for group in g['groups']:
        for arm in 'ABC':
            sid = group['recording_id']+'-'+arm
            k['streams'].append(dict(stream_id=sid,recording_id=group['recording_id'],arm=arm,
                source_manifest_sha256=group['source_manifest_sha256'],exposure_duration_ns=group['exposure_duration_ns'],
                execution_namespace='exec-'+sid,cache_namespace='cache-'+sid,isolation_policy_sha256='4'*64,
                requirements={c:dict(state='required' if c=='vlm' else 'not_applicable',reason_code='fixture',
                    justification_sha256=None if c=='vlm' else '5'*64,
                    lanes=[dict(resource_id='resource-'+sid,lane_id='vlm',coverage='whole_lifetime',lifecycle_binding_id=None)] if c=='vlm' else []) for c in CATEGORIES}))
    p = plan['comparison']
    e = dict(schema_version=2,kind='matched_source_exposure_full_lifetime',comparison_plan_sha256=plan_digest(plan),
        recordings_sha256=digest(g),latency_policy_sha256='6'*64,accounting_policy_sha256=digest(k),
        financial_adapter_inventory_sha256=f.digest,source_policy=dict(SOURCE_POLICY,max_acquisition_lateness_ns=1000000),
        bootstrap=dict(unit='original_recording',minimum_recordings=p['min_pairs'],seed=p['bootstrap_seed'],
            repetitions=p['bootstrap_repetitions'],order='source_manifest_sha256_ascending',interval='nearest_rank_95',undefined_draw='interval_undefined'),
        targets=copy.deepcopy(TARGETS),failure_policy=copy.deepcopy(FAILURE_POLICY),limits=copy.deepcopy(EXPOSURE_LIMITS))
    return plan,g,k,e


class Policies(unittest.TestCase):
    def test_twenty_four_balanced_original_groups_fit_and_no_lower_minimum(self):
        plan,g,k,e = declarations()
        self.assertEqual(validate_recording_opportunities(g,expected_sha256=digest(g),comparison_plan_sha256=plan_digest(plan)),g)
        self.assertEqual(validate_accounting_policy(k,expected_sha256=digest(k),comparison_plan_sha256=plan_digest(plan),recordings=g),k)
        self.assertEqual(validate_exposure_policy(e,plan,g,expected_sha256=digest(e),expected_recordings_sha256=digest(g)),e)
        self.assertEqual(len(k['streams']),72)
        plan,g,k,e = declarations(8)
        with self.assertRaises(ValueError): validate_exposure_policy(e,plan,g,expected_sha256=digest(e),expected_recordings_sha256=digest(g))

    def test_all_ten_categories_and_no_cross_arm_or_lane_reuse(self):
        plan,g,k,e = declarations()
        for mutation in ('category','lane','resource','not_applicable'):
            bad = copy.deepcopy(k)
            if mutation=='category': bad['components'].pop()
            elif mutation=='lane': bad['streams'][1]['requirements']['vlm']['lanes'] = bad['streams'][0]['requirements']['vlm']['lanes']
            elif mutation=='resource': bad['streams'][1]['requirements']['vlm']['lanes'][0]['resource_id'] = bad['streams'][0]['requirements']['vlm']['lanes'][0]['resource_id']
            else: bad['streams'][0]['requirements']['startup']['justification_sha256'] = None
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):
                validate_accounting_policy(bad,expected_sha256=digest(bad),comparison_plan_sha256=plan_digest(plan),recordings=g)

    def test_original_targets_cannot_be_lowered_and_joint_limit_not_reset(self):
        plan,g,k,e = declarations()
        for mutation in ('target','minimum','limit','physical'):
            bad = copy.deepcopy(e)
            if mutation=='target': bad['targets']['cost_ratio_upper'] = ratio(1)
            elif mutation=='minimum': bad['bootstrap']['minimum_recordings'] = 1
            elif mutation=='limit': bad['limits']['max_groups'] = 96
            else: bad['source_policy']['physical_device_truth'] = 'verified'
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):
                validate_exposure_policy(bad,plan,g,expected_sha256=digest(bad),expected_recordings_sha256=digest(g))


if __name__ == '__main__': unittest.main()
