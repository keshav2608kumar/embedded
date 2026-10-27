"""
Smart Parking Management System
Utility: Logger

STATUS: IMPLEMENTED
Writes structured logs (CSV or JSON) for every system event.
Columns: timestamp, S1, S2, S3, S4, available, ai_status, comm_status,
         gate_state, sensor_state, error
"""

import csv
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional


# --------------------------------------------------------------------------- #
#  Console / file logger (standard Python logging)
# --------------------------------------------------------------------------- #

def setup_logger(name: str = "smart_parking", log_dir: str = "logs",
                 level: str = "INFO") -> logging.Logger:
    """Set up a named logger that writes to console and a rotating log file."""
    Path(log_dir).mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    if logger.handlers:          # avoid duplicate handlers on re-import
        return logger

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Console handler
    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    # File handler
    log_file = Path(log_dir) / f"system_{datetime.now():%Y%m%d}.log"
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    return logger


# --------------------------------------------------------------------------- #
#  Structured event logger (CSV / JSON session file)
# --------------------------------------------------------------------------- #

class EventLogger:
    """
    Writes structured parking-system events to a CSV or JSON file.

    Each row/entry records the full system snapshot at a given timestamp.
    """

    COLUMNS = [
        "timestamp", "S1", "S2", "S3", "S4", "available",
        "ai_status", "comm_status", "gate_state", "sensor_state", "error"
    ]

    def __init__(self, log_dir: str = "logs", fmt: str = "csv") -> None:
        Path(log_dir).mkdir(parents=True, exist_ok=True)
        self._fmt = fmt.lower()
        session_ts = datetime.now().strftime("%Y%m%d_%H%M%S")

        if self._fmt == "csv":
            self._path = Path(log_dir) / f"session_{session_ts}.csv"
            self._file = open(self._path, "w", newline="", encoding="utf-8")
            self._writer = csv.DictWriter(self._file, fieldnames=self.COLUMNS)
            self._writer.writeheader()
            self._file.flush()
        else:                    # json
            self._path = Path(log_dir) / f"session_{session_ts}.json"
            self._file = open(self._path, "w", encoding="utf-8")
            self._records: list[dict] = []

        self._logger = setup_logger()
        self._logger.info("EventLogger started → %s", self._path)

    # ---------------------------------------------------------------------- #

    def log(
        self,
        slot_states: dict,          # {"S1": bool, "S2": bool, ...}  True=OCCUPIED
        available: int,
        ai_status: str = "AI_OK",
        comm_status: str = "COMM_OK",
        gate_state: str = "GATE_CLOSED",
        sensor_state: str = "CLEAR",
        error: Optional[str] = None,
    ) -> None:
        """Write one snapshot row/entry."""
        row = {
            "timestamp": datetime.now().isoformat(timespec="milliseconds"),
            "S1": int(slot_states.get("S1", False)),
            "S2": int(slot_states.get("S2", False)),
            "S3": int(slot_states.get("S3", False)),
            "S4": int(slot_states.get("S4", False)),
            "available": available,
            "ai_status": ai_status,
            "comm_status": comm_status,
            "gate_state": gate_state,
            "sensor_state": sensor_state,
            "error": error or "",
        }

        if self._fmt == "csv":
            self._writer.writerow(row)
            self._file.flush()
        else:
            self._records.append(row)
            self._file.seek(0)
            json.dump(self._records, self._file, indent=2)
            self._file.flush()

        if error:
            self._logger.error("EVENT ERROR: %s | states=%s", error, row)

    # ---------------------------------------------------------------------- #

    def log_wdt_reset(self) -> None:
        """Log a WDT (watchdog timer) reset event."""
        self._logger.critical("WDT RESET DETECTED — ESP32 recovered from watchdog timeout")
        self.log(
            slot_states={"S1": False, "S2": False, "S3": False, "S4": False},
            available=4,
            ai_status="AI_OK",
            comm_status="COMM_OK",
            gate_state="GATE_CLOSED",
            sensor_state="UNKNOWN",
            error="WDT_RESET",
        )

    # ---------------------------------------------------------------------- #

    def close(self) -> None:
        """Flush and close the log file."""
        if self._file and not self._file.closed:
            self._file.flush()
            self._file.close()
        self._logger.info("EventLogger closed → %s", self._path)

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass
