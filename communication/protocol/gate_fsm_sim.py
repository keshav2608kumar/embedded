"""
Smart Parking Management System
Gate Finite State Machine — Python Simulation

STATUS: IMPLEMENTED (Python simulation)
        Actual ESP32 FSM is in esp32/smart_parking/gate_fsm.cpp

This Python FSM mirrors the ESP32 gate_fsm.cpp logic exactly.
Used for:
  1. Simulation mode (python main.py --mode simulation)
  2. Unit testing (tests/test_gate_fsm.py)
  3. Logic verification before hardware testing

States:
    CLOSED          — gate is closed (default safe state)
    OPENING         — gate is moving to open position
    OPEN            — gate is fully open (waiting for vehicle)
    VEHICLE_PASSING — vehicle detected at gate sensor (hold open)
    CLOSING         — gate is moving to closed position

Transitions:
    CLOSED → OPENING        : free_count > 0 AND vehicle_request
    OPENING → OPEN          : gate reached open position (simulated by timer)
    OPEN → VEHICLE_PASSING  : vehicle sensor DETECTED
    VEHICLE_PASSING → CLOSING: vehicle sensor CLEARED
    CLOSING → CLOSED        : gate reached closed position (simulated by timer)
    CLOSING → OPENING       : vehicle sensor DETECTED while closing (SAFETY)

FULL condition:
    free_count == 0 → DENY entry, activate buzzer, gate REMAINS CLOSED
"""

import logging
import time
from enum import Enum
from typing import Callable, Optional

logger = logging.getLogger("smart_parking")


class GateState(str, Enum):
    CLOSED          = "GATE_CLOSED"
    OPENING         = "GATE_OPENING"
    OPEN            = "GATE_OPEN"
    VEHICLE_PASSING = "GATE_VEHICLE_PASSING"
    CLOSING         = "GATE_CLOSING"


class SensorState(str, Enum):
    CLEAR    = "CLEAR"
    DETECTED = "DETECTED"
    ERROR    = "SENSOR_ERROR"


class GateFSM:
    """
    Gate Finite State Machine.
    This is the Python simulation / unit-test mirror of the ESP32 FSM.
    """

    # Simulated gate travel time (seconds) — tune to match actual servo speed
    GATE_TRAVEL_TIME_SIM = 2.0

    def __init__(
        self,
        on_buzzer: Optional[Callable[[str], None]] = None,
        on_servo_open: Optional[Callable[[], None]] = None,
        on_servo_close: Optional[Callable[[], None]] = None,
    ) -> None:
        """
        Args:
            on_buzzer:      Callback to activate buzzer with a pattern name.
            on_servo_open:  Callback to open the gate servo.
            on_servo_close: Callback to close the gate servo.
        """
        self._state        = GateState.CLOSED
        self._free_count   = 4           # default: all free
        self._sensor       = SensorState.CLEAR
        self._gate_move_start: Optional[float] = None
        self._vehicle_request = False    # simulated: vehicle at entrance

        # Callbacks (connected to actual hardware in embedded; simulated here)
        self._buzzer     = on_buzzer     or (lambda pattern: None)
        self._servo_open  = on_servo_open  or (lambda: None)
        self._servo_close = on_servo_close or (lambda: None)

        logger.info("GateFSM initialised: state=%s", self._state.value)

    # ── Public interface ─────────────────────────────────────────────────── #

    def update_parking_status(self, free_count: int) -> None:
        """Called when new parking status is received from AI/serial."""
        self._free_count = max(0, min(4, free_count))
        logger.debug("GateFSM: free_count updated → %d", self._free_count)
        self._evaluate()

    def update_sensor(self, sensor_state: SensorState) -> None:
        """Called when vehicle-present sensor state changes."""
        if sensor_state != self._sensor:
            logger.info("GateFSM: sensor %s → %s",
                        self._sensor.value, sensor_state.value)
        self._sensor = sensor_state
        self._evaluate()

    def request_entry(self) -> None:
        """
        Signal that a vehicle is requesting entry (e.g. button press
        or external trigger in simulation). In the physical system this
        might be a push button or motion detector at the entrance.
        """
        self._vehicle_request = True
        logger.info("GateFSM: vehicle entry requested")
        self._evaluate()

    def tick(self) -> None:
        """
        Call periodically (e.g. every 100ms) to handle time-based transitions
        such as gate travel completion.
        """
        self._evaluate()

    @property
    def state(self) -> GateState:
        return self._state

    @property
    def state_str(self) -> str:
        return self._state.value

    # ── FSM logic ────────────────────────────────────────────────────────── #

    def _evaluate(self) -> None:
        """Evaluate current state and apply any valid transitions."""
        prev = self._state

        if self._state == GateState.CLOSED:
            self._from_closed()

        elif self._state == GateState.OPENING:
            self._from_opening()

        elif self._state == GateState.OPEN:
            self._from_open()

        elif self._state == GateState.VEHICLE_PASSING:
            self._from_vehicle_passing()

        elif self._state == GateState.CLOSING:
            self._from_closing()

        if prev != self._state:
            logger.info("GateFSM: %s → %s", prev.value, self._state.value)

    def _from_closed(self) -> None:
        if self._free_count == 0:
            # PARKING FULL — deny, buzz
            if self._vehicle_request:
                logger.info("GateFSM: PARKING FULL — entry denied")
                self._buzzer("PARKING_FULL")
                self._vehicle_request = False
        elif self._vehicle_request and self._free_count > 0:
            # Open gate
            self._transition_to(GateState.OPENING)
            self._servo_open()
            self._vehicle_request = False

    def _from_opening(self) -> None:
        # Safety: if sensor detects vehicle while still opening, hold open
        # Gate travel simulation: wait GATE_TRAVEL_TIME_SIM seconds
        if self._gate_move_start and \
                (time.time() - self._gate_move_start) >= self.GATE_TRAVEL_TIME_SIM:
            self._transition_to(GateState.OPEN)
        # Also check sensor
        if self._sensor == SensorState.DETECTED:
            self._transition_to(GateState.VEHICLE_PASSING)

    def _from_open(self) -> None:
        if self._sensor == SensorState.DETECTED:
            self._transition_to(GateState.VEHICLE_PASSING)

    def _from_vehicle_passing(self) -> None:
        if self._sensor == SensorState.CLEAR:
            # Vehicle has cleared — start closing
            self._transition_to(GateState.CLOSING)
            self._servo_close()

    def _from_closing(self) -> None:
        # SAFETY: vehicle detected during closing → reopen immediately
        if self._sensor == SensorState.DETECTED:
            logger.warning("GateFSM: SAFETY — vehicle detected during closing → REOPENING")
            self._buzzer("GATE_SAFETY")
            self._transition_to(GateState.OPENING)
            self._servo_open()
            return

        # Gate travel simulation
        if self._gate_move_start and \
                (time.time() - self._gate_move_start) >= self.GATE_TRAVEL_TIME_SIM:
            self._transition_to(GateState.CLOSED)

    # ── Transition helper ────────────────────────────────────────────────── #

    def _transition_to(self, new_state: GateState) -> None:
        self._state = new_state
        if new_state in (GateState.OPENING, GateState.CLOSING):
            self._gate_move_start = time.time()
        else:
            self._gate_move_start = None

    # ── Simulation helpers ───────────────────────────────────────────────── #

    def sim_trigger_sensor_detected(self) -> None:
        """Simulation: vehicle arrives at sensor."""
        self.update_sensor(SensorState.DETECTED)

    def sim_trigger_sensor_cleared(self) -> None:
        """Simulation: vehicle clears the sensor."""
        self.update_sensor(SensorState.CLEAR)

    def sim_trigger_sensor_error(self) -> None:
        """Simulation: sensor failure — system enters safe CLOSED state."""
        logger.error("GateFSM: SENSOR_ERROR detected")
        self._sensor = SensorState.ERROR
        self._buzzer("SYSTEM_ERROR")
        # On sensor error: close gate for safety
        if self._state != GateState.CLOSED:
            self._transition_to(GateState.CLOSING)
            self._servo_close()
