"""
Unit Tests — Temporal Filter

STATUS: IMPLEMENTED
Tests debouncing logic and occupancy session tracking.
Run: python -m pytest tests/test_temporal_filter.py -v
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ai.tracking.temporal_filter import TemporalFilter, SlotState


def make_filter(occ=5, free=8):
    return TemporalFilter(
        occupied_confirm_frames=occ,
        free_confirm_frames=free,
        uncertain_timeout_frames=15,
    )


def feed(tf: TemporalFilter, s1=False, s2=False, s3=False, s4=False, n=1):
    """Feed N identical frames to the temporal filter."""
    candidates = {"S1": s1, "S2": s2, "S3": s3, "S4": s4}
    for _ in range(n):
        tf.update(candidates)


class TestOccupiedConfirmation:

    def test_not_confirmed_before_threshold(self):
        tf = make_filter(occ=5)
        feed(tf, s1=True, n=4)   # 4 frames — one short of threshold
        assert tf.get_confirmed_states()["S1"] == SlotState.FREE

    def test_confirmed_at_threshold(self):
        tf = make_filter(occ=5)
        feed(tf, s1=True, n=5)   # exactly 5 → confirmed
        assert tf.get_confirmed_states()["S1"] == SlotState.OCCUPIED

    def test_stays_occupied_beyond_threshold(self):
        tf = make_filter(occ=5)
        feed(tf, s1=True, n=20)
        assert tf.get_confirmed_states()["S1"] == SlotState.OCCUPIED


class TestFreeConfirmation:

    def test_not_freed_before_threshold(self):
        tf = make_filter(occ=5, free=8)
        feed(tf, s1=True, n=10)   # confirm occupied
        feed(tf, s1=False, n=7)   # 7 free frames — one short of free threshold
        assert tf.get_confirmed_states()["S1"] == SlotState.OCCUPIED

    def test_freed_at_threshold(self):
        tf = make_filter(occ=5, free=8)
        # Feed exactly occ_confirm frames → confirms OCCUPIED, counter resets to 0
        feed(tf, s1=True, n=5)
        assert tf.get_confirmed_states()["S1"] == SlotState.OCCUPIED
        # Feed exactly free_confirm frames → counter reaches -free_confirm → FREE
        feed(tf, s1=False, n=8)
        assert tf.get_confirmed_states()["S1"] == SlotState.FREE

    def test_initial_state_is_free(self):
        tf = make_filter()
        assert tf.get_confirmed_states()["S1"] == SlotState.FREE


class TestMixedFrames:

    def test_mixed_frames_hold_state(self):
        """Alternating occupied/free frames should not flip state."""
        tf = make_filter(occ=5)
        for i in range(20):
            feed(tf, s1=(i % 2 == 0), n=1)
        # Should never have confirmed OCCUPIED (never 5 consecutive)
        assert tf.get_confirmed_states()["S1"] == SlotState.FREE

    def test_multiple_slots_independent(self):
        tf = make_filter(occ=5)
        feed(tf, s1=True, s2=False, s3=True, s4=False, n=5)
        states = tf.get_confirmed_states()
        assert states["S1"] == SlotState.OCCUPIED
        assert states["S2"] == SlotState.FREE
        assert states["S3"] == SlotState.OCCUPIED
        assert states["S4"] == SlotState.FREE


class TestAvailableCount:

    def test_all_free(self):
        tf = make_filter()
        assert tf.get_available_count() == 4

    def test_two_occupied(self):
        tf = make_filter(occ=5)
        feed(tf, s1=True, s3=True, n=5)
        assert tf.get_available_count() == 2

    def test_all_occupied(self):
        tf = make_filter(occ=5)
        feed(tf, s1=True, s2=True, s3=True, s4=True, n=5)
        assert tf.get_available_count() == 0


class TestOccupancySessions:

    def test_session_starts_on_occupied(self):
        tf = make_filter(occ=3)
        feed(tf, s1=True, n=3)
        assert tf.get_session_count("S1") == 1

    def test_session_ends_on_free(self):
        tf = make_filter(occ=3, free=3)
        feed(tf, s1=True, n=3)   # OCCUPIED
        feed(tf, s1=False, n=3)  # FREE
        history = tf.get_session_history("S1")
        assert len(history) == 1
        assert history[0].duration_seconds is not None
        assert history[0].duration_seconds >= 0

    def test_session_count_increments(self):
        tf = make_filter(occ=3, free=3)
        for _ in range(3):
            feed(tf, s1=True, n=3)
            feed(tf, s1=False, n=3)
        assert tf.get_session_count("S1") == 3

    def test_current_duration_when_occupied(self):
        tf = make_filter(occ=2)
        feed(tf, s1=True, n=2)
        dur = tf.get_current_occupancy_duration("S1")
        assert dur is not None
        assert dur >= 0

    def test_no_duration_when_free(self):
        tf = make_filter()
        assert tf.get_current_occupancy_duration("S1") is None


class TestForceState:

    def test_force_occupied(self):
        tf = make_filter()
        tf.force_state("S2", SlotState.OCCUPIED)
        assert tf.get_confirmed_states()["S2"] == SlotState.OCCUPIED

    def test_force_free(self):
        tf = make_filter(occ=2)
        feed(tf, s2=True, n=2)
        tf.force_state("S2", SlotState.FREE)
        assert tf.get_confirmed_states()["S2"] == SlotState.FREE
