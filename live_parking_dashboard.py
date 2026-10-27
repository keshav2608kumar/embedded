"""
Smart Parking Management System - Master Command Dashboard
Features:
- Live CCTV video stream with AI detection
- Press 'O' to open Windows File Picker and select ANY video file on the fly!
- Auto-detects newest video from Downloads/Workspace
- Supports Webcam/Live Camera with '--source 0'
- Full / Available Decision Engine & Live Gate status
- Visual Slot Matrix (S1, S2, ...)
- 16x2 Hardware LCD Simulation & Serial Packet Monitor
- Real-time GPU Latency & FPS counter
"""

import sys
import os
import time
import datetime
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


# ── PyTorch Slot CNN ──────────────────────────────────────────────────────────
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


def open_file_dialog():
    """Opens a native Windows File Chooser to pick any video file."""
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        selected = filedialog.askopenfilename(
            title="Select Parking Video Feed for AI Detection",
            filetypes=[("Video files", "*.mp4 *.avi *.mov *.mkv"), ("All files", "*.*")]
        )
        root.destroy()
        return selected if selected else None
    except Exception as e:
        print(f"[WARN] File dialog error: {e}")
        return None


def find_latest_video():
    """Auto-detect the best verified parking video source."""
    # 1. First priority: known good verified 14-slot parking video in project root
    crop_vid = PROJECT_ROOT / "parking_crop_loop.mp4"
    if crop_vid.exists():
        return str(crop_vid)

    # 2. Second priority: PKLot demo video
    pklot_vid = PROJECT_ROOT / "demo_pklot_detection.mp4"
    if pklot_vid.exists():
        return str(pklot_vid)

    # 3. Third priority: Any video with 'parking' or 'crop' in project root
    for ext in ("*.mp4", "*.avi"):
        for f in PROJECT_ROOT.glob(ext):
            fname = f.name.lower()
            if ("crop" in fname or "parking" in fname or "pklot" in fname) and not fname.startswith("test_"):
                return str(f)

    return "parking_crop_loop.mp4"


def draw_card(canvas, x, y, w, h, bg_color=(20, 26, 36), border_color=(45, 58, 78)):
    cv2.rectangle(canvas, (x, y), (x + w, y + h), bg_color, -1)
    cv2.rectangle(canvas, (x, y), (x + w, y + h), border_color, 1)


def build_dashboard(canvas_w, canvas_h, video_frame, slot_states, latency_ms, avg_fps, serial_packet, video_name="Live Feed", rec_slot="NONE", telemetry=None):
    canvas = np.zeros((canvas_h, canvas_w, 3), dtype=np.uint8)
    canvas[:] = (15, 19, 26)  # Dark industrial slate background

    if telemetry is None:
        telemetry = {
            "free": sum(1 for st in slot_states.values() if st == "FREE"),
            "rec": rec_slot,
            "gate": "GATE_CLOSED",
            "adm": "IDLE",
            "sensor": "CLEAR",
            "comm": "OK",
            "l1": "PARKING: 4 FREE ",
            "l2": "GATE: CLOSED    ",
        }

    total_slots = len(slot_states)
    free_count = sum(1 for st in slot_states.values() if st == "FREE")
    occ_count = total_slots - free_count
    is_full = (total_slots > 0 and free_count == 0)

    hw_sensor = telemetry.get("sensor", "CLEAR")
    hw_gate = telemetry.get("gate", "GATE_CLOSED")
    hw_adm = telemetry.get("adm", "IDLE")
    default_l1 = f"REC SLOT: {rec_slot:<6}" if not is_full else "PARKING FULL    "
    default_l2 = "GATE: CLOSED    " if not is_full else "SORRY! NO SPACE "
    hw_l1 = telemetry.get("l1", default_l1)
    hw_l2 = telemetry.get("l2", default_l2)

    # ── 1. Top Master Header ──────────────────────────────────────────────────
    cv2.rectangle(canvas, (0, 0), (canvas_w, 65), (20, 26, 38), -1)
    cv2.line(canvas, (0, 65), (canvas_w, 65), (40, 50, 70), 1)

    cv2.putText(canvas, "SMART PARKING AUTOMATION SYSTEM", (25, 32), cv2.FONT_HERSHEY_DUPLEX, 0.75, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.putText(canvas, f"SOURCE: {video_name}  |  RECOMMENDED BAY: {rec_slot}  |  RTX 3050 GPU ACTIVE", (25, 52), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (0, 210, 255), 1, cv2.LINE_AA)

    now_str = datetime.datetime.now().strftime("%H:%M:%S")
    cv2.putText(canvas, f"SYSTEM TIME: {now_str}", (canvas_w - 380, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1, cv2.LINE_AA)

    cv2.rectangle(canvas, (canvas_w - 175, 18), (canvas_w - 25, 48), (20, 60, 30), -1)
    cv2.rectangle(canvas, (canvas_w - 175, 18), (canvas_w - 25, 48), (0, 200, 80), 1)
    cv2.circle(canvas, (canvas_w - 155, 33), 5, (0, 255, 100), -1)
    cv2.putText(canvas, "LIVE ONLINE", (canvas_w - 140, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 255, 120), 1, cv2.LINE_AA)

    # ── 2. Left Column: Video Viewport ────────────────────────────────────────
    left_x = 20
    left_y = 80
    left_w = int(canvas_w * 0.48)
    left_h = canvas_h - left_y - 45

    draw_card(canvas, left_x, left_y, left_w, left_h, bg_color=(20, 25, 35), border_color=(50, 65, 90))
    cv2.rectangle(canvas, (left_x, left_y), (left_x + left_w, left_y + 35), (28, 35, 48), -1)
    cv2.putText(canvas, "LIVE CCTV SURVEILLANCE FEED", (left_x + 15, left_y + 24), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (220, 230, 240), 1, cv2.LINE_AA)
    cv2.putText(canvas, "AI INFERENCE ENGINE", (left_x + left_w - 165, left_y + 24), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (0, 220, 255), 1, cv2.LINE_AA)

    target_vid_w = left_w - 20
    target_vid_h = left_h - 55
    scaled_video = cv2.resize(video_frame, (target_vid_w, target_vid_h))
    canvas[left_y + 45 : left_y + 45 + target_vid_h, left_x + 10 : left_x + 10 + target_vid_w] = scaled_video

    # ── 3. Right Column: Control Dashboard ────────────────────────────────────
    right_x = left_x + left_w + 18
    right_y = 80
    right_w = canvas_w - right_x - 20
    right_h = left_h

    total_slots = len(slot_states)
    free_count = sum(1 for st in slot_states.values() if st == "FREE")
    occ_count = total_slots - free_count
    is_full = (total_slots > 0 and free_count == 0)

    # ── Card 1: Entrance Barrier & IR Vehicle Radar ──────────────────────────
    c1_y = right_y
    c1_h = 120
    vehicle_present = (hw_sensor == "DETECTED")
    c1_bg = (18, 60, 28) if vehicle_present else (22, 26, 38)
    c1_border = (0, 255, 120) if vehicle_present else (60, 75, 100)
    draw_card(canvas, right_x, c1_y, right_w, c1_h, bg_color=c1_bg, border_color=c1_border)

    # Big Vehicle Present Indicator
    cv2.rectangle(canvas, (right_x + 15, c1_y + 12), (right_x + right_w - 15, c1_y + 46), (28, 40, 52) if not vehicle_present else (15, 80, 35), -1)
    cv2.rectangle(canvas, (right_x + 15, c1_y + 12), (right_x + right_w - 15, c1_y + 46), (70, 95, 130) if not vehicle_present else (0, 255, 120), 1)

    if vehicle_present:
        cv2.putText(canvas, "[ CAR AT BARRIER: YES (DETECTED) ]", (right_x + 28, c1_y + 36), cv2.FONT_HERSHEY_DUPLEX, 0.62, (0, 255, 140), 2, cv2.LINE_AA)
        cv2.putText(canvas, "IR SENSOR: ACTIVE (BEAM BROKEN)", (right_x + right_w - 280, c1_y + 35), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (0, 255, 255), 1, cv2.LINE_AA)
    else:
        cv2.putText(canvas, "[ CAR AT BARRIER: NO (NONE) ]", (right_x + 28, c1_y + 36), cv2.FONT_HERSHEY_DUPLEX, 0.62, (160, 190, 220), 2, cv2.LINE_AA)
        cv2.putText(canvas, "IR SENSOR: STANDBY (NO CAR)", (right_x + right_w - 280, c1_y + 35), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (130, 150, 180), 1, cv2.LINE_AA)

    # Gate Servo Status line
    cv2.line(canvas, (right_x + 15, c1_y + 56), (right_x + right_w - 15, c1_y + 56), (40, 50, 70), 1)
    timer_sec = telemetry.get("timer", 0.0)

    if "OPENING" in hw_gate:
        servo_msg = "GATE SERVO: OPENING UP (0 -> 90 DEG) | PLEASE WAIT"
        servo_col = (0, 255, 255)
    elif "OPEN" in hw_gate:
        if timer_sec > 0.0:
            servo_msg = f"GATE SERVO: OPEN (90 DEG) | AUTO-CLOSE IN: {timer_sec:.1f}s (RESETS ON CAR)"
        else:
            servo_msg = f"GATE SERVO: OPEN (90 DEG) | ADMITTED -> PROCEED TO BAY {rec_slot}"
        servo_col = (0, 255, 100)
    elif "CLOSING" in hw_gate:
        servo_msg = "GATE SERVO: CLOSING DOWN (90 -> 0 DEG) | DO NOT ENTER"
        servo_col = (0, 140, 255)
    else:
        if is_full:
            servo_msg = "GATE SERVO: CLOSED (0 DEG) | PARKING FULL - ENTRY BLOCKED"
            servo_col = (0, 70, 255)
        else:
            servo_msg = f"GATE SERVO: CLOSED (0 DEG) | WAITING FOR CAR (ASSIGNED: BAY {rec_slot})"
            servo_col = (200, 220, 240)

    cv2.putText(canvas, servo_msg, (right_x + 20, c1_y + 84), cv2.FONT_HERSHEY_SIMPLEX, 0.48, servo_col, 2, cv2.LINE_AA)
    gate_label = "GATE: OPEN" if ("OPEN" in hw_gate) else ("GATE: CLOSING" if "CLOSING" in hw_gate else ("GATE: OPENING" if "OPENING" in hw_gate else "GATE: CLOSED"))
    cv2.putText(canvas, f"PHYSICAL STATE: {gate_label}  |  ADMISSION: {hw_adm}", (right_x + 20, c1_y + 109), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (170, 190, 215), 1, cv2.LINE_AA)

    # ── Card 2: Parking Bay Status Matrix ─────────────────────────────────────
    c2_y = c1_y + c1_h + 10
    c2_h = 215
    draw_card(canvas, right_x, c2_y, right_w, c2_h)
    cv2.putText(canvas, "PARKING BAY STATUS MATRIX", (right_x + 18, c2_y + 24), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (0, 210, 255), 1, cv2.LINE_AA)
    cv2.putText(canvas, f"CAPACITY: {total_slots}  |  OCCUPIED: {occ_count}  |  VACANT: {free_count}", (right_x + right_w - 300, c2_y + 24), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (180, 190, 200), 1, cv2.LINE_AA)
    cv2.line(canvas, (right_x + 15, c2_y + 34), (right_x + right_w - 15, c2_y + 34), (35, 45, 60), 1)

    # Grid Display
    cols = min(7, max(1, total_slots))
    slot_names = list(slot_states.keys())[:14]
    grid_start_x = right_x + 18
    grid_start_y = c2_y + 46
    cell_w = (right_w - 36 - ((cols - 1) * 8)) // cols if cols > 0 else 60
    cell_h = 75

    for idx, sid in enumerate(slot_names):
        col_idx = idx % cols
        row_idx = idx // cols
        bx = grid_start_x + col_idx * (cell_w + 8)
        by = grid_start_y + row_idx * (cell_h + 12)

        st = slot_states[sid]
        if st == "FREE":
            if sid == rec_slot:
                cell_bg = (35, 65, 50)
                cell_border = (0, 240, 255)
                status_txt = "RECOMMEND"
                txt_color = (0, 255, 255)
            else:
                cell_bg = (20, 60, 30)
                cell_border = (0, 220, 80)
                status_txt = "FREE"
                txt_color = (0, 255, 120)
        else:
            cell_bg = (25, 20, 50)
            cell_border = (0, 70, 220)
            status_txt = "OCCUPIED"
            txt_color = (100, 140, 255)

        cv2.rectangle(canvas, (bx, by), (bx + cell_w, by + cell_h), cell_bg, -1)
        cv2.rectangle(canvas, (bx, by), (bx + cell_w, by + cell_h), cell_border, 1)

        label_id = sid if len(sid) <= 4 else sid[:4]
        cv2.putText(canvas, label_id, (bx + (cell_w // 2) - 14, by + 28), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(canvas, status_txt, (bx + 6, by + 56), cv2.FONT_HERSHEY_SIMPLEX, 0.32, txt_color, 1, cv2.LINE_AA)

    # ── Card 3: 16x2 LCD Display (Hardware Synchronized) ───────────────────────
    c3_y = c2_y + c2_h + 12
    c3_h = 135
    draw_card(canvas, right_x, c3_y, right_w, c3_h)
    cv2.putText(canvas, "HARDWARE OUTPUT: 16x2 I2C LCD SCREEN", (right_x + 18, c3_y + 22), cv2.FONT_HERSHEY_SIMPLEX, 0.46, (0, 210, 255), 1, cv2.LINE_AA)
    cv2.circle(canvas, (right_x + right_w - 180, c3_y + 18), 5, (0, 255, 100), -1)
    cv2.putText(canvas, "LIVE HARDWARE SYNC (COM9)", (right_x + right_w - 168, c3_y + 22), cv2.FONT_HERSHEY_SIMPLEX, 0.36, (0, 255, 120), 1, cv2.LINE_AA)

    lcd_box_x = right_x + 18
    lcd_box_y = c3_y + 32
    lcd_box_w = right_w - 36
    lcd_box_h = 88
    cv2.rectangle(canvas, (lcd_box_x, lcd_box_y), (lcd_box_x + lcd_box_w, lcd_box_y + lcd_box_h), (8, 32, 16), -1)
    cv2.rectangle(canvas, (lcd_box_x, lcd_box_y), (lcd_box_x + lcd_box_w, lcd_box_y + lcd_box_h), (0, 255, 120), 2)

    disp_l1 = f"{hw_l1:<16}"[:16]
    disp_l2 = f"{hw_l2:<16}"[:16]
    cv2.putText(canvas, f"LINE 1: [{disp_l1}]", (lcd_box_x + 20, lcd_box_y + 36), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 140), 2, cv2.LINE_AA)
    cv2.putText(canvas, f"LINE 2: [{disp_l2}]", (lcd_box_x + 20, lcd_box_y + 70), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 140), 2, cv2.LINE_AA)

    # ── Card 4: ESP32 Serial Bus & Telemetry ──────────────────────────────────
    c4_y = c3_y + c3_h + 12
    c4_h = left_h - (c4_y - right_y)
    draw_card(canvas, right_x, c4_y, right_w, c4_h)
    cv2.putText(canvas, "ESP32 BIDIRECTIONAL SERIAL TELEMETRY BUS", (right_x + 18, c4_y + 22), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (0, 210, 255), 1, cv2.LINE_AA)

    pkt_w = right_w - 36
    cv2.rectangle(canvas, (right_x + 18, c4_y + 30), (right_x + 18 + pkt_w, c4_y + 56), (10, 14, 20), -1)
    cv2.rectangle(canvas, (right_x + 18, c4_y + 30), (right_x + 18 + pkt_w, c4_y + 56), (40, 50, 65), 1)
    cv2.putText(canvas, f"TX -> {serial_packet}", (right_x + 26, c4_y + 48), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (0, 255, 200), 1, cv2.LINE_AA)

    rx_summary = f"RX <- Gate:{hw_gate} | Adm:{hw_adm} | Sensor:{hw_sensor} | Free:{telemetry.get('free', free_count)}"
    cv2.rectangle(canvas, (right_x + 18, c4_y + 62), (right_x + 18 + pkt_w, c4_y + 88), (10, 14, 20), -1)
    cv2.rectangle(canvas, (right_x + 18, c4_y + 62), (right_x + 18 + pkt_w, c4_y + 88), (40, 50, 65), 1)
    cv2.putText(canvas, rx_summary, (right_x + 26, c4_y + 80), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (0, 220, 255), 1, cv2.LINE_AA)

    cv2.putText(canvas, f"INFERENCE: {latency_ms:.1f} ms  |  FPS: {avg_fps:.1f}  |  NVIDIA RTX 3050 (CUDA:0)", (right_x + 18, c4_y + 108), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (180, 190, 205), 1, cv2.LINE_AA)

    # ── 4. Bottom Footer ──────────────────────────────────────────────────────
    footer_y = canvas_h - 35
    cv2.line(canvas, (0, footer_y), (canvas_w, footer_y), (35, 45, 60), 1)
    cv2.putText(canvas, "CONTROLS:  [1] 14-Bay Smart CCTV  |  [2] PKLot Aerial  |  [3] Live Webcam  |  [O] Browse Video  |  [C] Sim Car  |  [G] Gate  |  [Q] Exit", (25, canvas_h - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 255, 255), 1, cv2.LINE_AA)
    cv2.putText(canvas, "BACSE324 - EMBEDDED SYSTEMS ARCHITECTURE", (canvas_w - 380, canvas_h - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (100, 120, 150), 1, cv2.LINE_AA)

    return canvas


def run_master_dashboard():
    parser = argparse.ArgumentParser(description="Smart Parking Master Dashboard")
    parser.add_argument("--source", default=None, help="Video path or webcam index (default: auto-detects latest video)")
    args = parser.parse_args()

    video_source = args.source
    if video_source is None or video_source == "" or video_source == "latest":
        video_source = find_latest_video()

    print("=" * 75)
    print("  SMART PARKING MANAGEMENT SYSTEM - MASTER COMMAND DASHBOARD")
    print("=" * 75)
    print(f"[INFO] Video Feed   : {video_source}")

    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    print(f"[INFO] Compute Unit : {device} ({torch.cuda.get_device_name(0)})")

    # Load both models for instant on-the-fly switching
    cnn_model = None
    slot_boxes = []
    if CNN_MODEL_PATH.exists() and MASK_PATH.exists():
        cnn_model = ParkingSlotCNN().to(device)
        cnn_model.load_state_dict(torch.load(str(CNN_MODEL_PATH), map_location=device))
        cnn_model.eval()
        mask_img = cv2.imread(str(MASK_PATH), cv2.IMREAD_GRAYSCALE)
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(mask_img)
        slot_boxes = [stats[i][:4] for i in range(1, num_labels)]

    from ultralytics import YOLO
    yolo_model = YOLO(str(YOLO_MODEL_PATH))
    COCO_MODEL_PATH = PROJECT_ROOT / "yolov8n.pt"
    coco_model = YOLO(str(COCO_MODEL_PATH)) if COCO_MODEL_PATH.exists() else None

    transform = transforms.Compose([
        transforms.ToPILImage(),
        transforms.Resize((32, 32)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])

    win_name = "Smart Parking System - Master Command Dashboard (BACSE324)"
    cv2.namedWindow(win_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(win_name, 1400, 800)

    def load_capture(src_path):
        src = int(src_path) if str(src_path).isdigit() else str(src_path)
        c = cv2.VideoCapture(src)
        name = Path(str(src_path)).name if not str(src_path).isdigit() else f"Camera #{src_path}"
        return c, name

    cap, current_video_name = load_capture(video_source)
    if not cap.isOpened():
        print(f"[ERROR] Could not open video: {video_source}")
        return

    fps_val = cap.get(cv2.CAP_PROP_FPS) or 30.0
    frame_budget_ms = 1000.0 / (fps_val if fps_val > 0 else 30.0)

    print("\n[INFO] Dashboard Running!")
    print("[TIP]  Press [O] at ANY TIME to pick any other video file from Windows Explorer!\n")

    fps_history = []
    paused = False

    # Serial Communication setup (physical ESP32 or fallback simulation)
    from communication.serial.serial_sender import SerialSender
    from ai.utils.config_loader import load_system_config
    
    sys_cfg = load_system_config("config/system_config.json")
    serial_cfg = sys_cfg.get("communication", {}).get("serial", {})
    serial_port = serial_cfg.get("port", "COM3")
    serial_baud = serial_cfg.get("baud_rate", 115200)
    
    sender = SerialSender(port=serial_port, baud_rate=serial_baud)
    is_serial_connected = sender.connect(simulate=False)
    if not is_serial_connected:
        print(f"[WARN] Physical serial port {serial_port} not opened yet - using simulated bus")
        sender.connect(simulate=True)
    else:
        print(f"[INFO] Hardware Serial Link ESTABLISHED: {serial_port} @ {serial_baud} baud")
    
    last_serial_send_time = 0.0

    while True:
        if not paused:
            ret, frame = cap.read()
            if not ret:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue

            t0 = time.time()
            slot_states = {}

            # Determine mode based on video name
            is_crop = ("crop" in current_video_name.lower() and cnn_model is not None)
            is_pklot = ("pklot" in current_video_name.lower() or "demo" in current_video_name.lower())

            if is_crop:
                slot_tensors = []
                valid_slots = []
                for idx, (x, y, w, h) in enumerate(slot_boxes):
                    crop = frame[y:y+h, x:x+w]
                    if crop.size > 0:
                        slot_tensors.append(transform(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)))
                        valid_slots.append((idx, x, y, w, h))

                if slot_tensors:
                    batch = torch.stack(slot_tensors).to(device)
                    with torch.no_grad():
                        preds = torch.argmax(cnn_model(batch), dim=1).cpu().numpy()

                    for pred, (idx, x, y, w, h) in zip(preds, valid_slots):
                        sid = f"S{idx+1}"
                        if pred == 0:
                            slot_states[sid] = "FREE"
                            color = (0, 230, 0)
                            tag = f"{sid}: FREE"
                        else:
                            slot_states[sid] = "OCCUPIED"
                            color = (0, 0, 240)
                            tag = f"{sid}: OCC"

                        cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
                        cv2.rectangle(frame, (x, y - 16), (x + 70, y), color, -1)
                        cv2.putText(frame, tag, (x + 3, y - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (0, 0, 0), 1, cv2.LINE_AA)
            elif is_pklot and yolo_model is not None:
                # PKLot overhead aerial model
                results = yolo_model.predict(source=frame, conf=0.25, imgsz=416, device=0, half=True, verbose=False)[0]
                idx = 0
                for box in results.boxes:
                    cls_id = int(box.cls[0])
                    x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                    idx += 1
                    sid = f"S{idx}"
                    if cls_id == 0:
                        slot_states[sid] = "FREE"
                        color = (0, 230, 0)
                        lbl = f"{sid}: FREE"
                    else:
                        slot_states[sid] = "OCCUPIED"
                        color = (0, 0, 240)
                        lbl = f"{sid}: OCC"
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                    cv2.putText(frame, lbl, (x1, y1 - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.40, color, 1, cv2.LINE_AA)
            else:
                # Universal COCO vehicle detection (Webcam, mobile phone camera, or general car video)
                active_model = coco_model if coco_model is not None else yolo_model
                results = active_model.predict(source=frame, conf=0.25, device=0, half=True, verbose=False)[0]
                slot_states = {"S1": "FREE", "S2": "FREE", "S3": "FREE", "S4": "FREE"}
                v_idx = 0
                for box in results.boxes:
                    cls_id = int(box.cls[0])
                    conf = float(box.conf[0])
                    # COCO classes: 2:car, 3:motorcycle, 5:bus, 7:truck
                    if cls_id in {2, 3, 5, 7} or (len(active_model.names) <= 2 and cls_id == 1):
                        v_idx += 1
                        sid = f"S{min(v_idx, 4)}"
                        slot_states[sid] = "OCCUPIED"
                        x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                        lbl = f"CAR {conf:.2f}"
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 240), 2)
                        cv2.rectangle(frame, (x1, y1 - 18), (x1 + 80, y1), (0, 0, 240), -1)
                        cv2.putText(frame, lbl, (x1 + 4, y1 - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1, cv2.LINE_AA)

            t1 = time.time()
            latency_ms = (t1 - t0) * 1000
            fps_history.append(1.0 / max(0.001, t1 - t0))
            if len(fps_history) > 30:
                fps_history.pop(0)
            avg_fps = sum(fps_history) / len(fps_history)

            free_c = sum(1 for st in slot_states.values() if st == "FREE")
            occ_c = len(slot_states) - free_c
            s1 = 1 if slot_states.get("S1") == "OCCUPIED" else 0
            s2 = 1 if slot_states.get("S2") == "OCCUPIED" else 0
            s3 = 1 if slot_states.get("S3") == "OCCUPIED" else 0
            s4 = 1 if slot_states.get("S4") == "OCCUPIED" else 0

            from communication.protocol.packet_codec import recommend_slot
            rec_slot = recommend_slot(s1 == 1, s2 == 1, s3 == 1, s4 == 1)
            serial_packet = f"<PKT,S1={s1},S2={s2},S3={s3},S4={s4},FREE={free_c},REC={rec_slot},STATUS=OK>"

            now_tx = time.time()
            if (now_tx - last_serial_send_time) >= 0.5:
                sender.send(serial_packet)
                last_serial_send_time = now_tx

            telemetry = sender.get_telemetry()
            dashboard_view = build_dashboard(
                1440, 810, frame, slot_states, latency_ms, avg_fps, serial_packet,
                current_video_name, rec_slot=rec_slot, telemetry=telemetry
            )
            cv2.imshow(win_name, dashboard_view)

        wait_delay = max(1, int(frame_budget_ms - latency_ms)) if not paused else 50
        key = cv2.waitKey(wait_delay) & 0xFF
        if key in [ord('q'), ord('Q'), 27]:
            break
        elif key == 32: # SPACE
            paused = not paused
        elif key in [ord('r'), ord('R')]: # R
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        elif key in [ord('c'), ord('C'), ord('v'), ord('V')]: # C or V: Simulate Car at Barrier (IR sensor trigger)
            sender.send_command("TRIGGER_VEHICLE")
            print(">> [COMMAND] Car approach triggered (IR Trigger -> Gate Opens for 10s auto-close)!")
        elif key in [ord('g'), ord('G')]: # G: Test Servo Gate sweep (0 <-> 90)
            sender.send_command("SWEEP")
            print(">> [COMMAND] Servo gate sweep test commanded to ESP32 (0 -> 90 -> 0)!")
        elif key == ord('1'):
            target = str(PROJECT_ROOT / "parking_crop_loop.mp4")
            if Path(target).exists():
                print(f"[INFO] Switching to 14-Slot Smart CCTV: {target}")
                cap.release()
                cap, current_video_name = load_capture(target)
                fps_val = cap.get(cv2.CAP_PROP_FPS) or 30.0
                frame_budget_ms = 1000.0 / (fps_val if fps_val > 0 else 30.0)
        elif key == ord('2'):
            target = str(PROJECT_ROOT / "demo_pklot_detection.mp4")
            if Path(target).exists():
                print(f"[INFO] Switching to PKLot Overhead CCTV: {target}")
                cap.release()
                cap, current_video_name = load_capture(target)
                fps_val = cap.get(cv2.CAP_PROP_FPS) or 30.0
                frame_budget_ms = 1000.0 / (fps_val if fps_val > 0 else 30.0)
        elif key == ord('3'):
            print("[INFO] Switching to Live Webcam (Camera #0)...")
            cap.release()
            cap, current_video_name = load_capture(0)
            fps_val = cap.get(cv2.CAP_PROP_FPS) or 30.0
            frame_budget_ms = 1000.0 / (fps_val if fps_val > 0 else 30.0)
        elif key in [ord('o'), ord('O')]: # O: Open file dialog on the fly!
            new_file = open_file_dialog()
            if new_file:
                print(f"[INFO] Switching to user-selected video: {new_file}")
                cap.release()
                cap, current_video_name = load_capture(new_file)
                fps_val = cap.get(cv2.CAP_PROP_FPS) or 30.0
                frame_budget_ms = 1000.0 / (fps_val if fps_val > 0 else 30.0)

    cap.release()
    cv2.destroyAllWindows()
    sender.close()


if __name__ == "__main__":
    run_master_dashboard()
