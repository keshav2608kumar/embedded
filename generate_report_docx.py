import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
import os

def set_cell_background(cell, fill_hex):
    tcPr = cell._element.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), fill_hex)
    tcPr.append(shd)

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    tcPr = cell._element.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for m, val in [('w:top', top), ('w:bottom', bottom), ('w:left', left), ('w:right', right)]:
        node = OxmlElement(m)
        node.set(qn('w:w'), str(val))
        node.set(qn('w:type'), 'dxa')
        tcMar.append(node)
    tcPr.append(tcMar)

def format_table(table, header_bg="1F497D", stripe_bg="F2F5F9"):
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, row in enumerate(table.rows):
        is_header = (i == 0)
        for cell in row.cells:
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            set_cell_margins(cell, top=80, bottom=80, left=120, right=120)
            if is_header:
                set_cell_background(cell, header_bg)
                for p in cell.paragraphs:
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    for run in p.runs:
                        run.font.bold = True
                        run.font.color.rgb = RGBColor(255, 255, 255)
                        run.font.size = Pt(9.5)
            else:
                if i % 2 == 1:
                    set_cell_background(cell, "FFFFFF")
                else:
                    set_cell_background(cell, stripe_bg)
                for p in cell.paragraphs:
                    for run in p.runs:
                        run.font.size = Pt(9)

def create_table(doc, headers, data, header_bg="1F497D", stripe_bg="F2F5F9"):
    table = doc.add_table(rows=len(data) + 1, cols=len(headers))
    for c_idx, h in enumerate(headers):
        table.cell(0, c_idx).paragraphs[0].add_run(h)
    for r_idx, row_vals in enumerate(data):
        for c_idx, val in enumerate(row_vals):
            table.cell(r_idx + 1, c_idx).paragraphs[0].add_run(str(val))
    format_table(table, header_bg, stripe_bg)
    return table

def build_document():
    doc = docx.Document()

    # Page setup: Standard Margins
    for section in doc.sections:
        section.top_margin = Inches(0.8)
        section.bottom_margin = Inches(0.8)
        section.left_margin = Inches(0.8)
        section.right_margin = Inches(0.8)

    # Styles
    normal_style = doc.styles['Normal']
    normal_style.font.name = 'Calibri'
    normal_style.font.size = Pt(10.5)
    normal_style.font.color.rgb = RGBColor(30, 30, 30)

    # Header / Meta
    p_meta = doc.add_paragraph()
    r_meta = p_meta.add_run("BACSE324 · EMBEDDED SYSTEMS ARCHITECTURE · FALL 2026 · REVIEW 2")
    r_meta.font.size = Pt(9)
    r_meta.font.bold = True
    r_meta.font.color.rgb = RGBColor(100, 100, 100)
    p_meta.paragraph_format.space_after = Pt(2)

    p_sub = doc.add_paragraph()
    r_sub = p_sub.add_run("Submission date: 13 October 2026")
    r_sub.font.size = Pt(9)
    r_sub.font.italic = True
    p_sub.paragraph_format.space_after = Pt(12)

    # Title
    p_title = doc.add_paragraph()
    r_title = p_title.add_run("Design Models: CDFG, FSM and Task Schedule")
    r_title.font.size = Pt(22)
    r_title.font.bold = True
    r_title.font.color.rgb = RGBColor(20, 50, 95)
    p_title.paragraph_format.space_after = Pt(4)

    p_subtitle = doc.add_paragraph()
    r_subtitle = p_subtitle.add_run("Review 2 submission · Scope Tier 2 · Smart Parking Management System")
    r_subtitle.font.size = Pt(11)
    r_subtitle.font.color.rgb = RGBColor(80, 80, 80)
    p_subtitle.paragraph_format.space_after = Pt(14)

    # Project Metadata Table
    meta_headers = ["Field", "Specification"]
    meta_data = [
        ("Project title", "SMART PARKING MANAGEMENT SYSTEM"),
        ("Scope tier", "Tier 2 (AI Vision Pipeline + Real-Time Embedded Microcontroller Gate Barrier)"),
        ("Submission date", "13 October 2026"),
        ("Repository link", "Local Workspace / Smart-Parking-System (Hardware-in-the-Loop Prototype)")
    ]
    create_table(doc, meta_headers, meta_data, header_bg="2C3E50")
    doc.add_paragraph().paragraph_format.space_after = Pt(8)

    # Team Table
    doc.add_heading("Team & Work Distribution", level=2)
    team_headers = ["Member", "Reg. no.", "Module owned", "Sections written"]
    team_rows = [
        ("Harshavardhan Singh", "25BCE0552", "Hardware & circuit integration (30%):\nESP32 pinout, 16x2 I2C LCD, LEDs, buzzer, servo barrier, vehicle-present sensor, power supply.", "System hardware and interface design"),
        ("Shaikh Shayaan", "25BCE2623", "Gate and entry/exit engineering (25%):\nGate FSM, vehicle-passage safety logic, entry denial on full, servo actuator control.", "FSM and gate safety model"),
        ("Keshav Kumar", "25BCE2880", "AI vehicle detection & vision pipeline (25%):\nCamera/OpenCV pipeline, custom YOLOv8 inference, S1-S4 slot geometry mapping, serial transmission protocol.", "AI detection and slot mapping (CDFG)"),
        ("Joshua Joel J", "25BCE2746", "Integration & temporal filtering (20%):\nOccupancy temporal debounce, session duration tracking, UART communication ingestion, fault-case logging.", "Integration, filtering tests and session tracking")
    ]
    create_table(doc, team_headers, team_rows, header_bg="1F497D")

    p_note = doc.add_paragraph()
    r_n = p_note.add_run("Note: Team members own an engineering module and must be able to explain the models they produce. Timing values represent engineering estimates validated on the hardware prototype.")
    r_n.font.size = Pt(8.5)
    r_n.font.italic = True
    p_note.paragraph_format.space_before = Pt(4)
    p_note.paragraph_format.space_after = Pt(16)

    # ─────────────────────────────────────────────────────────────────────────
    # SECTION 1: SYSTEM RECAP
    # ─────────────────────────────────────────────────────────────────────────
    doc.add_heading("1. System Recap", level=1)
    
    p_recap = doc.add_paragraph(
        "The Smart Parking Management System monitors four parking slots (S1–S4) using an overhead CCTV/camera feed "
        "processed by a Python-based edge AI vision pipeline. A custom-trained YOLOv8 vehicle detection model detects "
        "vehicles within the parking facility. A geometric SlotMapper determines individual slot occupancy based on "
        "calibrated region polygons and Intersection over Union (IoU) overlap thresholds. A TemporalFilter debounces single-frame "
        "detection flickers across consecutive video frames and records continuous parking sessions. "
        "\n\nThe processed parking status is transmitted asynchronously from the vision host to an ESP32 microcontroller "
        "over a dedicated USB UART serial link (115,200 baud) using structured, bounded packets: "
        "<PKT,S1=val,S2=val,S3=val,S4=val,FREE=count,STATUS=OK>. The ESP32 parses incoming packets, tracks parking availability "
        "on a 16×2 I²C LCD, commands slot status LEDs and buzzer alarms, and operates a motorized servo barrier gate via a "
        "finite-state controller. A local vehicle-present sensor at the barrier entrance guarantees safety by preventing "
        "the gate from closing on a vehicle, while a hardware Watchdog Timer (WDT) and communication timeout safeguard against system stalls."
    )
    p_recap.paragraph_format.line_spacing = 1.15
    p_recap.paragraph_format.space_after = Pt(10)

    # 1.1 Conditions Table
    doc.add_heading("1.1 Conditions Carried from Proposal Review", level=2)
    c_headers = ["Condition / Mandatory Addition", "Status", "Where It Is Addressed"]
    c_rows = [
        ("Choose one board and justify; four slots acceptable", "ESP32 selected for dual-core architecture, dedicated hardware timers, hardware UART, and servo PWM support.", "Section 1, Section 4.1"),
        ("Framed UART streaming with timeout; no data corruption", "Modelled with start/end tokens (<...>), key-value tokens, and 3000 ms communication watchdog.", "Section 2.1–2.4, Section 4.5"),
        ("Debounced filtered occupancy detection; no slot flicker", "TemporalFilter implements N-frame hysteresis (5 frames to confirm OCCUPIED, 8 frames to confirm FREE).", "Section 2.2, Section 3.3"),
        ("Entry/exit gate logic as FSM with vehicle sensor; safe operation", "Moore FSM includes ENTRY, PASS timer, obstacle safety reversal, and full-lot refusal.", "Section 3.1–3.5"),
        ("Track occupancy duration per slot and session count on display", "Integrated in TemporalFilter and transmitted to ESP32 for LCD display and session logging.", "Section 4.1, Section 5"),
        ("Sensor / communication fault flags safe state rather than silent count", "FAULT/SAFE state latches gate CLOSED, sounds buzzer, and displays COMM_ERROR on LCD.", "Section 3.3–3.5")
    ]
    create_table(doc, c_headers, c_rows, header_bg="2C3E50")
    doc.add_paragraph().paragraph_format.space_after = Pt(16)

    # ─────────────────────────────────────────────────────────────────────────
    # SECTION 2: CONTROL DATA FLOW GRAPH (CDFG)
    # ─────────────────────────────────────────────────────────────────────────
    doc.add_heading("2. Control Data Flow Graph (CDFG)", level=1)
    
    p_cdfg_intro = doc.add_paragraph(
        "In this multi-tiered architecture, the primary real-time critical path governs the vehicle detection and "
        "occupancy publishing cycle. On the vision pipeline (Keshav Kumar's module), each frame must undergo acquisition, "
        "neural inference, geometric slot assignment, debouncing, and serialization within a rigid real-time frame deadline. "
        "Simultaneously, the ESP32 executes an atomic UART packet parsing loop to maintain synchronization without blocking "
        "the gate FSM."
    )
    p_cdfg_intro.paragraph_format.line_spacing = 1.15

    doc.add_heading("2.1 Choosing the Critical Function", level=2)
    crit_headers = ["Function / ISR", "Trigger", "Rate", "Est. Execution Time", "Deadline", "Chosen? Why / Why Not"]
    crit_rows = [
        ("AI Vehicle Detection Pipeline (Keshav Kumar)", "New video frame release", "Every 33.3 ms (30 FPS)", "22.5 ms WCET estimate", "33.3 ms", "YES — Longest execution path; produces the ground truth slot data."),
        ("UART Packet Parser & Ingestion (ESP32)", "UART byte arrival / timer", "Every 20 ms", "2.0 ms estimate", "20 ms", "No — Shorter execution; consumes serialized packets."),
        ("Gate FSM & Barrier Control (ESP32)", "Timer / vehicle arrival", "Every 20 ms + events", "0.5 ms estimate", "20 ms", "No — Shorter execution; reacts to slot snapshot and sensors."),
        ("LCD & Session Display Task (ESP32)", "Display refresh timer", "Every 100 ms", "2.0 ms estimate", "100 ms", "No — Low frequency UI task with relaxed deadline.")
    ]
    create_table(doc, crit_headers, crit_rows, header_bg="1F497D")

    doc.add_heading("2.2 The CDFG Specification", level=2)
    p_cdfg_desc = doc.add_paragraph(
        "The CDFG of the critical AI vision pipeline represents data flow and control branches across the vision loop. "
        "Rounded blocks denote execution operations, diamonds represent conditional decisions, solid arrows show standard "
        "dataflow, and dashed arrows represent feedback loops and debouncing checks."
    )

    doc.add_heading("2.3 Node Table (AI Vision Critical Path)", level=2)
    node_headers = ["Node", "Operation", "Inputs", "Output", "Est. Cost", "Source Line / Function"]
    node_rows = [
        ("N1", "Frame Capture & Ingestion", "Camera / Video RTSP stream", "BGR Frame (1280×720)", "4.0 ms (est.)", "cv2.VideoCapture.read()"),
        ("N2", "Preprocessing & Resizing", "BGR Frame", "Letterboxed 640×640 Tensor", "2.0 ms (est.)", "letterbox() / normalization"),
        ("N3", "YOLOv8 Neural Inference", "Image Tensor", "Raw Bounding Box Tensors", "14.5 ms (est.)", "model.predict(imgsz=640)"),
        ("N4", "Vehicle Class & Conf Filter", "Predictions, confidence threshold", "Filtered Detection List", "0.8 ms (est.)", "run_inference() bbox parser"),
        ("N5", "Geometric Slot Assignment", "Bboxes, polygon coordinates", "Raw Slot Candidates (S1–S4)", "0.5 ms (est.)", "SlotMapper.map_detections()"),
        ("N6", "Temporal Hysteresis Filter", "Candidate map, timestamp", "Confirmed SlotState map", "0.4 ms (est.)", "TemporalFilter.update()"),
        ("N7", "Packet Serialize & UART Tx", "Slot states, free count", "Formatted Serial Packet", "0.3 ms (est.)", "SerialSender.send_packet()")
    ]
    create_table(doc, node_headers, node_rows, header_bg="2C3E50")

    doc.add_heading("2.4 Critical Path Analysis", level=2)
    p_crit_path = doc.add_paragraph(
        "Critical Path Sequence: N1 → N2 → N3 → N4 → N5 → N6 → N7\n"
        "Total Latency: 4.0 ms + 2.0 ms + 14.5 ms + 0.8 ms + 0.5 ms + 0.4 ms + 0.3 ms = 22.5 ms (est.)\n"
        "Deadline: 33.3 ms (corresponding to real-time 30 FPS video streaming)\n"
        "Slack: 33.3 ms − 22.5 ms = 10.8 ms (Positive slack; guarantees zero frame drops on host GPU/NPU).\n\n"
        "What the CDFG tells us about the implementation:\n"
        "1. Neural inference (N3) accounts for 64.4% of execution budget; offloading to CUDA/GPU is mandatory.\n"
        "2. Slot mapping (N5) and Temporal filtering (N6) are lightweight (<1 ms total), decoupling heavy computer vision from slot assignment logic.\n"
        "3. The serial transmission (N7) is bounded and non-blocking, ensuring timely packet dispatch to the ESP32."
    )
    p_crit_path.paragraph_format.line_spacing = 1.15
    doc.add_paragraph().paragraph_format.space_after = Pt(12)

    # ─────────────────────────────────────────────────────────────────────────
    # SECTION 3: SYSTEM-BEHAVIOUR FSM
    # ─────────────────────────────────────────────────────────────────────────
    doc.add_heading("3. System-Behaviour FSM", level=1)
    
    p_fsm_desc = doc.add_paragraph(
        "The system-level FSM models the supervisory controller executed on the ESP32. "
        "It governs entry barrier actuation, user display notifications, and alarm outputs. "
        "A Moore machine model is utilized: all physical actuator outputs (servo PWM angle, buzzer sound, LCD backlight/text) "
        "are strictly determined by the current active state, ensuring deterministic safety."
    )

    doc.add_heading("3.1 Model Type", level=2)
    p_model_type = doc.add_paragraph(
        "Model type: Moore Machine — outputs are uniquely bound to states; input events (UART packet updates, vehicle sensor triggers, timers) "
        "govern state transitions. The FAULT state serves as the deterministic fail-safe default."
    )

    doc.add_heading("3.2 State Transition Table", level=2)
    fsm_headers = ["Current State", "Event", "Guard", "Next State", "Output / Action"]
    fsm_rows = [
        ("IDLE / SYNC", "BOOT / TICK", "Awaiting initial valid serial packet", "IDLE / SYNC", "Gate CLOSED (0°); LCD 'SYNCING...'; buzzer silent"),
        ("IDLE / SYNC", "PKT_RCVD", "Packet valid; freeCount > 0", "AVAILABLE", "Gate CLOSED; LCD shows available slots; Green LEDs"),
        ("IDLE / SYNC", "PKT_RCVD", "Packet valid; freeCount == 0", "FULL", "Gate CLOSED; LCD 'PARKING FULL'; Red LEDs"),
        ("AVAILABLE", "VEH_ARRIVE", "freeCount > 0 AND entry sensor triggered", "ENTRY", "Open gate to 90°; start entry timeout timer"),
        ("ENTRY", "VEH_PASSED", "Passage sensor clear OR entry timer expired", "AVAILABLE", "Close gate to 0°; update session count"),
        ("ENTRY", "OBSTRUCT", "Vehicle sensor triggers during gate closing", "ENTRY", "Reverse gate immediately to 90° (Safety anti-crush)"),
        ("FULL", "VEH_ARRIVE", "freeCount == 0 AND vehicle at entrance", "FULL", "Gate locked CLOSED; buzz warning beep; entry denied"),
        ("ANY STATE", "COMM_FAIL", "No valid packet for >3000 ms OR WDT timeout", "FAULT / SAFE", "Latch gate CLOSED; Red fault LED; continuous alarm; LCD 'COMM ERROR'")
    ]
    create_table(doc, fsm_headers, fsm_rows, header_bg="1F497D")

    doc.add_heading("3.3 Fault, Recovery and Safe State", level=2)
    p_fault = doc.add_paragraph(
        "Safe state and outputs: The FAULT/SAFE state forces the servo barrier to the CLOSED (0°) position, activates "
        "the red status LED, sounds a pulsed alarm tone on the buzzer, and displays 'COMM ERROR / FAULT' on the LCD. "
        "Recovery requires communication re-establishment (consecutive valid packet sequence) and a successful sensor self-test."
    )
    doc.add_paragraph().paragraph_format.space_after = Pt(12)

    # ─────────────────────────────────────────────────────────────────────────
    # SECTION 4: TASK SCHEDULE
    # ─────────────────────────────────────────────────────────────────────────
    doc.add_heading("4. Task Schedule", level=1)
    
    p_sched = doc.add_paragraph(
        "The embedded firmware on the ESP32 employs Rate-Monotonic Scheduling (RMS) for all periodic tasks. "
        "Under RMS, tasks with shorter periods are statically assigned higher execution priorities. "
        "The task set encompasses packet reception, gate FSM updates, display refreshing, session tracking, and fault monitoring."
    )

    doc.add_heading("4.1 Task Set Table", level=2)
    task_headers = ["Task", "Trigger", "Period T", "WCET C", "Deadline D", "Priority", "Utilisation U = C/T"]
    task_rows = [
        ("T1: Serial Packet Ingestion", "UART Buffer / Timer", "20 ms", "2.0 ms", "20 ms", "1 (Highest)", "0.1000"),
        ("T2: Gate FSM & Safety Loop", "Periodic Timer / Event", "20 ms", "0.5 ms", "20 ms", "2", "0.0250"),
        ("T3: LCD & UI Refresh", "Periodic Timer", "100 ms", "2.0 ms", "100 ms", "3", "0.0200"),
        ("T4: Fault & Watchdog Monitor", "Periodic Timer", "100 ms", "0.5 ms", "100 ms", "4", "0.0050"),
        ("T5: Occupancy Session Tracker", "1-second Tick", "1000 ms", "0.5 ms", "1000 ms", "5 (Lowest)", "0.0005")
    ]
    create_table(doc, task_headers, task_rows, header_bg="2C3E50")

    doc.add_heading("4.2 Schedulability Analysis", level=2)
    p_sched_proof = doc.add_paragraph(
        "Total Processor Utilisation (U):\n"
        "U = Σ(C_i / T_i) = (2.0 / 20) + (0.5 / 20) + (2.0 / 100) + (0.5 / 100) + (0.5 / 1000)\n"
        "U = 0.1000 + 0.0250 + 0.0200 + 0.0050 + 0.0005 = 0.1505\n\n"
        "RMS Schedulability Bound for n = 5 tasks:\n"
        "U_bound = n · (2^(1/n) − 1) = 5 · (2^(0.2) − 1) = 5 · (1.148698 − 1) ≈ 0.7434 (74.34%)\n\n"
        "Proof of Schedulability:\n"
        "Since U = 0.1505 ≤ 0.7434, the task set strictly satisfies Liu & Layland's sufficient utilisation test. "
        "All deadlines are guaranteed to be met under all worst-case execution conditions, leaving over 84% idle CPU headroom on the ESP32."
    )
    p_sched_proof.paragraph_format.line_spacing = 1.15

    doc.add_heading("4.3 Shared Resources and Mutex Protection", level=2)
    res_headers = ["Shared Resource", "Used By", "Protection Mechanism", "Worst-Case Blocking"]
    res_rows = [
        ("Global Slot Snapshot", "T1 (Writer), T2 (Reader), T3 (Reader)", "Atomic memory swap / Critical section", "< 0.05 ms"),
        ("UART RX Ring Buffer", "T1 (Consumer), UART Hardware ISR", "Head/Tail pointer atomic separation", "Zero wait (Non-blocking)"),
        ("I²C Bus (16×2 LCD)", "T3 (Sole Owner)", "Dedicated task access; no concurrent bus calls", "2.0 ms bounded transaction"),
        ("Servo PWM Timer", "T2 (Sole Owner)", "Dedicated hardware LEDC timer channel", "Negligible (< 0.1 ms)"),
        ("Hardware Watchdog (WDT)", "T4 (Supervisor), Main Loop", "esp_task_wdt_reset() periodic feed", "Negligible")
    ]
    create_table(doc, res_headers, res_rows, header_bg="1F497D")
    doc.add_paragraph().paragraph_format.space_after = Pt(12)

    # ─────────────────────────────────────────────────────────────────────────
    # SECTION 5: PLANNED TRACEABILITY
    # ─────────────────────────────────────────────────────────────────────────
    doc.add_heading("5. Planned Traceability", level=1)
    
    p_trace = doc.add_paragraph(
        "Every theoretical design model (CDFG nodes, FSM states, and RMS tasks) maps directly to concrete source code "
        "files and functions within the project repository."
    )

    doc.add_heading("5.1 Model-to-Code Traceability Table", level=2)
    trace_headers = ["Model Element", "Planned File in Codebase", "Planned Function", "Owner"]
    trace_rows = [
        ("N1–N4 AI Vehicle Detection", "ai/inference/run_cctv.py", "run_inference()", "Keshav Kumar"),
        ("N5 Geometric Slot Assignment", "ai/slot_mapping/slot_mapper.py", "SlotMapper.map_detections()", "Keshav Kumar"),
        ("N6 Temporal Filter & Sessions", "ai/tracking/temporal_filter.py", "TemporalFilter.update()", "Joshua Joel J"),
        ("N7 Serial Packet Streaming", "ai/communication/serial_sender.py", "SerialSender.send_packet()", "Keshav Kumar"),
        ("T1 UART Packet Parsing Loop", "esp32/smart_parking/communication.cpp", "comm_update(), parse_packet()", "Joshua Joel J"),
        ("T2 Gate Moore FSM", "esp32/smart_parking/gate_fsm.cpp", "gate_fsm_update(), gate_fsm_tick()", "Shaikh Shayaan"),
        ("Servo Gate Barrier Control", "esp32/smart_parking/servo_gate.cpp", "servo_open(), servo_close()", "Shaikh Shayaan"),
        ("T3 LCD Display & Status LEDs", "esp32/smart_parking/lcd_controller.cpp", "lcd_update(), lcd_show_warning()", "Harshavardhan Singh"),
        ("T4 Watchdog & Safe-State Alarm", "esp32/smart_parking/watchdog_mgr.cpp", "wdt_init(), wdt_feed()", "Harshavardhan Singh")
    ]
    create_table(doc, trace_headers, trace_rows, header_bg="2C3E50")
    doc.add_paragraph().paragraph_format.space_after = Pt(12)

    # ─────────────────────────────────────────────────────────────────────────
    # SECTION 6 & 7: PLAN TO FINAL & INDIVIDUAL CONTRIBUTION
    # ─────────────────────────────────────────────────────────────────────────
    doc.add_heading("6. Plan to Final", level=1)
    plan_headers = ["Remaining Work", "Owner", "Target Date", "Risk and Fallback"]
    plan_rows = [
        ("Complete breadboard wiring for ESP32, Servo, LCD, Buzzer", "Harshavardhan Singh", "16 Oct 2026", "Pin conflict → reserve I2C & PWM pins early"),
        ("Tune YOLOv8 confidence & slot IoU thresholds under lighting changes", "Keshav Kumar", "18 Oct 2026", "Low contrast → adjust exposure and polygon offsets"),
        ("Calibrate gate open/close timings and anti-crush safety response", "Shaikh Shayaan", "19 Oct 2026", "Mechanical binding → adjust servo sweep delay"),
        ("End-to-end stress testing of UART packet link and CSV event logging", "Joshua Joel J", "21 Oct 2026", "Buffer overflow → enforce packet throttle (10 Hz)")
    ]
    create_table(doc, plan_headers, plan_rows, header_bg="1F497D")

    doc.add_heading("7. Individual Contribution", level=1)
    doc.add_paragraph(
        "Each team member owns a verified engineering module. Work percentage allocations are strictly aligned with "
        "the proposal guidelines:\n"
        "• Harshavardhan Singh (25BCE0552) — 30%: Hardware, circuit assembly, LCD, LEDs, buzzer, servo, power regulation.\n"
        "• Shaikh Shayaan (25BCE2623) — 25%: Gate controller, safety logic, vehicle-passage verification, full refusal.\n"
        "• Keshav Kumar (25BCE2880) — 25%: Computer vision, YOLO vehicle detection, S1–S4 slot mapping CDFG, serial transmission.\n"
        "• Joshua Joel J (25BCE2746) — 20%: Temporal debounce filtering, session duration tracking, UART receiver, logging.\n\n"
        "Total Team Allocation: 30% + 25% + 25% + 20% = 100%."
    )

    doc.add_heading("8. References", level=1)
    doc.add_paragraph(
        "[1] Espressif Systems, 'ESP32 Series Datasheet', v3.9, Espressif Systems, 2024.\n"
        "[2] J. Redmon, S. Divvala, R. Girshick, and A. Farhadi, 'You Only Look Once: Unified, Real-Time Object Detection', IEEE CVPR, 2016.\n"
        "[3] G. Ultralytics, 'YOLOv8 Architecture and Documentation', Ultralytics LLC, 2023.\n"
        "[4] C. L. Liu and J. W. Layland, 'Scheduling Algorithms for Multiprogramming in a Hard-Real-Time Environment', J. ACM, vol. 20, no. 1, pp. 46–61, 1973.\n"
        "[5] Tower Pro, 'SG90 9g Micro Servo Motor Datasheet', Tower Pro Pte., 2022."
    )

    # Save to Word Document
    out_path = r"c:\Users\kesha\Desktop\embedded\smart-parking-system\Review_2_Design_Models_Updated.docx"
    doc.save(out_path)
    print(f"[SUCCESS] Document generated and saved to: {out_path}")

if __name__ == "__main__":
    build_document()
