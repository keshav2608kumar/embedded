"""
Smart Parking Management System
Utility: Config Loader

STATUS: IMPLEMENTED
Centralised loader for system_config.json and parking_slots.json.
"""

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger("smart_parking")


def load_json(path: str | Path) -> dict:
    """Load and return a JSON config file. Raises FileNotFoundError with clear message."""
    p = Path(path)
    if not p.exists():
        # Fallback to project root if running from a parent or subdirectory
        project_root = Path(__file__).resolve().parent.parent.parent
        alt_p = project_root / path
        if alt_p.exists():
            p = alt_p
        else:
            raise FileNotFoundError(
                f"Config file not found: {p.resolve()}\n"
                f"Expected location: {p.resolve()}"
            )
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def load_system_config(path: str = "config/system_config.json") -> dict:
    """Load the main system configuration."""
    cfg = load_json(path)
    logger.info("System config loaded from %s", path)
    return cfg


def load_slot_config(path: str = "config/parking_slots.json") -> dict:
    """
    Load parking slot polygon configuration.
    Returns the slots dict. Raises ValueError if slots are empty (not calibrated).
    """
    cfg = load_json(path)
    slots = cfg.get("slots", {})

    empty_slots = [k for k, v in slots.items() if not v]
    if empty_slots:
        logger.warning(
            "Parking slots not calibrated for: %s\n"
            "Run: python ai/slot_mapping/calibrate_slots.py",
            empty_slots
        )
    return slots


def get(cfg: dict, *keys: str, default: Any = None) -> Any:
    """Safely traverse nested config dict. Returns default if any key is missing."""
    current = cfg
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key, default)
        if current is default:
            return default
    return current
