/**
 * Smart Parking Management System
 * ESP32 Firmware — Communication Module Implementation
 *
 * STATUS: IMPLEMENTED (HARDWARE TEST REQUIRED)
 */

#include "communication.h"
#include "servo_gate.h"
#include "gate_fsm.h"
#include "vehicle_sensor.h"
#include <Arduino.h>
#include <string.h>
#include <stdlib.h>

ParkingStatus g_parkingStatus;
bool g_cmdTriggerVehicle = false;

static char _rxBuffer[128];
static int  _rxIndex = 0;

void comm_init() {
    Serial.begin(SERIAL_BAUD);
    g_parkingStatus.lastValidPacketMs = millis();
    g_parkingStatus.commLost = false;
    Serial.println("[ESP32] Communication initialised");
}

// ── Main update — call every loop ────────────────────────────────────────────
void comm_update() {
    // Read all available bytes into ring buffer
    while (Serial.available() > 0) {
        char c = Serial.read();

        if (c == '<') {
            // Start of packet — reset buffer
            _rxIndex = 0;
            _rxBuffer[_rxIndex++] = c;
        } else if (c == '>') {
            // End of packet — terminate and parse
            if (_rxIndex > 0 && _rxIndex < (int)sizeof(_rxBuffer) - 1) {
                _rxBuffer[_rxIndex++] = c;
                _rxBuffer[_rxIndex]   = '\0';

                if (strncmp(_rxBuffer, "<CMD,", 5) == 0) {
                    char action[32] = "";
                    if (_comm_extract_field(_rxBuffer, "ACTION=", action, sizeof(action))) {
                        Serial.print("[CMD] Received command: ");
                        Serial.println(action);
                        if (strcmp(action, "OPEN") == 0) {
                            gate_fsm_request_open(g_parkingStatus.freeCount, false);
                        } else if (strcmp(action, "CLOSE") == 0) {
                            gate_fsm_request_close(false);
                        } else if (strcmp(action, "SWEEP") == 0) {
                            servo_test_sweep();
                        } else if (strcmp(action, "SERVO_OPEN") == 0 || strcmp(action, "FORCE_OPEN") == 0) {
                            Serial.println("[CMD] Direct SERVO_OPEN commanded");
                            servo_open();
                        } else if (strcmp(action, "SERVO_CLOSE") == 0 || strcmp(action, "FORCE_CLOSE") == 0) {
                            Serial.println("[CMD] Direct SERVO_CLOSE commanded");
                            servo_close();
                        } else if (strcmp(action, "TRIGGER_VEHICLE") == 0 || strcmp(action, "VEHICLE") == 0) {
                            g_cmdTriggerVehicle = true;
                        } else if (strcmp(action, "SCAN_PINS") == 0) {
                            sensor_scan_and_report();
                        }
                    }
                } else {
                    ParkingStatus parsed;
                    if (_comm_parse_packet(_rxBuffer, &parsed)) {
                        // Valid packet received
                        memcpy(&g_parkingStatus, &parsed, sizeof(ParkingStatus));
                        g_parkingStatus.lastValidPacketMs = millis();
                        g_parkingStatus.commLost = false;
                        // Optional ACK
                        // comm_send_ack("ACK");
                    }
                    // Invalid packets are silently ignored per protocol spec
                }
            }
            _rxIndex = 0;
        } else {
            // Accumulate packet bytes (guard against buffer overflow)
            if (_rxIndex > 0 && _rxIndex < (int)sizeof(_rxBuffer) - 2) {
                _rxBuffer[_rxIndex++] = c;
            }
        }
    }

    // Check for communication timeout
    if ((millis() - g_parkingStatus.lastValidPacketMs) > COMM_TIMEOUT_MS) {
        if (!g_parkingStatus.commLost) {
            Serial.println("[WARN] COMMUNICATION LOST — no valid packet received");
        }
        g_parkingStatus.commLost = true;
    }
}

bool comm_is_lost() {
    return g_parkingStatus.commLost;
}

void comm_send_ack(const char* msg) {
    Serial.print("<ACK,");
    Serial.print(msg);
    Serial.println(">");
}

// ── Packet parser ─────────────────────────────────────────────────────────────
// Expected: <PKT,S1=1,S2=0,S3=1,S4=0,FREE=2,STATUS=OK> or <PKT,FREE=2,STATUS=OK>
bool _comm_parse_packet(const char* raw, ParkingStatus* out) {
    // Basic structural checks
    if (strncmp(raw, "<PKT,", 5) != 0) return false;
    if (raw[strlen(raw) - 1] != '>')    return false;

    char val[16];

    // Optional slot flags S1-S4
    out->s1 = false;
    out->s2 = false;
    out->s3 = false;
    out->s4 = false;

    if (_comm_extract_field(raw, "S1=", val, sizeof(val))) {
        out->s1 = (val[0] == '1');
    }
    if (_comm_extract_field(raw, "S2=", val, sizeof(val))) {
        out->s2 = (val[0] == '1');
    }
    if (_comm_extract_field(raw, "S3=", val, sizeof(val))) {
        out->s3 = (val[0] == '1');
    }
    if (_comm_extract_field(raw, "S4=", val, sizeof(val))) {
        out->s4 = (val[0] == '1');
    }

    // Extract FREE (mandatory)
    if (!_comm_extract_field(raw, "FREE=", val, sizeof(val))) return false;
    int freeCount = atoi(val);
    if (freeCount < 0 || freeCount > 255) return false;
    out->freeCount = freeCount;

    // Extract REC (optional recommended slot)
    if (_comm_extract_field(raw, "REC=", val, sizeof(val))) {
        strncpy(out->recommendedSlot, val, sizeof(out->recommendedSlot) - 1);
        out->recommendedSlot[sizeof(out->recommendedSlot) - 1] = '\0';
    } else {
        if (out->freeCount == 0) {
            strcpy(out->recommendedSlot, "NONE");
        } else if (!out->s1) {
            strcpy(out->recommendedSlot, "S1");
        } else if (!out->s2) {
            strcpy(out->recommendedSlot, "S2");
        } else if (!out->s3) {
            strcpy(out->recommendedSlot, "S3");
        } else if (!out->s4) {
            strcpy(out->recommendedSlot, "S4");
        } else {
            strcpy(out->recommendedSlot, "NONE");
        }
    }

    // Extract STATUS (optional, default to OK)
    if (_comm_extract_field(raw, "STATUS=", val, sizeof(val))) {
        strncpy(out->status, val, sizeof(out->status) - 1);
        out->status[sizeof(out->status) - 1] = '\0';
    } else {
        strcpy(out->status, "OK");
    }

    return true;
}

// Find a key=VALUE field in the packet string, copy VALUE to out
bool _comm_extract_field(const char* src, const char* key, char* out, int maxLen) {
    const char* p = strstr(src, key);
    if (!p) return false;
    p += strlen(key);

    int i = 0;
    while (*p && *p != ',' && *p != '>' && i < maxLen - 1) {
        out[i++] = *p++;
    }
    out[i] = '\0';
    return (i > 0);
}
