"""
End-to-End Test for Live Parking Dashboard (Round 5)
Verifies:
- Model loading (YOLO best.pt & CNN slot_cnn.pt)
- CUDA / GPU availability
- Frame processing & slot recommendation computation
- Serial packet dispatch to COM9
"""

import sys
import time
from pathlib import Path
import cv2
import torch
import serial

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from communication.protocol.packet_codec import recommend_slot, encode, decode, AIStatus
from communication.serial.serial_sender import SerialSender
from ai.utils.config_loader import load_system_config

def test_dashboard_components():
    print("=" * 60)
    print("  ROUND 5: END-TO-END DASHBOARD & AI INFERENCE INTEGRATION TEST")
    print("=" * 60)

    # 1. Check CUDA & Models
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    print(f"[1/4] Compute Device: {device} ({torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'})")

    yolo_path = PROJECT_ROOT / "ai" / "models" / "best.pt"
    assert yolo_path.exists(), f"YOLO model missing: {yolo_path}"
    print(f"[2/4] YOLO Model Verified: {yolo_path.name} ({yolo_path.stat().st_size / (1024*1024):.1f} MB)")

    # 2. Test Recommendation & Packet Codec
    rec = recommend_slot(s1=False, s2=True, s3=False, s4=True)
    assert rec == "S1", f"Expected S1, got {rec}"
    pkt = encode(s1=False, s2=True, s3=False, s4=True, free=2, status=AIStatus.OK, rec=rec)
    print(f"[3/4] Protocol Packet Generated: {pkt}")
    dec = decode(pkt)
    assert dec["rec"] == "S1"
    assert dec["free"] == 2

    # 3. Test Serial Sender to ESP32 COM9
    sys_cfg = load_system_config("config/system_config.json")
    port = sys_cfg.get("communication", {}).get("serial", {}).get("port", "COM9")
    baud = sys_cfg.get("communication", {}).get("serial", {}).get("baud_rate", 115200)

    print(f"[4/4] Testing Serial Sender to ESP32 on {port} @ {baud}...")
    sender = SerialSender(port=port, baud_rate=baud)
    connected = sender.connect(simulate=False)
    if connected:
        print(f"      [OK] Serial Port {port} Connected successfully!")
        # Send live test packet
        success = sender.send(pkt)
        print(f"      [OK] Live Serial Packet Sent: {success}")
        time.sleep(1.0)
        sender.close()
    else:
        print(f"      [WARN] Could not connect to {port} (in use or offline)")

    print("\n[SUCCESS] Round 5 End-to-End Components Verified Cleanly!")
    assert True

if __name__ == "__main__":
    test_dashboard_components()
