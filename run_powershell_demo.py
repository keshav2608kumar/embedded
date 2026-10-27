"""
Smart Parking System - PowerShell Live Demonstration
Runs inference with the trained YOLO model on RTX 3050 and prints frame statistics.
"""

import glob
import time
from pathlib import Path
import cv2
from ultralytics import YOLO

def main():
    print("=" * 70)
    print("  SMART PARKING - LIVE POWERSHELL DEMO EXECUTION")
    print("=" * 70)

    model_path = Path("ai/models/best.pt")
    print(f"[1/4] Loading trained YOLOv8 model: {model_path}...")
    model = YOLO(str(model_path))
    print(f"      Model Classes: {model.names}")

    test_images = sorted(glob.glob("ai/dataset/pklot/test/images/*.jpg"))
    print(f"[2/4] Found {len(test_images)} test surveillance frames in PKLot dataset.")

    print("\n[3/4] Running live inference on consecutive frames (RTX 3050 GPU):")
    print("-" * 70)
    print(f"{'Frame':<10} | {'Empty Slots':<12} | {'Occupied Slots':<15} | {'Total Detected':<14} | {'Latency':<10}")
    print("-" * 70)

    saved_frames = []

    for idx, img_path in enumerate(test_images[:12]):
        t0 = time.time()
        img = cv2.imread(img_path)
        res = model.predict(source=img, conf=0.35, imgsz=416, device=0, verbose=False)[0]
        t1 = time.time()
        
        empty_cnt = 0
        occ_cnt = 0
        
        for box in res.boxes:
            cls_id = int(box.cls[0])
            conf = float(box.conf[0])
            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
            
            if cls_id == 0:
                empty_cnt += 1
                color = (0, 255, 0) # Green for empty
            else:
                occ_cnt += 1
                color = (0, 0, 255) # Red for occupied
                
            cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
            
        latency_ms = (t1 - t0) * 1000
        total = empty_cnt + occ_cnt
        print(f"Frame #{idx+1:<4} | {empty_cnt:<12} | {occ_cnt:<15} | {total:<14} | {latency_ms:.1f} ms")
        
        if idx in [0, 5, 11]:
            out_name = f"demo_result_frame_{idx+1}.jpg"
            cv2.imwrite(out_name, img)
            saved_frames.append(out_name)

    print("-" * 70)
    print("\n[4/4] Output Images with Bounding Boxes Saved:")
    for f in saved_frames:
        print(f"  -> Saved: {f}")
    print("=" * 70)
    print("  DEMONSTRATION RUN FINISHED SUCCESSFULLY!")
    print("=" * 70)

if __name__ == "__main__":
    main()
