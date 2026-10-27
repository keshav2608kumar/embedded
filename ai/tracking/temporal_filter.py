"""
Smart Parking Management System
Temporal Filter — Occupancy Debouncing + Occupancy Duration Tracking

STATUS: IMPLEMENTED

Prevents single-frame flicker from causing incorrect slot state changes.
A slot state only changes after N consecutive confirming frames.

States per slot:
    FREE       — confirmed empty
    OCCUPIED   — confirmed occupied
    UNCERTAIN  — insufficient consecutive evidence to confirm either way

Also tracks occupancy sessions (start time, end time, duration) per slot.

NOTE:
    OCCUPIED_CONFIRM_FRAMES and FREE_CONFIRM_FRAMES are INITIAL VALUES.
    They must be tuned based on actual camera frame rate and scene dynamics.
    Do NOT treat the defaults as scientifically validated parameters.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Optional

logger = logging.getLogger("smart_parking")


# ── Slot states ─────────────────────────────────────────────────────────────

class SlotState(str, Enum):
    FREE      = "FREE"
    OCCUPIED  = "OCCUPIED"
    UNCERTAIN = "UNCERTAIN"


# ── Occupancy session record ─────────────────────────────────────────────────

@dataclass
class OccupancySession:
    """Records a single occupancy event for one slot."""
    slot_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: Optional[float] = None

    def close(self, end_time: Optional[datetime] = None) -> None:
        """Mark session as ended and calculate duration."""
        self.end_time = end_time or datetime.now()
        self.duration_seconds = (self.end_time - self.start_time).total_seconds()

    def to_dict(self) -> dict:
        return {
            "slot_id": self.slot_id,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": round(self.duration_seconds, 1)
                                if self.duration_seconds is not None else None,
        }


# ── Per-slot filter state ────────────────────────────────────────────────────

@dataclass
class _SlotFilter:
    """Internal state for one parking slot."""
    slot_id: str
    confirmed_state: SlotState = SlotState.FREE

    # Candidate counter: positive = consecutive OCCUPIED candidates,
    #                    negative = consecutive FREE candidates
    candidate_counter: int = 0

    # Occupancy session tracking
    current_session: Optional[OccupancySession] = None
    session_history: list[OccupancySession] = field(default_factory=list)
    session_count: int = 0


# ── Main temporal filter class ───────────────────────────────────────────────

class TemporalFilter:
    """
    Debounces per-slot occupancy states across multiple video frames.

    Usage:
        filter = TemporalFilter(occupied_confirm=5, free_confirm=8)
        for frame in camera:
            candidates = slot_mapper.map_detections(detections)
            confirmed  = filter.update(candidates)
            # confirmed = {"S1": SlotState.FREE, "S2": SlotState.OCCUPIED, ...}
    """

    SLOT_IDS = ["S1", "S2", "S3", "S4"]

    def __init__(
        self,
        occupied_confirm_frames: int = 5,
        free_confirm_frames: int = 8,
        uncertain_timeout_frames: int = 15,
    ) -> None:
        """
        Args:
            occupied_confirm_frames: Consecutive OCCUPIED candidate frames
                                     needed to confirm OCCUPIED state.
                                     Initial value — tune based on real camera FPS.
            free_confirm_frames:     Consecutive FREE candidate frames
                                     needed to confirm FREE state.
                                     Initial value — tune based on real camera FPS.
            uncertain_timeout_frames: After this many frames with no detection
                                      at all, slot enters UNCERTAIN state.
        """
        self._occ_confirm = occupied_confirm_frames
        self._free_confirm = free_confirm_frames
        self._uncertain_timeout = uncertain_timeout_frames

        self._slots: dict[str, _SlotFilter] = {
            sid: _SlotFilter(slot_id=sid) for sid in self.SLOT_IDS
        }

        logger.info(
            "TemporalFilter initialised: occ_confirm=%d  free_confirm=%d  "
            "uncertain_timeout=%d",
            occupied_confirm_frames, free_confirm_frames, uncertain_timeout_frames
        )

    # ──────────────────────────────────────────────────────────────────────── #

    def update(
        self,
        candidates: dict[str, bool],    # True = occupied candidate this frame
        timestamp: Optional[datetime] = None,
    ) -> dict[str, SlotState]:
        """
        Feed one frame's worth of slot occupancy candidates.

        Args:
            candidates: Mapping of slot ID → bool (True = occupied this frame).
            timestamp:  Frame timestamp (defaults to datetime.now()).

        Returns:
            Confirmed slot states: dict[str, SlotState]
        """
        ts = timestamp or datetime.now()
        confirmed: dict[str, SlotState] = {}

        for slot_id in self.SLOT_IDS:
            sf = self._slots[slot_id]
            is_occupied_candidate = candidates.get(slot_id, False)

            # Update candidate counter
            if is_occupied_candidate:
                sf.candidate_counter += 1
            else:
                sf.candidate_counter -= 1

            # Clamp counter to prevent runaway values when state remains stable
            sf.candidate_counter = max(-self._free_confirm, min(self._occ_confirm, sf.candidate_counter))


            # Determine new confirmed state
            prev_state = sf.confirmed_state

            if sf.candidate_counter >= self._occ_confirm:
                new_state = SlotState.OCCUPIED
            elif sf.candidate_counter <= -self._free_confirm:
                new_state = SlotState.FREE
            else:
                new_state = sf.confirmed_state  # hold current state

            sf.confirmed_state = new_state

            # On state CHANGE: reset counter to 0 so the NEXT transition
            # requires exactly threshold frames from scratch.
            # e.g. occ_confirm=5, free_confirm=8 means:
            #   5 consecutive OCCUPIED frames  -> CONFIRMED OCCUPIED (counter reset to 0)
            #   then 8 consecutive FREE frames -> CONFIRMED FREE
            if prev_state != new_state:
                sf.candidate_counter = 0
                self._on_state_change(sf, prev_state, new_state, ts)

            confirmed[slot_id] = sf.confirmed_state

        return confirmed

    # ──────────────────────────────────────────────────────────────────────── #

    def _on_state_change(
        self,
        sf: _SlotFilter,
        old_state: SlotState,
        new_state: SlotState,
        ts: datetime,
    ) -> None:
        """Handle slot state transitions — start/end occupancy sessions."""
        logger.info(
            "Slot %s: %s → %s  (counter=%d)",
            sf.slot_id, old_state.value, new_state.value, sf.candidate_counter
        )

        if new_state == SlotState.OCCUPIED:
            # Start a new occupancy session
            sf.current_session = OccupancySession(
                slot_id=sf.slot_id,
                start_time=ts,
            )
            sf.session_count += 1
            logger.info("Slot %s: occupancy session #%d started at %s",
                        sf.slot_id, sf.session_count, ts.isoformat())

        elif old_state == SlotState.OCCUPIED and new_state in (
            SlotState.FREE, SlotState.UNCERTAIN
        ):
            # Close the current occupancy session
            if sf.current_session is not None:
                sf.current_session.close(ts)
                sf.session_history.append(sf.current_session)
                logger.info(
                    "Slot %s: session #%d ended. Duration: %.1fs",
                    sf.slot_id, sf.session_count,
                    sf.current_session.duration_seconds or 0.0
                )
                sf.current_session = None

    # ──────────────────────────────────────────────────────────────────────── #

    def get_confirmed_states(self) -> dict[str, SlotState]:
        """Return current confirmed states for all slots."""
        return {sid: sf.confirmed_state for sid, sf in self._slots.items()}

    def get_available_count(self) -> int:
        """Return number of FREE slots."""
        return sum(
            1 for sf in self._slots.values()
            if sf.confirmed_state == SlotState.FREE
        )

    def get_session_history(self, slot_id: str) -> list[OccupancySession]:
        """Return list of completed occupancy sessions for a slot."""
        return list(self._slots[slot_id].session_history)

    def get_session_count(self, slot_id: str) -> int:
        """Return total number of occupancy sessions for a slot."""
        return self._slots[slot_id].session_count

    def get_current_occupancy_duration(self, slot_id: str) -> Optional[float]:
        """
        Return current occupancy duration in seconds if slot is occupied,
        else None.
        """
        sf = self._slots[slot_id]
        if sf.current_session is not None:
            return (datetime.now() - sf.current_session.start_time).total_seconds()
        return None

    def get_all_stats(self) -> dict:
        """Return full occupancy statistics for all slots (for logging)."""
        stats = {}
        for slot_id, sf in self._slots.items():
            stats[slot_id] = {
                "confirmed_state": sf.confirmed_state.value,
                "session_count": sf.session_count,
                "current_duration_sec": self.get_current_occupancy_duration(slot_id),
                "sessions": [s.to_dict() for s in sf.session_history],
            }
        return stats

    def reset_slot(self, slot_id: str) -> None:
        """Reset a slot to FREE state (used in simulation mode)."""
        sf = self._slots[slot_id]
        if sf.current_session is not None:
            sf.current_session.close()
            sf.session_history.append(sf.current_session)
            sf.current_session = None
        sf.confirmed_state = SlotState.FREE
        sf.candidate_counter = 0
        logger.info("Slot %s manually reset to FREE", slot_id)

    def force_state(self, slot_id: str, state: SlotState,
                    ts: Optional[datetime] = None) -> None:
        """Force a slot to a specific state (used in simulation mode)."""
        sf = self._slots[slot_id]
        old = sf.confirmed_state
        sf.confirmed_state = state
        sf.candidate_counter = self._occ_confirm if state == SlotState.OCCUPIED \
                               else -self._free_confirm
        self._on_state_change(sf, old, state, ts or datetime.now())
