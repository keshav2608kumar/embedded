import os
import sys
import time
import subprocess
import json
import serial
import serial.tools.list_ports
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT_DIR / "config" / "system_config.json"
ESP32_DIR = ROOT_DIR / "esp32"
PIO_PATH = Path(os.environ["USERPROFILE"]) / ".platformio" / "penv" / "Scripts" / "pio.exe"

print("=" * 60)
print("  ESP32 AUTO-DETECTION & FLASHING SERVICE")
print("=" * 60)
print(f"Project root: {ROOT_DIR}")
print(f"PlatformIO:   {PIO_PATH}")
print("\nWaiting for CP2102 COM port to become active...")

def find_cp210x_port():
    ports = serial.tools.list_ports.comports()
    for p in ports:
        desc = p.description.lower()
        hwid = (p.hwid or "").lower()
        if "cp210" in desc or "10c4" in hwid or ("silicon" in desc and "bluetooth" not in desc):
            return p.device
        # Also check for any new non-bluetooth USB serial port
        if "bthenum" not in hwid and ("usb" in hwid or "ftdi" in desc or "ch340" in desc):
            return p.device
    return None

target_port = None
start_time = time.time()
timeout = 300  # 5 minutes

while (time.time() - start_time) < timeout:
    port = find_cp210x_port()
    if port:
        target_port = port
        print(f"\n[FOUND] Detected ESP32 device on port: {target_port}!")
        break
    time.sleep(1.0)

if not target_port:
    print("[TIMEOUT] No CP2102 port detected within timeout.")
    sys.exit(1)

# Update system_config.json with port
try:
    with open(CONFIG_PATH, "r") as f:
        cfg = json.load(f)
    cfg.setdefault("communication", {}).setdefault("serial", {})["port"] = target_port
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)
    print(f"[CONFIG] Updated config/system_config.json with port {target_port}")
except Exception as e:
    print(f"[WARN] Could not update config: {e}")

# Flash firmware using PlatformIO
print(f"\n[FLASHING] Uploading firmware to ESP32 on {target_port}...")
cmd = [str(PIO_PATH), "run", "--target", "upload", "--upload-port", target_port]
env = os.environ.copy()
env["PYTHONIOENCODING"] = "utf-8"

res = subprocess.run(cmd, cwd=str(ESP32_DIR), env=env, capture_output=True, text=True)
print(res.stdout)
if res.returncode != 0:
    print(res.stderr)
    print("\n[ERROR] Flashing failed!")
    sys.exit(2)

print("\n[SUCCESS] Firmware uploaded successfully!")
print("[VERIFY] Opening serial connection to test handshake...")
time.sleep(2.0)

try:
    ser = serial.Serial(port=target_port, baudrate=115200, timeout=2.0)
    time.sleep(1.0)
    ser.write(b"<PKT,S1=0,S2=0,S3=0,S4=0,FREE=4,STATUS=OK>\n")
    time.sleep(0.5)
    lines = []
    for _ in range(5):
        if ser.in_waiting > 0:
            lines.append(ser.readline().decode("utf-8", errors="replace").strip())
    ser.close()
    print("[SERIAL RESPONSE]:")
    for line in lines:
        print("  -> " + line)
except Exception as e:
    print(f"[WARN] Serial handshake note: {e}")

print("\n========================================================")
print("  ESP32 FLASHING & INTEGRATION COMPLETE!")
print("========================================================")
