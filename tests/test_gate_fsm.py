"""
Unit Tests — Gate FSM (Python Simulation)

STATUS: IMPLEMENTED
Tests all gate FSM states and transitions including safety behaviour.
Run: python -m pytest tests/test_gate_fsm.py -v
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from communication.protocol.gate_fsm_sim import GateFSM, GateState, SensorState


def make_fsm():
    """Create a FSM with short travel time for fast tests."""
    fsm = GateFSM()
    fsm.GATE_TRAVEL_TIME_SIM = 0.05   # 50ms for fast unit tests
    return fsm


class TestInitialState:

    def test_starts_closed(self):
        fsm = make_fsm()
        assert fsm.state == GateState.CLOSED

    def test_sensor_starts_clear(self):
        fsm = make_fsm()
        assert fsm._sensor == SensorState.CLEAR


class TestClosedToOpening:

    def test_opens_when_free_slot_and_vehicle_request(self):
        fsm = make_fsm()
        fsm.update_parking_status(free_count=2)
        fsm.request_entry()
        assert fsm.state == GateState.OPENING

    def test_stays_closed_when_parking_full(self):
        fsm = make_fsm()
        fsm.update_parking_status(free_count=0)
        fsm.request_entry()
        assert fsm.state == GateState.CLOSED

    def test_stays_closed_without_vehicle_request(self):
        fsm = make_fsm()
        fsm.update_parking_status(free_count=4)
        # No request_entry() called
        assert fsm.state == GateState.CLOSED


class TestOpeningToOpen:

    def test_transitions_to_open_after_travel(self):
        fsm = make_fsm()
        fsm.update_parking_status(2)
        fsm.request_entry()
        assert fsm.state == GateState.OPENING
        time.sleep(0.1)    # wait for travel time
        fsm.tick()
        assert fsm.state == GateState.OPEN


class TestOpenToVehiclePassing:

    def test_vehicle_passing_when_sensor_detected(self):
        fsm = make_fsm()
        fsm.update_parking_status(2)
        fsm.request_entry()
        time.sleep(0.1)
        fsm.tick()   # → OPEN
        assert fsm.state == GateState.OPEN
        fsm.sim_trigger_sensor_detected()
        assert fsm.state == GateState.VEHICLE_PASSING


class TestVehiclePassingToClosing:

    def test_starts_closing_when_sensor_cleared(self):
        fsm = make_fsm()
        fsm.update_parking_status(2)
        fsm.request_entry()
        time.sleep(0.1)
        fsm.tick()   # → OPEN
        fsm.sim_trigger_sensor_detected()    # → VEHICLE_PASSING
        assert fsm.state == GateState.VEHICLE_PASSING
        fsm.sim_trigger_sensor_cleared()     # → CLOSING
        assert fsm.state == GateState.CLOSING


class TestClosingToClosed:

    def test_reaches_closed_after_travel(self):
        fsm = make_fsm()
        fsm.update_parking_status(2)
        fsm.request_entry()
        time.sleep(0.1); fsm.tick()           # OPENING → OPEN
        fsm.sim_trigger_sensor_detected()     # → VEHICLE_PASSING
        fsm.sim_trigger_sensor_cleared()      # → CLOSING
        time.sleep(0.1); fsm.tick()           # CLOSING → CLOSED
        assert fsm.state == GateState.CLOSED


class TestSafetyTransition:

    def test_closing_to_opening_when_sensor_detected(self):
        """SAFETY: vehicle detected during closing → gate REOPENS."""
        fsm = make_fsm()
        fsm.update_parking_status(2)
        fsm.request_entry()
        time.sleep(0.1); fsm.tick()           # → OPEN
        fsm.sim_trigger_sensor_detected()     # → VEHICLE_PASSING
        fsm.sim_trigger_sensor_cleared()      # → CLOSING
        # Simulate vehicle detected mid-close
        fsm.sim_trigger_sensor_detected()     # SAFETY → OPENING
        assert fsm.state == GateState.OPENING

    def test_buzzer_called_on_safety(self):
        patterns = []
        fsm = GateFSM(on_buzzer=lambda p: patterns.append(p))
        fsm.GATE_TRAVEL_TIME_SIM = 0.05
        fsm.update_parking_status(2)
        fsm.request_entry()
        time.sleep(0.1); fsm.tick()
        fsm.sim_trigger_sensor_detected()
        fsm.sim_trigger_sensor_cleared()
        fsm.sim_trigger_sensor_detected()    # SAFETY → buzzer
        assert "GATE_SAFETY" in patterns


class TestParkingFullBuzzer:

    def test_buzzer_on_full_with_vehicle_request(self):
        patterns = []
        fsm = GateFSM(on_buzzer=lambda p: patterns.append(p))
        fsm.GATE_TRAVEL_TIME_SIM = 0.05
        fsm.update_parking_status(0)    # full
        fsm.request_entry()
        assert "PARKING_FULL" in patterns

    def test_gate_stays_closed_when_full(self):
        fsm = make_fsm()
        fsm.update_parking_status(0)
        fsm.request_entry()
        assert fsm.state == GateState.CLOSED


class TestSensorError:

    def test_sensor_error_closes_gate(self):
        fsm = make_fsm()
        fsm.update_parking_status(2)
        fsm.request_entry()
        time.sleep(0.1); fsm.tick()   # → OPEN
        fsm.sim_trigger_sensor_error()
        assert fsm.state in (GateState.CLOSING, GateState.CLOSED)


class TestFullScenario:

    def test_complete_cycle(self):
        """Full end-to-end FSM cycle: CLOSED → OPENING → OPEN → PASSING → CLOSING → CLOSED."""
        fsm = make_fsm()
        # Start
        assert fsm.state == GateState.CLOSED
        # Vehicle arrives, slot free
        fsm.update_parking_status(2)
        fsm.request_entry()
        assert fsm.state == GateState.OPENING
        # Gate opens
        time.sleep(0.1); fsm.tick()
        assert fsm.state == GateState.OPEN
        # Vehicle passes
        fsm.sim_trigger_sensor_detected()
        assert fsm.state == GateState.VEHICLE_PASSING
        # Vehicle clears
        fsm.sim_trigger_sensor_cleared()
        assert fsm.state == GateState.CLOSING
        # Gate closes
        time.sleep(0.1); fsm.tick()
        assert fsm.state == GateState.CLOSED
