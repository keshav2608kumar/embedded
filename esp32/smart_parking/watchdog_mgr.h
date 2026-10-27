/**
 * Smart Parking Management System
 * ESP32 Firmware — Watchdog Timer Manager
 *
 * STATUS: IMPLEMENTED (HARDWARE TEST REQUIRED)
 *
 * Uses esp_task_wdt API (current, non-deprecated in ESP-IDF v5.x).
 *
 * WDT vs FSM — IMPORTANT DISTINCTION:
 *   FSM = normal gate-control logic (occupancy → open/close gate).
 *   WDT = fault recovery mechanism (if software hangs → reset → safe state).
 *   Do NOT mix these concepts.
 *
 * After WDT reset:
 *   setup() runs → servo_init() places gate at CLOSED_ANGLE → system resumes.
 *   The first LCD screen shows "INITIALISING..." indicating a fresh start.
 *
 * Team Member: Keshav Kumar (25BCE2880) — AI + Embedded Logic
 */

#pragma once
#include "config.h"

void wdt_init();
void wdt_feed();   // Call each main loop iteration to prevent timeout reset
