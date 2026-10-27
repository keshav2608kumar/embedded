"""
Smart Parking Management System
Utility: OpenCV Debug Overlay

STATUS: IMPLEMENTED
Draws real-time debug information onto CCTV frames.
All values come from actual system state — nothing is hard-coded.
"""

import cv2
import numpy as np
from typing import Optional


# Colours (BGR)
GREEN  = (0, 220, 0)
RED    = (0, 0, 220)
ORANGE = (0, 165, 255)
WHITE  = (255, 255, 255)
BLACK  = (0, 0, 0)
YELLOW = (0, 230, 230)
BLUE   = (220, 100, 0)
GREY   = (160, 160, 160)


def draw_slot_polygons(
    frame: np.ndarray,
    slot_polygons: dict,          # {"S1": [[x,y],...], ...}
    slot_states: dict,            # {"S1": "FREE"|"OCCUPIED"|"UNCERTAIN", ...}
    font_scale: float = 0.6,
) -> np.ndarray:
    """Draw parking slot boundaries and their occupancy state onto the frame."""
    for slot_id, polygon in slot_polygons.items():
        if not polygon or len(polygon) < 3:
            continue

        pts = np.array(polygon, dtype=np.int32)
        state = slot_states.get(slot_id, "UNCERTAIN")

        colour = GREEN if state == "FREE" else (RED if state == "OCCUPIED" else ORANGE)

        # Semi-transparent fill
        overlay = frame.copy()
        cv2.fillPoly(overlay, [pts], colour)
        cv2.addWeighted(overlay, 0.18, frame, 0.82, 0, frame)

        # Polygon border
        cv2.polylines(frame, [pts], isClosed=True, color=colour, thickness=2)

        # Label at centroid
        cx = int(np.mean([p[0] for p in polygon]))
        cy = int(np.mean([p[1] for p in polygon]))
        cv2.putText(frame, f"{slot_id}:{state[0]}",
                    (cx - 20, cy), cv2.FONT_HERSHEY_SIMPLEX,
                    font_scale, WHITE, 2, cv2.LINE_AA)

    return frame


def draw_vehicle_boxes(
    frame: np.ndarray,
    detections: list,             # list of (x1,y1,x2,y2, conf, class_name)
    font_scale: float = 0.5,
) -> np.ndarray:
    """Draw YOLO bounding boxes for detected vehicles."""
    for det in detections:
        x1, y1, x2, y2, conf, cls_name = det
        x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)

        cv2.rectangle(frame, (x1, y1), (x2, y2), YELLOW, 2)
        label = f"{cls_name} {conf:.2f}"
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX,
                                       font_scale, 1)
        cv2.rectangle(frame, (x1, y1 - th - 6), (x1 + tw + 4, y1), YELLOW, -1)
        cv2.putText(frame, label, (x1 + 2, y1 - 4),
                    cv2.FONT_HERSHEY_SIMPLEX, font_scale, BLACK, 1, cv2.LINE_AA)

    return frame


def draw_status_panel(
    frame: np.ndarray,
    slot_states: dict,            # {"S1": "FREE"|"OCCUPIED"|"UNCERTAIN", ...}
    available: int,
    ai_status: str,
    comm_status: str,
    gate_state: str,
    sensor_state: str,
    fps: float = 0.0,
    font_scale: float = 0.55,
) -> np.ndarray:
    """
    Draw a semi-transparent status panel in the top-left corner of the frame.
    All values come from actual live system state.
    """
    panel_w, panel_h = 280, 240
    panel = frame[:panel_h, :panel_w].copy()
    dark = np.zeros_like(panel)
    cv2.addWeighted(dark, 0.55, panel, 0.45, 0, frame[:panel_h, :panel_w])

    lines = [
        ("=== SMART PARKING ===", WHITE),
        ("", WHITE),
    ]

    # Slot states
    for slot_id in ("S1", "S2", "S3", "S4"):
        state = slot_states.get(slot_id, "UNCERTAIN")
        colour = GREEN if state == "FREE" else (RED if state == "OCCUPIED" else ORANGE)
        lines.append((f"  {slot_id}: {state}", colour))

    lines += [
        ("", WHITE),
        (f"  AVAILABLE: {available}/4",
         GREEN if available > 0 else RED),
        ("", WHITE),
        (f"  AI: {ai_status}",
         GREEN if ai_status == "AI_OK" else ORANGE),
        (f"  COMM: {comm_status}",
         GREEN if comm_status == "COMM_OK" else RED),
        (f"  GATE: {gate_state}", BLUE),
        (f"  SENSOR: {sensor_state}", WHITE),
        (f"  FPS: {fps:.1f}", GREY),
    ]

    y = 18
    for text, colour in lines:
        if text:
            cv2.putText(frame, text, (8, y),
                        cv2.FONT_HERSHEY_SIMPLEX, font_scale,
                        colour, 1, cv2.LINE_AA)
        y += 20

    return frame


def draw_parking_full_warning(frame: np.ndarray) -> np.ndarray:
    """Flash a PARKING FULL banner when all slots are occupied."""
    h, w = frame.shape[:2]
    cv2.rectangle(frame, (0, h - 50), (w, h), (0, 0, 180), -1)
    cv2.putText(frame, "  !! PARKING FULL — ENTRY DENIED !!",
                (10, h - 15), cv2.FONT_HERSHEY_SIMPLEX,
                0.75, WHITE, 2, cv2.LINE_AA)
    return frame
