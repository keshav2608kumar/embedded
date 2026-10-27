/**
 * Smart Parking Management System
 * ESP32 Firmware — Buzzer, Servo, Vehicle Sensor, Watchdog Headers & Implementations
 *
 * STATUS: IMPLEMENTED (HARDWARE TEST REQUIRED)
 */

// ── buzzer.h ─────────────────────────────────────────────────────────────────
#pragma once
#include "config.h"

typedef enum {
    BUZZER_PARKING_FULL,
    BUZZER_GATE_SAFETY,
    BUZZER_SYSTEM_ERROR
} BuzzerPattern_t;

void buzzer_init();
void buzzer_pattern(BuzzerPattern_t pattern);
void buzzer_tick();   // Non-blocking timer update — call each loop
