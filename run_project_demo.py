"""
Smart Parking System - End-to-End Serial & Gate Demonstration
Shows the full integration: AI Detection -> Slot Mapping -> Temporal Filter -> ESP32 Serial Packet
"""

import time
import cv2
from pathlib import Path
from ultralytics import YOLO
from ai.slot_mapping.slot_mapper import SlotMapper, Detection
from ai.tracking.temporal_filter import TemporalFilter, SlotState
from communication.protocol.packet_codec import encode
import json

def main():
    print("=" * 70)
    print("  SMART PARKING - END-TO-END SYSTEM PIPELINE DEMONSTRATION")
    print("=" * 70)
    
    with open("config/parking_slots.json") as f:
        slots_cfg = json.load(f)["slots"]
        
    mapper = SlotMapper(slots_cfg, use_center_point=False, overlap_threshold=0.15)
    temporal = TemporalFilter(occupied_confirm_frames=3, free_confirm_frames=3)
    model = YOLO("ai/models/best.pt")
    
    cap = cv2.VideoCapture("parking_video.mp4")
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f"[INFO] Video loaded: parking_video.mp4 ({total_frames} frames)")
    print(f"[INFO] Calibrated slots: S1, S2, S3, S4")
    print(f"[INFO] ESP32 Serial Protocol: Active (Simulated)\n")
    
    print("-" * 70)
    print(f"{'Step':<6} | {'Slot S1':<8} | {'Slot S2':<8} | {'Slot S3':<8} | {'Slot S4':<8} | {'Available':<10} | {'Serial Packet to ESP32'}")
    print("-" * 70)
    
    for i in range(1, 11):
        ret, frame = cap.read()
        if not ret:
            break
            
        res = model.predict(source=frame, conf=0.25, imgsz=416, device=0, verbose=False)[0]
        
        detections = []
        for box in res.boxes:
            cls_id = int(box.cls[0])
            cls_name = model.names.get(cls_id, "")
            if cls_name == "space-occupied":
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                detections.append(Detection(x1, y1, x2, y2, float(box.conf[0]), "space-occupied"))
                
        candidates = mapper.map_detections(detections)
        confirmed = temporal.update(candidates)
        avail = temporal.get_available_count()
        
        s1 = confirmed["S1"] == SlotState.OCCUPIED
        s2 = confirmed["S2"] == SlotState.OCCUPIED
        s3 = confirmed["S3"] == SlotState.OCCUPIED
        s4 = confirmed["S4"] == SlotState.OCCUPIED
        
        pkt = encode(s1, s2, s3, s4, avail, "AI_OK")
        
        s1_str = "OCCUPIED" if s1 else "FREE"
        s2_str = "OCCUPIED" if s2 else "FREE"
        s3_str = "OCCUPIED" if s3 else "FREE"
        s4_str = "OCCUPIED" if s4 else "FREE"
        
        print(f"#{i:<5} | {s1_str:<8} | {s2_str:<8} | {s3_str:<8} | {s4_str:<8} | {avail:<10} | {pkt}")
        time.sleep(0.1)

    cap.release()
    print("-" * 70)
    print("  ALL SUBSYSTEMS OPERATIONAL: YOLO + SLOTS + TEMPORAL + SERIAL")
    print("=" * 70)

if __name__ == "__main__":
    main()
