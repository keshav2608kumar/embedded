/**
 * Smart Parking Management System
 * ESP32 Firmware — Universal Auto-Binding Vehicle Sensor Implementation
 *
 * Monitors true pull-up user pins:
 * 23, 4, 15, 14, 27, 26, 16, 17, 13, 12.
 * (Excludes GPIO 2 which is hardwired to onboard LED, and 34/35 which lack pullups).
 *
 * All candidate pins idle cleanly at 1 (HIGH / CLEAR).
 * When vehicle arrives or hand is placed, sensor pulls the pin to 0 (LOW / DETECTED).
 */

#include "vehicle_sensor.h"
#include <Arduino.h>

static const int PROBE_PINS[] = {23, 4, 32, 33, 25, 5, 27, 26, 16, 17, 14, 15, 13, 12};
static const int NUM_PROBE_PINS = sizeof(PROBE_PINS) / sizeof(PROBE_PINS[0]);

static int  _activePin = 23;
static bool _sensorLocked = false;

void sensor_init() {
    for (int i = 0; i < NUM_PROBE_PINS; i++) {
        pinMode(PROBE_PINS[i], INPUT_PULLUP);
    }
    Serial.println("[SENSOR] Universal IR Auto-Scanner active on GPIOs (23, 4, 32, 33, 25, 5, 27, 26, 16, 17, 14, 15, 13, 12)");
}

int sensor_get_active_pin() {
    return _activePin;
}

void sensor_scan_and_report() {
    Serial.println("--- [LIVE PIN MONITOR] ---");
    int lowCount = 0;
    for (int i = 0; i < NUM_PROBE_PINS; i++) {
        int pin = PROBE_PINS[i];
        int val = digitalRead(pin);
        Serial.print("  GPIO ");
        Serial.print(pin);
        Serial.print(": ");
        if (val == LOW) {
            Serial.println("0 (LOW) <-- [TRIGGERED / OBSTACLE DETECTED!]");
            lowCount++;
        } else {
            Serial.println("1 (HIGH) [idle]");
        }
    }
    Serial.print("  Active IR Pin: GPIO ");
    Serial.print(_activePin);
    Serial.println(_sensorLocked ? " [LOCKED BY DETECTION]" : " [AUTO-DETECT MODE]");
    Serial.println("--------------------------");
}

SensorState_t sensor_read() {
    static int confirmedState = HIGH;
    static int lastReading = HIGH;
    static unsigned long lastDebounceTime = 0;

    // Scan all candidate pins: any pin pulled LOW (0) indicates obstacle detection
    int triggeredPin = -1;
    for (int i = 0; i < NUM_PROBE_PINS; i++) {
        int pin = PROBE_PINS[i];
        if (digitalRead(pin) == LOW) {
            triggeredPin = pin;
            if (_activePin != pin) {
                _activePin = pin;
                _sensorLocked = true;
                Serial.print("[AUTO-BIND] IR Sensor OBSTACLE DETECTED on GPIO ");
                Serial.println(pin);
            }
            break;
        }
    }

    int raw = (triggeredPin != -1) ? LOW : HIGH;

    unsigned long now = millis();
    if (raw != lastReading) {
        lastDebounceTime = now;
        lastReading = raw;
    }

    if ((now - lastDebounceTime) >= 20) {
        confirmedState = raw;
    }

    return (confirmedState == LOW) ? SENSOR_DETECTED : SENSOR_CLEAR;
}
