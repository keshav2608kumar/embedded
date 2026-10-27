"""
Smart Parking Management System
Serial Communication — Python → ESP32

STATUS: IMPLEMENTED (serial code ready; hardware test = HARDWARE TEST REQUIRED)

Sends parking status packets to the ESP32 over USB serial.
Detects connection loss and handles errors gracefully.

Configuration:
    com_port, baud_rate, timeout_sec read from system_config.json
    Update 'port' in config/system_config.json before running.

Design:
    This module is the only place where serial I/O happens.
    The rest of the system calls send_status() and checks is_connected().
    Swapping to Wi-Fi later means replacing only this module.
"""

import logging
import threading
import time
from typing import Optional

logger = logging.getLogger("smart_parking")


class CommunicationLostError(Exception):
    """Raised when serial communication to ESP32 is lost."""
    pass


class SerialSender:
    """
    Manages USB serial communication from Python PC to ESP32.
    Supports bidirectional communication: packet dispatch and live telemetry ingestion.
    """

    def __init__(
        self,
        port: str = "COM3",
        baud_rate: int = 115200,
        timeout_sec: float = 2.0,
        comm_lost_timeout_sec: float = 10.0,
    ) -> None:
        self._port = port
        self._baud = baud_rate
        self._timeout = timeout_sec
        self._comm_lost_timeout = comm_lost_timeout_sec
        self._serial = None
        self._lock = threading.Lock()
        self._last_successful_send: Optional[float] = None
        self._connected = False
        self._simulated = False       # set True in simulation mode
        self._reader_thread = None
        self._running = False
        self._telemetry = {
            "free": 4,
            "rec": "S1",
            "gate": "GATE_CLOSED",
            "adm": "IDLE",
            "sensor": "CLEAR",
            "timer": 0.0,
            "comm": "OK",
            "l1": "PARKING: 4 FREE ",
            "l2": "GATE: CLOSED    ",
            "last_rx": 0.0,
        }

    # ──────────────────────────────────────────────────────────────────────── #

    def connect(self, simulate: bool = False) -> bool:
        """
        Open serial connection to ESP32.

        Args:
            simulate: If True, run in simulation mode (no hardware needed).

        Returns:
            True if connected (or simulated), False on failure.
        """
        if simulate:
            self._simulated = True
            self._connected = True
            logger.info("[SIMULATION] SerialSender in simulation mode — no hardware")
            return True

        try:
            import serial as pyserial
        except ImportError:
            logger.error(
                "pyserial not installed. Run: pip install pyserial\n"
                "Or use simulation mode: python main.py --mode simulation"
            )
            return False

        try:
            with self._lock:
                self._serial = pyserial.Serial(
                    port=self._port,
                    baudrate=self._baud,
                    timeout=self._timeout,
                )
                time.sleep(2.0)   # allow ESP32 to reset after serial open
                self._connected = True
                self._running = True
                self._last_successful_send = time.time()

            # Start background reader thread for telemetry and LCD synchronization
            self._reader_thread = threading.Thread(target=self._reader_loop, daemon=True)
            self._reader_thread.start()

            logger.info("Serial connected: %s @ %d baud", self._port, self._baud)
            return True

        except Exception as e:
            logger.error(
                "Serial connection failed: %s\n"
                "Check:\n"
                "  1. ESP32 is connected via USB\n"
                "  2. COM port is correct in config/system_config.json\n"
                "  3. No other program is using the port\n"
                "  Error: %s",
                self._port, e
            )
            self._connected = False
            return False

    def _reader_loop(self):
        """Continuously reads incoming telemetry and LCD updates from ESP32."""
        while self._running and self._connected and self._serial and self._serial.is_open:
            try:
                line = self._serial.readline().decode("utf-8", errors="ignore").strip()
                if line.startswith("[STATUS]"):
                    self._parse_telemetry(line)
            except Exception:
                time.sleep(0.05)

    def _parse_telemetry(self, line: str):
        try:
            telemetry = self._telemetry.copy()
            for part in ["Free:", "Rec:", "Gate:", "Adm:", "Sensor:", "Timer:", "Comm:"]:
                if part in line:
                    val = line.split(part)[1].split()[0]
                    key = part[:-1].lower()
                    if key == "free":
                        telemetry["free"] = int(val)
                    elif key == "timer":
                        try:
                            telemetry["timer"] = float(val)
                        except ValueError:
                            telemetry["timer"] = 0.0
                    else:
                        telemetry[key] = val

            if "L1:" in line:
                after_l1 = line.split("L1:")[1]
                if " L2:" in after_l1:
                    l1_val, l2_val = after_l1.split(" L2:", 1)
                    telemetry["l1"] = l1_val[:16]
                    telemetry["l2"] = l2_val[:16]
                else:
                    telemetry["l1"] = after_l1[:16]

            telemetry["last_rx"] = time.time()
            self._telemetry = telemetry
        except Exception:
            pass

    def get_telemetry(self) -> dict:
        """Returns the latest live telemetry from the ESP32 hardware."""
        return self._telemetry.copy()

    def send_command(self, action: str) -> bool:
        """Send a control command to the ESP32, e.g. TRIGGER_VEHICLE, SWEEP, OPEN, CLOSE."""
        return self.send(f"<CMD,ACTION={action}>")

    # ──────────────────────────────────────────────────────────────────────── #

    def send(self, packet: str) -> bool:
        """
        Send one packet string to ESP32.

        Args:
            packet: Encoded packet string (from packet_codec.encode())

        Returns:
            True on success, False on failure.
        """
        if self._simulated:
            logger.debug("[SIM] Would send: %s", packet)
            print(f"  [SERIAL → ESP32] {packet}")
            self._last_successful_send = time.time()
            return True

        if not self._connected or self._serial is None:
            logger.warning("Serial not connected — packet not sent: %s", packet)
            return False

        try:
            with self._lock:
                raw = (packet + "\n").encode("ascii")
                self._serial.write(raw)
                self._serial.flush()
                self._last_successful_send = time.time()

            logger.debug("Sent: %s", packet)
            return True

        except Exception as e:
            logger.error("Serial send failed: %s", e)
            self._connected = False
            return False

    # ──────────────────────────────────────────────────────────────────────── #

    def is_connected(self) -> bool:
        """Return True if serial link is active."""
        if self._simulated:
            return True

        if not self._connected:
            return False

        # Check for comm-lost timeout
        if self._last_successful_send is not None:
            elapsed = time.time() - self._last_successful_send
            if elapsed > self._comm_lost_timeout:
                logger.error(
                    "COMMUNICATION LOST — no successful send in %.1fs", elapsed
                )
                self._connected = False
                return False

        return self._connected

    def comm_status(self) -> str:
        """Return 'COMM_OK' or 'COMM_LOST' for logging and display."""
        return "COMM_OK" if self.is_connected() else "COMM_LOST"

    # ──────────────────────────────────────────────────────────────────────── #

    def close(self) -> None:
        """Close the serial port gracefully."""
        self._running = False
        with self._lock:
            if self._serial and not self._simulated:
                try:
                    self._serial.close()
                    logger.info("Serial port closed: %s", self._port)
                except Exception:
                    pass
            self._connected = False

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
