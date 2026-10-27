"""
Generates ultra-high resolution PNG images and an interactive HTML preview
for the Control Data Flow Graph (CDFG) and Moore Finite State Machine (FSM).
"""

import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, BoxStyle

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def create_cdfg_png():
    fig, ax = plt.subplots(figsize=(12, 14), dpi=300)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 110)
    ax.axis('off')

    # Background canvas
    fig.patch.set_facecolor('#f8fafc')
    ax.set_facecolor('#f8fafc')

    # Title Card
    title_box = FancyBboxPatch((5, 98), 90, 10, boxstyle="round,pad=0.5,rounding_size=1.5",
                               fc="#0f172a", ec="#1e293b", lw=1.5)
    ax.add_patch(title_box)
    ax.text(50, 104.5, "Control Data Flow Graph (CDFG): CCTV Occupancy Update Cycle",
            ha='center', va='center', color='white', fontsize=14, weight='bold', family='sans-serif')
    ax.text(50, 100.5, "Measured on RTX 3050 GPU | Total Critical Path: 13.43 ms | Deadline: 100 ms | Slack Margin: 86.57 ms (86.6%)",
            ha='center', va='center', color='#38bdf8', fontsize=9.5, weight='semibold', family='sans-serif')

    # Helper function for nodes
    def draw_node(x, y, w, h, title, subtitle, tag, fc, ec, text_color="white"):
        box = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.5,rounding_size=1.2",
                             fc=fc, ec=ec, lw=2, zorder=3)
        ax.add_patch(box)
        ax.text(x + w/2, y + h*0.62, title, ha='center', va='center', color=text_color,
                fontsize=11, weight='bold', zorder=4)
        ax.text(x + w/2, y + h*0.28, subtitle, ha='center', va='center', color=text_color,
                fontsize=8.5, style='normal', zorder=4)
        if tag:
            tbox = FancyBboxPatch((x + w - 18, y + h - 2.5), 17, 3.5, boxstyle="round,pad=0.2,rounding_size=0.8",
                                  fc='#0284c7', ec='none', lw=0, zorder=5)
            ax.add_patch(tbox)
            ax.text(x + w - 9.5, y + h - 0.75, tag, ha='center', va='center', color='white',
                    fontsize=7, weight='bold', zorder=6)

    def draw_diamond(x, y, w, h, title, subtitle, fc, ec):
        pts = [(x + w/2, y + h), (x + w, y + h/2), (x + w/2, y), (x, y + h/2)]
        poly = patches.Polygon(pts, closed=True, fc=fc, ec=ec, lw=2, zorder=3)
        ax.add_patch(poly)
        ax.text(x + w/2, y + h*0.58, title, ha='center', va='center', color='white',
                fontsize=10.5, weight='bold', zorder=4)
        ax.text(x + w/2, y + h*0.35, subtitle, ha='center', va='center', color='#cbd5e1',
                fontsize=8.5, zorder=4)

    # Nodes definition
    # Start
    draw_node(30, 89, 40, 5.5, "Start / Periodic Video Frame Trigger", "Cycle T = 100 ms (10 Hz Target Rate)", "", "#1e293b", "#334155")
    
    # N1
    draw_node(30, 78, 40, 6.5, "N1: Capture Camera Frame", "Measured: 0.47 ms  |  Allocated: 8.00 ms (Slack: +7.53 ms)", "0.47 ms", "#1e3a8a", "#2563eb")
    
    # D1 (Diamond)
    draw_diamond(30, 65, 40, 8.5, "D1: Valid Frame & Model Ready?", "cv2 frame check (< 0.01 ms)", "#0f172a", "#475569")
    
    # Degraded Branch (Right)
    draw_node(74, 53, 22, 6.5, "Degraded Fallback", "Retain Last Occupancy\nLog Frame Dropout", "FAILSAFE", "#7f1d1d", "#dc2626")

    # N2 (Dominant)
    draw_node(30, 52, 40, 7.5, "N2: YOLOv8 Car Detection Inference", "Measured: 12.93 ms on RTX 3050 (96.3% of Compute Path)", "12.93 ms", "#1d4ed8", "#3b82f6")

    # N3
    draw_node(30, 40, 40, 6.5, "N3: Geometric Slot Mapping", "cv2.pointPolygonTest (Bays S1–S4) | Measured: 0.006 ms", "0.006 ms", "#2563eb", "#60a5fa")

    # N4
    draw_node(30, 29, 40, 6.5, "N4: Temporal Hysteresis Filter", "5-Frame Occupied / 8-Frame Free Debounce | Measured: 0.004 ms", "0.004 ms", "#0284c7", "#38bdf8")

    # N5
    draw_node(30, 18, 40, 6.5, "N5: Count Free Bays & Best Slot", "Tally available slots & select best recommendation | Measured: 0.006 ms", "0.006 ms", "#0891b2", "#22d3ee")

    # N6
    draw_node(30, 7.5, 40, 6.5, "N6: Encode & Transmit Packet", "Serial <PKT,S1..FREE=..> to ESP32 | Measured: 0.003 ms", "0.003 ms", "#0d9488", "#2dd4bf")

    # End
    draw_node(30, -0.5, 40, 5, "End / Sleep Until Next Period", "Wait for next 100 ms clock tick", "", "#1e293b", "#334155")

    # Connectors & Arrows
    def arrow(x1, y1, x2, y2, color="#334155", lw=2, dashed=False, label=""):
        ls = '--' if dashed else '-'
        ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(facecolor=color, edgecolor=color, arrowstyle='-|>', lw=lw, linestyle=ls, mutation_scale=15),
                    zorder=2)
        if label:
            mx, my = (x1 + x2)/2, (y1 + y2)/2
            ax.text(mx + 1.5, my, label, color=color, fontsize=9, weight='bold',
                    bbox=dict(boxstyle="round,pad=0.2", fc="white", ec=color, lw=1))

    # Main spine
    arrow(50, 89, 50, 84.5)
    arrow(50, 78, 50, 73.5)
    arrow(50, 65, 50, 59.5, color="#059669", label="Yes (Valid)")
    arrow(50, 52, 50, 46.5)
    arrow(50, 40, 50, 35.5)
    arrow(50, 29, 50, 24.5)
    arrow(50, 18, 50, 14.0)
    arrow(50, 7.5, 50, 4.5)

    # Degraded Branch
    # D1 to Degraded
    ax.annotate('', xy=(74, 56.5), xytext=(70, 69.25),
                arrowprops=dict(facecolor='#dc2626', edgecolor='#dc2626', arrowstyle='-|>', lw=2, mutation_scale=15),
                zorder=2)
    ax.text(71, 64, "No (Drop)", color="#dc2626", fontsize=8.5, weight='bold',
            bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="#dc2626", lw=1))

    # Degraded to End (orthogonal line)
    ax.plot([85, 85, 50], [53, 2, 2], color='#dc2626', lw=1.5, ls='--', zorder=2)
    ax.annotate('', xy=(50, 2), xytext=(55, 2),
                arrowprops=dict(facecolor='#dc2626', edgecolor='#dc2626', arrowstyle='-|>', lw=1.5, mutation_scale=12),
                zorder=2)

    # Side Card: Timing Analysis Summary
    card = FancyBboxPatch((3, 25), 23, 40, boxstyle="round,pad=0.5,rounding_size=1.2",
                          fc="#ffffff", ec="#cbd5e1", lw=1.5, zorder=3)
    ax.add_patch(card)
    ax.text(14.5, 62.5, "Timing Breakdown", ha='center', va='center', color='#0f172a', fontsize=11, weight='bold')
    
    timings = [
        ("N1 Frame Capture", "0.47 ms", "#1e3a8a"),
        ("D1 Sanity Check", "<0.01 ms", "#475569"),
        ("N2 YOLO Inference", "12.93 ms", "#1d4ed8"),
        ("N3 Slot Mapping", "0.006 ms", "#2563eb"),
        ("N4 Debounce Filter", "0.004 ms", "#0284c7"),
        ("N5 Free Bays Count", "0.006 ms", "#0891b2"),
        ("N6 Serial Encode", "0.003 ms", "#0d9488"),
    ]
    
    y_pos = 58
    for name, val, col in timings:
        ax.text(5, y_pos, f"• {name}:", color='#334155', fontsize=8.5, weight='semibold')
        ax.text(23, y_pos, val, ha='right', color=col, fontsize=8.5, weight='bold')
        y_pos -= 3.3

    # Divider line
    ax.plot([5, 24], [y_pos + 1, y_pos + 1], color='#cbd5e1', lw=1)
    y_pos -= 2.5
    ax.text(5, y_pos, "Total Measured:", color='#0f172a', fontsize=9, weight='bold')
    ax.text(23, y_pos, "13.43 ms", ha='right', color='#059669', fontsize=9.5, weight='bold')
    y_pos -= 3.5
    ax.text(5, y_pos, "Cycle Deadline:", color='#0f172a', fontsize=9, weight='bold')
    ax.text(23, y_pos, "100.00 ms", ha='right', color='#dc2626', fontsize=9.5, weight='bold')
    y_pos -= 3.5
    ax.text(5, y_pos, "Safety Slack Margin:", color='#0f172a', fontsize=9, weight='bold')
    ax.text(23, y_pos, "+86.57 ms", ha='right', color='#2563eb', fontsize=10, weight='bold')
    y_pos -= 3.2
    ax.text(14.5, y_pos, "(86.6% Safety Margin)", ha='center', color='#2563eb', fontsize=8, style='italic')

    out_path = os.path.join(BASE_DIR, "cdfg_diagram.png")
    plt.tight_layout()
    plt.savefig(out_path, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none', bbox_inches='tight')
    plt.close()
    print(f"CDFG PNG generated at: {out_path}")


def create_fsm_png():
    fig, ax = plt.subplots(figsize=(15, 11), dpi=300)
    ax.set_xlim(0, 150)
    ax.set_ylim(0, 110)
    ax.axis('off')

    fig.patch.set_facecolor('#f8fafc')
    ax.set_facecolor('#f8fafc')

    # Title Card
    title_box = FancyBboxPatch((10, 97), 130, 10, boxstyle="round,pad=0.5,rounding_size=1.5",
                               fc="#0f172a", ec="#1e293b", lw=1.5)
    ax.add_patch(title_box)
    ax.text(75, 103.5, "System Behavior: Moore Gate Finite State Machine (FSM)",
            ha='center', va='center', color='white', fontsize=15, weight='bold', family='sans-serif')
    ax.text(75, 99.5, "Six States · One Dedicated Safe State (FAULT_SAFE) · Outputs Depend Strictly on Current State",
            ha='center', va='center', color='#38bdf8', fontsize=10, weight='semibold', family='sans-serif')

    # State Drawing Helper
    def draw_state(x, y, w, h, name, outputs, fc, ec, text_color='#0f172a'):
        box = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.6,rounding_size=2.0",
                             fc=fc, ec=ec, lw=2.5, zorder=3)
        ax.add_patch(box)
        # Header line inside state
        ax.text(x + w/2, y + h*0.75, name, ha='center', va='center', color=text_color,
                fontsize=12, weight='bold', family='sans-serif', zorder=4)
        ax.plot([x + 2, x + w - 2], [y + h*0.60, y + h*0.60], color=ec, lw=1.2, zorder=4)
        # Output lines
        y_text = y + h*0.46
        for line in outputs:
            ax.text(x + 3, y_text, f"• {line}", ha='left', va='center', color=text_color,
                    fontsize=8.2, weight='medium', zorder=4)
            y_text -= h*0.18

    # States Layout
    # State 1: CLOSED (Left)
    draw_state(12, 50, 32, 22, "1. CLOSED",
               ["Servo: 0° (Barrier Down)", "LCD: 'GATE: CLOSED'", "Safe Default State"],
               "#f8fafc", "#334155")

    # State 2: OPENING (Top Middle)
    draw_state(59, 72, 32, 22, "2. OPENING",
               ["Servo: Sweeping 0° → 90°", "LCD: 'GATE: OPENING'", "Travel Timer = 1.5s"],
               "#eff6ff", "#2563eb", text_color='#1e3a8a')

    # State 3: OPEN (Right Top)
    draw_state(106, 50, 32, 22, "3. OPEN",
               ["Servo: 90° (Barrier Up)", "LCD: 'GATE: OPEN'", "10s Hold Timer Active"],
               "#ecfdf5", "#059669", text_color='#064e3b')

    # State 4: VEHICLE_PASSING (Right Bottom)
    draw_state(106, 18, 32, 22, "4. VEHICLE_PASSING",
               ["Servo: 90° Maintained", "IR Sensor Active (Beam Cut)", "Timer Continuously Resets"],
               "#fef3c7", "#d97706", text_color='#78350f')

    # State 5: CLOSING (Bottom Middle)
    draw_state(59, 28, 32, 22, "5. CLOSING",
               ["Servo: Sweeping 90° → 0°", "LCD: 'GATE: CLOSING'", "Safety Override Armed"],
               "#fff1f2", "#e11d48", text_color='#881337')

    # State 6: FAULT_SAFE (Bottom Center)
    draw_state(59, 2, 32, 20, "6. FAULT_SAFE",
               ["Servo: 0° Locked Firmly", "LCD: 'SYSTEM OFFLINE'", "Bounded Buzzer Warning"],
               "#0f172a", "#000000", text_color='#ffffff')

    # Transition labels helper
    def draw_edge_text(x, y, text, color, bg="white", border=None):
        ec = border if border else color
        ax.text(x, y, text, ha='center', va='center', color=color, fontsize=8, weight='bold',
                bbox=dict(boxstyle="round,pad=0.25", fc=bg, ec=ec, lw=1.2), zorder=6)

    # Transitions Arrows
    # 1 -> 2: CLOSED -> OPENING
    ax.annotate('', xy=(59, 81), xytext=(35, 72),
                arrowprops=dict(facecolor='#059669', edgecolor='#059669', arrowstyle='-|>',
                                connectionstyle="arc3,rad=-0.15", lw=2.2, mutation_scale=15), zorder=5)
    draw_edge_text(38, 83, "Vehicle at IR & Free Bays > 0\n[Or Web Button Pressed]", '#059669')

    # 2 -> 3: OPENING -> OPEN
    ax.annotate('', xy=(106, 68), xytext=(91, 81),
                arrowprops=dict(facecolor='#2563eb', edgecolor='#2563eb', arrowstyle='-|>',
                                connectionstyle="arc3,rad=-0.15", lw=2.2, mutation_scale=15), zorder=5)
    draw_edge_text(108, 83, "Gate Fully Open Reached\n[1.5s Travel Time]", '#2563eb')

    # 3 -> 4: OPEN -> VEHICLE_PASSING
    ax.annotate('', xy=(122, 40), xytext=(122, 50),
                arrowprops=dict(facecolor='#d97706', edgecolor='#d97706', arrowstyle='-|>', lw=2.2, mutation_scale=15), zorder=5)
    draw_edge_text(136, 45, "Vehicle Breaks\nIR Beam", '#d97706')

    # 4 -> 5: VEHICLE_PASSING -> CLOSING
    ax.annotate('', xy=(91, 35), xytext=(106, 26),
                arrowprops=dict(facecolor='#334155', edgecolor='#334155', arrowstyle='-|>',
                                connectionstyle="arc3,rad=0.1", lw=2.2, mutation_scale=15), zorder=5)
    draw_edge_text(101, 26, "Beam Cleared\n(Debounced >500ms)", '#334155')

    # 3 -> 5: OPEN -> CLOSING (Timeout direct)
    ax.annotate('', xy=(91, 46), xytext=(106, 56),
                arrowprops=dict(facecolor='#334155', edgecolor='#334155', arrowstyle='-|>',
                                connectionstyle="arc3,rad=-0.1", lw=1.8, ls='--', mutation_scale=14), zorder=5)
    draw_edge_text(96, 54, "10s Hold Expired\n(No entry)", '#334155')

    # 5 -> 1: CLOSING -> CLOSED
    ax.annotate('', xy=(35, 53), xytext=(59, 35),
                arrowprops=dict(facecolor='#1e293b', edgecolor='#1e293b', arrowstyle='-|>',
                                connectionstyle="arc3,rad=-0.15", lw=2.2, mutation_scale=15), zorder=5)
    draw_edge_text(40, 39, "Gate Fully Closed (0°)\n[Sensor Clear]", '#1e293b')

    # CRITICAL: 5 -> 2: SAFETY REVERSAL! (CLOSING -> OPENING)
    ax.annotate('', xy=(72, 72), xytext=(72, 50),
                arrowprops=dict(facecolor='#dc2626', edgecolor='#dc2626', arrowstyle='-|>', lw=3.0, mutation_scale=18), zorder=7)
    draw_edge_text(72, 61, "CRITICAL SAFETY REVERSAL!\nObstacle Detected during Closing\n[Immediate Re-Open in < 25 ms]", '#dc2626', bg='#fff1f2', border='#dc2626')

    # Fault transitions (dashed grey)
    # CLOSED -> FAULT_SAFE
    ax.annotate('', xy=(59, 12), xytext=(28, 50),
                arrowprops=dict(facecolor='#64748b', edgecolor='#64748b', arrowstyle='-|>',
                                connectionstyle="arc3,rad=0.2", lw=1.5, ls='--', mutation_scale=12), zorder=2)
    # CLOSING -> FAULT_SAFE
    ax.annotate('', xy=(75, 22), xytext=(75, 28),
                arrowprops=dict(facecolor='#64748b', edgecolor='#64748b', arrowstyle='-|>', lw=1.5, ls='--', mutation_scale=12), zorder=2)

    # Recovery: FAULT_SAFE -> CLOSED
    ax.annotate('', xy=(15, 50), xytext=(59, 7),
                arrowprops=dict(facecolor='#059669', edgecolor='#059669', arrowstyle='-|>',
                                connectionstyle="arc3,rad=0.3", lw=1.8, ls='--', mutation_scale=14), zorder=2)
    draw_edge_text(24, 20, "Fault Cleared & Reset\n[Safe Re-arm]", '#059669')

    # Notes Card (Right Bottom)
    note_box = FancyBboxPatch((10, 18), 34, 26, boxstyle="round,pad=0.5,rounding_size=1.2",
                              fc="#ffffff", ec="#cbd5e1", lw=1.5, zorder=3)
    ax.add_patch(note_box)
    ax.text(27, 41, "Moore Machine Properties", ha='center', va='center', color='#0f172a', fontsize=10, weight='bold')
    notes = [
        "• Pure State-Driven Outputs",
        "• Safe State: FAULT_SAFE (Servo 0°)",
        "• Anti-Pinch Reversal: < 25 ms",
        "• 10s Hold-Open Auto-Timer",
        "• Inhibit entry on Full Parking",
        "• RMS Utilization: U = 2.6% << 75.7%"
    ]
    ny = 37
    for n in notes:
        ax.text(12, ny, n, color='#334155', fontsize=8, weight='medium')
        ny -= 3.3

    out_path = os.path.join(BASE_DIR, "fsm_diagram.png")
    plt.tight_layout()
    plt.savefig(out_path, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none', bbox_inches='tight')
    plt.close()
    print(f"FSM PNG generated at: {out_path}")


def create_html_viewer():
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Smart Parking - Exact Diagrams (CDFG & FSM) | BACSE324</title>
  <style>
    :root {
      --bg: #0f172a;
      --card-bg: #1e293b;
      --text: #f8fafc;
      --accent: #38bdf8;
      --green: #22c55e;
      --red: #ef4444;
      --border: #334155;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    body {
      background-color: #0b0f19;
      color: var(--text);
      padding: 24px;
      display: flex;
      flex-direction: column;
      align-items: center;
    }
    .header {
      text-align: center;
      max-width: 900px;
      margin-bottom: 24px;
    }
    .header h1 {
      font-size: 26px;
      font-weight: 800;
      color: #ffffff;
      margin-bottom: 8px;
    }
    .header p {
      font-size: 14px;
      color: #94a3b8;
      line-height: 1.5;
    }
    .badge-bar {
      display: flex;
      gap: 12px;
      justify-content: center;
      margin-top: 12px;
      flex-wrap: wrap;
    }
    .badge {
      background: rgba(56, 189, 248, 0.12);
      border: 1px solid rgba(56, 189, 248, 0.3);
      color: var(--accent);
      padding: 4px 12px;
      border-radius: 9999px;
      font-size: 12px;
      font-weight: 600;
    }
    .tabs {
      display: flex;
      gap: 8px;
      background: var(--card-bg);
      padding: 6px;
      border-radius: 12px;
      border: 1px solid var(--border);
      margin-bottom: 24px;
    }
    .tab-btn {
      background: transparent;
      border: none;
      color: #94a3b8;
      padding: 10px 24px;
      font-size: 14px;
      font-weight: 700;
      cursor: pointer;
      border-radius: 8px;
      transition: all 0.2s ease;
    }
    .tab-btn.active {
      background: #0284c7;
      color: #ffffff;
      box-shadow: 0 4px 12px rgba(2, 132, 199, 0.4);
    }
    .diagram-panel {
      display: none;
      width: 100%;
      max-width: 1100px;
      background: #ffffff;
      border-radius: 16px;
      box-shadow: 0 20px 40px rgba(0, 0, 0, 0.5);
      overflow: hidden;
      border: 2px solid var(--border);
      position: relative;
    }
    .diagram-panel.active {
      display: block;
    }
    .diagram-img-wrap {
      width: 100%;
      text-align: center;
      background: #f8fafc;
      padding: 16px;
      overflow-x: auto;
    }
    .diagram-img-wrap img {
      max-width: 100%;
      height: auto;
      border-radius: 8px;
      display: block;
      margin: 0 auto;
    }
    .action-bar {
      background: var(--card-bg);
      padding: 14px 24px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-top: 1px solid var(--border);
      flex-wrap: wrap;
      gap: 12px;
    }
    .btn {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      background: #2563eb;
      color: white;
      text-decoration: none;
      padding: 9px 18px;
      border-radius: 8px;
      font-size: 13px;
      font-weight: 600;
      transition: background 0.2s;
      cursor: pointer;
      border: none;
    }
    .btn:hover {
      background: #1d4ed8;
    }
    .btn-secondary {
      background: #334155;
    }
    .btn-secondary:hover {
      background: #475569;
    }
    .instructions {
      max-width: 1100px;
      width: 100%;
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 20px 24px;
      margin-top: 24px;
    }
    .instructions h2 {
      font-size: 16px;
      color: var(--accent);
      margin-bottom: 12px;
    }
    .instructions ol {
      padding-left: 20px;
      color: #cbd5e1;
      font-size: 13px;
      line-height: 1.8;
    }
    .instructions code {
      background: #0f172a;
      padding: 2px 6px;
      border-radius: 4px;
      color: #38bdf8;
      font-size: 12px;
    }
  </style>
</head>
<body>

  <div class="header">
    <h1>Smart Parking Management System — Exact Design Diagrams</h1>
    <p>High-resolution, measured-benchmark diagrams for BACSE324 Review 2 presentation & report.</p>
    <div class="badge-bar">
      <span class="badge">CDFG Path: 13.43 ms (Slack: 86.57 ms)</span>
      <span class="badge">YOLOv8 Inference: 12.93 ms (RTX 3050)</span>
      <span class="badge">Safety Reversal: &lt; 25 ms</span>
      <span class="badge">Moore 6-State FSM</span>
      <span class="badge">RMS Utilization: 2.6% &lt;&lt; 75.7%</span>
    </div>
  </div>

  <div class="tabs">
    <button class="tab-btn active" onclick="switchTab('cdfg')">📊 1. CDFG Diagram (CCTV Pipeline)</button>
    <button class="tab-btn" onclick="switchTab('fsm')">🔄 2. Moore FSM Diagram (Gate Control)</button>
  </div>

  <!-- CDFG Panel -->
  <div id="panel-cdfg" class="diagram-panel active">
    <div class="diagram-img-wrap">
      <img src="cdfg_diagram.png" alt="Control Data Flow Graph (CDFG) Diagram">
    </div>
    <div class="action-bar">
      <div>
        <strong style="color:white; font-size:14px;">Control Data Flow Graph (CDFG)</strong>
        <p style="color:#94a3b8; font-size:12px;">Total critical path: 13.43 ms against 100 ms deadline (86.6% safety margin)</p>
      </div>
      <div style="display:flex; gap:10px;">
        <a href="cdfg_diagram.png" download="cdfg_diagram.png" class="btn">📥 Download High-Res PNG</a>
        <a href="cdfg_diagram.drawio" download="cdfg_diagram.drawio" class="btn btn-secondary">📐 Download .drawio File</a>
      </div>
    </div>
  </div>

  <!-- FSM Panel -->
  <div id="panel-fsm" class="diagram-panel">
    <div class="diagram-img-wrap">
      <img src="fsm_diagram.png" alt="Moore Gate Finite State Machine (FSM) Diagram">
    </div>
    <div class="action-bar">
      <div>
        <strong style="color:white; font-size:14px;">Moore Gate Finite State Machine (FSM)</strong>
        <p style="color:#94a3b8; font-size:12px;">6 states, FAULT_SAFE recovery, anti-pinch reversal in &lt;25 ms, 10s auto-close timer</p>
      </div>
      <div style="display:flex; gap:10px;">
        <a href="fsm_diagram.png" download="fsm_diagram.png" class="btn">📥 Download High-Res PNG</a>
        <a href="fsm_diagram.drawio" download="fsm_diagram.drawio" class="btn btn-secondary">📐 Download .drawio File</a>
      </div>
    </div>
  </div>

  <!-- Instructions for Draw.io -->
  <div class="instructions">
    <h2>🎯 How to Open and Edit in Draw.io (app.diagrams.net):</h2>
    <ol>
      <li>Go to your web browser and open: <strong><a href="https://app.diagrams.net" target="_blank" style="color:#38bdf8; text-decoration:none;">https://app.diagrams.net</a></strong></li>
      <li>Click <strong>"Open Existing Diagram"</strong> (or simply drag and drop the file into the draw.io window).</li>
      <li>Select <code>c:\\Users\\kesha\\Desktop\\embedded\\smart-parking-system\\cdfg_diagram.drawio</code> or <code>fsm_diagram.drawio</code>.</li>
      <li>The complete diagram with all rounded shapes, exact labels, measured timings, and color-coded paths will open instantly!</li>
      <li>You can edit text, move nodes, or click <strong>File &rarr; Export as &rarr; PNG / PDF / SVG</strong> anytime.</li>
    </ol>
  </div>

  <script>
    function switchTab(type) {
      document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
      document.querySelectorAll('.diagram-panel').forEach(panel => panel.classList.remove('active'));
      if (type === 'cdfg') {
        document.querySelector('.tabs button:nth-child(1)').classList.add('active');
        document.getElementById('panel-cdfg').classList.add('active');
      } else {
        document.querySelector('.tabs button:nth-child(2)').classList.add('active');
        document.getElementById('panel-fsm').classList.add('active');
      }
    }
  </script>
</body>
</html>
"""
    html_path = os.path.join(BASE_DIR, "diagrams_preview.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"HTML Viewer generated at: {html_path}")

if __name__ == "__main__":
    create_cdfg_png()
    create_fsm_png()
    create_html_viewer()
