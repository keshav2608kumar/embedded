/**
 * Smart Parking Management System
 * ESP32 Firmware — Gate FSM Header
 *
 * STATUS: IMPLEMENTED (HARDWARE TEST REQUIRED)
 *
 * Implements the parking gate Finite State Machine.
 * This module is responsible for safe gate operation.
 *
 * States: CLOSED → OPENING → OPEN → VEHICLE_PASSING → CLOSING → CLOSED
 * Safety: CLOSING → OPENING (if vehicle detected mid-close)
 * Full:   CLOSED, ENTRY DENIED, BUZZER (if freeCount == 0)
 *
 * Team Member: Shaikh Shayaan (25BCE2623) — Gate & Entry/Exit Engineering
 */

#pragma once
#include "config.h"

typedef enum {
    GATE_CLOSED,
    GATE_OPENING,
    GATE_OPEN,
    GATE_VEHICLE_PASSING,
    GATE_CLOSING,
    GATE_FAULT_SAFE
} GateState_t;

typedef enum {
    ADMISSION_IDLE,
    ADMISSION_CHECKING,
    ADMISSION_APPROVED,
    ADMISSION_DENIED_FULL,
    ADMISSION_DENIED_OFFLINE,
    ADMISSION_SAFETY_REVERSAL
} AdmissionState_t;

// Current state variables
extern GateState_t      g_gateState;
extern AdmissionState_t g_admissionState;
extern unsigned long    g_admissionEventMs;

void gate_fsm_init();
void gate_fsm_update(int freeCount, bool commLost, bool vehicleSensor, bool manualOpenReq);
void gate_fsm_request_open(int freeCount, bool commLost);
void gate_fsm_request_close(bool vehicleSensor);
void gate_fsm_tick();           // Call each loop for time-based transitions
float gate_fsm_get_remaining_sec(); // Returns seconds until auto-close
const char* gate_fsm_state_str();
const char* gate_admission_state_str();
