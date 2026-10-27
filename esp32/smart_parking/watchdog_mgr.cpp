/**
 * Smart Parking Management System
 * ESP32 Firmware — Watchdog Timer Manager Implementation
 *
 * STATUS: IMPLEMENTED (HARDWARE TEST REQUIRED)
 *
 * Uses esp_task_wdt_init() / esp_task_wdt_add() / esp_task_wdt_reset()
 * from esp_task_wdt.h (ESP-IDF v5.x compatible, non-deprecated).
 *
 * If the main loop hangs for WDT_TIMEOUT_SEC seconds without calling
 * wdt_feed(), the ESP32 resets automatically and re-enters setup().
 * setup() initialises the servo to GATE_CLOSED_ANGLE as the FIRST action,
 * ensuring a safe hardware state after any crash.
 */

#include "watchdog_mgr.h"
#include <Arduino.h>
#include "esp_task_wdt.h"
#include "esp_idf_version.h"

void wdt_init() {
#if ESP_IDF_VERSION >= ESP_IDF_VERSION_VAL(5, 0, 0)
    // esp_task_wdt_config_t available in ESP-IDF v5.x
    esp_task_wdt_config_t wdt_config = {
        .timeout_ms     = (uint32_t)(WDT_TIMEOUT_SEC * 1000),
        .idle_core_mask = 0,    // Don't watch idle tasks
        .trigger_panic  = true  // Trigger panic (causes reset) on timeout
    };
    esp_err_t err = esp_task_wdt_init(&wdt_config);
#else
    // ESP-IDF v4.x signature: timeout in seconds, panic bool
    esp_err_t err = esp_task_wdt_init(WDT_TIMEOUT_SEC, true);
#endif
    if (err != ESP_OK) {
        Serial.print("[WDT] Init failed: ");
        Serial.println(err);
        return;
    }

    // Subscribe the current (main) task to the WDT
    esp_task_wdt_add(NULL);
    Serial.print("[WDT] Initialised: timeout=");
    Serial.print(WDT_TIMEOUT_SEC);
    Serial.println("s");
}

void wdt_feed() {
    // Reset the WDT counter — call every main loop iteration
    esp_task_wdt_reset();
}
