import platform
import serial
import serial.tools.list_ports


# ===== Auto-detect Arduino Serial Port =====
def detect_arduino_port():
    for port in serial.tools.list_ports.comports():
        dev = port.device
        if platform.system() == 'Linux' and 'ttyACM' in dev:
            return dev
        if platform.system() == 'Darwin' and ('usbmodem' in dev or 'usbserial' in dev):
            return dev
        if platform.system() == 'Windows' and 'COM' in dev:
            return dev
    return None


# Read distance from Arduino (returns float or None)
def read_distance(arduino):
    if not arduino or arduino.in_waiting == 0:
        return None
    try:
        val = arduino.readline().decode('utf-8').strip()
        return float(val)
    except (UnicodeDecodeError, ValueError):
        return None

import time

def connect_to_arduino(arduino_port, baud_rate=115200, timeout=1):
    try:
        arduino = serial.Serial(arduino_port, baud_rate, timeout=timeout)
        time.sleep(2)  # wait for Arduino to reset
        print(f"[Arduino Connector]Connected to Arduino on {arduino_port} at {baud_rate} baud.")
        return arduino
    except serial.SerialException as e:
        print(f"[Arduino Connector] Failed to connect to Arduino on {arduino_port}: {e}")
        return None
