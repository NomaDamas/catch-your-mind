from dataclasses import replace
import hashlib
import unittest
from benchmarks.owned_capture import CapturePacket
from benchmarks.recorded_ticks import RecordedTickSchedule


def packet(offset, acquired, ordinal=0):
    payload = bytes(32*32*3)
    return CapturePacket('a'*64, 'b'*64, ordinal, 0, 'camera', 'video', 'old-epoch',
        ordinal, 1000000000+offset, offset, 'c'*64, 10000000000+offset, acquired,
        2000000000000+offset//1000000, offset%1000000, 'bgr8_hwc', (32,32,3),
        None, None, hashlib.sha256(payload).hexdigest(), payload)


class Ticks(unittest.TestCase):
    def schedule(self, **changes):
        values = dict(duration_ns=4000000000, period_ns=1000000000, phase_ns=500000000,
            time_origin_policy='recording_start', origin_capture_ns=1000000000,
            max_age_ms=1000, deadline_tolerance_ns=50000000)
        values.update(changes); return RecordedTickSchedule(**values)

    def test_after_tick_acquisition_cannot_replace_prior_eligible_capture(self):
        schedule = self.schedule(); tick, = schedule.advance(510000000)
        before = packet(400000000, 10410000000)
        # Original timestamp is eligible, actual capture arrival is too late.
        after = packet(490000000, 10501000000, 1)
        selected = schedule.select(tick, (before, after), anchor_ns=10000000000,
            observed_ns=10510000000, source_index=0)
        self.assertEqual(selected.outcome, 'selected'); self.assertIs(selected.packet, before)
        missing = schedule.select(tick, (after,), anchor_ns=10000000000,
            observed_ns=10510000000, source_index=0)
        self.assertEqual(missing.outcome, 'no_frame')

    def test_missing_phase_zero_and_unique_capture_are_honest(self):
        schedule = self.schedule(phase_ns=0); tick, = schedule.advance(0)
        selected = schedule.select(tick, (packet(0, 10000000001),), anchor_ns=10000000000,
                                   observed_ns=10000000001, source_index=0)
        self.assertEqual(selected.outcome, 'no_frame')
        available = packet(0, 10000000000)
        self.assertEqual(schedule.select(tick, (available,), anchor_ns=10000000000,
            observed_ns=10000000000, source_index=0, last_selected_ordinal=0).outcome, 'no_frame')

    def test_delayed_timer_skips_original_ticks_without_catchup(self):
        schedule = self.schedule(); opportunities = schedule.advance(2520000000)
        self.assertEqual([(o.index, o.count, o.first_due_offset_ns) for o in opportunities],
                         [(0, 2, 500000000), (2, 1, 2500000000)])
        self.assertEqual(schedule.next_due_offset(), 3500000000)
        self.assertEqual(schedule.advance(2520000000), ())
        final, = schedule.advance(4000000000)
        self.assertEqual(final.index, 3); self.assertIsNone(schedule.next_due_offset())

    def test_original_epoch_phase_and_exact_lateness_boundary(self):
        schedule = self.schedule(time_origin_policy='capture_epoch', origin_capture_ns=1200000000)
        self.assertEqual(schedule.first_due_ns, 300000000)
        tick, = schedule.advance(300000000)
        capture = packet(250000000, 10260000000)
        at = schedule.select(tick, (capture,), anchor_ns=10000000000,
            observed_ns=10350000000, source_index=0)
        self.assertEqual(at.outcome, 'selected')
        late = schedule.select(tick, (capture,), anchor_ns=10000000000,
            observed_ns=10350000001, source_index=0)
        self.assertEqual(late.outcome, 'late')
        busy = schedule.select(tick, (capture,), anchor_ns=10000000000,
            observed_ns=10300000000, source_index=0, busy=True)
        self.assertEqual(busy.outcome, 'busy')


if __name__ == '__main__': unittest.main()
