/**
 * Smart Parking Management System
 * ESP32 Firmware — WiFi & Mobile Web Dashboard Server
 *
 * Provides a mobile-responsive real-time parking dashboard accessible
 * directly from any smartphone or tablet over ESP32 WiFi.
 *
 * Modes:
 *   1. SoftAP (Access Point) Mode: Broadcasts SSID "Smart-Parking-WiFi"
 *      Phone connects directly to ESP32 (IP: 192.168.4.1) without any router.
 *   2. Optional Station Mode: Can also connect to home/hotspot router if configured.
 *   3. mDNS: Accessible via http://parking.local
 */

#pragma once
#include "config.h"

void wifi_server_init();
void wifi_server_update();
const char* wifi_server_get_ap_ip();
const char* wifi_server_get_sta_ip();
bool wifi_server_is_ap_active();
