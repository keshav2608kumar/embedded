/**
 * Smart Parking Management System
 * ESP32 Firmware — Vehicle Sensor & Watchdog
 *
 * STATUS: IMPLEMENTED (HARDWARE TEST REQUIRED)
 *
 * Vehicle Sensor (vehicle_sensor.h/cpp):
 *   Gate-safety only — NOT used for slot occupancy.
 *   Debounced digital read with configurable SENSOR_DEBOUNCE_MS.
 *
 * Watchdog Timer (watchdog_mgr.h/cpp):
 *   Uses esp_task_wdt API (non-deprecated in current ESP-IDF).
 *   On timeout → ESP32 resets → setup() runs → gate initialised CLOSED.
 */

// ═══════════════════════════════════════════════════════════════════════════
//  vehicle_sensor.h
// ═══════════════════════════════════════════════════════════════════════════
#pragma once
#include "config.h"

typedef enum {
    SENSOR_CLEAR,       // No vehicle at gate
    SENSOR_DETECTED,    // Vehicle present at gate
    SENSOR_ERROR        // Read failure (future: analog range check)
} SensorState_t;

void         sensor_init();
SensorState_t sensor_read();   // Debounced read
int          sensor_get_active_pin();
void         sensor_scan_and_report();
