/**
 * Smart Parking Management System
 * ESP32 Firmware — Servo Gate
 *
 * STATUS: IMPLEMENTED (HARDWARE TEST REQUIRED)
 * Requires: ESP32Servo library (install via Arduino Library Manager)
 * Library: "ESP32Servo" by Kevin Harrington
 */

#pragma once
#include "config.h"

void servo_init();
void servo_open();
void servo_close();
void servo_test_sweep();
bool servo_is_ready();
