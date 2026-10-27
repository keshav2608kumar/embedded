/**
 * Smart Parking Management System
 * ESP32 Firmware — Gate FSM Implementation
 *
 * STATUS: IMPLEMENTED (HARDWARE TEST REQUIRED)
 *
 * Team Member: Shaikh Shayaan (25BCE2623) — Gate & Entry/Exit Engineering
 */

#include "gate_fsm.h"
#include "servo_gate.h"
#include "buzzer.h"
#include <Arduino.h>

GateState_t      g_gateState = GATE_CLOSED;
AdmissionState_t g_admissionState = ADMISSION_IDLE;
unsigned long    g_admissionEventMs = 0;

static unsigned long _gateMoveStartMs = 0;
static unsigned long _gateOpenStartMs = 0;
static unsigned long _vehicleClearMs = 0;
static unsigned long _gateCloseDeadlineMs = 0;
static int  _lastFreeCount = 4;
static bool _lastVehicleSensor = false;
static bool _lastCommLost = false;

void gate_fsm_init() {
    g_gateState = GATE_CLOSED;
    g_admissionState = ADMISSION_IDLE;
    _gateMoveStartMs = 0;
    _gateOpenStartMs = 0;
    _vehicleClearMs = 0;
    _gateCloseDeadlineMs = 0;
    servo_close(); // Ensure barrier is strictly down (0 deg) at startup
    Serial.println("[FSM] Gate FSM initialised: CLOSED (0 deg default)");
}

// ── Main update ───────────────────────────────────────────────────────────────
void gate_fsm_update(int freeCount, bool commLost, bool vehicleSensor, bool manualOpenReq) {
    _lastFreeCount = freeCount;
    _lastCommLost = commLost;
    _lastVehicleSensor = vehicleSensor;
    GateState_t prev = g_gateState;
    unsigned long now = millis();

    switch (g_gateState) {

        case GATE_CLOSED:
            // Gate must remain strictly closed (0 deg) unless a vehicle is detected AND slot is available
            if (vehicleSensor || manualOpenReq) {
                if (commLost) {
                    g_admissionState = ADMISSION_DENIED_OFFLINE;
                    g_admissionEventMs = now;
                    Serial.println("[ADMISSION] REJECTED: System Offline / Stale AI Data");
                    buzzer_pattern(BUZZER_SYSTEM_ERROR);
                } else if (freeCount <= 0) {
                    g_admissionState = ADMISSION_DENIED_FULL;
                    g_admissionEventMs = now;
                    Serial.println("[ADMISSION] REJECTED: PARKING FULL (0 Free)");
                    buzzer_pattern(BUZZER_PARKING_FULL);
                } else {
                    // Admission Approved -> Open barrier for 10 seconds
                    g_admissionState = ADMISSION_APPROVED;
                    g_admissionEventMs = now;
                    g_gateState = GATE_OPENING;
                    _gateMoveStartMs = now;
                    _gateCloseDeadlineMs = now + GATE_TRAVEL_TIME_MS + GATE_HOLD_OPEN_MS;
                    servo_open();
                    Serial.println("[ADMISSION] APPROVED! Opening barrier (10s auto-close timer started)...");
                }
            } else {
                if (g_admissionState != ADMISSION_IDLE && (now - g_admissionEventMs) > 4000) {
                    g_admissionState = ADMISSION_IDLE;
                }
            }
            break;

        case GATE_OPENING:
            if (vehicleSensor) {
                // Car detected while opening -> keep 10-second timer fresh
                _gateCloseDeadlineMs = now + GATE_HOLD_OPEN_MS;
            }
            break;

        case GATE_OPEN:
        case GATE_VEHICLE_PASSING:
            if (vehicleSensor) {
                // CAR DETECTED AT BARRIER: CONTINUOUSLY RESET 10-SECOND TIMER!
                _gateCloseDeadlineMs = now + GATE_HOLD_OPEN_MS;
                g_gateState = GATE_VEHICLE_PASSING;
            } else {
                g_gateState = GATE_OPEN;
                // When car is no longer in front of IR, auto-close after 10 seconds
                if (now >= _gateCloseDeadlineMs) {
                    g_gateState = GATE_CLOSING;
                    _gateMoveStartMs = now;
                    servo_close();
                    Serial.println("[FSM] 10 seconds elapsed without car -> Gate CLOSING");
                }
            }
            break;

        case GATE_CLOSING:
            // Safety reversal: if car detected while closing, IMMEDIATELY RE-OPEN!
            if (vehicleSensor) {
                Serial.println("[FSM] SAFETY REVERSAL! Car detected during CLOSING -> RE-OPENING!");
                buzzer_pattern(BUZZER_GATE_SAFETY);
                g_admissionState = ADMISSION_SAFETY_REVERSAL;
                g_admissionEventMs = now;
                g_gateState = GATE_OPENING;
                _gateMoveStartMs = now;
                _gateCloseDeadlineMs = now + GATE_TRAVEL_TIME_MS + GATE_HOLD_OPEN_MS;
                servo_open();
            }
            break;

        case GATE_FAULT_SAFE:
            servo_close();
            break;
    }

    if (prev != g_gateState) {
        Serial.print("[FSM] State: ");
        Serial.println(gate_fsm_state_str());
    }
}

// ── Manual & Button Requests ──────────────────────────────────────────────────
void gate_fsm_request_open(int freeCount, bool commLost) {
    if (g_gateState == GATE_CLOSED) {
        if (commLost) {
            Serial.println("[FSM] Open request BLOCKED: System Offline");
            buzzer_pattern(BUZZER_SYSTEM_ERROR);
            g_admissionState = ADMISSION_DENIED_OFFLINE;
            g_admissionEventMs = millis();
        } else if (freeCount <= 0) {
            Serial.println("[FSM] Open request BLOCKED: PARKING FULL");
            buzzer_pattern(BUZZER_PARKING_FULL);
            g_admissionState = ADMISSION_DENIED_FULL;
            g_admissionEventMs = millis();
        } else {
            Serial.println("[FSM] Open APPROVED: CLOSED -> OPENING (10s timer)");
            g_admissionState = ADMISSION_APPROVED;
            g_admissionEventMs = millis();
            g_gateState = GATE_OPENING;
            _gateMoveStartMs = millis();
            _gateCloseDeadlineMs = millis() + GATE_TRAVEL_TIME_MS + GATE_HOLD_OPEN_MS;
            servo_open();
        }
    } else if (g_gateState == GATE_CLOSING) {
        // Safety reopen
        Serial.println("[FSM] Request during CLOSING: Reopening for safety!");
        g_gateState = GATE_OPENING;
        _gateMoveStartMs = millis();
        _gateCloseDeadlineMs = millis() + GATE_TRAVEL_TIME_MS + GATE_HOLD_OPEN_MS;
        servo_open();
    }
}

void gate_fsm_request_close(bool vehicleSensor) {
    if (g_gateState == GATE_OPEN || g_gateState == GATE_VEHICLE_PASSING) {
        if (vehicleSensor) {
            Serial.println("[FSM] Manual close BLOCKED: Car detected at gate!");
            buzzer_pattern(BUZZER_GATE_SAFETY);
        } else {
            Serial.println("[FSM] Manual close APPROVED: GATE -> CLOSING");
            g_gateState = GATE_CLOSING;
            _gateMoveStartMs = millis();
            servo_close();
        }
    }
}

// ── Tick — time-based transitions ─────────────────────────────────────────────
void gate_fsm_tick() {
    unsigned long now = millis();

    if (g_gateState == GATE_OPENING) {
        if ((now - _gateMoveStartMs) >= GATE_TRAVEL_TIME_MS) {
            g_gateState = GATE_OPEN;
            _gateOpenStartMs = now;
            _gateCloseDeadlineMs = now + GATE_HOLD_OPEN_MS;
            Serial.println("[FSM] OPENING -> OPEN (10-second countdown started)");
        }
    } else if (g_gateState == GATE_OPEN || g_gateState == GATE_VEHICLE_PASSING) {
        if (_lastVehicleSensor) {
            // Timer continuously resets to 10 seconds while car is detected
            _gateCloseDeadlineMs = now + GATE_HOLD_OPEN_MS;
        } else if (now >= _gateCloseDeadlineMs) {
            g_gateState = GATE_CLOSING;
            _gateMoveStartMs = now;
            servo_close();
            Serial.println("[FSM] 10s countdown complete -> CLOSING");
        }
    } else if (g_gateState == GATE_CLOSING) {
        if ((now - _gateMoveStartMs) >= GATE_TRAVEL_TIME_MS) {
            g_gateState = GATE_CLOSED;
            g_admissionState = ADMISSION_IDLE;
            servo_close();
            Serial.println("[FSM] CLOSING -> CLOSED (Gate firmly locked at 0 deg)");
        }
    }
}

float gate_fsm_get_remaining_sec() {
    if (g_gateState == GATE_OPEN || g_gateState == GATE_VEHICLE_PASSING || g_gateState == GATE_OPENING) {
        unsigned long now = millis();
        if (_gateCloseDeadlineMs > now) {
            return (_gateCloseDeadlineMs - now) / 1000.0f;
        }
        return 0.0f;
    }
    return 0.0f;
}

const char* gate_fsm_state_str() {
    switch (g_gateState) {
        case GATE_CLOSED:          return "GATE_CLOSED";
        case GATE_OPENING:         return "GATE_OPENING";
        case GATE_OPEN:            return "GATE_OPEN";
        case GATE_VEHICLE_PASSING: return "GATE_OPEN"; // Unambiguous: shows OPEN when barrier is up
        case GATE_CLOSING:         return "GATE_CLOSING";
        case GATE_FAULT_SAFE:      return "GATE_CLOSED";
        default:                   return "GATE_CLOSED";
    }
}

const char* gate_admission_state_str() {
    switch (g_admissionState) {
        case ADMISSION_IDLE:             return "IDLE";
        case ADMISSION_CHECKING:         return "CHECKING";
        case ADMISSION_APPROVED:         return "APPROVED";
        case ADMISSION_DENIED_FULL:      return "DENIED_FULL";
        case ADMISSION_DENIED_OFFLINE:   return "DENIED_OFFLINE";
        case ADMISSION_SAFETY_REVERSAL:  return "SAFETY_ALERT";
        default:                         return "UNKNOWN";
    }
}
