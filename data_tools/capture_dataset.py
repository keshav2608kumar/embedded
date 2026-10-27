"""
Smart Parking Management System
Dataset Capture Tool

STATUS: IMPLEMENTED

Captures frames from webcam / USB camera / IP camera / video file
and saves them to the YOLO dataset directory for annotation.

Usage:
    python data_tools/capture_dataset.py --source 0             # webcam
    python data_tools/capture_dataset.py --source 1             # USB camera
    python data_tools/capture_dataset.py --source parking.mp4   # video file
    python data_tools/capture_dataset.py --source rtsp://...    # IP camera

    Optional:
    --interval 2.0     # capture 1 frame every 2 seconds (default)
    --output ai/dataset/images/train  # destination folder
    --prefix frame     # filename prefix (default: frame)
    --max 500          # max frames to capture (default: unlimited)

Controls (during capture):
    SPACE  - capture frame manually
    Q      - quit
    P      - pause / resume auto-capture

Captured frames are UNLABELLED. Use a tool like:
    - LabelImg (https://github.com/heartexlabs/labelImg)
    - Roboflow (online, free tier available)
to add YOLO-format bounding box annotations.
"""

import argparse
import os
import sys
import time
from pathlib import Path


def resolve_project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def open_source(source: str | int):
    """Open a camera / video source via OpenCV."""
    try:
        import cv2
    except ImportError:
        print("[ERROR] opencv-python not installed. Run: pip install opencv-python")
        sys.exit(1)

    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        print(f"[ERROR] Cannot open source: {source}")
        sys.exit(1)
    return cap, cv2


def capture(source_arg: str, output_dir: str, interval_sec: float,
            prefix: str, max_frames: int) -> None:
    """Main capture loop."""
    # Parse source
    try:
        source: str | int = int(source_arg)    # webcam index
    except ValueError:
        source = source_arg                     # file path or RTSP URL

    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    cap, cv2 = open_source(source)

    # Count existing frames to avoid overwriting
    existing = len(list(out_path.glob(f"{prefix}_*.jpg")))
    frame_idx = existing
    total_saved = 0
    last_capture_time = 0.0
    paused = False

    source_label = str(source) if isinstance(source, str) else f"Camera {source}"
    print(f"\n[INFO] Capture started")
    print(f"[INFO] Source  : {source_label}")
    print(f"[INFO] Output  : {out_path.resolve()}")
    print(f"[INFO] Interval: {interval_sec}s")
    print(f"[INFO] Controls: SPACE=manual capture | P=pause | Q=quit\n")

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("[WARN] Frame read failed — source may have ended")
                break

            now = time.time()

            # Auto-capture
            if not paused and (now - last_capture_time) >= interval_sec:
                fname = out_path / f"{prefix}_{frame_idx:05d}.jpg"
                cv2.imwrite(str(fname), frame)
                last_capture_time = now
                frame_idx += 1
                total_saved += 1
                print(f"[SAVED] {fname.name}  (total: {total_saved})")

                if max_frames > 0 and total_saved >= max_frames:
                    print(f"[INFO] Reached max_frames={max_frames}. Stopping.")
                    break

            # Overlay info
            display = frame.copy()
            status = "PAUSED" if paused else f"AUTO ({interval_sec:.1f}s)"
            cv2.putText(display, f"Status: {status}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(display, f"Saved: {total_saved}", (10, 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(display, "SPACE=capture  P=pause  Q=quit",
                        (10, display.shape[0] - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
            cv2.imshow("Dataset Capture - Smart Parking", display)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') or key == 27:
                print("[INFO] Quit key pressed.")
                break
            elif key == ord(' '):           # manual capture
                fname = out_path / f"{prefix}_{frame_idx:05d}.jpg"
                cv2.imwrite(str(fname), frame)
                frame_idx += 1
                total_saved += 1
                print(f"[MANUAL SAVED] {fname.name}  (total: {total_saved})")
            elif key == ord('p'):
                paused = not paused
                print(f"[INFO] {'Paused' if paused else 'Resumed'}")

    finally:
        cap.release()
        cv2.destroyAllWindows()

    print(f"\n[INFO] Capture finished. Total frames saved: {total_saved}")
    print(f"[INFO] Frames saved to: {out_path.resolve()}")
    print("\n[NEXT STEP] Annotate saved images with YOLO-format labels.")
    print("  Recommended tools:")
    print("    LabelImg : https://github.com/heartexlabs/labelImg")
    print("    Roboflow : https://roboflow.com (free tier available)")
    print("  Label class 0 = vehicle")


# ── CLI ────────────────────────────────────────────────────────────────────── #

def main() -> None:
    project_root = resolve_project_root()
    default_output = str(project_root / "ai" / "dataset" / "images" / "train")

    parser = argparse.ArgumentParser(
        description="Smart Parking - Dataset Frame Capture Tool"
    )
    parser.add_argument(
        "--source", default="0",
        help="Camera index (0,1,...), video file path, or RTSP URL"
    )
    parser.add_argument(
        "--output", default=default_output,
        help="Output directory for captured frames"
    )
    parser.add_argument(
        "--interval", type=float, default=2.0,
        help="Auto-capture interval in seconds (default: 2.0)"
    )
    parser.add_argument(
        "--prefix", default="frame",
        help="Output filename prefix (default: frame)"
    )
    parser.add_argument(
        "--max", type=int, default=0,
        help="Maximum frames to capture (0 = unlimited)"
    )

    args = parser.parse_args()
    capture(args.source, args.output, args.interval, args.prefix, args.max)


if __name__ == "__main__":
    main()
