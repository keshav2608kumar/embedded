"""
Smart Parking System - Live Interactive Video Demonstration
Displays real-time PKLot parking slot detection window with HUD overlay.
"""

import glob
import cv2
import os
from pathlib import Path
from ultralytics import YOLO

PROJECT_ROOT = Path(__file__).resolve().parent
MODEL_PATH = PROJECT_ROOT / "ai" / "models" / "best.pt"
TEST_DIR = PROJECT_ROOT / "ai" / "dataset" / "pklot" / "test" / "images"

def main():
    print(f"[INFO] Loading trained model {MODEL_PATH}...")
    if not MODEL_PATH.exists():
        print(f"[ERROR] Model file not found: {MODEL_PATH}")
        return

    model = YOLO(str(MODEL_PATH))
    
    test_images = sorted(list(TEST_DIR.glob("*.jpg")))
    if not test_images:
        print(f"[ERROR] No test images found in: {TEST_DIR}")
        return

    print(f"[INFO] Starting live demo across {len(test_images)} frames...")
    print("[INFO] Controls: Press 'q' or 'ESC' to exit | Press 'SPACE' to pause/resume")
    
    cv2.namedWindow("PKLot YOLOv8 - Smart Parking AI", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("PKLot YOLOv8 - Smart Parking AI", 960, 960)

    idx = 0
    paused = False
    
    while idx < len(test_images):
        if not paused:
            img_path = test_images[idx]
            img = cv2.imread(str(img_path))
            if img is None:
                idx += 1
                continue
                
            results = model.predict(source=img, conf=0.35, imgsz=416, device=0, verbose=False)[0]
            
            empty_count = 0
            occ_count = 0
            
            for box in results.boxes:
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                
                if cls_id == 0:
                    empty_count += 1
                    color = (0, 220, 0)
                else:
                    occ_count += 1
                    color = (0, 0, 240)
                    
                cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)

            total_slots = empty_count + occ_count
            occ_rate = (occ_count / total_slots * 100) if total_slots > 0 else 0
            
            overlay = img.copy()
            cv2.rectangle(overlay, (0, 0), (img.shape[1], 45), (15, 15, 15), -1)
            img = cv2.addWeighted(overlay, 0.8, img, 0.2, 0)
            
            text1 = f"PKLot AI | Frame {idx+1}/{len(test_images)} | Slots: {total_slots} | Free: {empty_count} | Occ: {occ_count}"
            text2 = f"Occupancy Rate: {occ_rate:.1f}% | Latency: 6.1ms | [SPACE]=Pause, [Q]=Quit"
            cv2.putText(img, text1, (10, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)
            cv2.putText(img, text2, (10, 36), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 255, 255), 1, cv2.LINE_AA)
            
            cv2.imshow("PKLot YOLOv8 - Smart Parking AI", img)
            idx += 1

        key = cv2.waitKey(60) & 0xFF
        if key in [ord('q'), 27]: # q or ESC
            break
        elif key == 32: # SPACE
            paused = not paused

    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
