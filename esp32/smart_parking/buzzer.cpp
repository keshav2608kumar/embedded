/**
 * Smart Parking Management System
 * ESP32 Firmware — Buzzer Implementation
 *
 * STATUS: IMPLEMENTED (HARDWARE TEST REQUIRED)
 *
 * Non-blocking buzzer patterns using millis()-based timers.
 * The buzzer never blocks the main loop.
 *
 * Patterns:
 *   PARKING_FULL : 3× short beeps (100ms on / 200ms off)
 *   GATE_SAFETY  : 2× long beeps  (400ms on / 200ms off)
 *   SYSTEM_ERROR : 3× long beeps  (500ms on / 300ms off)
 */

#include "buzzer.h"
#include <Arduino.h>

static unsigned long _beepStartMs  = 0;
static int           _beepCount    = 0;
static int           _beepTarget   = 0;
static int           _beepOnMs     = 0;
static int           _beepOffMs    = 0;
static bool          _beepActive   = false;
static bool          _beepPhaseOn  = false;

void buzzer_init() {
    pinMode(BUZZER_PIN, OUTPUT);
    digitalWrite(BUZZER_PIN, LOW);
    Serial.println("[BUZZER] Initialised");
}

void buzzer_pattern(BuzzerPattern_t pattern) {
    // Stop any running pattern
    _beepActive  = false;
    _beepCount   = 0;
    _beepPhaseOn = false;
    digitalWrite(BUZZER_PIN, LOW);

    switch (pattern) {
        case BUZZER_PARKING_FULL:
            _beepTarget = 3;  _beepOnMs = 100;  _beepOffMs = 200;
            break;
        case BUZZER_GATE_SAFETY:
            _beepTarget = 2;  _beepOnMs = 400;  _beepOffMs = 200;
            break;
        case BUZZER_SYSTEM_ERROR:
            _beepTarget = 3;  _beepOnMs = 500;  _beepOffMs = 300;
            break;
        default:
            return;
    }

    _beepActive   = true;
    _beepPhaseOn  = true;
    _beepStartMs  = millis();
    tone(BUZZER_PIN, BUZZER_FREQ_HZ);
}

void buzzer_tick() {
    if (!_beepActive) return;

    unsigned long now = millis();
    unsigned long elapsed = now - _beepStartMs;

    if (_beepPhaseOn) {
        if (elapsed >= (unsigned long)_beepOnMs) {
            noTone(BUZZER_PIN);
            digitalWrite(BUZZER_PIN, LOW);
            _beepPhaseOn = false;
            _beepStartMs = now;
            _beepCount++;
            if (_beepCount >= _beepTarget) {
                _beepActive = false;  // Pattern complete
            }
        }
    } else {
        if (elapsed >= (unsigned long)_beepOffMs) {
            _beepPhaseOn = true;
            _beepStartMs = now;
            tone(BUZZER_PIN, BUZZER_FREQ_HZ);
        }
    }
}
