/**
 * Smart Parking Management System
 * ESP32 Firmware — LCD Controller Implementation
 *
 * Professional 16x2 I2C LCD Display:
 * - Clean, concise, stable format:
 *   Available: Line 1 = "REC SLOT: S1    ", Line 2 = "GATE: CLOSED    " (or "GATE: OPEN      ")
 *   Full:      Line 1 = "PARKING FULL    ", Line 2 = "SORRY! NO SPACE "
 *   Offline:   Line 1 = "SYSTEM OFFLINE  ", Line 2 = "GATE: CLOSED    "
 *
 * Differential write eliminates screen flicker and maintains rock-solid stability.
 */

#include "lcd_controller.h"
#include <Arduino.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <stdio.h>
#include <string.h>

static LiquidCrystal_I2C _lcd(LCD_I2C_ADDR, LCD_COLS, LCD_ROWS);
int g_lcdScreen = 0;

// Anti-flicker differential line cache (16 chars + null)
static char _curLine0[17] = "";
static char _curLine1[17] = "";

static void _lcd_write_differential(const char* l0, const char* l1) {
    char buf0[17];
    char buf1[17];

    // Format with exactly 16 characters padded with spaces
    snprintf(buf0, sizeof(buf0), "%-16.16s", l0);
    snprintf(buf1, sizeof(buf1), "%-16.16s", l1);

    if (strcmp(_curLine0, buf0) != 0) {
        _lcd.setCursor(0, 0);
        _lcd.print(buf0);
        strncpy(_curLine0, buf0, sizeof(_curLine0));
    }
    if (strcmp(_curLine1, buf1) != 0) {
        _lcd.setCursor(0, 1);
        _lcd.print(buf1);
        strncpy(_curLine1, buf1, sizeof(_curLine1));
    }
}

void lcd_init() {
    Wire.begin(LCD_SDA_PIN, LCD_SCL_PIN);
    _lcd.init();
    _lcd.backlight();
    lcd_show_startup();
    Serial.println("[LCD] Initialised (Anti-flicker controller active)");
}

void lcd_show_startup() {
    _lcd_write_differential("SMART PARKING   ", "GATE: CLOSED    ");
    delay(500);
}

void lcd_show_comm_lost() {
    _lcd_write_differential("SYSTEM OFFLINE  ", "GATE: CLOSED    ");
}

// Main update — call each loop
void lcd_update(const ParkingStatus* st, const char* gateState) {
    // 1. Critical Communication Lost / Stale AI Data
    if (st->commLost) {
        lcd_show_comm_lost();
        return;
    }

    // 2. Obstacle / Safety Reversal
    if (g_admissionState == ADMISSION_SAFETY_REVERSAL) {
        _lcd_write_differential("OBSTACLE ALERT  ", "GATE: RE-OPENING");
        return;
    }

    // 3. Parking Full or Admission Denied (Full Parking)
    if (st->freeCount == 0 || g_admissionState == ADMISSION_DENIED_FULL) {
        _lcd_write_differential("PARKING FULL    ", "SORRY! NO SPACE ");
        return;
    }

    // 4. Normal Operation (Available slots):
    // Line 1: Recommended slot ONLY
    char line0[17] = "";
    if (st->recommendedSlot[0] != '\0' && strcmp(st->recommendedSlot, "NONE") != 0) {
        snprintf(line0, sizeof(line0), "REC SLOT: %-6s", st->recommendedSlot);
    } else {
        snprintf(line0, sizeof(line0), "REC SLOT: S1    ");
    }

    // Line 2: Gate state ONLY
    char line1[17] = "";
    if (g_gateState == GATE_OPENING) {
        snprintf(line1, sizeof(line1), "GATE: OPENING   ");
    } else if (g_gateState == GATE_OPEN || g_gateState == GATE_VEHICLE_PASSING) {
        snprintf(line1, sizeof(line1), "GATE: OPEN      ");
    } else if (g_gateState == GATE_CLOSING) {
        snprintf(line1, sizeof(line1), "GATE: CLOSING   ");
    } else {
        snprintf(line1, sizeof(line1), "GATE: CLOSED    ");
    }

    _lcd_write_differential(line0, line1);
}

const char* lcd_get_line0() {
    return _curLine0;
}

const char* lcd_get_line1() {
    return _curLine1;
}
