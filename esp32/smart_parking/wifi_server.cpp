/**
 * Smart Parking Management System
 * ESP32 Firmware — WiFi & Mobile Web Dashboard Server Implementation
 */

#include "wifi_server.h"
#include "communication.h"
#include "gate_fsm.h"
#include "servo_gate.h"
#include "vehicle_sensor.h"
#include "lcd_controller.h"
#include "buzzer.h"
#include <Arduino.h>
#include <WiFi.h>
#include <WebServer.h>
#include <ESPmDNS.h>

static WebServer server(80);
static String s_apIP = "192.168.4.1";
static String s_staIP = "Not connected";
static bool s_apActive = false;

// ── Mobile Responsive Dashboard HTML/CSS/JS (Stored in Flash PROGMEM) ────────
static const char INDEX_HTML[] PROGMEM = R"rawliteral(<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>Smart Parking Mobile Dashboard</title>
<style>
:root {
  --bg: #0b0f19;
  --card-bg: #141c2e;
  --card-border: #1e2c47;
  --accent-cyan: #00e5ff;
  --accent-green: #00e676;
  --accent-red: #ff1744;
  --accent-amber: #ffab00;
  --text-main: #f1f5f9;
  --text-dim: #94a3b8;
}
* { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
body { background: var(--bg); color: var(--text-main); min-height: 100vh; padding: 16px; padding-bottom: 30px; }
.container { max-width: 480px; margin: 0 auto; }

/* Header */
.header { text-align: center; padding: 12px 0 16px 0; border-bottom: 1px solid var(--card-border); margin-bottom: 16px; position: relative; }
.header h1 { font-size: 1.3rem; font-weight: 700; letter-spacing: 0.5px; color: #ffffff; }
.header p { font-size: 0.8rem; color: var(--accent-cyan); margin-top: 4px; font-weight: 500; }
.badge-live { display: inline-flex; align-items: center; gap: 6px; padding: 3px 10px; border-radius: 20px; font-size: 0.75rem; background: rgba(0, 230, 118, 0.15); color: var(--accent-green); border: 1px solid rgba(0, 230, 118, 0.3); margin-top: 8px; }
.dot { width: 8px; height: 8px; background: var(--accent-green); border-radius: 50%; animation: pulse 1.8s infinite; }
@keyframes pulse { 0%, 100% { opacity: 1; transform: scale(1); } 50% { opacity: 0.4; transform: scale(0.85); } }

/* Quick Metric Cards */
.metrics-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 16px; }
.metric-card { background: var(--card-bg); border: 1px solid var(--card-border); border-radius: 12px; padding: 14px; text-align: center; }
.metric-title { font-size: 0.72rem; text-transform: uppercase; color: var(--text-dim); letter-spacing: 0.5px; }
.metric-val { font-size: 1.6rem; font-weight: 800; margin-top: 4px; }
.metric-val.free { color: var(--accent-green); }
.metric-val.rec { color: var(--accent-cyan); }

/* Available Parking Bays */
.section-title { font-size: 0.85rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: var(--text-dim); margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center; }
.bays-container { display: flex; flex-direction: column; gap: 10px; margin-bottom: 18px; }
.bay-card-available { background: linear-gradient(135deg, #141c2e 0%, rgba(0, 230, 118, 0.10) 100%); border: 1.5px solid rgba(0, 230, 118, 0.45); border-radius: 12px; padding: 12px 16px; display: flex; justify-content: space-between; align-items: center; position: relative; overflow: hidden; box-shadow: 0 4px 10px rgba(0,0,0,0.25); }
.bay-card-available.recommended { border: 2px solid var(--accent-cyan); background: linear-gradient(135deg, #141c2e 0%, rgba(0, 229, 255, 0.15) 100%); box-shadow: 0 0 14px rgba(0, 229, 255, 0.35); }
.bay-title-wrap { display: flex; align-items: center; gap: 10px; }
.bay-code { font-size: 1.35rem; font-weight: 800; color: #fff; letter-spacing: 0.5px; }
.bay-tag { font-size: 0.72rem; font-weight: 700; padding: 3px 9px; border-radius: 20px; text-transform: uppercase; }
.bay-tag.rec { background: rgba(0, 229, 255, 0.25); color: var(--accent-cyan); border: 1px solid var(--accent-cyan); }
.bay-tag.avail { background: rgba(0, 230, 118, 0.2); color: var(--accent-green); }
.bay-hint { font-size: 0.82rem; font-weight: 700; }
.full-notice-box { background: linear-gradient(135deg, #1e141a 0%, rgba(255, 23, 68, 0.12) 100%); border: 1.5px solid rgba(255, 23, 68, 0.5); border-radius: 12px; padding: 22px 16px; text-align: center; color: var(--accent-red); margin-bottom: 18px; }
.full-notice-box h3 { font-size: 1.25rem; font-weight: 800; margin-bottom: 4px; letter-spacing: 0.5px; }
.full-notice-box p { font-size: 0.85rem; color: #fca5a5; font-weight: 500; }

/* Gate & Sensor Status */
.hw-card { background: var(--card-bg); border: 1px solid var(--card-border); border-radius: 12px; padding: 14px; margin-bottom: 14px; }
.hw-row { display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,0.05); }
.hw-row:last-child { border-bottom: none; padding-bottom: 0; }
.hw-label { font-size: 0.85rem; color: var(--text-dim); }
.hw-status { font-size: 0.88rem; font-weight: 700; }
.gate-open { color: var(--accent-green); }
.gate-closed { color: var(--accent-amber); }
.sensor-detected { color: var(--accent-red); animation: pulse 1s infinite; }
.sensor-clear { color: var(--accent-green); }

/* Retro LCD Mirror */
.lcd-box { background: #132211; border: 3px solid #233e20; border-radius: 8px; padding: 10px 14px; margin-bottom: 16px; box-shadow: inset 0 0 8px rgba(0,0,0,0.8); }
.lcd-title { font-size: 0.65rem; color: #4e8248; text-transform: uppercase; margin-bottom: 4px; font-weight: 700; }
.lcd-line { font-family: "Courier New", Courier, monospace; font-size: 1.05rem; font-weight: 700; color: #72ff59; letter-spacing: 1px; white-space: pre; line-height: 1.35; text-shadow: 0 0 4px rgba(114, 255, 89, 0.6); }

/* Remote Buttons */
.controls-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 16px; }
.btn-gate { border: none; padding: 13px 10px; border-radius: 10px; font-size: 0.88rem; font-weight: 700; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 6px; transition: all 0.2s; outline: none; }
.btn-open { background: linear-gradient(135deg, #00c853, #00e676); color: #00220d; box-shadow: 0 4px 10px rgba(0, 230, 118, 0.3); }
.btn-close { background: linear-gradient(135deg, #d50000, #ff1744); color: #ffffff; box-shadow: 0 4px 10px rgba(255, 23, 68, 0.3); }
.btn-gate:active { transform: scale(0.96); filter: brightness(0.9); }

/* Footer */
.footer { text-align: center; font-size: 0.7rem; color: #64748b; margin-top: 14px; }
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>SMART PARKING SYSTEM</h1>
    <p>ESP32 WiFi Node &bull; Live AI Dashboard</p>
    <div class="badge-live" id="connBadge"><span class="dot" id="connDot"></span> <span id="connText">CONNECTED (192.168.4.1)</span></div>
  </div>

  <div class="metrics-row">
    <div class="metric-card">
      <div class="metric-title">Free Bays</div>
      <div class="metric-val free" id="freeCount">--</div>
    </div>
    <div class="metric-card">
      <div class="metric-title">Recommended</div>
      <div class="metric-val rec" id="recSlot">--</div>
    </div>
  </div>

  <div class="section-title">
    <span>Available Parking Bays</span>
    <span style="font-size:0.75rem; color:var(--accent-green);" id="freeBadge"></span>
  </div>
  <div class="bays-container" id="baysContainer">
    <!-- Only available free slots rendered here -->
  </div>

  <div class="section-title"><span>Hardware & Gate Status</span></div>
  <div class="hw-card">
    <div class="hw-row">
      <span class="hw-label">Barrier Gate State</span>
      <span class="hw-status" id="gateState">--</span>
    </div>
    <div class="hw-row">
      <span class="hw-label">Auto-Close Timer</span>
      <span class="hw-status" id="gateTimer" style="color:var(--accent-cyan);">--</span>
    </div>
    <div class="hw-row">
      <span class="hw-label">IR Entrance Sensor</span>
      <span class="hw-status" id="sensorState">--</span>
    </div>
  </div>

  <div class="section-title"><span>Remote Barrier Control</span></div>
  <div class="controls-grid">
    <button class="btn-gate btn-open" onclick="sendGateCmd('open')">&#x1F513; OPEN GATE</button>
    <button class="btn-gate btn-close" onclick="sendGateCmd('close')">&#x1F512; CLOSE GATE</button>
  </div>

  <div class="section-title"><span>16x2 LCD Live Mirror</span></div>
  <div class="lcd-box">
    <div class="lcd-title">Physical Display Mirror</div>
    <div class="lcd-line" id="lcdL1">REC SLOT: S1    </div>
    <div class="lcd-line" id="lcdL2">GATE: CLOSED    </div>
  </div>

  <div class="footer">Smart Parking Management System &bull; ESP32-WROOM-32</div>
</div>

<script>
function sendGateCmd(action) {
  fetch('/api/gate?cmd=' + action)
    .then(r => r.json())
    .then(d => { updateUI(d); })
    .catch(e => console.error(e));
}

function updateUI(data) {
  if (!data) return;
  document.getElementById('freeCount').textContent = data.free;
  document.getElementById('recSlot').textContent = (data.free === 0) ? 'NONE' : data.rec;

  const container = document.getElementById('baysContainer');
  container.innerHTML = '';

  const slots = ['S1', 'S2', 'S3', 'S4'];
  const freeSlots = slots.filter(s => data.slots && data.slots[s] === 0);

  if (freeSlots.length === 0 || data.free === 0) {
    document.getElementById('freeBadge').textContent = 'FULL';
    document.getElementById('freeBadge').style.color = 'var(--accent-red)';
    container.innerHTML = '<div class="full-notice-box"><h3>PARKING FULL</h3><p>SORRY! NO SPACE AVAILABLE</p></div>';
  } else {
    document.getElementById('freeBadge').textContent = freeSlots.length + ' AVAILABLE';
    document.getElementById('freeBadge').style.color = 'var(--accent-green)';

    freeSlots.forEach(slot => {
      const isRec = (data.rec === slot);
      const card = document.createElement('div');
      card.className = 'bay-card-available' + (isRec ? ' recommended' : '');
      card.innerHTML = `
        <div class="bay-title-wrap">
          <span class="bay-code">${slot}</span>
          ${isRec ? '<span class="bay-tag rec">&#9733; RECOMMENDED</span>' : '<span class="bay-tag avail">AVAILABLE</span>'}
        </div>
        <div class="bay-hint" style="color:${isRec ? 'var(--accent-cyan)' : 'var(--accent-green)'}">
          ${isRec ? 'BEST SPOT' : 'READY TO PARK'}
        </div>
      `;
      container.appendChild(card);
    });
  }

  // Gate
  const gateEl = document.getElementById('gateState');
  gateEl.textContent = data.gate;
  if (data.gate.includes('OPEN')) {
    gateEl.className = 'hw-status gate-open';
  } else {
    gateEl.className = 'hw-status gate-closed';
  }

  // Timer
  const timerEl = document.getElementById('gateTimer');
  if (data.timer > 0) {
    timerEl.textContent = data.timer.toFixed(1) + 's (Counting down)';
  } else {
    timerEl.textContent = 'Standby (0.0s)';
  }

  // Sensor
  const sensorEl = document.getElementById('sensorState');
  if (data.sensor === 'DETECTED') {
    sensorEl.textContent = 'VEHICLE DETECTED';
    sensorEl.className = 'hw-status sensor-detected';
  } else {
    sensorEl.textContent = 'CLEAR (Standby)';
    sensorEl.className = 'hw-status sensor-clear';
  }

  // LCD Mirror
  if (data.lcd1) document.getElementById('lcdL1').textContent = data.lcd1;
  if (data.lcd2) document.getElementById('lcdL2').textContent = data.lcd2;

  // Connection badge
  document.getElementById('connText').textContent = 'CONNECTED (' + data.ip + ')';
  document.getElementById('connDot').style.background = 'var(--accent-green)';
}

function poll() {
  fetch('/api/status')
    .then(r => r.json())
    .then(d => {
      updateUI(d);
    })
    .catch(e => {
      document.getElementById('connText').textContent = 'RECONNECTING...';
      document.getElementById('connDot').style.background = 'var(--accent-amber)';
    });
}

setInterval(poll, 600);
poll();
</script>
</body>
</html>
)rawliteral";

// ── JSON Status Builder ───────────────────────────────────────────────────────
static String build_status_json() {
    SensorState_t sensorSt = sensor_read();
    bool vehicleSensor = (sensorSt == SENSOR_DETECTED);
    int activePin = sensor_get_active_pin();
    float remSec = gate_fsm_get_remaining_sec();

    String json = "{";
    json += "\"slots\":{";
    json += "\"S1\":" + String(g_parkingStatus.s1 ? 1 : 0) + ",";
    json += "\"S2\":" + String(g_parkingStatus.s2 ? 1 : 0) + ",";
    json += "\"S3\":" + String(g_parkingStatus.s3 ? 1 : 0) + ",";
    json += "\"S4\":" + String(g_parkingStatus.s4 ? 1 : 0);
    json += "},";
    json += "\"free\":" + String(g_parkingStatus.freeCount) + ",";
    json += "\"occupied\":" + String(4 - g_parkingStatus.freeCount) + ",";
    json += "\"total\":4,";
    json += "\"rec\":\"" + String(g_parkingStatus.recommendedSlot) + "\",";
    json += "\"gate\":\"" + String(gate_fsm_state_str()) + "\",";
    json += "\"gateAngle\":" + String(g_gateState == GATE_CLOSED ? 0 : 90) + ",";
    json += "\"timer\":" + String(remSec, 1) + ",";
    json += "\"sensor\":\"" + String(vehicleSensor ? "DETECTED" : "CLEAR") + "\",";
    json += "\"pin\":" + String(activePin) + ",";
    json += "\"comm\":\"" + String(comm_is_lost() ? "LOST" : "OK") + "\",";
    json += "\"lcd1\":\"" + String(lcd_get_line0()) + "\",";
    json += "\"lcd2\":\"" + String(lcd_get_line1()) + "\",";
    json += "\"ip\":\"" + s_apIP + "\"";
    json += "}";
    return json;
}

// ── Handlers ──────────────────────────────────────────────────────────────────
static void handle_root() {
    server.send(200, "text/html", INDEX_HTML);
}

static void handle_api_status() {
    server.sendHeader("Access-Control-Allow-Origin", "*");
    server.send(200, "application/json", build_status_json());
}

static void handle_api_gate() {
    server.sendHeader("Access-Control-Allow-Origin", "*");
    if (server.hasArg("cmd")) {
        String cmd = server.arg("cmd");
        if (cmd == "open") {
            gate_fsm_request_open(g_parkingStatus.freeCount, comm_is_lost());
            buzzer_pattern(BUZZER_GATE_SAFETY);
        } else if (cmd == "close") {
            gate_fsm_request_close(sensor_read() == SENSOR_DETECTED);
            buzzer_pattern(BUZZER_GATE_SAFETY);
        }
    }
    server.send(200, "application/json", build_status_json());
}

// ── Initialisation ────────────────────────────────────────────────────────────
void wifi_server_init() {
    Serial.println("[WIFI] Initialising WiFi subsystem...");

    // Start in AP mode (creates WiFi network for phones)
    WiFi.mode(WIFI_AP);
    bool apSuccess = WiFi.softAP(WIFI_AP_SSID, (strlen(WIFI_AP_PASS) >= 8) ? WIFI_AP_PASS : NULL, WIFI_AP_CHANNEL);

    if (apSuccess) {
        s_apIP = WiFi.softAPIP().toString();
        s_apActive = true;
        Serial.print("[WIFI] AP Started! SSID: \"");
        Serial.print(WIFI_AP_SSID);
        Serial.print("\" | Password: \"");
        Serial.print(WIFI_AP_PASS);
        Serial.println("\"");
        Serial.print("[WIFI] Connect your phone to this WiFi, then open http://");
        Serial.println(s_apIP);
    } else {
        Serial.println("[WIFI] Failed to start SoftAP!");
    }

    // Optional Station mode connection if configured
    if (strlen(WIFI_STA_SSID) > 0) {
        WiFi.mode(WIFI_AP_STA);
        Serial.print("[WIFI] Connecting to home WiFi: ");
        Serial.println(WIFI_STA_SSID);
        WiFi.begin(WIFI_STA_SSID, WIFI_STA_PASS);
        unsigned long startMs = millis();
        while (WiFi.status() != WL_CONNECTED && (millis() - startMs) < 6000) {
            delay(200);
            Serial.print(".");
        }
        if (WiFi.status() == WL_CONNECTED) {
            s_staIP = WiFi.localIP().toString();
            Serial.println("\n[WIFI] Connected to Home WiFi! IP: " + s_staIP);
        } else {
            Serial.println("\n[WIFI] Home WiFi connection timed out; using AP mode only.");
        }
    }

    // Setup mDNS responder
    if (MDNS.begin(WIFI_MDNS_HOST)) {
        Serial.println("[WIFI] mDNS responder started: http://" + String(WIFI_MDNS_HOST) + ".local");
    }

    // Register HTTP routes
    server.on("/", HTTP_GET, handle_root);
    server.on("/api/status", HTTP_GET, handle_api_status);
    server.on("/api/gate", HTTP_GET, handle_api_gate);

    server.begin();
    Serial.println("[WIFI] Mobile Web Server listening on port 80");
}

void wifi_server_update() {
    server.handleClient();
}

const char* wifi_server_get_ap_ip() {
    return s_apIP.c_str();
}

const char* wifi_server_get_sta_ip() {
    return s_staIP.c_str();
}

bool wifi_server_is_ap_active() {
    return s_apActive;
}
