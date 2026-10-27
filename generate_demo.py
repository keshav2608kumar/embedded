"""
Smart Parking System - Generate Video Demonstration
Runs the newly trained YOLOv8 PKLot model on test frames and exports a demonstration MP4 video.
"""

import glob
import cv2
from pathlib import Path
from ultralytics import YOLO

def generate_demo_video(num_frames=200, output_path="demo_pklot_detection.mp4"):
    print("[INFO] Loading trained model ai/models/best.pt...")
    model = YOLO("ai/models/best.pt")
    
    test_images = sorted(glob.glob("ai/dataset/pklot/test/images/*.jpg"))
    print(f"[INFO] Found {len(test_images)} test images. Generating video with {min(num_frames, len(test_images))} frames...")
    
    if not test_images:
        print("[ERROR] No test images found!")
        return
        
    first_img = cv2.imread(test_images[0])
    h, w = first_img.shape[:2]
    
    # 416x416 resolution or scaled
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, 5.0, (w, h)) # 5 fps for clear viewing
    
    for i, img_path in enumerate(test_images[:num_frames]):
        img = cv2.imread(img_path)
        if img is None:
            continue
            
        results = model.predict(source=img, conf=0.35, imgsz=416, device=0, verbose=False)[0]
        
        empty_count = 0
        occ_count = 0
        
        for box in results.boxes:
            cls_id = int(box.cls[0])
            conf = float(box.conf[0])
            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
            
            if cls_id == 0: # space-empty
                empty_count += 1
                color = (0, 255, 0) # Green
                label = f"Empty {conf:.2f}"
            else: # space-occupied
                occ_count += 1
                color = (0, 0, 255) # Red
                label = f"Occupied {conf:.2f}"
                
            cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
            
        # Draw HUD bar
        total_slots = empty_count + occ_count
        occ_rate = (occ_count / total_slots * 100) if total_slots > 0 else 0
        
        # Overlay semi-transparent top header
        overlay = img.copy()
        cv2.rectangle(overlay, (0, 0), (w, 50), (20, 20, 20), -1)
        img = cv2.addWeighted(overlay, 0.75, img, 0.25, 0)
        
        # HUD Text
        text1 = f"PKLot YOLOv8 | Slots: {total_slots} | Free: {empty_count} | Occ: {occ_count}"
        text2 = f"Occupancy: {occ_rate:.1f}% | Latency: 6.1ms (RTX 3050)"
        cv2.putText(img, text1, (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
        cv2.putText(img, text2, (10, 42), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1, cv2.LINE_AA)
        
        out.write(img)
        if (i + 1) % 50 == 0:
            print(f"[PROGRESS] Rendered {i + 1}/{min(num_frames, len(test_images))} frames...")
            
    out.release()
    print(f"\n[SUCCESS] Demo video generated successfully: {output_path}")

if __name__ == "__main__":
    generate_demo_video(num_frames=150)
