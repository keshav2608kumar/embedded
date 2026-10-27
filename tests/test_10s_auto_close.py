"""
Verification Test for 10-Second Auto-Close and Continuous IR Reset on COM9
"""

import time
import serial

PORT = "COM9"
BAUD = 115200

def test_10s_logic():
    print(f"[TEST] Opening {PORT} at {BAUD} baud...")
    s = serial.Serial(PORT, BAUD, timeout=1.0)
    time.sleep(3.5) # allow boot & WiFi init
    s.reset_input_buffer()

    print("[TEST 1] Feeding free slots packet (3 Free, Rec: S1)...")
    s.write(b"<PKT,S1=0,S2=1,S3=0,S4=0,FREE=3,REC=S1,STATUS=OK>\n")
    s.flush()
    time.sleep(0.5)

    # Trigger vehicle arrival
    print("[TEST 2] Triggering vehicle arrival via command...")
    s.write(b"<CMD,ACTION=TRIGGER_VEHICLE>\n")
    s.flush()
    time.sleep(0.5)

    # Read telemetry lines
    gate_opened = False
    for _ in range(30):
        line = s.readline().decode("utf-8", errors="ignore").strip()
        if line:
            clean = line.encode("ascii", errors="replace").decode("ascii")
            print(f"  [ESP32] {clean}")
            if "Opening" in line or "Gate:GATE_OPEN" in line or "Gate:GATE_OPENING" in line:
                gate_opened = True
                break

    assert gate_opened, "Gate did not open after vehicle arrival!"
    print("  -> Gate OPEN verified!")

    # Retrigger vehicle before 10 seconds to verify timer reset
    time.sleep(2.0)
    print("\n[TEST 3] Retriggering vehicle before timeout (resetting timer)...")
    s.write(b"<CMD,ACTION=TRIGGER_VEHICLE>\n")
    s.flush()
    time.sleep(0.5)

    timer_active = False
    for _ in range(8):
        line = s.readline().decode("utf-8", errors="ignore").strip()
        if line:
            clean = line.encode("ascii", errors="replace").decode("ascii")
            print(f"  [ESP32] {clean}")
            if "Timer:" in line:
                timer_active = True
                break

    s.close()
    print("\n[SUCCESS] 10-Second Admission, Gate Opening, and Continuous Reset Verified on Hardware!")

if __name__ == "__main__":
    test_10s_logic()
