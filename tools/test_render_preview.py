"""
Renders a sample frame of the new enhanced dashboard with live telemetry simulation
and saves it to dashboard_live_preview.jpg for visual verification.
"""

import sys
from pathlib import Path
import cv2
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from live_parking_dashboard import build_dashboard

# Create dummy video frame
dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
cv2.putText(dummy_frame, "CCTV PARKING CAM #1", (30, 240), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 255), 2)

slot_states = {
    "S1": "OCCUPIED",
    "S2": "FREE",
    "S3": "FREE",
    "S4": "OCCUPIED"
}

telemetry = {
    "free": 2,
    "rec": "S2",
    "gate": "GATE_OPEN",
    "adm": "APPROVED",
    "sensor": "DETECTED",
    "timer": 8.5,
    "comm": "OK",
    "l1": "ENTRY APPROVED  ",
    "l2": "PROCEED TO S2   ",
    "last_rx": 100.0,
}

canvas = build_dashboard(
    canvas_w=1440,
    canvas_h=810,
    video_frame=dummy_frame,
    slot_states=slot_states,
    latency_ms=14.2,
    avg_fps=42.5,
    serial_packet="<PKT,S1=1,S2=0,S3=0,S4=1,FREE=2,REC=S2,STATUS=OK>",
    video_name="Demo Video Feed",
    rec_slot="S2",
    telemetry=telemetry
)

out_path = PROJECT_ROOT / "dashboard_live_preview.jpg"
cv2.imwrite(str(out_path), canvas)
print(f"[OK] Saved dashboard preview to: {out_path} ({out_path.stat().st_size} bytes)")
