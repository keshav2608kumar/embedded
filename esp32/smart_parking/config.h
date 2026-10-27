/**
 * Smart Parking Management System
 * ESP32 Firmware — Main Configuration Header
 *
 * STATUS: IMPLEMENTED (firmware code ready; HARDWARE TEST REQUIRED)
 *
 * All hardware-specific constants are defined HERE only.
 * To adapt to different wiring, change only this file.
 *
 * Team Member: Harshavardhan Singh (25BCE0552) — Hardware & Circuit Design
 */

#pragma once

// ── I²C LCD ────────────────────────────────────────────────────────────────
#define LCD_I2C_ADDR    0x27    // Common PCF8574 backpack. Try 0x3F if 0x27 fails.
#define LCD_SDA_PIN     21      // ESP32 default I²C SDA
#define LCD_SCL_PIN     22      // ESP32 default I²C SCL
#define LCD_COLS        16
#define LCD_ROWS        2
#define LCD_SCREEN_INTERVAL_MS  3000    // Rotate display every 3 seconds

// ── Servo (Gate) ────────────────────────────────────────────────────────────
#define SERVO_PIN           18
#define GATE_OPEN_ANGLE     90      // Tune to actual servo/gate mechanics
#define GATE_CLOSED_ANGLE   0       // Tune to actual servo/gate mechanics
#define SERVO_MOVE_DELAY_MS 500     // Delay after servo command (settle time)

// ── Buzzer ──────────────────────────────────────────────────────────────────
#define BUZZER_PIN          19
#define BUZZER_FREQ_HZ      2000    // Beep frequency

// ── Push Buttons (Entry & Exit/Reset) ───────────────────────────────────────
#define BUTTON_ENTRY_PIN    32      // Button 1: Request Gate Open (active LOW, internal pullup)
#define BUTTON_CLOSE_PIN    33      // Button 2: Manual Gate Close / Reset (active LOW, internal pullup)
#define BUTTON_DEBOUNCE_MS  50      // Debounce period in ms

// ── Vehicle-Present Sensor (Optional IR / Break-Beam) ───────────────────────
// This sensor is ONLY for gate safety — NOT for slot occupancy detection.
// Slot occupancy is determined by the AI pipeline via serial communication.
#define VEHICLE_SENSOR_PIN      23      // Primary IR Sensor pin (D23)
#define VEHICLE_SENSOR_ALT_PIN  4       // Alternate IR Sensor pin (D4)
#define VEHICLE_SENSOR_ALT2_PIN 27      // Alternate IR Sensor pin (D27)
#define SENSOR_DEBOUNCE_MS  50      // Debounce time for sensor readings

// ── Serial Communication (PC → ESP32) ───────────────────────────────────────
#define SERIAL_BAUD         115200
#define COMM_TIMEOUT_MS     15000   // Declare COMM_LOST if no valid packet in 15s

// ── Watchdog Timer ───────────────────────────────────────────────────────────
#define WDT_TIMEOUT_SEC     10      // WDT timeout in seconds

// ── Gate FSM Timing ──────────────────────────────────────────────────────────
#define GATE_TRAVEL_TIME_MS 1500    // Time for gate to fully open or close (ms)
#define GATE_HOLD_OPEN_MS   10000   // Hold gate open for exactly 10 seconds (resets on car detection)

// ── System ───────────────────────────────────────────────────────────────────
#define LOOP_DELAY_MS       50      // Main loop delay (20 Hz)

// ── WiFi Mobile Dashboard ───────────────────────────────────────────────────
#define WIFI_AP_SSID        "Smart-Parking-WiFi"
#define WIFI_AP_PASS        "12345678"    // Minimum 8 chars for WPA2, or "" for open
#define WIFI_AP_CHANNEL     1
#define WIFI_MDNS_HOST      "parking"     // http://parking.local
#define WIFI_STA_SSID       ""            // Optional home/hotspot SSID (empty = AP only)
#define WIFI_STA_PASS       ""            // Optional home/hotspot password
