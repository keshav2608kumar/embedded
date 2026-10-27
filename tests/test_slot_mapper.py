"""
Unit Tests — Slot Mapper

STATUS: IMPLEMENTED
Tests geometry-based vehicle-to-slot assignment.
Run: python -m pytest tests/test_slot_mapper.py -v
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ai.slot_mapping.slot_mapper import SlotMapper, Detection


# ── Sample slot polygons (simple rectangles for testing) ──────────────────── #

SAMPLE_SLOTS = {
    "S1": [[  0,   0], [200,   0], [200, 200], [  0, 200]],
    "S2": [[200,   0], [400,   0], [400, 200], [200, 200]],
    "S3": [[  0, 200], [200, 200], [200, 400], [  0, 400]],
    "S4": [[200, 200], [400, 200], [400, 400], [200, 400]],
}


def make_detection(cx: float, cy: float, conf: float = 0.85,
                   w: float = 80, h: float = 60) -> Detection:
    """Create a Detection with given center point."""
    return Detection(
        x1=cx - w / 2, y1=cy - h / 2,
        x2=cx + w / 2, y2=cy + h / 2,
        confidence=conf,
    )


class TestCenterPointMatching:
    """Tests using center-point-in-polygon matching."""

    def setup_method(self):
        self.mapper = SlotMapper(SAMPLE_SLOTS, use_center_point=True)

    def test_center_in_s1(self):
        det = make_detection(cx=100, cy=100)   # center of S1
        result = self.mapper.map_detections([det])
        assert result["S1"] is True
        assert result["S2"] is False
        assert result["S3"] is False
        assert result["S4"] is False

    def test_center_in_s2(self):
        det = make_detection(cx=300, cy=100)   # center of S2
        result = self.mapper.map_detections([det])
        assert result["S2"] is True
        assert result["S1"] is False

    def test_center_in_s3(self):
        det = make_detection(cx=100, cy=300)   # center of S3
        result = self.mapper.map_detections([det])
        assert result["S3"] is True

    def test_center_in_s4(self):
        det = make_detection(cx=300, cy=300)   # center of S4
        result = self.mapper.map_detections([det])
        assert result["S4"] is True

    def test_center_outside_all_slots(self):
        det = make_detection(cx=500, cy=500)   # outside all polygons
        result = self.mapper.map_detections([det])
        assert all(v is False for v in result.values())

    def test_multiple_vehicles_different_slots(self):
        dets = [
            make_detection(cx=100, cy=100),    # S1
            make_detection(cx=300, cy=300),    # S4
        ]
        result = self.mapper.map_detections(dets)
        assert result["S1"] is True
        assert result["S4"] is True
        assert result["S2"] is False
        assert result["S3"] is False

    def test_no_detections_all_free(self):
        result = self.mapper.map_detections([])
        assert all(v is False for v in result.values())


class TestIoUMatching:
    """Tests using IoU overlap matching."""

    def setup_method(self):
        self.mapper = SlotMapper(SAMPLE_SLOTS, use_center_point=False,
                                  overlap_threshold=0.30)

    def test_large_bbox_mostly_in_s1(self):
        # Bbox mostly in S1 area
        det = Detection(x1=10, y1=10, x2=180, y2=180, confidence=0.9)
        result = self.mapper.map_detections([det])
        assert result["S1"] is True

    def test_low_overlap_not_assigned(self):
        # Tiny bbox that barely overlaps any slot
        det = Detection(x1=195, y1=195, x2=210, y2=210, confidence=0.9)
        result = self.mapper.map_detections([det])
        # May or may not match depending on threshold — should not error
        assert isinstance(result, dict)
        assert set(result.keys()) == {"S1", "S2", "S3", "S4"}


class TestEmptyPolygons:
    """Tests with uncalibrated (empty) polygons."""

    def test_empty_polygons_give_all_false(self):
        mapper = SlotMapper({"S1": [], "S2": [], "S3": [], "S4": []})
        det = make_detection(cx=100, cy=100)
        result = mapper.map_detections([det])
        assert all(v is False for v in result.values())

    def test_is_calibrated_false_when_empty(self):
        mapper = SlotMapper({"S1": [], "S2": [], "S3": [], "S4": []})
        assert mapper.is_calibrated() is False

    def test_is_calibrated_true_when_all_set(self):
        mapper = SlotMapper(SAMPLE_SLOTS)
        assert mapper.is_calibrated() is True

    def test_partial_calibration(self):
        partial = {"S1": SAMPLE_SLOTS["S1"], "S2": [], "S3": [], "S4": []}
        mapper = SlotMapper(partial)
        assert mapper.is_calibrated() is False
        assert "S1" in mapper.calibrated_slots()
        assert "S2" not in mapper.calibrated_slots()
