"""Pure original-capture timing for the separately owned visual replay driver.

This is not a claim of Smol worker/sentinel equivalence. Legacy sentinel timing
is unchanged; replay additionally enforces acquisition before the original tick.
"""
from dataclasses import dataclass
from .recorded_source import _integer
from .owned_capture import CapturePacket


@dataclass(frozen=True, slots=True)
class TickOpportunity:
    index: int
    count: int
    first_due_offset_ns: int
    period_ns: int


@dataclass(frozen=True, slots=True)
class TickSelection:
    outcome: str
    packet: CapturePacket | None


class RecordedTickSchedule:
    def __init__(self, *, duration_ns, period_ns, phase_ns, time_origin_policy,
                 origin_capture_ns, max_age_ms, deadline_tolerance_ns):
        self.duration_ns = _integer(duration_ns, 1, 3600*10**9)
        self.period_ns = _integer(period_ns, 1, 2**63-1)
        phase = _integer(phase_ns, 0, self.period_ns-1)
        _integer(origin_capture_ns, 0, 2**63-1)
        if time_origin_policy not in ('recording_start', 'capture_epoch'):
            raise ValueError('original tick time-origin policy required')
        self.first_due_ns = phase if time_origin_policy == 'recording_start' else (phase-origin_capture_ns)%self.period_ns
        self.max_age_ns = _integer(max_age_ms, 1, 60000)*10**6
        self.tolerance_ns = _integer(deadline_tolerance_ns, 0, self.period_ns-1)
        self.opportunity_count = (max(0, self.duration_ns-self.first_due_ns)+self.period_ns-1)//self.period_ns
        if self.opportunity_count > 16384: raise ValueError('logical original tick capacity exceeded')
        self._next = 0

    def next_due_offset(self):
        return None if self._next == self.opportunity_count else self.first_due_ns+self._next*self.period_ns

    def advance(self, observed_offset_ns):
        """Return at most one skipped range and one current opportunity.

        The caller records the skipped range as late and dispatches only the
        current opportunity. Never replay missed model opportunities in a burst.
        """
        _integer(observed_offset_ns, 0, 2**63-1)
        due = self.next_due_offset()
        if due is None or observed_offset_ns < due: return ()
        index = min((observed_offset_ns-self.first_due_ns)//self.period_ns,
                    self.opportunity_count-1)
        result = []
        if index > self._next:
            result.append(TickOpportunity(self._next, index-self._next, due, self.period_ns))
        result.append(TickOpportunity(index, 1, self.first_due_ns+index*self.period_ns, self.period_ns))
        self._next = index+1
        return tuple(result)

    def select(self, opportunity, packets, *, anchor_ns, observed_ns,
               source_index, last_selected_ordinal=-1, busy=False, closed=False):
        if type(opportunity) is not TickOpportunity or opportunity.count != 1:
            raise ValueError('one original current tick required')
        _integer(anchor_ns, 0, 2**63-1); _integer(observed_ns, anchor_ns, 2**63-1)
        _integer(source_index, 0, 15)
        if type(busy) is not bool or type(closed) is not bool: raise ValueError('exact driver state required')
        if type(packets) is not tuple or len(packets) > 2 or any(type(p) is not CapturePacket for p in packets):
            raise ValueError('at most two retained immutable packets required')
        due = anchor_ns+opportunity.first_due_offset_ns
        if closed: return TickSelection('closed', None)
        if observed_ns < due: raise ValueError('tick cannot execute before original due time')
        if observed_ns-due > self.tolerance_ns: return TickSelection('late', None)
        if busy: return TickSelection('busy', None)
        candidates = [p for p in packets if p.source_index == source_index
            and p.record_ordinal > last_selected_ordinal
            and p.offset_ns <= opportunity.first_due_offset_ns
            and p.acquired_monotonic_ns <= due]
        if not candidates: return TickSelection('no_frame', None)
        packet = max(candidates, key=lambda p: (p.offset_ns, p.capture_sequence))
        if (observed_ns-packet.scheduled_monotonic_ns > self.max_age_ns
                or observed_ns-packet.acquired_monotonic_ns > self.max_age_ns):
            return TickSelection('stale', packet)
        return TickSelection('selected', packet)
