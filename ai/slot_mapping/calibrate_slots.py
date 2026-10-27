"""
Smart Parking Management System
Parking Slot Calibration Tool

STATUS: IMPLEMENTED

Interactively define S1, S2, S3, S4 parking slot polygons on a CCTV frame.
Saves coordinates to config/parking_slots.json.

Usage:
    python ai/slot_mapping/calibrate_slots.py --source 0         # webcam
    python ai/slot_mapping/calibrate_slots.py --source video.mp4
    python ai/slot_mapping/calibrate_slots.py --source frame.jpg # single image

Controls (per slot):
    LEFT CLICK  - add polygon point
    RIGHT CLICK - remove last point
    ENTER       - confirm current slot polygon and move to next slot
    R           - reset current slot polygon
    ESC         - abort calibration (nothing saved)

Calibration workflow:
    1. Tool opens the CCTV frame.
    2. User clicks corners of S1 parking region.
    3. ENTER to confirm S1.
    4. Repeat for S2, S3, S4.
    5. All slots confirmed → saved to config/parking_slots.json.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np


SLOT_IDS = ["S1", "S2", "S3", "S4"]
COLOURS = {
    "S1": (0, 255, 0),    # green
    "S2": (255, 100, 0),  # blue
    "S3": (0, 165, 255),  # orange
    "S4": (200, 0, 200),  # purple
}


def resolve_project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def get_frame(source_arg: str, cv2):
    """Grab a single representative frame from the source."""
    try:
        idx = int(source_arg)
        cap = cv2.VideoCapture(idx)
    except ValueError:
        p = Path(source_arg)
        if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".bmp"):
            frame = cv2.imread(str(p))
            if frame is None:
                print(f"[ERROR] Cannot read image: {p}")
                sys.exit(1)
            return frame, None
        cap = cv2.VideoCapture(source_arg)

    if not cap.isOpened():
        print(f"[ERROR] Cannot open source: {source_arg}")
        sys.exit(1)

    ret, frame = cap.read()
    cap.release()
    if not ret:
        print("[ERROR] Could not read frame from source.")
        sys.exit(1)
    return frame, cap


class SlotCalibrator:
    """Manages interactive polygon drawing for one slot at a time."""

    def __init__(self, frame: np.ndarray, cv2_module) -> None:
        self.cv2 = cv2_module
        self.base_frame = frame.copy()
        self.current_points: list[list[int]] = []
        self.all_slots: dict[str, list[list[int]]] = {}
        self.current_slot_idx = 0

    @property
    def current_slot(self) -> str:
        return SLOT_IDS[self.current_slot_idx]

    def _redraw(self) -> np.ndarray:
        """Rebuild display frame with all confirmed slots + current in-progress."""
        cv2 = self.cv2
        display = self.base_frame.copy()

        # Draw confirmed slots
        for slot_id, pts in self.all_slots.items():
            if len(pts) >= 3:
                arr = np.array(pts, dtype=np.int32)
                cv2.polylines(display, [arr], isClosed=True,
                              color=COLOURS[slot_id], thickness=2)
                cx = int(np.mean([p[0] for p in pts]))
                cy = int(np.mean([p[1] for p in pts]))
                cv2.putText(display, slot_id, (cx - 15, cy),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                            COLOURS[slot_id], 2, cv2.LINE_AA)

        # Draw current in-progress polygon
        if self.current_points:
            colour = COLOURS[self.current_slot]
            for pt in self.current_points:
                cv2.circle(display, tuple(pt), 5, colour, -1)
            if len(self.current_points) >= 2:
                arr = np.array(self.current_points, dtype=np.int32)
                cv2.polylines(display, [arr], isClosed=False, color=colour, thickness=2)

        # Status overlay
        slot_col = COLOURS[self.current_slot]
        cv2.rectangle(display, (0, 0), (display.shape[1], 55), (30, 30, 30), -1)
        cv2.putText(display,
                    f"Calibrating: {self.current_slot}  ({len(self.current_points)} pts)",
                    (10, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.65, slot_col, 2)
        cv2.putText(display,
                    "LClick=add  RClick=undo  ENTER=confirm  R=reset  ESC=abort",
                    (10, 47), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)
        return display

    def _mouse_callback(self, event, x, y, flags, param) -> None:
        cv2 = self.cv2
        if event == cv2.EVENT_LBUTTONDOWN:
            self.current_points.append([x, y])
        elif event == cv2.EVENT_RBUTTONDOWN:
            if self.current_points:
                self.current_points.pop()

    def run(self) -> dict[str, list[list[int]]] | None:
        """Run calibration loop. Returns slot dict or None if aborted."""
        cv2 = self.cv2
        win = "Slot Calibration - Smart Parking System"
        cv2.namedWindow(win, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(win, 1280, 720)
        cv2.setMouseCallback(win, self._mouse_callback)

        print(f"\n[CALIBRATION] Starting slot calibration")
        print(f"[CALIBRATION] Define {len(SLOT_IDS)} slots: {SLOT_IDS}")

        while self.current_slot_idx < len(SLOT_IDS):
            slot = self.current_slot
            print(f"\n[CALIBRATION] Click corners for slot {slot}"
                  f" → ENTER to confirm | R to reset | ESC to abort")

            while True:
                display = self._redraw()
                cv2.imshow(win, display)
                key = cv2.waitKey(20) & 0xFF

                if key == 27:          # ESC — abort
                    print("[CALIBRATION] Aborted. No data saved.")
                    cv2.destroyAllWindows()
                    return None

                elif key == 13 or key == 10:   # ENTER — confirm
                    if len(self.current_points) < 3:
                        print(f"[WARN] Need at least 3 points for {slot}."
                              f" Currently: {len(self.current_points)}")
                        continue
                    self.all_slots[slot] = list(self.current_points)
                    print(f"[CALIBRATION] {slot} confirmed: {len(self.current_points)} points")
                    self.current_points = []
                    self.current_slot_idx += 1
                    break

                elif key == ord('r'):   # R — reset current
                    self.current_points = []
                    print(f"[CALIBRATION] {slot} reset.")

        cv2.destroyAllWindows()
        return self.all_slots


def save_slots(slots: dict, frame: np.ndarray, project_root: Path) -> None:
    """Save calibrated slot polygons to config/parking_slots.json."""
    config_path = project_root / "config" / "parking_slots.json"
    h, w = frame.shape[:2]

    data = {
        "_description": "Parking slot polygon coordinates in pixel space",
        "_calibrated_at": datetime.now().isoformat(),
        "_status": "CALIBRATED",
        "image_reference": {
            "width": w,
            "height": h,
            "source": "calibration_frame",
        },
        "slots": slots,
    }

    with open(config_path, "w") as f:
        json.dump(data, f, indent=2)

    print(f"\n[SAVED] Slot configuration → {config_path.resolve()}")
    for slot_id, pts in slots.items():
        print(f"  {slot_id}: {len(pts)} points")


def main() -> None:
    import argparse
    try:
        import cv2
    except ImportError:
        print("[ERROR] opencv-python not installed.")
        sys.exit(1)

    project_root = resolve_project_root()

    parser = argparse.ArgumentParser(
        description="Smart Parking - Interactive Slot Calibration"
    )
    parser.add_argument(
        "--source", default=None,
        help="Camera index, video file, or image file (default: from system_config.json)"
    )
    args = parser.parse_args()

    # Load config to get default source if not provided
    sys_config_path = project_root / "config" / "system_config.json"
    default_source = "0"
    if sys_config_path.exists():
        try:
            with open(sys_config_path, "r") as f:
                cfg = json.load(f)
                default_source = str(cfg.get("camera", {}).get("source", "0"))
        except Exception:
            pass

    source_val = args.source if args.source is not None else default_source

    print("[INFO] Loading calibration frame...")
    frame, _ = get_frame(source_val, cv2)
    print(f"[INFO] Frame size: {frame.shape[1]}×{frame.shape[0]}")

    calibrator = SlotCalibrator(frame, cv2)
    slots = calibrator.run()

    if slots:
        save_slots(slots, frame, project_root)
        print("\n[NEXT STEP] Run: python ai/inference/run_cctv.py")
    else:
        print("[INFO] Calibration aborted. config/parking_slots.json not updated.")


if __name__ == "__main__":
    main()
