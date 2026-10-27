"""
Smart Parking Management System
Real-Time CCTV Inference Pipeline

STATUS: IMPLEMENTED
    Camera capture + YOLO inference + slot mapping + temporal filtering
    + occupancy calculation + serial communication + debug overlay.
    Hardware test required for ESP32 serial link.

Usage:
    python ai/inference/run_cctv.py
    python ai/inference/run_cctv.py --source 0          # webcam
    python ai/inference/run_cctv.py --source video.mp4  # video file
    python ai/inference/run_cctv.py --source rtsp://... # IP camera
    python ai/inference/run_cctv.py --no-display        # headless

Press 'Q' or ESC to stop.

Pipeline:
    Camera → OpenCV → YOLO → bounding boxes → SlotMapper (geometry)
    → TemporalFilter (debounce) → occupancy states → SerialSender → ESP32
    → debug overlay display

IMPORTANT: YOLO detects 'vehicle'. S1-S4 assignment is done by SlotMapper.
"""

import argparse
import logging
import sys
import time
from pathlib import Path
from typing import Optional

import cv2
import numpy as np


def resolve_project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def _add_project_to_path() -> None:
    """Ensure project root is on sys.path for imports."""
    root = str(resolve_project_root())
    if root not in sys.path:
        sys.path.insert(0, root)


_add_project_to_path()


def run_inference(
    source,
    config: dict,
    slot_polygons: dict,
    simulate_comm: bool = False,
    show_display: bool = True,
) -> None:
    """
    Main CCTV inference loop.

    Args:
        source:        Camera index (int) or path/URL (str).
        config:        Loaded system_config.json dict.
        slot_polygons: Loaded parking_slots.json slots dict.
        simulate_comm: If True, serial sends are simulated (no hardware).
        show_display:  If True, show OpenCV debug window.
    """
    from ai.utils.logger import setup_logger, EventLogger
    from ai.utils.overlay import (
        draw_slot_polygons, draw_vehicle_boxes,
        draw_status_panel, draw_parking_full_warning
    )
    from ai.utils.config_loader import get
    from ai.slot_mapping.slot_mapper import SlotMapper, Detection
    from ai.tracking.temporal_filter import TemporalFilter, SlotState
    from communication.protocol.packet_codec import encode, AIStatus
    from communication.serial.serial_sender import SerialSender

    logger = setup_logger(log_dir=get(config, "logging", "log_dir", default="logs"))

    # ── Initialise components ──────────────────────────────────────────────
    slot_mapper = SlotMapper(
        slot_polygons=slot_polygons,
        use_center_point=get(config, "slot_mapping", "use_center_point", default=True),
        overlap_threshold=get(config, "slot_mapping", "overlap_threshold", default=0.30),
    )

    if not slot_mapper.is_calibrated():
        logger.warning(
            "Slot polygons are not fully calibrated. "
            "Run: python ai/slot_mapping/calibrate_slots.py\n"
            "Detection will still run but slot assignment may be incorrect."
        )

    tf_cfg = config.get("temporal_filter", {})
    temporal = TemporalFilter(
        occupied_confirm_frames=tf_cfg.get("occupied_confirm_frames", 5),
        free_confirm_frames=tf_cfg.get("free_confirm_frames", 8),
        uncertain_timeout_frames=tf_cfg.get("uncertain_timeout_frames", 15),
    )

    serial_cfg = get(config, "communication", "serial", default={})
    sender = SerialSender(
        port=serial_cfg.get("port", "COM3"),
        baud_rate=serial_cfg.get("baud_rate", 115200),
        timeout_sec=serial_cfg.get("timeout_sec", 2.0),
        comm_lost_timeout_sec=serial_cfg.get("comm_lost_timeout_sec", 10.0),
    )
    comm_enabled = get(config, "communication", "enabled", default=True)
    if comm_enabled:
        sender.connect(simulate=simulate_comm)

    event_log = EventLogger(
        log_dir=get(config, "logging", "log_dir", default="logs"),
        fmt=get(config, "logging", "log_format", default="csv"),
    )

    # ── Load YOLO model ────────────────────────────────────────────────────
    model_cfg = config.get("model", {})
    model_path = model_cfg.get("path", "ai/models/best.pt")
    fallback   = model_cfg.get("fallback_model", "yolov8n.pt")
    conf_thr   = model_cfg.get("confidence_threshold", 0.40)
    iou_thr    = model_cfg.get("iou_threshold", 0.45)
    imgsz      = model_cfg.get("imgsz", 640)
    device_cfg = model_cfg.get("device", "auto")

    project_root = resolve_project_root()
    model_file   = project_root / model_path

    try:
        from ultralytics import YOLO
        if model_file.exists():
            model = YOLO(str(model_file))
            logger.info("Loaded trained model: %s", model_file)
        else:
            logger.warning(
                "Trained model not found at %s. "
                "Using fallback: %s (pretrained COCO — vehicle class included)",
                model_file, fallback
            )
            model = YOLO(fallback)
    except Exception as e:
        logger.critical("Failed to load YOLO model: %s", e)
        sys.exit(1)

    # Resolve device
    if device_cfg == "auto":
        import torch
        device = "0" if torch.cuda.is_available() else "cpu"
    else:
        device = device_cfg

    logger.info("YOLO running on device: %s", device)

    # ── Open camera ────────────────────────────────────────────────────────
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        logger.critical("Cannot open camera source: %s", source)
        sys.exit(1)

    # Set resolution if configured
    cam_cfg = config.get("camera", {})
    if cam_cfg.get("frame_width"):
        cap.set(cv2.CAP_PROP_FRAME_WIDTH,  cam_cfg["frame_width"])
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cam_cfg["frame_height"])

    logger.info("Camera opened: source=%s", source)

    # ── Display settings ───────────────────────────────────────────────────
    disp_cfg    = config.get("display", {})
    font_scale  = disp_cfg.get("overlay_font_scale", 0.6)
    window_name = disp_cfg.get("window_name", "Smart Parking - AI Pipeline")
    send_interval = serial_cfg.get("send_interval_sec", 1.0)
    
    if show_display:
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window_name, 1280, 720)

    # ── Main loop ──────────────────────────────────────────────────────────
    ai_status  = "AI_OK"
    slot_states_str: dict[str, str] = {
        "S1": SlotState.FREE, "S2": SlotState.FREE,
        "S3": SlotState.FREE, "S4": SlotState.FREE
    }
    last_send_time = 0.0
    frame_count    = 0
    fps_start      = time.time()
    fps            = 0.0

    # For COCO model: vehicle classes (car=2, motorcycle=3, bus=5, truck=7)
    COCO_VEHICLE_CLASSES = {2, 3, 5, 7}

    logger.info("Inference loop starting. Press Q or ESC to stop.")

    try:
        while True:
            ret, frame = cap.read()

            # ── Camera error handling & Video Looping ──────────────────────────
            if not ret or frame is None:
                # If source is a video file, loop it
                if isinstance(source, str) and source.lower().endswith((".mp4", ".avi", ".mov", ".mkv")):
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue
                
                logger.error("Camera frame read failed — AI_STATUS: CAMERA_ERROR")
                ai_status = AIStatus.CAMERA_ERROR

                # Do NOT change slot states on camera error — hold last known
                if show_display:
                    err_frame = np.zeros((480, 640, 3), dtype=np.uint8)
                    cv2.putText(err_frame, "CAMERA ERROR — Frame unavailable",
                                (40, 240), cv2.FONT_HERSHEY_SIMPLEX,
                                0.8, (0, 0, 220), 2)
                    cv2.imshow(window_name, err_frame)
                    if cv2.waitKey(500) & 0xFF in (ord('q'), 27):
                        break
                continue

            frame_count += 1
            ai_status = "AI_OK"

            # ── YOLO inference ─────────────────────────────────────────────
            try:
                results = model.predict(
                    source=frame,
                    conf=conf_thr,
                    iou=iou_thr,
                    imgsz=imgsz,
                    device=device,
                    verbose=False,
                )
            except Exception as e:
                logger.error("YOLO inference error: %s", e)
                ai_status = "AI_DEGRADED"
                results = []

            # ── Extract vehicle detections ─────────────────────────────────
            detections: list[Detection] = []
            if results:
                for r in results:
                    if r.boxes is None:
                        continue
                    for box in r.boxes:
                        cls_id = int(box.cls[0])
                        conf   = float(box.conf[0])
                        cls_name = model.names.get(cls_id, "")

                        # Match occupied slots or vehicles:
                        # 1. Custom PKLot model: class 1 is 'space-occupied'
                        # 2. Custom 1-class model: class 0 is 'vehicle'
                        # 3. Base COCO model: car(2), motorcycle(3), bus(5), truck(7)
                        is_occupied = (
                            cls_name in ["space-occupied", "occupied", "vehicle"]
                            or (len(model.names) == 1 and cls_id == 0)
                            or (cls_id in COCO_VEHICLE_CLASSES and len(model.names) == 80)
                        )

                        if is_occupied and conf >= conf_thr:
                            x1, y1, x2, y2 = box.xyxy[0].tolist()
                            detections.append(Detection(
                                x1=x1, y1=y1, x2=x2, y2=y2,
                                confidence=conf, class_name=cls_name or "vehicle"
                            ))

            # ── Slot mapping (geometry layer) ──────────────────────────────
            candidates = slot_mapper.map_detections(detections)

            # ── Temporal filtering (debounce) ──────────────────────────────
            confirmed  = temporal.update(candidates)
            slot_states_str = {sid: state.value for sid, state in confirmed.items()}
            available  = temporal.get_available_count()

            # ── Serial communication ───────────────────────────────────────
            now = time.time()
            comm_status = sender.comm_status()

            if comm_enabled and (now - last_send_time) >= send_interval:
                s1 = confirmed.get("S1") == SlotState.OCCUPIED
                s2 = confirmed.get("S2") == SlotState.OCCUPIED
                s3 = confirmed.get("S3") == SlotState.OCCUPIED
                s4 = confirmed.get("S4") == SlotState.OCCUPIED
                packet = encode(s1, s2, s3, s4, available, ai_status)
                sender.send(packet)
                last_send_time = now

            # ── Event logging ──────────────────────────────────────────────
            event_log.log(
                slot_states={k: v == "OCCUPIED" for k, v in slot_states_str.items()},
                available=available,
                ai_status=ai_status,
                comm_status=comm_status,
            )

            # ── FPS calculation ────────────────────────────────────────────
            if frame_count % 30 == 0:
                elapsed = time.time() - fps_start
                fps = 30.0 / elapsed if elapsed > 0 else 0.0
                fps_start = time.time()

            # ── Debug overlay ──────────────────────────────────────────────
            if show_display:
                display = frame.copy()

                if disp_cfg.get("show_slot_polygons", True):
                    display = draw_slot_polygons(display, slot_polygons,
                                                 slot_states_str, font_scale)

                if disp_cfg.get("show_bounding_boxes", True):
                    display = draw_vehicle_boxes(
                        display, [d.as_tuple() for d in detections], 0.5
                    )

                display = draw_status_panel(
                    display, slot_states_str, available,
                    ai_status, comm_status,
                    gate_state="N/A (ESP32)",
                    sensor_state="N/A (ESP32)",
                    fps=fps,
                    font_scale=font_scale,
                )

                if available == 0:
                    display = draw_parking_full_warning(display)

                cv2.imshow(window_name, display)
                key = cv2.waitKey(1) & 0xFF
                if key in (ord('q'), 27):
                    logger.info("Quit key pressed — stopping inference.")
                    break

    finally:
        cap.release()
        if show_display:
            cv2.destroyAllWindows()
        sender.close()
        event_log.close()
        logger.info(
            "Inference stopped. Frames processed: %d  FPS: %.1f",
            frame_count, fps
        )


# ── CLI ────────────────────────────────────────────────────────────────────── #

def main() -> None:
    _add_project_to_path()
    from ai.utils.config_loader import load_system_config, load_slot_config

    parser = argparse.ArgumentParser(
        description="Smart Parking - Real-Time CCTV Inference"
    )
    parser.add_argument(
        "--source", default=None,
        help="Camera source: integer index, video file, or RTSP URL. "
             "Overrides system_config.json if provided."
    )
    parser.add_argument(
        "--config", default="config/system_config.json",
        help="Path to system_config.json"
    )
    parser.add_argument(
        "--simulate-comm", action="store_true",
        help="Simulate serial communication (no ESP32 hardware needed)"
    )
    parser.add_argument(
        "--no-display", action="store_true",
        help="Run headless (no OpenCV window)"
    )
    args = parser.parse_args()

    project_root = resolve_project_root()

    config_path = project_root / args.config
    config = load_system_config(str(config_path))

    slot_config_path = project_root / "config" / "parking_slots.json"
    slot_polygons = load_slot_config(str(slot_config_path))

    # Resolve camera source
    if args.source is not None:
        try:
            source = int(args.source)
        except ValueError:
            source = args.source
    else:
        raw_src = config.get("camera", {}).get("source", 0)
        try:
            source = int(raw_src)
        except (ValueError, TypeError):
            source = raw_src

    run_inference(
        source=source,
        config=config,
        slot_polygons=slot_polygons,
        simulate_comm=args.simulate_comm,
        show_display=not args.no_display,
    )


if __name__ == "__main__":
    main()
