# Communication Protocol

The system uses a highly structured ASCII string protocol over USB Serial.

## Packet Format

**Format:** `<PKT,S1=X,S2=X,S3=X,S4=X,FREE=Y,STATUS=MSG>`

**Example:** `<PKT,S1=1,S2=0,S3=1,S4=0,FREE=2,STATUS=AI_OK>`

### Fields
- `S1` to `S4`: Slot occupancy boolean (`1` = Occupied, `0` = Free)
- `FREE`: Integer count of available slots (`0` to `4`)
- `STATUS`: String representing AI pipeline health (`AI_OK`, `CAMERA_ERROR`, `DEGRADED`)

## Implementation Details

### Python Encoder (`communication/protocol/packet_codec.py`)
- Takes boolean states and formats them into the exact string required.
- Prevents invalid strings (e.g. sanitizes the STATUS message).

### ESP32 Decoder (`communication.cpp`)
- Reads serial data into a ring buffer.
- Validates that packets start with `<PKT,` and end with `>`.
- **Strict Adherence:** Any packet that is malformed, truncated, or corrupted is silently ignored. The ESP32 will simply wait for the next valid packet.

### `COMM_LOST` State
If the ESP32 does not receive a valid packet within `COMM_TIMEOUT_MS` (default 15 seconds), it sets a `COMM_LOST` flag. This triggers the LCD to display a warning ("COMM LOST - CHECK PC CONN") and prevents the system from acting on stale data.
