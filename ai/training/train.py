"""
Smart Parking Management System
AI Training Script

STATUS: IMPLEMENTED (script verified; actual model metrics = TO BE TESTED)
       Training requires a populated dataset in ai/dataset/

Usage:
    python ai/training/train.py
    python ai/training/train.py --config ai/training/config.yaml
    python ai/training/train.py --stage finetune --resume ai/models/stage1_best.pt

IMPORTANT DESIGN NOTE:
    The YOLO model is trained to detect ONE class: "vehicle".
    Parking slot assignment (S1-S4) is handled by the slot_mapper.py geometry
    layer AFTER detection. The model is layout-independent.

Training stages:
    Stage 1 (baseline): Public parking dataset → initial fine-tune of yolov8n.pt
    Stage 2 (finetune): Project-specific CCTV frames → domain adaptation
"""

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

import yaml


def resolve_project_root() -> Path:
    """Return the project root directory (smart-parking-system/)."""
    # This script lives at ai/training/train.py — go up two levels
    return Path(__file__).resolve().parent.parent.parent


def load_config(config_path: str) -> dict:
    """Load and return the training configuration YAML."""
    with open(config_path, "r") as f:
        cfg = yaml.safe_load(f)
    return cfg


def resolve_device(device_str: str) -> str:
    """Resolve 'auto' to the best available device."""
    if device_str == "auto":
        try:
            import torch
            if torch.cuda.is_available():
                device_name = torch.cuda.get_device_name(0)
                print(f"[INFO] CUDA available → using GPU: {device_name}")
                return "0"
            else:
                print("[INFO] CUDA not available → using CPU")
                return "cpu"
        except ImportError:
            print("[WARN] torch not found → defaulting to CPU")
            return "cpu"
    return device_str


def train(config_path: str, stage: str, resume_from: str | None) -> None:
    """Run YOLO training for the specified stage."""
    # ── Imports ────────────────────────────────────────────────────────────
    try:
        from ultralytics import YOLO
    except ImportError:
        print("[ERROR] ultralytics not installed. Run: pip install ultralytics")
        sys.exit(1)

    # ── Load config ────────────────────────────────────────────────────────
    cfg = load_config(config_path)
    project_root = resolve_project_root()

    device = resolve_device(cfg.get("device", "auto"))

    # ── Determine model ────────────────────────────────────────────────────
    if resume_from:
        model_path = resume_from
        print(f"[INFO] Resuming/fine-tuning from checkpoint: {model_path}")
    elif cfg.get("resume_from"):
        model_path = cfg["resume_from"]
        print(f"[INFO] Resuming from config checkpoint: {model_path}")
    else:
        model_path = cfg.get("model", "yolov8n.pt")
        print(f"[INFO] Starting from pretrained model: {model_path}")

    # ── Dataset path ───────────────────────────────────────────────────────
    dataset_yaml = project_root / cfg.get("dataset", "ai/dataset/dataset.yaml")
    if not dataset_yaml.exists():
        print(f"[ERROR] Dataset YAML not found: {dataset_yaml}")
        print("[ERROR] Populate ai/dataset/ with training images and labels first.")
        sys.exit(1)

    # ── Output directory ───────────────────────────────────────────────────
    run_name = f"{cfg.get('run_name', 'baseline')}_{stage}_{datetime.now():%Y%m%d_%H%M}"
    output_dir = project_root / cfg.get("output_dir", "outputs/training")
    output_dir.mkdir(parents=True, exist_ok=True)

    # ── Load model ─────────────────────────────────────────────────────────
    print(f"[INFO] Loading model: {model_path}")
    model = YOLO(model_path)

    # ── Start training ─────────────────────────────────────────────────────
    print("\n" + "="*60)
    print(f"  SMART PARKING YOLO TRAINING — Stage: {stage.upper()}")
    print("="*60)
    print(f"  Model:    {model_path}")
    print(f"  Dataset:  {dataset_yaml}")
    print(f"  Epochs:   {cfg.get('epochs', 50)}")
    print(f"  Img size: {cfg.get('imgsz', 640)}")
    print(f"  Batch:    {cfg.get('batch', 16)}")
    print(f"  Device:   {device}")
    print(f"  Output:   {output_dir / run_name}")
    print("="*60 + "\n")

    results = model.train(
        data=str(dataset_yaml),
        epochs=cfg.get("epochs", 50),
        imgsz=cfg.get("imgsz", 640),
        batch=cfg.get("batch", 16),
        lr0=cfg.get("lr0", 0.01),
        lrf=cfg.get("lrf", 0.01),
        momentum=cfg.get("momentum", 0.937),
        weight_decay=cfg.get("weight_decay", 0.0005),
        warmup_epochs=cfg.get("warmup_epochs", 3.0),
        patience=cfg.get("patience", 15),
        conf=cfg.get("conf", 0.40),
        iou=cfg.get("iou", 0.45),
        device=device,
        workers=cfg.get("workers", 4),
        project=str(output_dir),
        name=run_name,
        augment=cfg.get("augment", True),
        hsv_h=cfg.get("hsv_h", 0.015),
        hsv_s=cfg.get("hsv_s", 0.7),
        hsv_v=cfg.get("hsv_v", 0.4),
        degrees=cfg.get("degrees", 10.0),
        translate=cfg.get("translate", 0.1),
        scale=cfg.get("scale", 0.5),
        fliplr=cfg.get("fliplr", 0.5),
        mosaic=cfg.get("mosaic", 1.0),
        exist_ok=True,
        verbose=True,
    )

    # ── Copy best weights to ai/models/ ───────────────────────────────────
    models_dir = project_root / "ai" / "models"
    models_dir.mkdir(parents=True, exist_ok=True)

    best_src = output_dir / run_name / "weights" / "best.pt"
    if best_src.exists():
        import shutil
        dest_name = f"best_{stage}.pt"
        shutil.copy2(best_src, models_dir / dest_name)
        # Also update the generic best.pt
        shutil.copy2(best_src, models_dir / "best.pt")
        print(f"\n[INFO] Best weights saved → ai/models/{dest_name}")
        print(f"[INFO] Also updated → ai/models/best.pt")
    else:
        print(f"[WARN] best.pt not found at {best_src}")

    print("\n[INFO] Training complete.")
    print("[INFO] Next step: python ai/training/validate.py")


# ── CLI entry point ────────────────────────────────────────────────────────── #

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Smart Parking - YOLO Training Script"
    )
    parser.add_argument(
        "--config",
        default="ai/training/config.yaml",
        help="Path to training config YAML (default: ai/training/config.yaml)"
    )
    parser.add_argument(
        "--stage",
        choices=["baseline", "finetune"],
        default="baseline",
        help="Training stage: baseline (public dataset) or finetune (project CCTV data)"
    )
    parser.add_argument(
        "--resume",
        default=None,
        metavar="CHECKPOINT",
        help="Path to .pt checkpoint to resume from or fine-tune"
    )
    args = parser.parse_args()

    # Resolve config path relative to project root
    project_root = resolve_project_root()
    config_path = args.config if Path(args.config).is_absolute() \
                  else str(project_root / args.config)

    if not Path(config_path).exists():
        print(f"[ERROR] Config not found: {config_path}")
        sys.exit(1)

    train(config_path, args.stage, args.resume)


if __name__ == "__main__":
    main()
