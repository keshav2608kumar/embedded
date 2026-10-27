"""
Smart Parking Management System
High-Accuracy YOLOv8 Training on PKLot Dataset (8,690 Train Images, 2,483 Val Images)
Classes: ['space-empty', 'space-occupied']
"""

import sys
import shutil
from pathlib import Path
import torch
from ultralytics import YOLO

PROJECT_ROOT = Path(r"C:\Users\kesha\Desktop\embedded\smart-parking-system")
DATA_YAML = PROJECT_ROOT / "ai" / "dataset" / "pklot" / "data.yaml"
OUTPUT_DIR = PROJECT_ROOT / "ai" / "models"

def main():
    print("=" * 65)
    print("  SMART PARKING YOLOv8 TRAINING ON PKLOT DATASET")
    print("=" * 65)
    
    # 1. Verify CUDA GPU
    cuda_ok = torch.cuda.is_available()
    device = 0 if cuda_ok else "cpu"
    if cuda_ok:
        gpu_name = torch.cuda.get_device_name(0)
        vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
        print(f"[INFO] GPU Detected: {gpu_name} ({vram_gb:.1f} GB VRAM)")
        print(f"[INFO] Device assigned: {device} (CUDA)")
    else:
        print("[WARN] CUDA not found, falling back to CPU")

    # 2. Check data.yaml
    if not DATA_YAML.exists():
        print(f"[ERROR] data.yaml not found at: {DATA_YAML}")
        sys.exit(1)
    print(f"[INFO] Dataset Config: {DATA_YAML}")

    # 3. Load base model (yolov8n.pt for high FPS real-time embedded CCTV inference)
    base_model_path = PROJECT_ROOT / "yolov8n.pt"
    if not base_model_path.exists():
        base_model_path = "yolov8n.pt"
    print(f"[INFO] Base weights: {base_model_path}")
    model = YOLO(str(base_model_path))

    # 4. Training configuration
    # 8,690 images at batch 16 = 543 steps per epoch.
    # 20 epochs with patience 5 gives high convergence without overfitting.
    epochs = 20
    imgsz = 416
    batch = 16
    workers = 4

    print(f"[INFO] Epochs: {epochs} | ImgSz: {imgsz} | Batch: {batch} | Workers: {workers}")
    print("[INFO] Starting training now...\n")

    results = model.train(
        data=str(DATA_YAML),
        epochs=epochs,
        imgsz=imgsz,
        batch=batch,
        device=device,
        workers=workers,
        patience=5,
        project=str(OUTPUT_DIR),
        name="pklot_yolov8_model",
        exist_ok=True,
        save=True,
        plots=True,
        verbose=True
    )

    print("\n" + "=" * 65)
    print("  TRAINING COMPLETE! COPYING WEIGHTS")
    print("=" * 65)

    best_pt = OUTPUT_DIR / "pklot_yolov8_model" / "weights" / "best.pt"
    target_pt = OUTPUT_DIR / "best.pt"

    if best_pt.exists():
        shutil.copy2(best_pt, target_pt)
        print(f"[SUCCESS] Trained weights saved to: {target_pt}")
    else:
        print(f"[WARN] best.pt not found at: {best_pt}")

    # Print summary metrics
    try:
        metrics = model.val()
        print("\n=== Validation Results ===")
        print(f"mAP50:     {metrics.box.map50:.4f}")
        print(f"mAP50-95:  {metrics.box.map:.4f}")
        print(f"Precision: {metrics.box.mp:.4f}")
        print(f"Recall:    {metrics.box.mr:.4f}")
    except Exception as e:
        print(f"[NOTE] Val metrics print error: {e}")

if __name__ == "__main__":
    main()
