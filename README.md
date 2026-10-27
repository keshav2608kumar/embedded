# Smart Parking Management System
## CCTV + YOLOv8 + ESP32 + Gate FSM + Watchdog Timer

> **University Engineering Project**
> Domain: Embedded Systems + Computer Vision + AI

---

## Team

| Member | Reg. No. | Subsystem |
|--------|----------|-----------|
| **Harshavardhan Singh** | 25BCE0552 | Hardware & Circuit Design (ESP32, LCD, Buzzer, Servo, Sensor, Wiring, Power) |
| **Shaikh Shayaan** | 25BCE2623 | Gate & Entry/Exit Engineering (FSM, Servo Safety, Sensor Logic, Entry Decision) |
| **Keshav Kumar** | 25BCE2880 | AI + Embedded Logic (CCTV, YOLO, Dataset, Slot Mapping, Temporal Filter, Communication) |

All three subsystems are equally critical. The complete system depends on Hardware + Gate/Safety + AI/Embedded Logic working together.

---

## System Architecture

```
CCTV / USB / IP CAMERA
        ↓
      OpenCV
        ↓
  YOLO Vehicle Detection
        ↓
  Bounding Boxes + Confidence
        ↓
  Parking Slot Mapping (Geometry Layer)
        ↓
  Temporal Filtering (Debounce)
        ↓
  S1  S2  S3  S4 Occupancy Status
        ↓
  Available Slot Calculation
        ↓
  PC → ESP32 (USB Serial)
        ↓
       ESP32
    ↙   ↓    ↘
  LCD  Buzzer  Gate FSM
                  ↓
            Vehicle Sensor (Safety)
                  ↓
            Servo Motor → Parking Gate
```

**IMPORTANT:** YOLO detects vehicles. The application geometry layer (slot_mapper.py) maps bounding boxes to S1–S4. YOLO does NOT identify parking slots directly.

---

## Project Status

| Component | Status |
|-----------|--------|
| Project structure | ✅ IMPLEMENTED |
| Config system | ✅ IMPLEMENTED |
| Dataset pipeline | ✅ IMPLEMENTED |
| YOLO training script | ✅ IMPLEMENTED |
| YOLO validation script | ✅ IMPLEMENTED |
| Frame capture tool | ✅ IMPLEMENTED |
| Slot calibration tool | ✅ IMPLEMENTED |
| Slot mapper (geometry) | ✅ IMPLEMENTED |
| Temporal filter | ✅ IMPLEMENTED |
| Occupancy session tracking | ✅ IMPLEMENTED |
| Serial communication | ✅ IMPLEMENTED |
| Simulation mode | ✅ IMPLEMENTED |
| Gate FSM (Python sim) | ✅ IMPLEMENTED |
| Unit tests (69/69) | ✅ IMPLEMENTED |
| ESP32 firmware (all modules) | ✅ IMPLEMENTED |
| Model training metrics | 🔲 TO BE TESTED |
| Real-time CCTV inference | 🔲 TO BE TESTED (requires camera) |
| Hardware integration | 🔧 HARDWARE TEST REQUIRED |

---

## Quick Start

### 1. Install Python dependencies
```bash
cd smart-parking-system
pip install -r requirements.txt
```

### 2. Run simulation (no hardware needed)
```bash
python main.py --mode simulation
```
Use the interactive menu to toggle slot states, trigger sensor events, test FSM transitions.

### 3. Run all unit tests
```bash
python -m pytest tests/ -v
```

### 4. Prepare dataset
Place annotated images in YOLO format:
```
ai/dataset/images/train/   ← training images (.jpg)
ai/dataset/labels/train/   ← YOLO .txt labels (class cx cy w h, class=0)
ai/dataset/images/val/     ← validation images
ai/dataset/labels/val/     ← validation labels
```

Or capture frames from your parking camera:
```bash
python data_tools/capture_dataset.py --source 0 --interval 2.0
```

### 5. Train the model
```bash
# Stage 1: public dataset fine-tune
python ai/training/train.py --stage baseline

# Stage 2: project CCTV data fine-tune
python ai/training/train.py --stage finetune --resume ai/models/best_baseline.pt
```

### 6. Validate the model
```bash
python ai/training/validate.py
```
Metrics are saved to `outputs/eval/`. **All values are actual measured metrics — never fabricated.**

### 7. Calibrate parking slots
```bash
python ai/slot_mapping/calibrate_slots.py --source 0
```
Click corners for S1 → S2 → S3 → S4. Press ENTER after each slot.
Coordinates saved to `config/parking_slots.json`.

### 8. Run real-time CCTV inference (no ESP32)
```bash
python ai/inference/run_cctv.py --source 0 --simulate-comm
```

### 9. Upload ESP32 firmware
1. Open `esp32/smart_parking/smart_parking.ino` in Arduino IDE
2. Install libraries: **LiquidCrystal I2C**, **ESP32Servo**
3. Board: `ESP32 Dev Module`
4. Upload speed: `115200`
5. Update `config/system_config.json` → set correct COM port
6. Click Upload

### 10. Run full live system
```bash
# Update COM port in config/system_config.json first
python main.py --mode live
```

### 11. Hardware component testing
```bash
python main.py --mode hardware_test
```

---

## Configuration

All parameters in `config/system_config.json`:
- `camera.source` — webcam index, file path, or RTSP URL
- `model.path` — path to trained `.pt` model
- `model.confidence_threshold` — YOLO detection threshold
- `temporal_filter.occupied_confirm_frames` — frames before confirming OCCUPIED
- `temporal_filter.free_confirm_frames` — frames before confirming FREE
- `communication.serial.port` — ESP32 COM port (e.g. `COM3`)

ESP32 hardware constants in `esp32/smart_parking/config.h`:
- `GATE_OPEN_ANGLE` / `GATE_CLOSED_ANGLE` — servo angles
- `LCD_I2C_ADDR` — LCD I²C address (0x27 or 0x3F)
- `WDT_TIMEOUT_SEC` — watchdog timeout

---

## Key Design Decisions

1. **YOLO detects `vehicle` only** — one class. S1/S2/S3/S4 assignment is geometry (polygon), not AI.
2. **Temporal filter** — slot state only changes after N consecutive confirming frames. Prevents single-frame flicker.
3. **Simulation mode** — all software logic runs without any hardware using `--mode simulation`.
4. **WDT ≠ FSM** — watchdog is a fault-recovery mechanism. FSM is normal gate logic. Not the same thing.
5. **Safe defaults** — on any ESP32 boot or reset: servo moves to `GATE_CLOSED_ANGLE` as first action.
6. **No fabricated results** — all model metrics are marked `TO BE TESTED` until actually measured.

---

## Limitations

- Camera positioning affects slot polygon accuracy
- Poor lighting reduces YOLO detection reliability
- Occlusion (vehicles hiding other vehicles) may affect detection
- AI requires a computer with sufficient CPU/GPU resources
- Camera failure causes occupancy to be held at last known state
- Incorrect slot calibration directly affects S1-S4 assignment accuracy
- Serial communication failure prevents ESP32 from receiving updates
- Public datasets may not perfectly represent the project's actual parking view
- Servo mechanics vary — GATE_OPEN_ANGLE and GATE_CLOSED_ANGLE must be tuned

---

## Future Scope

- Multiple CCTV cameras for larger parking areas
- ANPR/License plate recognition
- Wi-Fi/MQTT communication (protocol module is already modular)
- Web/mobile dashboard
- Cloud monitoring and history
- Automatic parking reservation
- Dynamic slot allocation
- Edge AI deployment (Raspberry Pi / Jetson)
- Vehicle classification (car vs motorcycle vs bus)
- Payment integration

---

## File Structure

```
smart-parking-system/
├── ai/
│   ├── dataset/             ← YOLO dataset (images + labels + dataset.yaml)
│   ├── models/              ← Saved .pt checkpoints
│   ├── training/            ← train.py, validate.py, config.yaml
│   ├── inference/           ← run_cctv.py (real-time pipeline)
│   ├── slot_mapping/        ← calibrate_slots.py, slot_mapper.py
│   ├── tracking/            ← temporal_filter.py (occupancy sessions)
│   └── utils/               ← logger.py, overlay.py, config_loader.py
├── esp32/smart_parking/     ← Arduino firmware (8 modules + main .ino)
├── communication/
│   ├── protocol/            ← packet_codec.py, gate_fsm_sim.py
│   └── serial/              ← serial_sender.py
├── config/
│   ├── system_config.json   ← all runtime parameters
│   └── parking_slots.json   ← S1-S4 polygon coordinates
├── data_tools/              ← capture_dataset.py
├── tests/                   ← 69 unit tests + test_matrix.md
├── documentation/           ← architecture.md, ai_pipeline.md, etc.
├── logs/                    ← session CSV/JSON logs
├── outputs/                 ← training results, eval metrics
├── main.py                  ← entry point (--mode live/simulation/hardware_test)
└── requirements.txt
```
