"""
Smart Parking Management System - Universal Real-Time Presentation Engine
Supports:
1. Crop Video (parking_crop_loop.mp4) with Deep Learning Slot CNN (ai/models/slot_cnn.pt)
2. Overhead CCTV (PKLot) with YOLOv8 Object Detector (ai/models/best.pt)
3. Webcam / Any video input

Features:
- Endless video loop
- Real-time GPU inference on NVIDIA GeForce RTX 3050 (<5ms latency)
- Dynamic Green (Free) / Red (Occupied) Bounding Boxes
- Big Professional Top Banner: 'SLOTS AVAILABLE' vs 'PARKING FULL'
- Virtual 16x2 LCD Hardware Screen (Laptop display)
- Live Telemetry Card (FPS, Latency, Counts)
- Keyboard controls: [SPACE] Pause | [R] Restart | [Q] Quit
"""

import sys
import os
import time
import argparse
from pathlib import Path
import cv2
import numpy as np
import torch
import torch.nn as nn
from torchvision import transforms

PROJECT_ROOT = Path(__file__).resolve().parent
YOLO_MODEL_PATH = PROJECT_ROOT / "ai" / "models" / "best.pt"
CNN_MODEL_PATH = PROJECT_ROOT / "ai" / "models" / "slot_cnn.pt"
MASK_PATH = PROJECT_ROOT / "ai" / "dataset" / "archive" / "parking" / "mask_crop.png"
DOWNLOADS_DIR = Path(r"C:\Users\kesha\Downloads")


# ── PyTorch Slot CNN Definition ───────────────────────────────────────────────
class ParkingSlotCNN(nn.Module):
    def __init__(self):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(3, 16, 3, padding=1),
            nn.BatchNorm2d(16),
            nn.ReLU(),
            nn.MaxPool2d(2, 2),
            nn.Conv2d(16, 32, 3, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(),
            nn.MaxPool2d(2, 2),
            nn.Conv2d(32, 64, 3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(),
            nn.AdaptiveAvgPool2d((4, 4))
        )
        self.classifier = nn.Sequential(
            nn.Dropout(0.2),
            nn.Linear(64 * 4 * 4, 64),
            nn.ReLU(),
            nn.Linear(64, 2)
        )

    def forward(self, x):
        x = self.features(x)
        x = x.view(x.size(0), -1)
        return self.classifier(x)


def find_latest_video():
    """Auto-detect the best verified parking video source."""
    # 1. Primary: 14-slot verified parking video
    crop_vid = PROJECT_ROOT / "parking_crop_loop.mp4"
    if crop_vid.exists():
        return str(crop_vid)

    # 2. Secondary: PKLot demo
    pklot_vid = PROJECT_ROOT / "demo_pklot_detection.mp4"
    if pklot_vid.exists():
        return str(pklot_vid)

    for ext in ("*.mp4", "*.avi"):
        for f in PROJECT_ROOT.glob(ext):
            fname = f.name.lower()
            if ("crop" in fname or "parking" in fname or "pklot" in fname) and not fname.startswith("test_"):
                return str(f)

    return "parking_crop_loop.mp4"


def draw_professional_hud(frame, empty_cnt, occ_cnt, latency_ms, fps):
    """Draws Top Status Banner, Telemetry, and Virtual 16x2 LCD on the screen."""
    h, w = frame.shape[:2]
    total_slots = empty_cnt + occ_cnt
    is_full = (total_slots > 0 and empty_cnt == 0)

    # 1. Top Banner
    banner_h = 55
    overlay = frame.copy()
    if is_full:
        bg_col = (0, 0, 180)  # Red
        t1 = "[ALERT] PARKING FULL  -  NO SLOTS AVAILABLE"
        t2 = "GATE: CLOSED  |  ACCESS DENIED  |  PLEASE WAIT"
    else:
        bg_col = (0, 140, 0)  # Green
        t1 = f"[WELCOME]  {empty_cnt} PARKING SLOTS AVAILABLE"
        t2 = "GATE: OPEN  |  ENTRY PERMITTED  |  PROCEED TO SPOT"

    cv2.rectangle(overlay, (0, 0), (w, banner_h), bg_col, -1)
    frame = cv2.addWeighted(overlay, 0.85, frame, 0.15, 0)
    cv2.putText(frame, t1, (15, 24), cv2.FONT_HERSHEY_DUPLEX, 0.65, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.putText(frame, t2, (15, 46), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (230, 255, 230) if not is_full else (255, 220, 220), 1, cv2.LINE_AA)

    # 2. Top Right Telemetry Card
    cw, ch = 230, 105
    cx, cy = w - cw - 12, banner_h + 10
    card_overlay = frame.copy()
    cv2.rectangle(card_overlay, (cx, cy), (cx + cw, cy + ch), (20, 20, 20), -1)
    cv2.rectangle(card_overlay, (cx, cy), (cx + cw, cy + ch), (60, 60, 60), 1)
    frame = cv2.addWeighted(card_overlay, 0.82, frame, 0.18, 0)

    rate = (occ_cnt / total_slots * 100) if total_slots > 0 else 0
    cv2.putText(frame, "LIVE SYSTEM TELEMETRY", (cx + 10, cy + 18), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 220, 255), 1, cv2.LINE_AA)
    cv2.putText(frame, f"Total Capacity : {total_slots} Slots", (cx + 10, cy + 38), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (230, 230, 230), 1, cv2.LINE_AA)
    cv2.putText(frame, f"Free Slots     : {empty_cnt}", (cx + 10, cy + 56), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (0, 255, 0), 1, cv2.LINE_AA)
    cv2.putText(frame, f"Occupied Slots : {occ_cnt} ({rate:.1f}%)", (cx + 10, cy + 74), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (0, 100, 255), 1, cv2.LINE_AA)
    cv2.putText(frame, f"RTX 3050 GPU   : {latency_ms:.1f} ms ({fps:.0f} FPS)", (cx + 10, cy + 94), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (180, 180, 180), 1, cv2.LINE_AA)

    # 3. Virtual 16x2 Hardware LCD (Bottom Left)
    lw, lh = 270, 70
    lx, ly = 12, h - lh - 12
    lcd_overlay = frame.copy()
    cv2.rectangle(lcd_overlay, (lx, ly), (lx + lw, ly + lh), (15, 35, 15), -1)
    cv2.rectangle(lcd_overlay, (lx, ly), (lx + lw, ly + lh), (0, 230, 100), 2)
    frame = cv2.addWeighted(lcd_overlay, 0.88, frame, 0.12, 0)

    cv2.putText(frame, "[ ESP32 16x2 I2C LCD ]", (lx + 8, ly - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.36, (0, 240, 120), 1, cv2.LINE_AA)
    if is_full:
        line1 = "SMART PARKING   "
        line2 = "PARKING FULL!   "
    else:
        line1 = f"FREE: {empty_cnt} SLOTS"
        line2 = "ENTRY PERMITTED "
    cv2.putText(frame, line1, (lx + 12, ly + 28), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (0, 255, 140), 2, cv2.LINE_AA)
    cv2.putText(frame, line2, (lx + 12, ly + 54), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (0, 255, 140), 2, cv2.LINE_AA)

    return frame


def run_live():
    parser = argparse.ArgumentParser(description="Smart Parking Live Real-time System")
    parser.add_argument("--source", default=None, help="Video path or webcam index (default: auto-detects latest video)")
    args = parser.parse_args()

    video_source = args.source
    if video_source is None or video_source == "" or video_source == "latest":
        video_source = find_latest_video()

    print("=" * 70)
    print("  SMART PARKING MANAGEMENT SYSTEM - REAL-TIME DEMO")
    print("=" * 70)
    print(f"[INFO] Video Feed   : {video_source}")

    is_crop_mode = ("crop" in str(video_source).lower() and MASK_PATH.exists() and CNN_MODEL_PATH.exists())
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    print(f"[INFO] Hardware     : {device} ({torch.cuda.get_device_name(0)})")

    # Load appropriate AI model
    if is_crop_mode:
        print(f"[INFO] Mode         : High-Resolution Slot CNN Mode (ai/models/slot_cnn.pt)")
        model = ParkingSlotCNN().to(device)
        model.load_state_dict(torch.load(str(CNN_MODEL_PATH), map_location=device))
        model.eval()

        mask_img = cv2.imread(str(MASK_PATH), cv2.IMREAD_GRAYSCALE)
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(mask_img)
        slot_boxes = [stats[i][:4] for i in range(1, num_labels)]
        print(f"[INFO] Slots Tracked: {len(slot_boxes)} parking spots")
        
        transform = transforms.Compose([
            transforms.ToPILImage(),
            transforms.Resize((32, 32)),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
        ])
    else:
        print(f"[INFO] Mode         : Universal YOLOv8 Object Detection Mode (ai/models/best.pt)")
        from ultralytics import YOLO
        yolo_model = YOLO(str(YOLO_MODEL_PATH))

    # Open Video
    src = int(video_source) if str(video_source).isdigit() else str(video_source)
    cap = cv2.VideoCapture(src)
    if not cap.isOpened():
        print(f"[ERROR] Could not open video: {src}")
        return

    fps_val = cap.get(cv2.CAP_PROP_FPS)
    fps_val = 30.0 if (fps_val is None or fps_val <= 0 or fps_val > 120) else fps_val
    frame_budget_ms = 1000.0 / fps_val

    win_name = "Smart Parking AI - Live Presentation Dashboard"
    cv2.namedWindow(win_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(win_name, 1100, 720)

    print("\n[INFO] Live Display Started! Press [SPACE] to Pause | [R] to Restart | [Q] to Exit\n")

    fps_history = []
    paused = False

    while True:
        if not paused:
            ret, frame = cap.read()
            if not ret:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue

            t0 = time.time()
            empty_cnt = 0
            occ_cnt = 0

            # ── AI Processing ─────────────────────────────────────────────────
            if is_crop_mode:
                # Batch slot inference
                slot_tensors = []
                valid_indices = []
                for idx, (x, y, w, h) in enumerate(slot_boxes):
                    crop = frame[y:y+h, x:x+w]
                    if crop.size > 0:
                        slot_tensors.append(transform(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)))
                        valid_indices.append((idx, x, y, w, h))

                if slot_tensors:
                    batch = torch.stack(slot_tensors).to(device)
                    with torch.no_grad():
                        preds = torch.argmax(model(batch), dim=1).cpu().numpy()

                    for pred, (idx, x, y, w, h) in zip(preds, valid_indices):
                        if pred == 0:  # empty
                            empty_cnt += 1
                            color = (0, 230, 0)  # Green
                            lbl = f"S{idx+1}: FREE"
                        else:  # occupied
                            occ_cnt += 1
                            color = (0, 0, 240)  # Red
                            lbl = f"S{idx+1}: OCC"

                        cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
                        cv2.rectangle(frame, (x, y - 16), (x + 75, y), color, -1)
                        cv2.putText(frame, lbl, (x + 3, y - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (0, 0, 0), 1, cv2.LINE_AA)
            else:
                results = yolo_model.predict(source=frame, conf=0.30, imgsz=416, device=0, half=True, verbose=False)[0]
                for box in results.boxes:
                    cls_id = int(box.cls[0])
                    conf = float(box.conf[0])
                    x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                    if cls_id == 0:
                        empty_cnt += 1
                        color = (0, 230, 0)
                        lbl = f"FREE {conf:.2f}"
                    else:
                        occ_cnt += 1
                        color = (0, 0, 240)
                        lbl = f"OCC {conf:.2f}"
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                    cv2.putText(frame, lbl, (x1, y1 - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.40, color, 1, cv2.LINE_AA)

            t1 = time.time()
            latency_ms = (t1 - t0) * 1000
            fps_history.append(1.0 / max(0.001, t1 - t0))
            if len(fps_history) > 30:
                fps_history.pop(0)
            avg_fps = sum(fps_history) / len(fps_history)

            # Draw HUD
            frame = draw_professional_hud(frame, empty_cnt, occ_cnt, latency_ms, avg_fps)
            cv2.imshow(win_name, frame)

        wait_delay = max(1, int(frame_budget_ms - latency_ms)) if not paused else 50
        key = cv2.waitKey(wait_delay) & 0xFF
        if key in [ord('q'), ord('Q'), 27]:
            break
        elif key == 32:
            paused = not paused
        elif key in [ord('r'), ord('R')]:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    run_live()
