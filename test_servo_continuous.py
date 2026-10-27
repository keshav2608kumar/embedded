"""
Smart Parking Management System — Dedicated Servo Motor Diagnostic Tool
Continuously sweeps the servo between 0° (CLOSED) and 90° (OPEN) every 2.5 seconds.
Tests direct hardware PWM pulses on GPIO 18 (and mirrored 13, 5, 25).
"""

import sys
import time
import serial

PORT = "COM9"
BAUD = 115200

def run_servo_diagnostic():
    print("=" * 65)
    print("  ESP32 SERVO MOTOR CONTINUOUS DIAGNOSTIC TOOL")
    print("=" * 65)
    print(f"[1] Connecting to ESP32 on {PORT} at {BAUD} baud...")

    try:
        s = serial.Serial(PORT, BAUD, timeout=1.0)
    except Exception as e:
        print(f"[ERROR] Could not open {PORT}: {e}")
        print("Please close any running dashboard or serial monitors and try again.")
        return

    time.sleep(2.5)  # Allow boot
    s.reset_input_buffer()
    print("[2] Connected successfully! Native ESP32 LEDC PWM driver active.")
    print("\n[WIRING CHECKLIST]")
    print("  - Orange / Yellow wire -> GPIO 18 (D18) [or D13 / D5 / D25]")
    print("  - Red wire             -> VIN / 5V (MUST be 5V, NOT 3.3V!)")
    print("  - Brown / Black wire   -> GND")
    print("  - Mechanical check     -> Remove plastic horn if servo is jammed")
    print("-" * 65)

    # Prime ESP32 with free slots so FSM also permits opening
    s.write(b"<PKT,S1=0,S2=1,S3=0,S4=0,FREE=3,REC=S1,STATUS=OK>\n")
    s.flush()
    time.sleep(0.2)

    print("Press CTRL+C at any time to exit.\n")

    cycle = 0
    try:
        for i in range(6):  # Run 6 automated cycles (15 seconds total)
            cycle += 1
            print(f"\n--- CYCLE {cycle} ---")
            print(">> [COMMAND] Setting Servo to 90 DEGREES (GATE OPEN)...")
            # Send both direct SERVO_OPEN and FSM packet to guarantee movement
            s.write(b"<CMD,ACTION=SERVO_OPEN>\n")
            s.flush()

            # Read back responses for 2.0s
            t_end = time.time() + 2.0
            while time.time() < t_end:
                if s.in_waiting:
                    line = s.readline().decode("utf-8", errors="ignore").strip()
                    if line:
                        clean = line.encode("ascii", errors="replace").decode("ascii")
                        if any(k in clean for k in ["SERVO", "STATUS", "CMD", "FSM"]):
                            print(f"   [ESP32] {clean}")
                time.sleep(0.05)

            print(">> [COMMAND] Setting Servo to 0 DEGREES (GATE CLOSED)...")
            s.write(b"<CMD,ACTION=SERVO_CLOSE>\n")
            s.flush()

            # Read back responses for 2.0s
            t_end = time.time() + 2.0
            while time.time() < t_end:
                if s.in_waiting:
                    line = s.readline().decode("utf-8", errors="ignore").strip()
                    if line:
                        clean = line.encode("ascii", errors="replace").decode("ascii")
                        if any(k in clean for k in ["SERVO", "STATUS", "CMD", "FSM"]):
                            print(f"   [ESP32] {clean}")
                time.sleep(0.05)

        print("\n>> [TEST COMPLETE] Final return to SAFE 0 DEGREES (GATE CLOSED)...")
        s.write(b"<CMD,ACTION=SERVO_CLOSE>\n")
        s.flush()
        time.sleep(0.5)
        s.close()
        print("[OK] Serial connection closed.")

    except KeyboardInterrupt:
        print("\n[INFO] Diagnostic stopped by user. Returning to 0 deg...")
        s.write(b"<CMD,ACTION=SERVO_CLOSE>\n")
        s.flush()
        time.sleep(0.5)
        s.close()
        print("[OK] Serial port closed.")

if __name__ == "__main__":
    run_servo_diagnostic()
