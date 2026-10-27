"""
Smart Parking Management System
Communication Protocol — Packet Codec

STATUS: IMPLEMENTED

Encodes and decodes communication packets between the Python AI pipeline
and the ESP32 embedded controller.

Protocol format:
    <PKT,S1=1,S2=0,S3=1,S4=0,FREE=2,STATUS=OK>

Where:
    S1..S4  : 1 = OCCUPIED, 0 = FREE
    FREE    : count of free slots (0–4)
    STATUS  : AI system status string

Design:
    The protocol is modular — the same encode/decode logic can be used
    over USB serial (current) or Wi-Fi/MQTT (future scope) without changes.

ESP32 validation rules:
    - Packet must start with '<PKT,'
    - Packet must end with '>'
    - Must contain exactly S1=, S2=, S3=, S4=, FREE=, STATUS=
    - S1..S4 values must be 0 or 1
    - FREE must be 0–4
    - Any malformed packet → IGNORE
"""

import re
import logging
from typing import Optional

logger = logging.getLogger("smart_parking")


# ── Valid STATUS values ───────────────────────────────────────────────────── #

class AIStatus:
    OK           = "OK"
    DEGRADED     = "DEGRADED"
    CAMERA_ERROR = "CAMERA_ERROR"
    COMM_LOST    = "COMM_LOST"
    INITIALIZING = "INIT"


# ── Packet structure ─────────────────────────────────────────────────────── #

PACKET_START = "<PKT,"
PACKET_END   = ">"
FIELD_SEP    = ","
FIELD_ASSIGN = "="


# ── Regex for validation ─────────────────────────────────────────────────── #

_PACKET_PATTERN = re.compile(
    r"^<PKT,"
    r"(?:S1=([01]),S2=([01]),S3=([01]),S4=([01]),)?"
    r"FREE=([0-4]),"
    r"(?:REC=([A-Za-z0-9_]+),)?"
    r"(?:OCC=\d+,)?"
    r"(?:GATE=\w+,)?"
    r"STATUS=(\w+)"
    r">$"
)


# ── Slot Recommendation ──────────────────────────────────────────────────── #

def recommend_slot(s1: bool, s2: bool, s3: bool, s4: bool) -> str:
    """
    Select the first reliably available slot in order: S1 -> S2 -> S3 -> S4.
    Never recommend a slot currently classified as occupied.
    If all slots are occupied, returns 'NONE'.
    """
    for name, occ in [("S1", s1), ("S2", s2), ("S3", s3), ("S4", s4)]:
        if not occ:
            return name
    return "NONE"


# ── Encoder ─────────────────────────────────────────────────────────────────

def encode(
    s1: bool,
    s2: bool,
    s3: bool,
    s4: bool,
    free: int,
    status: str = AIStatus.OK,
    rec: Optional[str] = None,
) -> str:
    """
    Encode parking status into a protocol packet string with slot recommendation.

    Args:
        s1..s4 : True = OCCUPIED, False = FREE
        free   : Number of free slots
        status : AI system status string
        rec    : Recommended slot ID ('S1'..'S4' or 'NONE'). If None, computed automatically.

    Returns:
        Encoded packet string, e.g. '<PKT,S1=1,S2=0,S3=1,S4=0,FREE=2,REC=S2,STATUS=OK>'
    """
    # Clamp and validate inputs
    free = max(0, min(4, int(free)))
    s1_v = 1 if s1 else 0
    s2_v = 1 if s2 else 0
    s3_v = 1 if s3 else 0
    s4_v = 1 if s4 else 0

    if rec is None:
        rec = recommend_slot(s1, s2, s3, s4)
    else:
        rec = re.sub(r"[^\w]", "", str(rec))[:8]

    # Sanitize status — only alphanumeric + underscore
    status_safe = re.sub(r"[^\w]", "_", status)[:16]

    packet = f"<PKT,S1={s1_v},S2={s2_v},S3={s3_v},S4={s4_v},FREE={free},REC={rec},STATUS={status_safe}>"
    logger.debug("Encoded packet: %s", packet)
    return packet


def encode_from_states(
    slot_states: dict[str, str],   # {"S1": "OCCUPIED"|"FREE"|"UNCERTAIN", ...}
    status: str = AIStatus.OK,
    rec: Optional[str] = None,
) -> str:
    """
    Convenience encoder from slot state strings.
    UNCERTAIN slots are treated as OCCUPIED for recommendation safety (conservative).
    """
    from ai.tracking.temporal_filter import SlotState

    s1 = slot_states.get("S1", "FREE") == SlotState.OCCUPIED
    s2 = slot_states.get("S2", "FREE") == SlotState.OCCUPIED
    s3 = slot_states.get("S3", "FREE") == SlotState.OCCUPIED
    s4 = slot_states.get("S4", "FREE") == SlotState.OCCUPIED

    free = sum(1 for v in (s1, s2, s3, s4) if not v)
    return encode(s1, s2, s3, s4, free, status, rec=rec)


# ── Decoder ─────────────────────────────────────────────────────────────────

def decode(raw: str) -> Optional[dict]:
    """
    Decode a received packet string.

    Returns:
        dict with keys: s1, s2, s3, s4 (bool), free (int), rec (str), status (str)
        None if packet is malformed or invalid.
    """
    if not raw:
        return None

    raw = raw.strip()
    match = _PACKET_PATTERN.match(raw)
    if not match:
        logger.warning("Invalid packet (ignored): %r", raw[:80])
        return None

    s1_v, s2_v, s3_v, s4_v, free_v, rec_v, status_v = match.groups()
    s1 = (s1_v == "1") if s1_v is not None else False
    s2 = (s2_v == "1") if s2_v is not None else False
    s3 = (s3_v == "1") if s3_v is not None else False
    s4 = (s4_v == "1") if s4_v is not None else False
    free = int(free_v)
    rec = rec_v if rec_v else recommend_slot(s1, s2, s3, s4)

    result = {
        "s1": s1,
        "s2": s2,
        "s3": s3,
        "s4": s4,
        "free": free,
        "rec": rec,
        "status": status_v,
        "raw": raw,
    }
    logger.debug("Decoded packet: %s", result)
    return result


def validate(raw: str) -> bool:
    """Return True if the packet string is valid."""
    return decode(raw) is not None
