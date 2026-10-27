"""
Smart Parking Management System
Automated PKLot Dataset Extraction & Accurate YOLOv8 Training Script
"""

import os
import sys
import time
import zipfile
import shutil
from pathlib import Path
import yaml

DOWNLOADS_DIR = Path(r"C:\Users\kesha\Downloads")
PROJECT_ROOT = Path(r"C:\Users\kesha\Desktop\embedded\smart-parking-system")
DATASET_DIR = PROJECT_ROOT / "ai" / "dataset" / "pklot"
MODELS_DIR = PROJECT_ROOT / "ai" / "models"


def wait_for_zip_download(timeout_seconds=600):
    """Wait until the PKLot zip download is completely finished in Downloads folder."""
    print("[INFO] Waiting for PKLot zip download to complete...")
    start_time = time.time()
    
    while time.time() - start_time < timeout_seconds:
        # Check for completed zip
        zips = list(DOWNLOADS_DIR.glob("*PKLot*.zip"))
        crdownloads = list(DOWNLOADS_DIR.glob("*PKLot*.crdownload"))
        
        if zips and not crdownloads:
            zip_path = zips[0]
            # Verify file size stability (ensure Chrome finished writing)
            size1 = zip_path.stat().st_size
            time.sleep(2)
            size2 = zip_path.stat().st_size
            if size1 == size2 and size1 > 10_000_000: # at least 10MB
                print(f"[SUCCESS] Found completed zip: {zip_path.name} ({size1 / (1024*1024):.2f} MB)")
                return zip_path
        
        if crdownloads:
            size_mb = crdownloads[0].stat().st_size / (1024 * 1024)
            print(f"[DOWNLOADING] Still downloading... {size_mb:.1f} MB written so far")
            
        time.sleep(5)

    raise TimeoutError("Download did not complete within timeout!")


def extract_dataset(zip_path):
    """Extract the zip archive into ai/dataset/pklot/."""
    print(f"[INFO] Extracting {zip_path.name} to {DATASET_DIR}...")
    DATASET_DIR.mkdir(parents=True, exist_ok=True)
    
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(DATASET_DIR)
        
    print("[SUCCESS] Extraction complete!")


def configure_data_yaml():
    """Ensure data.yaml exists and paths are correctly configured for YOLOv8."""
    yaml_candidates = list(DATASET_DIR.glob("*.yaml")) + list(DATASET_DIR.glob("*.yml"))
    if not yaml_candidates:
        raise FileNotFoundError(f"No YAML configuration found in {DATASET_DIR}")
        
    yaml_path = yaml_candidates[0]
    print(f"[INFO] Configuring dataset YAML: {yaml_path}")
    
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
        
    print(f"[INFO] Original YAML content: {data}")
    
    # Set explicit absolute base path
    data["path"] = str(DATASET_DIR.resolve())
    
    # Save back
    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, sort_keys=False)
        
    print(f"[SUCCESS] Dataset YAML updated with absolute paths.")
    return yaml_path, data


def train_yolo(yaml_path):
    """Train YOLOv8 on RTX 3050 GPU using the PKLot dataset."""
    from ultralytics import YOLO
    import torch
    
    print("\n" + "="*60)
    print("  STARTING HIGH-ACCURACY YOLO TRAINING ON RTX 3050 GPU")
    print("="*60)
    
    cuda_available = torch.cuda.is_available()
    device = 0 if cuda_available else "cpu"
    if cuda_available:
        print(f"[INFO] Using GPU: {torch.cuda.get_device_name(0)}")
        print(f"[INFO] CUDA Version: {torch.version.cuda}")
    else:
        print("[WARN] CUDA not available, using CPU")
        
    # Load YOLOv8n base model
    model = YOLO("yolov8n.pt")
    
    # Start training with thorough parameters
    # PKLot is 416x416 resolution, so imgsz=416 gives high accuracy & blazing fast speed
    results = model.train(
        data=str(yaml_path),
        epochs=30,
        imgsz=416,
        batch=16,
        device=device,
        patience=10,
        workers=4,
        project=str(MODELS_DIR),
        name="pklot_yolov8_model",
        exist_ok=True,
        save=True,
        verbose=True
    )
    
    print("\n[INFO] Training finished! Saving weights...")
    trained_best = MODELS_DIR / "pklot_yolov8_model" / "weights" / "best.pt"
    target_best = MODELS_DIR / "best.pt"
    
    if trained_best.exists():
        shutil.copy2(trained_best, target_best)
        print(f"[SUCCESS] High-accuracy weights copied to: {target_best}")
    else:
        print(f"[WARN] Could not find weights at {trained_best}")
        
    print("\n" + "="*60)
    print("  TRAINING & DEPLOYMENT COMPLETE!")
    print("="*60)


if __name__ == "__main__":
    try:
        zip_file = wait_for_zip_download()
        extract_dataset(zip_file)
        yaml_file, cfg = configure_data_yaml()
        train_yolo(yaml_file)
    except Exception as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
