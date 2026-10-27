import cv2
import os
import shutil
from ultralytics import YOLO

def create_dataset():
    print("[INFO] Setting up dataset folders...")
    base_dir = "ai/dataset/custom_parking"
    os.makedirs(f"{base_dir}/images/train", exist_ok=True)
    os.makedirs(f"{base_dir}/images/val", exist_ok=True)
    os.makedirs(f"{base_dir}/labels/train", exist_ok=True)
    os.makedirs(f"{base_dir}/labels/val", exist_ok=True)

    print("[INFO] Extracting frames from video for training...")
    cap = cv2.VideoCapture("parking_video.mp4")
    model = YOLO("yolov8n.pt")  # Use base model to pseudo-label

    frame_count = 0
    saved_count = 0

    while saved_count < 20: # Save 20 frames for a quick train
        ret, frame = cap.read()
        if not ret:
            break
        
        # Take a frame every 30 frames (1 second)
        if frame_count % 30 == 0:
            # Predict to get auto-labels
            results = model.predict(frame, conf=0.25, verbose=False)
            
            if len(results) > 0 and len(results[0].boxes) > 0:
                img_path = f"{base_dir}/images/train/frame_{saved_count}.jpg"
                lbl_path = f"{base_dir}/labels/train/frame_{saved_count}.txt"
                
                # Also put 20% in val
                if saved_count % 5 == 0:
                    img_path = img_path.replace("train", "val")
                    lbl_path = lbl_path.replace("train", "val")
                
                cv2.imwrite(img_path, frame)
                
                with open(lbl_path, "w") as f:
                    for box in results[0].boxes:
                        cls_id = int(box.cls[0])
                        # Map cars (2), trucks (7) to class 0 (vehicle)
                        if cls_id in [2, 3, 5, 7, 0]:
                            x, y, w, h = box.xywhn[0].tolist()
                            f.write(f"0 {x} {y} {w} {h}\n")
                
                saved_count += 1
        frame_count += 1
        
    cap.release()

    # Create dataset.yaml
    yaml_content = f"""
path: {os.path.abspath(base_dir)}
train: images/train
val: images/val

names:
  0: vehicle
"""
    with open("ai/dataset/custom_parking.yaml", "w") as f:
        f.write(yaml_content.strip())
        
    print(f"[INFO] Dataset created with {saved_count} labeled frames!")

def train_model():
    print("[INFO] Starting custom YOLO training on RTX 3050...")
    model = YOLO("yolov8n.pt")
    
    # Train for 5 epochs (very fast, just for project requirement)
    model.train(
        data="ai/dataset/custom_parking.yaml",
        epochs=5,
        imgsz=640,
        device=0, # Use GPU
        project="ai/models",
        name="custom_parking_model"
    )
    
    print("[INFO] Training complete! Copying best.pt to standard location...")
    try:
        shutil.copy("ai/models/custom_parking_model/weights/best.pt", "ai/models/best.pt")
        print("[SUCCESS] New custom trained model saved to ai/models/best.pt")
    except Exception as e:
        print(f"Could not copy weights: {e}")

if __name__ == "__main__":
    create_dataset()
    train_model()
