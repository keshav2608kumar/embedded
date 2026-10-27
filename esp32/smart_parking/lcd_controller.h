/**
 * Smart Parking Management System
 * ESP32 Firmware — LCD Controller
 *
 * STATUS: IMPLEMENTED (HARDWARE TEST REQUIRED)
 * Requires: LiquidCrystal_I2C library (install via Arduino Library Manager)
 *
 * Library: "LiquidCrystal I2C" by Frank de Brabander
 * Install: Arduino IDE → Tools → Manage Libraries → search "LiquidCrystal I2C"
 *
 * Team Member: Harshavardhan Singh (25BCE0552) — Hardware & Circuit Design
 */

#pragma once
#include "config.h"
#include "communication.h"
#include "gate_fsm.h"

void lcd_init();
void lcd_update(const ParkingStatus* status, const char* gateState);
void lcd_show_startup();
void lcd_show_comm_lost();
const char* lcd_get_line0();
const char* lcd_get_line1();

// Screen rotation index (internal)
extern int g_lcdScreen;
