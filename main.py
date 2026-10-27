"""
Smart Parking Management System
Main Entry Point

STATUS: IMPLEMENTED

Usage:
    python main.py --mode live          # real camera + real ESP32 serial
    python main.py --mode simulation    # no hardware needed; interactive terminal
    python main.py --mode hardware_test # test each ESP32 component individually

Simulation mode drives an interactive terminal UI that lets you:
    - Toggle S1-S4 occupied/free
    - Trigger vehicle at gate sensor
    - Simulate vehicle passing/clearing
    - Simulate communication failure
    - Simulate AI failure
    - Trigger gate safety event
All FSM logic, temporal filtering, occupancy tracking, and logging
run identically in both live and simulation modes.
"""

import argparse
import sys
import time
import threading
from pathlib import Path
from datetime import datetime


def resolve_project_root() -> Path:
    return Path(__file__).resolve().parent


def _add_project_to_path() -> None:
    root = str(resolve_project_root())
    if root not in sys.path:
        sys.path.insert(0, root)


_add_project_to_path()


# ─────────────────────────────────────────────────────────────────────────────
#  SIMULATION MODE
# ─────────────────────────────────────────────────────────────────────────────

def run_simulation(config: dict) -> None:
    """
    Interactive terminal simulation.
    Runs the full software stack (FSM, temporal filter, comms, logging)
    without any physical hardware.
    """
    from ai.utils.logger import setup_logger, EventLogger
    from ai.utils.config_loader import get
    from ai.tracking.temporal_filter import TemporalFilter, SlotState
    from communication.protocol.packet_codec import encode, AIStatus
    from communication.serial.serial_sender import SerialSender
    from communication.protocol.gate_fsm_sim import GateFSM, SensorState

    logger = setup_logger(log_dir=get(config, "logging", "log_dir", default="logs"))
    logger.info("=== SIMULATION MODE STARTED ===")

    # ── Initialise subsystems ──────────────────────────────────────────────
    tf_cfg   = config.get("temporal_filter", {})
    temporal = TemporalFilter(
        occupied_confirm_frames=tf_cfg.get("occupied_confirm_frames", 5),
        free_confirm_frames=tf_cfg.get("free_confirm_frames", 8),
    )

    # Pre-load initial slot states from config
    sim_cfg = config.get("simulation", {}).get("initial_slots", {})
    for slot_id, occupied in sim_cfg.items():
        if occupied:
            temporal.force_state(slot_id, SlotState.OCCUPIED)

    # Buzzer/servo callbacks for simulation (print-based)
    def buzzer_cb(pattern: str) -> None:
        PATTERNS = {
            "PARKING_FULL": "🔔 BUZZ — short repeated beeps (PARKING FULL)",
            "GATE_SAFETY":  "⚠️  BUZZ — two-tone alert (GATE SAFETY)",
            "SYSTEM_ERROR": "🚨 BUZZ — triple long beep (SYSTEM ERROR)",
        }
        print(f"\n  [{PATTERNS.get(pattern, f'BUZZ: {pattern}')}]")

    def servo_open_cb() -> None:
        print("  [SERVO] Gate → OPENING (angle: GATE_OPEN_ANGLE)")

    def servo_close_cb() -> None:
        print("  [SERVO] Gate → CLOSING (angle: GATE_CLOSED_ANGLE)")

    gate_fsm = GateFSM(
        on_buzzer=buzzer_cb,
        on_servo_open=servo_open_cb,
        on_servo_close=servo_close_cb,
    )

    serial_cfg = get(config, "communication", "serial", default={})
    sender = SerialSender(
        port=serial_cfg.get("port", "COM3"),
        baud_rate=serial_cfg.get("baud_rate", 115200),
    )
    sender.connect(simulate=True)    # simulation mode — no hardware

    event_log = EventLogger(
        log_dir=get(config, "logging", "log_dir", default="logs"),
        fmt=get(config, "logging", "log_format", default="csv"),
    )

    # ── Ticker thread (FSM needs periodic ticks) ───────────────────────────
    _running = [True]

    def ticker() -> None:
        while _running[0]:
            gate_fsm.tick()
            time.sleep(0.1)

    tick_thread = threading.Thread(target=ticker, daemon=True)
    tick_thread.start()

    # ── Helper: print current status ───────────────────────────────────────
    def print_status(ai_status: str = "AI_OK") -> None:
        states   = temporal.get_confirmed_states()
        available = temporal.get_available_count()
        sep = "-" * 50
        print("\n" + sep)
        print("  PARKING STATUS")
        print(sep)
        for sid, state in states.items():
            dur = temporal.get_current_occupancy_duration(sid)
            dur_str = f"  [{dur:.0f}s]" if dur is not None else ""
            icon = "[OCCUPIED]" if state == SlotState.OCCUPIED else \
                   "[FREE]    " if state == SlotState.FREE else "[UNCERTAIN]"
            print(f"  {sid}: {icon}{dur_str}")
        print(f"\n  AVAILABLE : {available}/4")
        print(f"  AI STATUS : {ai_status}")
        print(f"  GATE      : {gate_fsm.state_str}")
        print(sep)

        # Send packet
        states_bool = {k: v == SlotState.OCCUPIED for k, v in states.items()}
        packet = encode(
            states_bool["S1"], states_bool["S2"],
            states_bool["S3"], states_bool["S4"],
            available, ai_status
        )
        sender.send(packet)

        # Log
        event_log.log(
            slot_states=states_bool,
            available=available,
            ai_status=ai_status,
            comm_status=sender.comm_status(),
            gate_state=gate_fsm.state_str,
        )

    # ── Menu ──────────────────────────────────────────────────────────────
    MENU = """
  SIMULATION CONTROLS
  -----------------------------
  [1] Toggle S1 occupied/free
  [2] Toggle S2 occupied/free
  [3] Toggle S3 occupied/free
  [4] Toggle S4 occupied/free
  [5] Request vehicle entry (vehicle at gate)
  [6] Trigger vehicle-present sensor (vehicle passing)
  [7] Clear vehicle sensor (vehicle has passed)
  [8] Simulate communication failure
  [9] Simulate AI failure / camera error
  [0] Trigger gate closing safety event
  [s] Show current status
  [q] Quit
  -----------------------------
"""

    print("\n" + "=" * 50)
    print("  SMART PARKING SYSTEM - SIMULATION MODE")
    print("  STATUS: SIMULATED (no hardware)")
    print("=" * 50)
    print_status()
    print(MENU)

    ai_status = "AI_OK"
    comm_simulated_fail = False

    try:
        while True:
            try:
                choice = input("  Choice: ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                break

            if choice == "q":
                break

            elif choice in ("1", "2", "3", "4"):
                slot_id = f"S{choice}"
                current = temporal.get_confirmed_states()[slot_id]
                new_state = SlotState.FREE if current == SlotState.OCCUPIED \
                            else SlotState.OCCUPIED
                temporal.force_state(slot_id, new_state)
                print(f"\n  [SIM] {slot_id} → {new_state.value}")
                # Feed the FSM the updated free count
                gate_fsm.update_parking_status(temporal.get_available_count())
                print_status(ai_status)

            elif choice == "5":
                print("\n  [SIM] Vehicle requesting entry...")
                gate_fsm.request_entry()
                print_status(ai_status)

            elif choice == "6":
                print("\n  [SIM] Vehicle-present sensor: DETECTED")
                from communication.protocol.gate_fsm_sim import SensorState
                gate_fsm.sim_trigger_sensor_detected()
                print_status(ai_status)

            elif choice == "7":
                print("\n  [SIM] Vehicle-present sensor: CLEARED")
                gate_fsm.sim_trigger_sensor_cleared()
                print_status(ai_status)

            elif choice == "8":
                comm_simulated_fail = not comm_simulated_fail
                state = "LOST" if comm_simulated_fail else "RESTORED"
                print(f"\n  [SIM] Communication {state}")
                ai_status_comm = "COMM_LOST" if comm_simulated_fail else ai_status
                print_status(ai_status_comm)

            elif choice == "9":
                ai_status = "CAMERA_ERROR" if ai_status == "AI_OK" else "AI_OK"
                print(f"\n  [SIM] AI status toggled → {ai_status}")
                print_status(ai_status)

            elif choice == "0":
                print("\n  [SIM] Triggering GATE SAFETY EVENT...")
                print("  [SIM] Gate is CLOSING — vehicle detected → REOPENING")
                # Force gate to CLOSING state then trigger sensor
                from communication.protocol.gate_fsm_sim import GateState
                gate_fsm._state = GateState.CLOSING
                gate_fsm._gate_move_start = time.time() - 0.5  # mid-travel
                gate_fsm.sim_trigger_sensor_detected()
                print_status(ai_status)

            elif choice == "s":
                print_status(ai_status)

            else:
                print("  Unknown choice. Enter 1-9, 0, s, or q.")

    finally:
        _running[0] = False
        sender.close()
        event_log.close()
        logger.info("=== SIMULATION MODE ENDED ===")
        print("\n[INFO] Simulation ended. Logs saved to logs/")


# ─────────────────────────────────────────────────────────────────────────────
#  HARDWARE TEST MODE
# ─────────────────────────────────────────────────────────────────────────────

def run_hardware_test(config: dict) -> None:
    """
    Hardware test mode.
    Tests each ESP32 component independently over serial.

    STATUS: HARDWARE TEST REQUIRED
    Each test sends a specific command to the ESP32 and waits for response.
    """
    from ai.utils.config_loader import get
    from communication.protocol.packet_codec import encode, AIStatus

    print("\n" + "=" * 55)
    print("  SMART PARKING — HARDWARE TEST MODE")
    print("  STATUS: HARDWARE TEST REQUIRED")
    print("  Connect ESP32 and update COM port in config/system_config.json")
    print("=" * 55)

    serial_cfg = get(config, "communication", "serial", default={})
    port = serial_cfg.get("port", "COM3")
    baud = serial_cfg.get("baud_rate", 115200)

    TESTS = [
        ("1", "LCD Test",             f"<TEST,LCD>"),
        ("2", "Buzzer Test",          f"<TEST,BUZZER,PATTERN=FULL>"),
        ("3", "Servo Open Test",      f"<TEST,SERVO,CMD=OPEN>"),
        ("4", "Servo Close Test",     f"<TEST,SERVO,CMD=CLOSE>"),
        ("5", "Vehicle Sensor Read",  f"<TEST,SENSOR>"),
        ("6", "Serial Echo Test",     f"<TEST,ECHO,MSG=HELLO>"),
        ("7", "WDT Test (30s wait)",  f"<TEST,WDT>"),
        ("8", "Full FSM Scenario",    encode(False, True, False, True, 2, AIStatus.OK)),
    ]

    print(f"\n  Port: {port}  Baud: {baud}")
    print("\n  Available tests:")
    for tid, name, _ in TESTS:
        print(f"    [{tid}] {name}")
    print("    [q] Quit\n")

    try:
        import serial as pyserial
        ser = pyserial.Serial(port, baud, timeout=3)
        time.sleep(2.0)
        print(f"  [OK] Connected to {port}")
    except ImportError:
        print("  [ERROR] pyserial not installed: pip install pyserial")
        return
    except Exception as e:
        print(f"\n  [ERROR] Cannot connect to {port}: {e}")
        print("  [INFO] Check USB connection and COM port in config/system_config.json")
        return

    try:
        while True:
            choice = input("  Test number: ").strip().lower()
            if choice == "q":
                break

            test = next((t for t in TESTS if t[0] == choice), None)
            if not test:
                print("  Invalid choice.")
                continue

            tid, name, cmd = test
            print(f"\n  Running: {name}")
            print(f"  Sending: {cmd}")

            ser.write((cmd + "\n").encode("ascii"))
            time.sleep(0.2)

            response = ser.read(ser.in_waiting or 1).decode("ascii", errors="replace")
            print(f"  ESP32 Response: {response.strip() if response.strip() else '(no response within timeout)'}")
            print("  Status: HARDWARE TEST REQUIRED — record actual result above\n")

    finally:
        ser.close()
        print("\n[INFO] Hardware test session ended.")


# ─────────────────────────────────────────────────────────────────────────────
#  LIVE MODE
# ─────────────────────────────────────────────────────────────────────────────

def run_live(config: dict) -> None:
    """Run the full live system: camera + AI + serial + ESP32."""
    from ai.utils.config_loader import load_slot_config
    from ai.inference.run_cctv import run_inference

    slot_polygons = load_slot_config("config/parking_slots.json")

    raw_src = config.get("camera", {}).get("source", 0)
    try:
        source = int(raw_src)
    except (ValueError, TypeError):
        source = raw_src

    print("\n[INFO] Starting LIVE mode — real camera + real serial")
    run_inference(
        source=source,
        config=config,
        slot_polygons=slot_polygons,
        simulate_comm=False,
        show_display=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    _add_project_to_path()
    from ai.utils.config_loader import load_system_config

    parser = argparse.ArgumentParser(
        description="Smart Parking Management System"
    )
    parser.add_argument(
        "--mode",
        choices=["live", "simulation", "hardware_test"],
        default="simulation",
        help=(
            "live           = real camera + real ESP32\n"
            "simulation     = no hardware needed (default)\n"
            "hardware_test  = test ESP32 components individually"
        ),
    )
    parser.add_argument(
        "--config",
        default="config/system_config.json",
        help="Path to system configuration file",
    )
    args = parser.parse_args()

    project_root = resolve_project_root()
    config = load_system_config(str(project_root / args.config))

    print(f"\n{'='*55}")
    print("   SMART PARKING MANAGEMENT SYSTEM  v1.0")
    print("   CCTV + YOLOv8 + ESP32 + Gate FSM + WDT")
    print(f"{'='*55}")
    print(f"   Mode: {args.mode.upper()}")
    print(f"{'='*55}")

    if args.mode == "live":
        run_live(config)
    elif args.mode == "simulation":
        run_simulation(config)
    elif args.mode == "hardware_test":
        run_hardware_test(config)


if __name__ == "__main__":
    main()
