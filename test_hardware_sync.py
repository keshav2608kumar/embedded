"""
Smart Parking Management System — Complete Hardware Sync & IR Auto-Binding Tool
"""

import sys
import time
import serial

PORT = "COM9"
BAUD = 115200

def run_hardware_sync_test():
    print("=" * 75)
    print("    SMART PARKING MANAGEMENT SYSTEM — IR SENSOR & BARRIER SYNC TOOL")
    print("=" * 75)
    print(f"[1] Connecting to ESP32 on {PORT} at {BAUD} baud...")

    try:
        s = serial.Serial(PORT, BAUD, timeout=1.0)
    except Exception as e:
        print(f"[ERROR] Could not open {PORT}: {e}")
        print("Please close any running python processes or serial monitors and try again.")
        return

    time.sleep(2.5)  # Allow boot
    s.reset_input_buffer()
    print("[2] Connected successfully!")

    # Perform initial pin scan
    s.write(b"<CMD,ACTION=SCAN_PINS>\n")
    s.flush()
    time.sleep(0.4)
    while s.in_waiting:
        line = s.readline().decode("utf-8", errors="ignore").strip()
        if "LIVE PIN" in line or "GPIO" in line or "Active IR" in line:
            print(f"    {line}")

    # Prime ESP32 with free slot (2 Free, Rec: S2)
    s.write(b"<PKT,S1=1,S2=0,S3=1,S4=0,FREE=2,REC=S2,STATUS=OK>\n")
    s.flush()

    print("\n[3] STARTING LIVE SENSOR MONITOR (AUTO-BINDING ACTIVE):")
    print("    -> Abhi apna HATH IR sensor ke aage 5-10 cm par layein!")
    print("    -> Jaise hi module ki LED jalegi, ESP32 turant us pin ko lock kar lega")
    print("       aur Servo Gate 90 deg upar khulega!")
    print("    -> Hath hatane par 10-second countdown shuru hoga aur gate wapas band hoga.")
    print("-" * 75)
    print("Press CTRL+C at any time to exit.\n")

    last_pkt_time = time.time()
    try:
        while True:
            if time.time() - last_pkt_time > 1.2:
                s.write(b"<PKT,S1=1,S2=0,S3=1,S4=0,FREE=2,REC=S2,STATUS=OK>\n")
                s.flush()
                last_pkt_time = time.time()

            if s.in_waiting:
                line = s.readline().decode("utf-8", errors="ignore").strip()
                if line:
                    clean = line.encode("ascii", errors="replace").decode("ascii")
                    if "AUTO-BIND" in clean:
                        print(f"\n>>> {clean} <<<\n")
                    elif "STATUS" in clean:
                        sensor = "DETECTED" if "Sensor:DETECTED" in clean else "CLEAR"
                        pin = clean.split("Pin:")[1].split()[0] if "Pin:" in clean else "23"
                        raw = clean.split("Raw:")[1].split()[0] if "Raw:" in clean else "1"
                        gate = clean.split("Gate:")[1].split()[0] if "Gate:" in clean else "?"
                        timer = clean.split("Timer:")[1].split()[0] if "Timer:" in clean else "0.0"
                        l1 = clean.split("L1:")[1].split("L2:")[0].strip() if "L1:" in clean else ""
                        l2 = clean.split("L2:")[1].strip() if "L2:" in clean else ""

                        tag = "[*] CAR AT BARRIER -> GATE OPEN!" if sensor == "DETECTED" else "[ ] Standby (Clear)"
                        print(f"IR:{sensor:<8} (GPIO {pin:<2}, Volt:{raw}) | Gate:{gate:<12} | Timer:{timer:>4}s | LCD: [{l1}] / [{l2}]  {tag}")

            time.sleep(0.04)

    except KeyboardInterrupt:
        print("\n\n[INFO] Stopped. Setting gate safely to CLOSED (0 deg)...")
        s.write(b"<CMD,ACTION=SERVO_CLOSE>\n")
        s.flush()
        time.sleep(0.4)
        s.close()
        print("[OK] Finished.")

if __name__ == "__main__":
    run_hardware_sync_test()
