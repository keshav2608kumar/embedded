# Hardware Watchdog Timer (WDT)

The ESP32 firmware includes a Task Watchdog Timer to ensure system reliability and autonomous recovery from software faults.

## How It Works

- Configured via the ESP-IDF `esp_task_wdt_*` API in `watchdog_mgr.cpp`.
- Initialized with `WDT_TIMEOUT_SEC` (default 10 seconds).
- The main `loop()` calls `wdt_feed()` on every iteration.
- **Trigger Condition:** If the main loop hangs (e.g., an infinite `while` loop, a frozen I2C bus blocking the LCD, or a deadlock), `wdt_feed()` stops being called.
- **Action:** After 10 seconds, the hardware watchdog triggers a CPU Panic. The ESP32 is forcefully restarted.

## Post-Crash Recovery (Safe State)

Because embedded systems operate physical hardware (like heavy gates), crash recovery must be safe:
1. ESP32 Reboots.
2. `setup()` runs.
3. The **very first** action in `setup()` is `servo_init()`, which immediately writes `GATE_CLOSED_ANGLE`.
4. The system safely resets the environment before any logic processes stale requests.
