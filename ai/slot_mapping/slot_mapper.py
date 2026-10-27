"""
Smart Parking Management System
Slot Mapper — Geometry Layer

STATUS: IMPLEMENTED

This module assigns YOLO vehicle detections to parking slots (S1–S4)
using polygon geometry. It is completely independent of the YOLO model.

IMPORTANT DESIGN PRINCIPLE:
    YOLO detects vehicles → returns bounding boxes.
    SlotMapper maps bounding boxes → S1/S2/S3/S4.
    "YOLO knows which slot is occupied" is INCORRECT.
    The slot assignment is done here, in this geometry module.

Algorithm:
    For each detection:
    1. Calculate center point (cx, cy) of bounding box.
    2. Test if center is inside each slot polygon (cv2.pointPolygonTest).
    3. Optionally: if no center match, test IoU overlap of bbox vs slot bbox.
    4. Assign vehicle to matched slot (if any).
    5. Return occupancy candidate dict for each slot.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

import cv2
import numpy as np

logger = logging.getLogger("smart_parking")


@dataclass
class Detection:
    """A single vehicle detection from YOLO."""
    x1: float
    y1: float
    x2: float
    y2: float
    confidence: float
    class_name: str = "vehicle"

    @property
    def center_x(self) -> float:
        return (self.x1 + self.x2) / 2.0

    @property
    def center_y(self) -> float:
        return (self.y1 + self.y2) / 2.0

    @property
    def width(self) -> float:
        return self.x2 - self.x1

    @property
    def height(self) -> float:
        return self.y2 - self.y1

    def as_tuple(self) -> tuple:
        """Return (x1, y1, x2, y2, conf, class_name) for overlay drawing."""
        return (self.x1, self.y1, self.x2, self.y2, self.confidence, self.class_name)


class SlotMapper:
    """
    Maps vehicle detection bounding boxes to parking slot IDs using polygon geometry.

    Supports two matching strategies (configurable):
    1. center_point: vehicle bbox center must be inside slot polygon.
    2. overlap: IoU between vehicle bbox and slot polygon bounding box
                must exceed overlap_threshold.
    """

    SLOT_IDS = ["S1", "S2", "S3", "S4"]

    def __init__(
        self,
        slot_polygons: dict[str, list[list[int]]],
        use_center_point: bool = True,
        overlap_threshold: float = 0.30,
    ) -> None:
        """
        Args:
            slot_polygons: Dict mapping slot IDs to polygon point lists.
                           e.g. {"S1": [[x1,y1],[x2,y2],...], ...}
            use_center_point: If True, use center-point-in-polygon matching.
            overlap_threshold: Minimum IoU to assign vehicle (for overlap mode).
        """
        self._raw_polygons = slot_polygons
        self._use_center = use_center_point
        self._overlap_threshold = overlap_threshold

        # Pre-convert to numpy arrays
        self._np_polygons: dict[str, Optional[np.ndarray]] = {}
        for slot_id in self.SLOT_IDS:
            pts = slot_polygons.get(slot_id, [])
            if pts and len(pts) >= 3:
                self._np_polygons[slot_id] = np.array(pts, dtype=np.float32)
            else:
                self._np_polygons[slot_id] = None
                if pts is not None:
                    logger.warning(
                        "Slot %s polygon has fewer than 3 points (%d). "
                        "Run calibrate_slots.py.",
                        slot_id, len(pts)
                    )

        calibrated = sum(1 for v in self._np_polygons.values() if v is not None)
        logger.info("SlotMapper initialised: %d/%d slots calibrated",
                    calibrated, len(self.SLOT_IDS))

    # ──────────────────────────────────────────────────────────────────────── #

    def map_detections(
        self, detections: list[Detection]
    ) -> dict[str, bool]:
        """
        Assign each detection to a parking slot.

        Returns:
            Dict mapping slot ID → bool (True = occupied candidate this frame).
            Slots with no matching detection → False.
        """
        # Start all slots as un-occupied candidates this frame
        occupancy: dict[str, bool] = {sid: False for sid in self.SLOT_IDS}

        for det in detections:
            matched_slot = self._find_slot(det)
            if matched_slot:
                occupancy[matched_slot] = True
                logger.debug(
                    "Detection conf=%.2f assigned to %s (center=%.0f,%.0f)",
                    det.confidence, matched_slot, det.center_x, det.center_y
                )
            else:
                logger.debug(
                    "Detection conf=%.2f at (%.0f,%.0f) matched no slot",
                    det.confidence, det.center_x, det.center_y
                )

        return occupancy

    # ──────────────────────────────────────────────────────────────────────── #

    def _find_slot(self, det: Detection) -> Optional[str]:
        """Return the slot ID that best matches this detection, or None."""
        if self._use_center:
            return self._match_center_point(det)
        else:
            return self._match_overlap(det)

    def _match_center_point(self, det: Detection) -> Optional[str]:
        """Check if vehicle center point falls inside any slot polygon."""
        cx, cy = det.center_x, det.center_y
        for slot_id, poly in self._np_polygons.items():
            if poly is None:
                continue
            # cv2.pointPolygonTest returns +ve if inside, 0 on edge, -ve if outside
            result = cv2.pointPolygonTest(poly, (float(cx), float(cy)), False)
            if result >= 0:
                return slot_id
        return None

    def _match_overlap(self, det: Detection) -> Optional[str]:
        """Find slot with highest IoU overlap with detection bbox."""
        best_slot: Optional[str] = None
        best_iou: float = self._overlap_threshold  # minimum threshold

        for slot_id, poly in self._np_polygons.items():
            if poly is None:
                continue
            # Use polygon bounding box for IoU calculation
            px1, py1 = float(poly[:, 0].min()), float(poly[:, 1].min())
            px2, py2 = float(poly[:, 0].max()), float(poly[:, 1].max())

            iou = self._compute_iou(
                (det.x1, det.y1, det.x2, det.y2),
                (px1, py1, px2, py2)
            )
            if iou > best_iou:
                best_iou = iou
                best_slot = slot_id

        return best_slot

    @staticmethod
    def _compute_iou(box_a: tuple, box_b: tuple) -> float:
        """Compute Intersection over Union between two axis-aligned bounding boxes."""
        ax1, ay1, ax2, ay2 = box_a
        bx1, by1, bx2, by2 = box_b

        ix1 = max(ax1, bx1)
        iy1 = max(ay1, by1)
        ix2 = min(ax2, bx2)
        iy2 = min(ay2, by2)

        inter_w = max(0.0, ix2 - ix1)
        inter_h = max(0.0, iy2 - iy1)
        inter_area = inter_w * inter_h

        if inter_area == 0:
            return 0.0

        area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
        area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
        union_area = area_a + area_b - inter_area

        return inter_area / union_area if union_area > 0 else 0.0

    # ──────────────────────────────────────────────────────────────────────── #

    def get_polygon_arrays(self) -> dict[str, Optional[np.ndarray]]:
        """Return pre-computed numpy polygon arrays (for overlay drawing)."""
        return self._np_polygons

    def is_calibrated(self) -> bool:
        """Return True if all 4 slot polygons are defined."""
        return all(v is not None for v in self._np_polygons.values())

    def calibrated_slots(self) -> list[str]:
        """Return list of slot IDs that have valid polygons."""
        return [sid for sid, poly in self._np_polygons.items() if poly is not None]
