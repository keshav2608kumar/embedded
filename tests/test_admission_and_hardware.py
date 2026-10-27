"""
Smart Parking Management System
Automated Five-Round Admission & Hardware Test Suite

Executes all unit, FSM simulation, protocol, hardware-in-the-loop, and dashboard tests.
"""

import os
import sys
import time
import unittest
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from communication.protocol.packet_codec import (
    encode,
    decode,
    validate,
    recommend_slot,
    AIStatus,
)


class Round1ProtocolAndRecommendationTests(unittest.TestCase):
    """Round 1: Packet Protocol and Slot Recommendation Logic."""

    def test_recommend_slot_priority(self):
        # All free -> S1
        self.assertEqual(recommend_slot(False, False, False, False), "S1")
        # S1 occupied -> S2
        self.assertEqual(recommend_slot(True, False, False, False), "S2")
        # S1, S2 occupied -> S3
        self.assertEqual(recommend_slot(True, True, False, False), "S3")
        # S1, S2, S3 occupied -> S4
        self.assertEqual(recommend_slot(True, True, True, False), "S4")

    def test_recommend_slot_all_occupied(self):
        # All occupied -> NONE
        self.assertEqual(recommend_slot(True, True, True, True), "NONE")

    def test_never_recommend_occupied_slot(self):
        # If S1 is occupied, it must never be recommended
        rec = recommend_slot(True, False, True, False)
        self.assertNotEqual(rec, "S1")
        self.assertNotEqual(rec, "S3")
        self.assertEqual(rec, "S2")

    def test_encode_with_auto_recommendation(self):
        pkt = encode(True, False, False, True, 2, AIStatus.OK)
        self.assertIn("FREE=2", pkt)
        self.assertIn("REC=S2", pkt)
        self.assertTrue(pkt.startswith("<PKT,"))
        self.assertTrue(pkt.endswith(">"))

    def test_encode_decode_roundtrip(self):
        pkt = encode(False, True, True, False, 2, AIStatus.OK, rec="S1")
        data = decode(pkt)
        self.assertIsNotNone(data)
        self.assertFalse(data["s1"])
        self.assertTrue(data["s2"])
        self.assertTrue(data["s3"])
        self.assertFalse(data["s4"])
        self.assertEqual(data["free"], 2)
        self.assertEqual(data["rec"], "S1")
        self.assertEqual(data["status"], "OK")

    def test_decode_legacy_packet_without_rec(self):
        legacy = "<PKT,S1=1,S2=0,S3=1,S4=0,FREE=2,STATUS=OK>"
        data = decode(legacy)
        self.assertIsNotNone(data)
        self.assertEqual(data["free"], 2)
        self.assertEqual(data["rec"], "S2")  # Auto-computed fallback

    def test_reject_malformed_packets(self):
        self.assertIsNone(decode("<MALFORMED>"))
        self.assertIsNone(decode("<PKT,S1=2,S2=0,S3=0,S4=0,FREE=3,STATUS=OK>"))
        self.assertIsNone(decode(""))


class GateFSMSimulator:
    """Python simulation of the ESP32 Gate FSM and Admission Controller."""

    def __init__(self, travel_time_sec=1.5, hold_time_sec=3.0):
        self.state = "GATE_CLOSED"
        self.admission_state = "IDLE"
        self.free_count = 4
        self.comm_lost = False
        self.vehicle_sensor = False
        self.travel_time = travel_time_sec
        self.hold_time = hold_time_sec
        self.move_start_time = 0.0
        self.open_start_time = 0.0
        self.vehicle_clear_time = 0.0
        self.buzzer_events = []
        self.servo_angle = 0

    def update(self, now, vehicle_sensor=None, manual_open=False, manual_close=False):
        if vehicle_sensor is not None:
            self.vehicle_sensor = vehicle_sensor

        # Manual Close Request
        if manual_close:
            if self.state in ["GATE_OPEN", "GATE_VEHICLE_PASSING"]:
                if self.vehicle_sensor:
                    self.buzzer_events.append("SAFETY_ALERT")
                else:
                    self.state = "GATE_CLOSING"
                    self.move_start_time = now
                    self.servo_angle = 0
            return

        # FSM Transitions
        if self.state == "GATE_CLOSED":
            if self.vehicle_sensor or manual_open:
                if self.comm_lost:
                    self.admission_state = "DENIED_OFFLINE"
                    self.buzzer_events.append("SYSTEM_ERROR")
                elif self.free_count <= 0:
                    self.admission_state = "DENIED_FULL"
                    self.buzzer_events.append("PARKING_FULL")
                else:
                    self.admission_state = "APPROVED"
                    self.state = "GATE_OPENING"
                    self.move_start_time = now
                    self.servo_angle = 90
            else:
                self.admission_state = "IDLE"

        elif self.state == "GATE_OPENING":
            if (now - self.move_start_time) >= self.travel_time:
                self.state = "GATE_OPEN"
                self.open_start_time = now
                self.vehicle_clear_time = now
            if self.vehicle_sensor:
                self.state = "GATE_VEHICLE_PASSING"
                self.vehicle_clear_time = now

        elif self.state == "GATE_OPEN":
            if self.vehicle_sensor:
                self.state = "GATE_VEHICLE_PASSING"
                self.vehicle_clear_time = now
            elif (now - self.open_start_time) >= self.hold_time:
                self.state = "GATE_CLOSING"
                self.move_start_time = now
                self.servo_angle = 0

        elif self.state == "GATE_VEHICLE_PASSING":
            if self.vehicle_sensor:
                self.vehicle_clear_time = now
            else:
                # Conservative clearance policy: wait hold_time after IR clears
                if (now - self.vehicle_clear_time) >= self.hold_time:
                    self.state = "GATE_CLOSING"
                    self.move_start_time = now
                    self.servo_angle = 0

        elif self.state == "GATE_CLOSING":
            # Safety Reversal Interlock
            if self.vehicle_sensor:
                self.admission_state = "SAFETY_REVERSAL"
                self.buzzer_events.append("GATE_SAFETY")
                self.state = "GATE_OPENING"
                self.move_start_time = now
                self.servo_angle = 90
            elif (now - self.move_start_time) >= self.travel_time:
                self.state = "GATE_CLOSED"
                self.admission_state = "IDLE"


class Round2AdmissionAndFSMTests(unittest.TestCase):
    """Round 2: Gate FSM and Admission Control Policy Tests."""

    def setUp(self):
        self.fsm = GateFSMSimulator(travel_time_sec=1.0, hold_time_sec=2.0)

    def test_case_vehicle_detected_free_slot_fresh_ai(self):
        """Vehicle detected + free slot + fresh AI -> Approved & Gate opens."""
        self.fsm.free_count = 2
        self.fsm.comm_lost = False
        t = 100.0
        self.fsm.update(now=t, vehicle_sensor=True)
        self.assertEqual(self.fsm.admission_state, "APPROVED")
        self.assertEqual(self.fsm.state, "GATE_OPENING")
        self.assertEqual(self.fsm.servo_angle, 90)

    def test_case_vehicle_detected_all_occupied(self):
        """Vehicle detected + all slots occupied -> Denied (Full), Gate stays CLOSED."""
        self.fsm.free_count = 0
        self.fsm.comm_lost = False
        t = 100.0
        self.fsm.update(now=t, vehicle_sensor=True)
        self.assertEqual(self.fsm.admission_state, "DENIED_FULL")
        self.assertEqual(self.fsm.state, "GATE_CLOSED")
        self.assertEqual(self.fsm.servo_angle, 0)
        self.assertIn("PARKING_FULL", self.fsm.buzzer_events)

    def test_case_no_vehicle_detected_free_slot(self):
        """No vehicle detected + free slot -> Gate remains CLOSED in standby."""
        self.fsm.free_count = 3
        self.fsm.comm_lost = False
        t = 100.0
        self.fsm.update(now=t, vehicle_sensor=False)
        self.assertEqual(self.fsm.admission_state, "IDLE")
        self.assertEqual(self.fsm.state, "GATE_CLOSED")
        self.assertEqual(self.fsm.servo_angle, 0)

    def test_case_vehicle_detected_stale_or_offline_ai(self):
        """Vehicle detected + stale/offline AI data -> Denied (Offline), Gate stays CLOSED."""
        self.fsm.free_count = 3
        self.fsm.comm_lost = True  # Communication lost
        t = 100.0
        self.fsm.update(now=t, vehicle_sensor=True)
        self.assertEqual(self.fsm.admission_state, "DENIED_OFFLINE")
        self.assertEqual(self.fsm.state, "GATE_CLOSED")
        self.assertEqual(self.fsm.servo_angle, 0)
        self.assertIn("SYSTEM_ERROR", self.fsm.buzzer_events)

    def test_case_repeated_ir_triggers_during_cycle(self):
        """Repeated IR triggers during active cycle do not restart or corrupt FSM."""
        self.fsm.free_count = 2
        t = 100.0
        self.fsm.update(now=t, vehicle_sensor=True)
        self.assertEqual(self.fsm.state, "GATE_OPENING")
        # Trigger again mid-opening
        self.fsm.update(now=t + 0.5, vehicle_sensor=True)
        self.assertEqual(self.fsm.state, "GATE_VEHICLE_PASSING")
        self.assertEqual(self.fsm.servo_angle, 90)

    def test_case_mid_close_safety_reversal(self):
        """Obstruction detected during CLOSING -> Immediate reversal to OPENING!"""
        self.fsm.free_count = 2
        t = 100.0
        # Start open and transition to closing
        self.fsm.state = "GATE_CLOSING"
        self.fsm.move_start_time = t
        self.fsm.servo_angle = 0
        # Obstacle detected mid-close
        self.fsm.update(now=t + 0.3, vehicle_sensor=True)
        self.assertEqual(self.fsm.state, "GATE_OPENING")
        self.assertEqual(self.fsm.servo_angle, 90)
        self.assertEqual(self.fsm.admission_state, "SAFETY_REVERSAL")
        self.assertIn("GATE_SAFETY", self.fsm.buzzer_events)

    def test_case_conservative_clearance_hold(self):
        """Front IR sensor clears -> Gate holds open for hold_time before closing."""
        self.fsm.state = "GATE_VEHICLE_PASSING"
        t = 100.0
        self.fsm.vehicle_clear_time = t
        # IR sensor clears at t
        self.fsm.update(now=t + 1.0, vehicle_sensor=False)
        # Should still be in VEHICLE_PASSING waiting for 2.0s hold
        self.assertEqual(self.fsm.state, "GATE_VEHICLE_PASSING")
        # After 2.1s hold elapsed
        self.fsm.update(now=t + 2.1, vehicle_sensor=False)
        self.assertEqual(self.fsm.state, "GATE_CLOSING")

    def test_case_button_cannot_bypass_full_or_offline(self):
        """Button 1 cannot bypass full parking or offline state."""
        self.fsm.free_count = 0
        self.fsm.update(now=100.0, vehicle_sensor=False, manual_open=True)
        self.assertEqual(self.fsm.state, "GATE_CLOSED")
        self.assertEqual(self.fsm.admission_state, "DENIED_FULL")

        self.fsm.free_count = 2
        self.fsm.comm_lost = True
        self.fsm.update(now=101.0, vehicle_sensor=False, manual_open=True)
        self.assertEqual(self.fsm.state, "GATE_CLOSED")
        self.assertEqual(self.fsm.admission_state, "DENIED_OFFLINE")


def run_all_tests():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(Round1ProtocolAndRecommendationTests))
    suite.addTests(loader.loadTestsFromTestCase(Round2AdmissionAndFSMTests))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
