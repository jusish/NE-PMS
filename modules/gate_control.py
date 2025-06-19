# modules/gate_control.py
import serial
import serial.tools.list_ports
import platform
import time


class GateController:
    def __init__(self, baud_rate=9600, timeout=1):
        self.arduino = None
        self.baud_rate = baud_rate
        self.timeout = timeout
        self.connect()

    def detect_arduino_port(self):
        """Auto-detect Arduino serial port"""
        for port in serial.tools.list_ports.comports():
            dev = port.device
            if platform.system() == 'Linux' and 'ttyACM' in dev:
                return dev
            if platform.system() == 'Darwin' and ('usbmodem' in dev or 'usbserial' in dev):
                return dev
            if platform.system() == 'Windows' and 'COM' in dev:
                return dev
        return None

    def connect(self):
        """Connect to Arduino"""
        port = self.detect_arduino_port()
        if not port:
            print("[ERROR] Arduino not detected.")
            return False

        try:
            self.arduino = serial.Serial(port, self.baud_rate, timeout=self.timeout)
            time.sleep(2)  # Wait for Arduino to reset
            print(f"[GATE] Connected to Arduino on {port}")
            return True
        except serial.SerialException as e:
            print(f"[ERROR] Failed to connect to Arduino: {e}")
            return False

    def read_distance(self):
        """Read distance from ultrasonic sensor"""
        if not self.arduino or self.arduino.in_waiting == 0:
            return None
        try:
            val = self.arduino.readline().decode('utf-8').strip()
            return float(val)
        except (UnicodeDecodeError, ValueError):
            return None

    def open_gate(self, duration=15):
        """Open gate for specified duration"""
        if self.arduino:
            self.arduino.write(b'1')
            print(f"[GATE] Opening gate for {duration} seconds")
            time.sleep(duration)
            self.arduino.write(b'0')
            print("[GATE] Gate closed")
            return True
        return False

    def trigger_alert(self):
        """Trigger buzzer/alert"""
        if self.arduino:
            self.arduino.write(b'2')
            print("[GATE] Alert triggered")
            return True
        return False

    def close(self):
        """Close Arduino connection"""
        if self.arduino:
            self.arduino.close()
            print("[GATE] Connection closed")
