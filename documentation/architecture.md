# System Architecture

## High-Level Overview

The Smart Parking Management System is an end-to-end IoT solution that bridges Computer Vision (CV) with Embedded Systems. It is split into two primary domains:

1. **AI & Vision Pipeline (Python / PC-based)**
2. **Embedded Controller (ESP32 / C++)**

These two domains communicate asynchronously over a USB serial connection, passing highly compressed state packets.

## Data Flow Diagram

```mermaid
flowchart TD
    subgraph AI Pipeline [Python / PC]
        Cam[Camera / Video Source] --> OpenCV[OpenCV Frame Capture]
        OpenCV --> YOLO[YOLOv8 Inference]
        YOLO --> BBox[Detected Vehicles Bounding Boxes]
        BBox --> SlotMap[SlotMapper (Geometry Test)]
        SlotMap --> TempFilt[Temporal Filter (Debouncing)]
        TempFilt --> SerialSender[Serial Protocol Encoder]
    end

    subgraph Communication [Serial Link]
        SerialSender -- "<PKT,S1=1,S2=0,S3=1,S4=0,FREE=2,STATUS=OK>" --> ESP32Rx[ESP32 Serial Receiver]
    end

    subgraph Embedded System [ESP32 Firmware]
        ESP32Rx --> Parser[Packet Parser]
        Parser --> GlobalState[Global Parking Status]
        GlobalState --> LCD[16x2 I2C LCD]
        GlobalState --> FSM[Gate Finite State Machine]
        FSM --> Servo[Gate Servo Motor]
        FSM --> Buzzer[Buzzer Alarms]
        Sensor[Vehicle-Present Sensor] --> FSM
        WDT[Watchdog Timer] -.-> ESP32Rx
    end
```

## Core Design Principles

1. **Separation of Concerns:** 
   The AI model does *not* know about parking slots. It only knows what a "vehicle" looks like. The assignment of a vehicle to a slot (S1-S4) is purely geometric and handled by the `SlotMapper`.
2. **Debouncing via Temporal Filtering:**
   Computer vision models flicker. The `TemporalFilter` absorbs this noise, ensuring the embedded system only reacts to confirmed, stable occupancy changes.
3. **Decoupled Hardware FSM:**
   The gate FSM runs autonomously on the ESP32. Even if the AI crashes or communication is lost, the gate will safely complete its current motion and will not close on a vehicle (thanks to the local vehicle-present sensor).
4. **Fault Tolerance:**
   - **AI Side:** Fallbacks to pre-trained COCO models if the custom model is missing.
   - **Comm Side:** Detects `COMM_LOST` and holds states securely.
   - **ESP32 Side:** Hardware Watchdog Timer (WDT) triggers a full reboot to a safe state if the main loop hangs.
