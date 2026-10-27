"""
Smart Parking Management System
AI Validation Script

STATUS: IMPLEMENTED (script ready; metrics = TO BE TESTED after actual training)

Usage:
    python ai/training/validate.py
    python ai/training/validate.py --model ai/models/best.pt
    python ai/training/validate.py --split test

Outputs (saved to outputs/eval/):
    - metrics.json  : Precision, Recall, mAP50, mAP50-95, F1
    - eval_report.txt : Human-readable evaluation summary

NOTE: If the model has not been trained yet, this script will report:
    MODEL TRAINING: TO BE TESTED
Do not fabricate metric values.
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import yaml


def resolve_project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def validate(model_path: str, dataset_yaml: str, split: str,
             device: str, conf: float, iou: float, output_dir: str) -> None:
    """Run YOLO validation and save real metrics."""
    try:
        from ultralytics import YOLO
    except ImportError:
        print("[ERROR] ultralytics not installed.")
        sys.exit(1)

    model_file = Path(model_path)
    if not model_file.exists():
        print(f"\n{'='*60}")
        print("  MODEL TRAINING: TO BE TESTED")
        print(f"{'='*60}")
        print(f"[INFO] Model not found at: {model_file.resolve()}")
        print("[INFO] Train the model first:")
        print("       python ai/training/train.py")
        print("       Then re-run validation.")
        return

    # ── Device ─────────────────────────────────────────────────────────────
    if device == "auto":
        try:
            import torch
            device = "0" if torch.cuda.is_available() else "cpu"
        except ImportError:
            device = "cpu"

    print(f"\n{'='*60}")
    print("  SMART PARKING YOLO VALIDATION")
    print(f"{'='*60}")
    print(f"  Model:   {model_path}")
    print(f"  Dataset: {dataset_yaml}")
    print(f"  Split:   {split}")
    print(f"  Device:  {device}")
    print(f"{'='*60}\n")

    model = YOLO(model_path)

    # ── Run validation ─────────────────────────────────────────────────────
    metrics = model.val(
        data=dataset_yaml,
        split=split,
        conf=conf,
        iou=iou,
        device=device,
        verbose=True,
    )

    # ── Extract metrics ────────────────────────────────────────────────────
    # ultralytics metrics object exposes: box.p, box.r, box.map50, box.map, box.f1
    try:
        precision    = float(metrics.box.p[0])    if hasattr(metrics.box, 'p')    else None
        recall       = float(metrics.box.r[0])    if hasattr(metrics.box, 'r')    else None
        map50        = float(metrics.box.map50)   if hasattr(metrics.box, 'map50') else None
        map50_95     = float(metrics.box.map)     if hasattr(metrics.box, 'map')   else None
        f1           = float(metrics.box.f1[0])   if hasattr(metrics.box, 'f1')   else None
    except Exception as e:
        print(f"[WARN] Could not extract all metrics: {e}")
        precision = recall = map50 = map50_95 = f1 = None

    # ── Build results dict ─────────────────────────────────────────────────
    results = {
        "evaluation_timestamp": datetime.now().isoformat(),
        "model_path": str(model_file.resolve()),
        "dataset_yaml": dataset_yaml,
        "split": split,
        "confidence_threshold": conf,
        "iou_threshold": iou,
        "metrics": {
            "precision":   round(precision, 4) if precision is not None else "NOT_AVAILABLE",
            "recall":      round(recall, 4)    if recall is not None    else "NOT_AVAILABLE",
            "mAP50":       round(map50, 4)     if map50 is not None     else "NOT_AVAILABLE",
            "mAP50_95":    round(map50_95, 4)  if map50_95 is not None  else "NOT_AVAILABLE",
            "F1":          round(f1, 4)        if f1 is not None        else "NOT_AVAILABLE",
        },
        "status": "EVALUATED",
        "note": (
            "Metrics are actual values from model evaluation. "
            "No values have been fabricated."
        )
    }

    # ── Save outputs ───────────────────────────────────────────────────────
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = out_dir / f"metrics_{ts}.json"
    txt_path  = out_dir / f"eval_report_{ts}.txt"

    with open(json_path, "w") as f:
        json.dump(results, f, indent=2)

    # Human-readable report
    report_lines = [
        "=" * 60,
        "  SMART PARKING SYSTEM — MODEL EVALUATION REPORT",
        "=" * 60,
        f"  Timestamp : {results['evaluation_timestamp']}",
        f"  Model     : {results['model_path']}",
        f"  Dataset   : {results['dataset_yaml']}",
        f"  Split     : {results['split']}",
        f"  Conf thr  : {conf}",
        f"  IoU thr   : {iou}",
        "-" * 60,
        "  METRICS (actual, not fabricated):",
        f"    Precision  : {results['metrics']['precision']}",
        f"    Recall     : {results['metrics']['recall']}",
        f"    mAP@50     : {results['metrics']['mAP50']}",
        f"    mAP@50-95  : {results['metrics']['mAP50_95']}",
        f"    F1 Score   : {results['metrics']['F1']}",
        "-" * 60,
        "  NOTE: Values above are actual computed metrics.",
        "  Run training before validation to obtain real values.",
        "=" * 60,
    ]
    report_text = "\n".join(report_lines)

    with open(txt_path, "w") as f:
        f.write(report_text)

    print("\n" + report_text)
    print(f"\n[INFO] Metrics saved → {json_path}")
    print(f"[INFO] Report saved  → {txt_path}")


# ── CLI ────────────────────────────────────────────────────────────────────── #

def main() -> None:
    project_root = resolve_project_root()

    # Load defaults from training config
    config_path = project_root / "ai" / "training" / "config.yaml"
    defaults: dict = {}
    if config_path.exists():
        with open(config_path) as f:
            defaults = yaml.safe_load(f)

    parser = argparse.ArgumentParser(
        description="Smart Parking - YOLO Validation Script"
    )
    parser.add_argument(
        "--model",
        default=str(project_root / defaults.get("output_dir", "outputs/training") / "best.pt"),
        help="Path to trained .pt model (default: ai/models/best.pt)"
    )
    parser.add_argument(
        "--dataset",
        default=str(project_root / defaults.get("dataset", "ai/dataset/dataset.yaml")),
        help="Path to dataset YAML"
    )
    parser.add_argument(
        "--split",
        choices=["val", "test"],
        default="val",
        help="Dataset split to evaluate on (default: val)"
    )
    parser.add_argument(
        "--device",
        default=defaults.get("device", "auto"),
        help="Device: auto | 0 | cpu"
    )
    parser.add_argument(
        "--conf",
        type=float,
        default=defaults.get("conf", 0.40),
        help="Confidence threshold"
    )
    parser.add_argument(
        "--iou",
        type=float,
        default=defaults.get("iou", 0.45),
        help="IoU threshold"
    )
    parser.add_argument(
        "--output",
        default=str(project_root / "outputs" / "eval"),
        help="Output directory for metrics"
    )
    args = parser.parse_args()

    # Use ai/models/best.pt as primary
    model_arg = str(project_root / "ai" / "models" / "best.pt") \
                if "--model" not in sys.argv else args.model

    validate(model_arg, args.dataset, args.split,
             args.device, args.conf, args.iou, args.output)


if __name__ == "__main__":
    main()
