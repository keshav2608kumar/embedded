# Testing Strategy

The system is designed to be highly testable without requiring the full hardware loop to be active. 

## 1. Unit Tests (Pytest)
Located in `/tests/`. 
Run with: `python -m pytest tests/ -v`

69 test cases cover:
- Temporal Filter thresholding, debounce, and session counting.
- Slot Mapper polygon intersection and IoU logic.
- Packet Codec encoding/decoding and error handling.
- Gate FSM state transitions and safety overrides.

## 2. Simulation Mode
Run with: `python main.py --mode simulation`

Runs the entire software stack (AI logic, temporal filters, simulated FSM) in the terminal. No ESP32 or Camera required. Allows interactive testing of edge cases (e.g., triggering the safety sensor while the gate is closing).

## 3. Hardware Test Mode
Run with: `python main.py --mode hardware_test`

Connect the ESP32. This mode provides a CLI to send specific `<TEST,...>` packets to the ESP32 to verify individual components:
- `[1]` Test LCD
- `[2]` Test Buzzer Patterns
- `[3/4]` Test Servo Open/Close
- `[5]` Read Vehicle Sensor
- `[7]` Test Watchdog Reset

## 4. Formal Test Matrix
See `tests/test_matrix.md` for a comprehensive list of all 35 formal test cases mapped to their current verification status.
