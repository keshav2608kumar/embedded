/**
 * Smart Parking Management System
 * ESP32 Firmware — Main Sketch
 *
 * STATUS: IMPLEMENTED (HARDWARE TEST REQUIRED)
 *
 * Firmware architecture: Each subsystem is a separate module.
 * setup() → initialise all modules → gate starts CLOSED (safe state)
 * loop()  → comm_update → gate_fsm_update → lcd_update → wdt_feed
 *
 * Required Arduino Libraries (install via Library Manager):
 *   1. LiquidCrystal I2C  (by Frank de Brabander)
 *   2. ESP32Servo          (by Kevin Harrington)
 *
 * Board: ESP32 Dev Module
 * Upload speed: 115200
 *
 * Team:
 *   Harshavardhan Singh (25BCE0552) — Hardware & Circuit Design
 *   Shaikh Shayaan      (25BCE2623) — Gate & Entry/Exit Engineering
 *   Keshav Kumar        (25BCE2880) — AI + Embedded Logic
 *
 * HARDWARE TEST REQUIRED — this firmware has not yet been tested on
 * physical hardware. No results are fabricated.
 */

#include "config.h"
#include "communication.h"
#include "lcd_controller.h"
#include "buzzer.h"
#include "servo_gate.h"
#include "vehicle_sensor.h"
#include "gate_fsm.h"
#include "watchdog_mgr.h"
#include "wifi_server.h"

// ── Simple vehicle-request detection ─────────────────────────────────────────
// In the physical system this could be: push button, IR break-beam,
// or a motion sensor at the entrance. For the prototype, we use the
// vehicle-present sensor as the entry request trigger.
// A more robust design would use a separate entrance sensor.
static bool _vehicleRequestPending = false;
static unsigned long _lastVehicleRequestMs = 0;
#define VEHICLE_REQUEST_COOLDOWN_MS 5000    // Min ms between gate-open requests

// ── setup() — runs once on boot and after WDT reset ──────────────────────────
void setup() {
    Serial.begin(SERIAL_BAUD);
    delay(500);

    Serial.println("\n==========================================");
    Serial.println("  SMART PARKING MANAGEMENT SYSTEM v1.0");
    Serial.println("  ESP32 Firmware");
    Serial.println("==========================================\n");

    // IMPORTANT: servo FIRST — gate must be in safe CLOSED state on any boot/reset
    servo_init();     // Commands GATE_CLOSED_ANGLE immediately

    // Initialise all other modules
    buzzer_init();
    sensor_init();

    lcd_init();
    comm_init();
    gate_fsm_init();
    wifi_server_init(); // Mobile Web Dashboard via ESP32 WiFi
    wdt_init();         // WDT last — system must be stable before arming

    Serial.println("[MAIN] All modules initialised. Entering main loop.");
    Serial.println("[MAIN] STATUS: HARDWARE TEST REQUIRED");
}

// ── loop() — main execution loop ─────────────────────────────────────────────
void loop() {
    // Feed WDT FIRST — ensures WDT is reset regardless of how long the rest takes
    wdt_feed();

    // 1. Read latest parking status from Python AI pipeline
    comm_update();

    // 2. Read vehicle-present sensor (gate safety only — NOT slot occupancy)
    SensorState_t sensorState = sensor_read();
    bool vehicleSensor = (sensorState == SENSOR_DETECTED);
    if (g_cmdTriggerVehicle) {
        vehicleSensor = true;
        g_cmdTriggerVehicle = false;
        Serial.println("[CMD] Vehicle approach simulated via serial command");
    }
    unsigned long now = millis();

    // 3. Update gate FSM and admission control (fully automated via IR sensor & AI telemetry)
    gate_fsm_update(
        g_parkingStatus.freeCount,
        comm_is_lost(),
        vehicleSensor,
        false
    );
    gate_fsm_tick();   // Time-based transitions

    // 4. Update LCD display
    lcd_update(&g_parkingStatus, gate_fsm_state_str());

    // 5. Update non-blocking buzzer
    buzzer_tick();

    // 5b. Update WiFi Mobile Dashboard Server
    wifi_server_update();

    // 6. Debug serial output (telemetry stream with exact LCD lines and auto-close countdown)
    static unsigned long _lastDebugMs = 0;
    if ((now - _lastDebugMs) > 200) {
        _lastDebugMs = now;
        Serial.print("[STATUS] Free:");
        Serial.print(g_parkingStatus.freeCount);
        Serial.print(" Rec:");
        Serial.print(g_parkingStatus.recommendedSlot);
        Serial.print(" Gate:");
        Serial.print(gate_fsm_state_str());
        Serial.print(" Adm:");
        Serial.print(gate_admission_state_str());
        Serial.print(" Sensor:");
        Serial.print(vehicleSensor ? "DETECTED" : "CLEAR");
        Serial.print(" Pin:");
        Serial.print(sensor_get_active_pin());
        Serial.print(" Raw:");
        Serial.print(digitalRead(sensor_get_active_pin()));
        Serial.print(" Timer:");
        Serial.print(gate_fsm_get_remaining_sec(), 1);
        Serial.print(" Comm:");
        Serial.print(comm_is_lost() ? "LOST" : "OK");
        Serial.print(" L1:");
        Serial.print(lcd_get_line0());
        Serial.print(" L2:");
        Serial.println(lcd_get_line1());
    }

    delay(LOOP_DELAY_MS);
}
