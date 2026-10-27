# Hardware Wiring & Setup

The hardware component is built around the ESP32 microcontroller. 

## Component Pinout (config.h)

| Component | Pin / Interface | Description |
|-----------|-----------------|-------------|
| **16x2 LCD** | I2C (SDA: 21, SCL: 22) | Address `0x27` or `0x3F`. Uses PCF8574 backpack. |
| **Servo Motor** | GPIO 18 (PWM) | Controls the entry/exit gate. |
| **Buzzer** | GPIO 19 | Active/Passive buzzer for alerts. |
| **Vehicle Sensor** | GPIO 23 (INPUT_PULLUP) | IR obstacle or ultrasonic. Detects if vehicle is physically under the gate. |
| **PC Connection** | USB Serial | Used for both power (initially) and communication (115200 baud). |

## Safety Considerations

1. **Power Supply:** The Servo motor draws significant current. Do NOT power a standard SG90/MG996R directly from the ESP32 3.3V pin. Use a dedicated 5V rail or external power supply with a common ground.
2. **Logic Levels:** The ESP32 is 3.3V logic. If your vehicle sensor outputs 5V logic on detection, you MUST use a voltage divider or level shifter before connecting it to GPIO 23 to prevent damaging the ESP32.
3. **Failsafe Position:** The servo is initialized to `GATE_CLOSED_ANGLE` during `setup()`. This ensures that in the event of a power loss and reboot, the gate defaults to a secure state.
