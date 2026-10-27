# AI & Vision Pipeline

## 1. YOLOv8 Detection
We use Ultralytics YOLOv8 for real-time object detection.
- **Model:** Custom fine-tuned `best.pt` (or fallback to pretrained `yolov8n.pt`).
- **Classes:** The model is trained to detect a single class: `vehicle`. (If using the fallback COCO model, car/motorcycle/bus/truck classes are merged).
- **Inference:** Configured in `system_config.json`. Typically runs at 640x640 resolution. Confidence thresholds prevent false positives.

## 2. Slot Mapping (Geometry Layer)
Once YOLO provides bounding boxes `(x1, y1, x2, y2)` for vehicles, the `SlotMapper` (`ai/slot_mapping/slot_mapper.py`) determines if they are inside a parking slot.

- Slots are defined as 4-point polygons in `parking_slots.json`.
- Users calibrate these polygons using `python ai/slot_mapping/calibrate_slots.py`.
- **Matching Algorithm:** Uses `cv2.pointPolygonTest` to check if the center point of the vehicle's bounding box falls inside any of the 4 slot polygons. (IoU thresholding is also supported as a fallback).

## 3. Temporal Filtering
Raw AI detections flicker frame-to-frame. The `TemporalFilter` (`ai/tracking/temporal_filter.py`) requires multiple consecutive frames of the *same* state before confirming a transition.

- `OCCUPIED_CONFIRM_FRAMES` (e.g., 5 frames)
- `FREE_CONFIRM_FRAMES` (e.g., 8 frames)

**Occupancy Tracking:**
The filter also acts as a session tracker, recording the exact `start_time`, `end_time`, and `duration_seconds` for every parking event.

## 4. Pipeline Execution
The pipeline is launched via `run_cctv.py`. It loops through:
1. Capture Frame
2. YOLO Predict
3. Map Detections to Slots
4. Update Temporal Filter
5. Encode Serial Packet
6. Draw Overlay (OpenCV `imshow`)
