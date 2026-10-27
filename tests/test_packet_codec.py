"""
Unit Tests — Packet Codec

STATUS: IMPLEMENTED
Tests the communication protocol encoder and decoder.
Run: python -m pytest tests/test_packet_codec.py -v
"""

import sys
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from communication.protocol.packet_codec import encode, decode, validate, AIStatus


class TestEncode:
    """Tests for packet encoding."""

    def test_all_free(self):
        pkt = encode(False, False, False, False, 4, AIStatus.OK)
        assert pkt == "<PKT,S1=0,S2=0,S3=0,S4=0,FREE=4,REC=S1,STATUS=OK>"

    def test_all_occupied(self):
        pkt = encode(True, True, True, True, 0, AIStatus.OK)
        assert pkt == "<PKT,S1=1,S2=1,S3=1,S4=1,FREE=0,REC=NONE,STATUS=OK>"

    def test_partial_occupancy(self):
        pkt = encode(True, False, True, False, 2, AIStatus.OK)
        assert pkt == "<PKT,S1=1,S2=0,S3=1,S4=0,FREE=2,REC=S2,STATUS=OK>"

    def test_camera_error_status(self):
        pkt = encode(False, False, False, False, 4, AIStatus.CAMERA_ERROR)
        assert "STATUS=CAMERA_ERROR" in pkt

    def test_degraded_status(self):
        pkt = encode(False, False, False, False, 4, AIStatus.DEGRADED)
        assert "STATUS=DEGRADED" in pkt

    def test_free_clamped_to_4(self):
        pkt = encode(False, False, False, False, 99, AIStatus.OK)
        assert "FREE=4" in pkt

    def test_free_clamped_to_0(self):
        pkt = encode(True, True, True, True, -5, AIStatus.OK)
        assert "FREE=0" in pkt

    def test_packet_starts_with_pkt(self):
        pkt = encode(False, False, False, False, 4, AIStatus.OK)
        assert pkt.startswith("<PKT,")

    def test_packet_ends_with_bracket(self):
        pkt = encode(False, False, False, False, 4, AIStatus.OK)
        assert pkt.endswith(">")


class TestDecode:
    """Tests for packet decoding."""

    def test_valid_all_free(self):
        result = decode("<PKT,S1=0,S2=0,S3=0,S4=0,FREE=4,STATUS=OK>")
        assert result is not None
        assert result["s1"] is False
        assert result["s2"] is False
        assert result["s3"] is False
        assert result["s4"] is False
        assert result["free"] == 4
        assert result["status"] == "OK"

    def test_valid_all_occupied(self):
        result = decode("<PKT,S1=1,S2=1,S3=1,S4=1,FREE=0,STATUS=OK>")
        assert result is not None
        assert result["s1"] is True
        assert result["free"] == 0

    def test_valid_partial(self):
        result = decode("<PKT,S1=1,S2=0,S3=1,S4=0,FREE=2,STATUS=OK>")
        assert result is not None
        assert result["s1"] is True
        assert result["s2"] is False
        assert result["s3"] is True
        assert result["s4"] is False
        assert result["free"] == 2

    def test_malformed_missing_fields(self):
        assert decode("<PKT,S1=1,S2=0>") is None

    def test_malformed_wrong_start(self):
        assert decode("PKT,S1=1,S2=0,S3=1,S4=0,FREE=2,STATUS=OK>") is None

    def test_malformed_no_end_bracket(self):
        assert decode("<PKT,S1=1,S2=0,S3=1,S4=0,FREE=2,STATUS=OK") is None

    def test_malformed_invalid_slot_value(self):
        assert decode("<PKT,S1=2,S2=0,S3=1,S4=0,FREE=2,STATUS=OK>") is None

    def test_malformed_invalid_free_value(self):
        assert decode("<PKT,S1=1,S2=0,S3=1,S4=0,FREE=9,STATUS=OK>") is None

    def test_empty_string(self):
        assert decode("") is None

    def test_none_like_garbage(self):
        assert decode("garbage_data_12345") is None

    def test_roundtrip(self):
        """Encode then decode must produce the same data."""
        pkt = encode(True, False, True, False, 2, AIStatus.OK)
        result = decode(pkt)
        assert result is not None
        assert result["s1"] is True
        assert result["s2"] is False
        assert result["s3"] is True
        assert result["s4"] is False
        assert result["free"] == 2
        assert result["status"] == "OK"


class TestValidate:
    """Tests for packet validation helper."""

    def test_valid_packet_returns_true(self):
        assert validate("<PKT,S1=0,S2=0,S3=0,S4=0,FREE=4,STATUS=OK>") is True

    def test_invalid_packet_returns_false(self):
        assert validate("not_a_packet") is False

    def test_empty_returns_false(self):
        assert validate("") is False
