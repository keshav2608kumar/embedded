# Smart Parking System — Formal Test Matrix

> All tests are labelled with their current status:
> - ✅ **IMPLEMENTED** — software logic exists and is verified
> - 🧪 **SIMULATED** — verified through simulation mode (`python main.py --mode simulation`)
> - 🔲 **TO BE TESTED** — requires actual camera / video / dataset
> - 🔧 **HARDWARE TEST REQUIRED** — requires physical ESP32 + components

---

## AI Subsystem Tests

| # | Test Case | Expected Result | Status |
|---|-----------|----------------|--------|
| AI-01 | Empty parking → 0 vehicles detected | 4 slots FREE, available=4 | 🔲 TO BE TESTED |
| AI-02 | 1 vehicle in S1 → only S1 occupied | S1=OCCUPIED, S2-S4=FREE, available=3 | 🔲 TO BE TESTED |
| AI-03 | 2 vehicles in S1, S3 | S1=S3=OCCUPIED, S2=S4=FREE, available=2 | 🔲 TO BE TESTED |
| AI-04 | 3 vehicles occupying 3 slots | 1 slot FREE, available=1 | 🔲 TO BE TESTED |
| AI-05 | 4 vehicles → all slots occupied | available=0, PARKING FULL state | 🔲 TO BE TESTED |
| AI-06 | Temporary detection loss (1-4 frames) | Slot state remains stable (temporal filter holds) | ✅ IMPLEMENTED (temporal filter verified) |
| AI-07 | Low-confidence detection (<0.40) | Detection ignored, slot state unchanged | ✅ IMPLEMENTED (conf_threshold filter in run_cctv.py) |
| AI-08 | Camera disconnected | AI_STATUS=CAMERA_ERROR, slot states held | ✅ IMPLEMENTED (error handler in run_cctv.py) |
| AI-09 | Multiple vehicles → correct slot assignment | Each vehicle maps to correct polygon | ✅ IMPLEMENTED (slot_mapper tested in test_slot_mapper.py) |
| AI-10 | Lighting variation (shadows, low light) | Detection robustness evaluation | 🔲 TO BE TESTED (model training required) |

---

## Temporal Filter Tests

| # | Test Case | Expected Result | Status |
|---|-----------|----------------|--------|
| TF-01 | N-1 consecutive OCCUPIED frames | State stays FREE | ✅ IMPLEMENTED |
| TF-02 | Exactly N consecutive OCCUPIED frames | State → OCCUPIED | ✅ IMPLEMENTED |
| TF-03 | N-1 consecutive FREE frames after OCCUPIED | State stays OCCUPIED | ✅ IMPLEMENTED |
| TF-04 | Exactly N consecutive FREE frames after OCCUPIED | State → FREE | ✅ IMPLEMENTED |
| TF-05 | Alternating OCCUPIED/FREE frames | State stays FREE (never confirms) | ✅ IMPLEMENTED |
| TF-06 | Occupancy session start timestamp recorded | Non-None start_time on OCCUPIED confirm | ✅ IMPLEMENTED |
| TF-07 | Occupancy session duration calculated on FREE | duration_seconds >= 0 | ✅ IMPLEMENTED |
| TF-08 | Multiple occupancy cycles | Session count increments correctly | ✅ IMPLEMENTED |

---

## Communication Protocol Tests

| # | Test Case | Expected Result | Status |
|---|-----------|----------------|--------|
| CP-01 | Valid packet encode + decode roundtrip | Decoded values match encoded values | ✅ IMPLEMENTED |
| CP-02 | Malformed packet (missing fields) | decode() returns None | ✅ IMPLEMENTED |
| CP-03 | Packet with wrong start sequence | decode() returns None | ✅ IMPLEMENTED |
| CP-04 | Packet with invalid S-value (e.g. S1=2) | decode() returns None | ✅ IMPLEMENTED |
| CP-05 | Packet with invalid FREE value (>4) | decode() returns None | ✅ IMPLEMENTED |
| CP-06 | Python → ESP32 serial send | Packet received correctly on ESP32 | 🔧 HARDWARE TEST REQUIRED |
| CP-07 | COMM_LOST after 15s no packet | comm_is_lost() returns true | 🔲 TO BE TESTED |

---

## Gate FSM Tests

| # | Test Case | Expected Result | Status |
|---|-----------|----------------|--------|
| GF-01 | Free slot available + vehicle request → gate opens | State: CLOSED → OPENING | ✅ IMPLEMENTED |
| GF-02 | All slots occupied + vehicle request → gate stays closed | State: CLOSED, buzzer PARKING_FULL | ✅ IMPLEMENTED |
| GF-03 | Vehicle passing → gate holds OPEN | State: VEHICLE_PASSING, gate stays open | ✅ IMPLEMENTED |
| GF-04 | Vehicle clears → gate closes | State: VEHICLE_PASSING → CLOSING → CLOSED | ✅ IMPLEMENTED |
| GF-05 | Vehicle detected while gate closing → gate reopens (SAFETY) | State: CLOSING → OPENING, buzzer GATE_SAFETY | ✅ IMPLEMENTED |
| GF-06 | Communication LOST → gate behaviour | Gate holds current state; no automatic open | 🧪 SIMULATED |
| GF-07 | ESP32 hang → WDT recovery | WDT timeout → reset → gate CLOSED on boot | 🔧 HARDWARE TEST REQUIRED |
| GF-08 | Sensor failure (SENSOR_ERROR) | Gate closes conservatively | ✅ IMPLEMENTED |

---

## Hardware Tests (Individual Components)

> All hardware tests are: 🔧 HARDWARE TEST REQUIRED
> Use: `python main.py --mode hardware_test`

| # | Component | Test Procedure | Status |
|---|-----------|---------------|--------|
| HW-01 | LCD | Display test message on all 16 chars × 2 rows | 🔧 HARDWARE TEST REQUIRED |
| HW-02 | Buzzer | Play PARKING_FULL, GATE_SAFETY, SYSTEM_ERROR patterns | 🔧 HARDWARE TEST REQUIRED |
| HW-03 | Servo open | Command GATE_OPEN_ANGLE, verify physical movement | 🔧 HARDWARE TEST REQUIRED |
| HW-04 | Servo close | Command GATE_CLOSED_ANGLE, verify physical movement | 🔧 HARDWARE TEST REQUIRED |
| HW-05 | Vehicle sensor | Trigger sensor, verify DETECTED state in serial monitor | 🔧 HARDWARE TEST REQUIRED |
| HW-06 | Serial echo | Send `<TEST,ECHO,MSG=HELLO>`, expect echo back | 🔧 HARDWARE TEST REQUIRED |
| HW-07 | WDT test | Halt main loop, verify ESP32 resets in WDT_TIMEOUT_SEC seconds | 🔧 HARDWARE TEST REQUIRED |
| HW-08 | Full FSM cycle | Send valid PKT, trigger sensor, verify gate completes CLOSED→OPEN→CLOSED | 🔧 HARDWARE TEST REQUIRED |

---

## End-to-End Scenario Tests

| # | Scenario | Expected End State | Status |
|---|----------|--------------------|--------|
| E2E-01 | Parking available — vehicle arrives, parks, leaves | Gate: CLOSED→OPEN→VEHICLE_PASSING→CLOSED | 🔧 HARDWARE TEST REQUIRED |
| E2E-02 | Parking full — vehicle arrives at gate | Gate: stays CLOSED, buzzer sounds | 🧪 SIMULATED |
| E2E-03 | Safety during closing — vehicle redetected | Gate: CLOSING→OPENING, buzzer sounds | 🧪 SIMULATED |
| E2E-04 | ESP32 software fault — WDT recovery | ESP32 resets, gate closes, system resumes | 🔧 HARDWARE TEST REQUIRED |
| E2E-05 | Camera disconnects mid-session | AI_STATUS=CAMERA_ERROR, slot states held, no unsafe gate action | 🧪 SIMULATED |

---

## Performance Metrics (TO BE MEASURED)

> The following metrics will be measured during hardware testing.
> No values are fabricated. All fields below are placeholders.

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| YOLO detection precision | > 0.80 | NOT TESTED | 🔲 TO BE TESTED |
| YOLO recall | > 0.80 | NOT TESTED | 🔲 TO BE TESTED |
| mAP@50 | > 0.75 | NOT TESTED | 🔲 TO BE TESTED |
| Inference FPS (RTX 3050) | > 15 | NOT TESTED | 🔲 TO BE TESTED |
| CCTV-to-ESP32 latency | < 2s | NOT TESTED | 🔲 TO BE TESTED |
| Gate response time | < 3s from request | NOT TESTED | 🔧 HARDWARE TEST REQUIRED |
| WDT recovery time | < WDT_TIMEOUT_SEC + 3s | NOT TESTED | 🔧 HARDWARE TEST REQUIRED |
