/**
 * Smart Parking Management System
 * ESP32 Firmware — Servo Gate Implementation
 *
 * Uses ESP32 Native LEDC Hardware PWM on GPIO 18 ONLY.
 * Dedicated channel 0, 50Hz, 16-bit resolution (544us to 2400us pulses).
 * Clean, isolated, zero pin conflicts.
 */

#include "servo_gate.h"
#include "config.h"
#include <Arduino.h>

#define SERVO_LEDC_CH       0
#define SERVO_LEDC_FREQ     50      // 50Hz = 20ms period

static bool _ready = false;
static int  _currentAngle = 0;
static uint32_t _maxTicks = 65535;

static void _write_pwm_angle(int angle) {
    if (angle < 0) angle = 0;
    if (angle > 180) angle = 180;
    _currentAngle = angle;

    // Standard SG90 / MG90S pulse width: 544us (0 deg) to 2400us (180 deg)
    uint32_t pulseUs = 544 + ((angle * (2400 - 544)) / 180);
    uint32_t duty = (uint32_t)(((uint64_t)pulseUs * (uint64_t)_maxTicks) / 20000ULL);

    ledcWrite(SERVO_LEDC_CH, duty);
}

void servo_init() {
    uint32_t actualFreq = ledcSetup(SERVO_LEDC_CH, SERVO_LEDC_FREQ, 16);
    if (actualFreq > 0) {
        _maxTicks = 65535;
        Serial.println("[SERVO] LEDC Hardware Timer: 50Hz @ 16-bit resolution");
    } else {
        actualFreq = ledcSetup(SERVO_LEDC_CH, SERVO_LEDC_FREQ, 14);
        _maxTicks = 16383;
        Serial.println("[SERVO] LEDC Hardware Timer: 50Hz @ 14-bit resolution");
    }

    ledcAttachPin(SERVO_PIN, SERVO_LEDC_CH);
    _ready = (actualFreq > 0);
    _write_pwm_angle(GATE_CLOSED_ANGLE);

    Serial.print("[SERVO] Hardware PWM active on GPIO ");
    Serial.print(SERVO_PIN);
    Serial.println(_ready ? " - ONLINE" : " - FAILED");
}

void servo_open() {
    if (!_ready) return;
    _write_pwm_angle(GATE_OPEN_ANGLE);
    Serial.print("[SERVO] Opening -> angle: ");
    Serial.println(GATE_OPEN_ANGLE);
}

void servo_close() {
    if (!_ready) return;
    _write_pwm_angle(GATE_CLOSED_ANGLE);
    Serial.print("[SERVO] Closing -> angle: ");
    Serial.println(GATE_CLOSED_ANGLE);
}

void servo_test_sweep() {
    if (!_ready) return;
    Serial.println("[SERVO] Diagnostic Sweep: 0 -> 90 -> 0");
    _write_pwm_angle(GATE_OPEN_ANGLE);
    delay(1000);
    _write_pwm_angle(GATE_CLOSED_ANGLE);
    delay(1000);
}

bool servo_is_ready() {
    return _ready;
}
