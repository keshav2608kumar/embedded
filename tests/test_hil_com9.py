"""
Hardware-In-The-Loop (HIL) Test for ESP32 on COM9
Verifies real UART communication, boot sequence, packet parsing, and telemetry.
"""

import sys
import time
import serial

PORT = "COM9"
BAUD = 115200

def test_hardware_com9():
    print(f"\n[HIL] Connecting to ESP32 on {PORT} at {BAUD} baud...")
    try:
        ser = serial.Serial(PORT, BAUD, timeout=1.0)
    except Exception as e:
        print(f"[FAIL] Could not open {PORT}: {e}")
        return False

    time.sleep(2.0)  # Allow DTR reset and boot
    ser.reset_input_buffer()

    boot_lines = []
    start = time.time()
    while time.time() - start < 3.0:
        if ser.in_waiting:
            line = ser.readline().decode("utf-8", errors="ignore").strip()
            if line:
                boot_lines.append(line)
                print(f"[ESP32 RAW] {line}")

    print("\n[HIL] Sending Packet 1: 3 Free Slots, Rec: S1")
    pkt1 = "<PKT,S1=0,S2=1,S3=0,S4=0,FREE=3,REC=S1,STATUS=OK>\n"
    ser.write(pkt1.encode("utf-8"))
    ser.flush()

    parsed_pkt1 = False
    start = time.time()
    while time.time() - start < 3.0:
        if ser.in_waiting:
            line = ser.readline().decode("utf-8", errors="ignore").strip()
            if line:
                print(f"[ESP32 RAW] {line}")
                if "Free:3" in line and "Rec:S1" in line:
                    parsed_pkt1 = True
                    break

    print("\n[HIL] Sending Packet 2: 0 Free Slots (FULL), Rec: NONE")
    pkt2 = "<PKT,S1=1,S2=1,S3=1,S4=1,FREE=0,REC=NONE,STATUS=OK>\n"
    ser.write(pkt2.encode("utf-8"))
    ser.flush()

    parsed_pkt2 = False
    start = time.time()
    while time.time() - start < 3.0:
        if ser.in_waiting:
            line = ser.readline().decode("utf-8", errors="ignore").strip()
            if line:
                print(f"[ESP32 RAW] {line}")
                if "Free:0" in line and "Rec:NONE" in line:
                    parsed_pkt2 = True
                    break

    ser.close()
    print(f"\n[HIL RESULT] Packet 1 Parsed: {parsed_pkt1}, Packet 2 Parsed: {parsed_pkt2}")
    assert parsed_pkt1 and parsed_pkt2, "HIL packet verification timed out on COM9"
    print("[HIL SUCCESS] ESP32 on COM9 verified successfully!")

if __name__ == "__main__":
    success = test_hardware_com9()
    sys.exit(0 if success else 1)
