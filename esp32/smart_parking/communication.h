/**
 * Smart Parking Management System
 * ESP32 Firmware — Communication Module
 *
 * STATUS: IMPLEMENTED (HARDWARE TEST REQUIRED)
 *
 * Receives parking status packets from the Python AI pipeline over USB serial.
 * Protocol: <PKT,S1=1,S2=0,S3=1,S4=0,FREE=2,STATUS=OK>
 *
 * Malformed / invalid packets are silently IGNORED per protocol spec.
 * COMM_LOST is declared if no valid packet arrives within COMM_TIMEOUT_MS.
 *
 * Team Member: Keshav Kumar (25BCE2880) — AI + Embedded Logic
 */

#pragma once
#include "config.h"

// ── Parsed parking status ────────────────────────────────────────────────────
struct ParkingStatus {
    bool s1 = false;      // true = OCCUPIED
    bool s2 = false;
    bool s3 = false;
    bool s4 = false;
    int  freeCount = 4;
    char recommendedSlot[8] = "NONE";
    char status[16] = "INIT";
    bool commLost = false;
    unsigned long lastValidPacketMs = 0;
};

// Global parking status (updated by comm_update())
extern ParkingStatus g_parkingStatus;
extern bool g_cmdTriggerVehicle;

// ── Function declarations ─────────────────────────────────────────────────────
void comm_init();
void comm_update();           // Call each loop — reads serial, updates g_parkingStatus
bool comm_is_lost();          // Returns true if COMM_TIMEOUT_MS exceeded
void comm_send_ack(const char* msg);   // Optional ACK back to Python

// ── Internal helpers (not for external use) ──────────────────────────────────
bool _comm_parse_packet(const char* raw, ParkingStatus* out);
bool _comm_extract_field(const char* src, const char* key, char* out, int maxLen);
