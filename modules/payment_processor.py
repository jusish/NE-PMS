# modules/payment_processor.py
from math import ceil
import serial
import time
from datetime import datetime
from modules.database_utils import DatabaseManager


class PaymentProcessor:
    def __init__(self, rate_per_minute=9):
        self.rate_per_minute = rate_per_minute
        self.db = DatabaseManager()

    def calculate_parking_fee(self, entry_time_str):
        """Calculate parking fee based on duration rounded up to nearest hour"""
        entry_time = datetime.strptime(entry_time_str, '%Y-%m-%d %H:%M:%S')
        duration_seconds = (datetime.now() - entry_time).total_seconds()
        duration_hours = ceil(duration_seconds / 3600)  # Always round up
        return duration_hours * 500  # 500 per hour

    def parse_arduino_data(self, line):
        """Parse plate and balance from Arduino data"""
        try:
            parts = line.strip().split(',')
            if len(parts) != 2:
                return None, None

            plate = parts[0].strip()
            balance_str = ''.join(c for c in parts[1] if c.isdigit())

            if balance_str:
                return plate, int(balance_str)
            return None, None
        except ValueError:
            return None, None

    def process_payment(self, plate, balance, serial_conn):
        """Process payment for a parking session"""
        record = self.db.get_unpaid_record(plate)
        if not record:
            print(f"[PAYMENT] No unpaid record found for {plate}")
            return False

        amount_due = self.calculate_parking_fee(record['entry_time'])
        self.db.update_exit_and_payment(plate, amount_due)

        if balance < amount_due:
            print(f"[PAYMENT] Insufficient balance. Need: {amount_due}, Have: {balance}")
            serial_conn.write(b'I\n')  # Insufficient funds
            return False

        new_balance = balance - amount_due

        # Wait for Arduino ready signal
        if self._wait_for_arduino_ready(serial_conn):
            serial_conn.write(f"{new_balance}\r\n".encode())
            print(f"[PAYMENT] Sent new balance: {new_balance}")

            if self._wait_for_confirmation(serial_conn):
                self.db.mark_as_paid(plate)
                print(f"[PAYMENT] Payment successful for {plate}")
                return True

        return False

    def _wait_for_arduino_ready(self, serial_conn, timeout=5):
        """Wait for Arduino READY signal"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            if serial_conn.in_waiting:
                response = serial_conn.readline().decode().strip()
                if response == "READY":
                    return True
            time.sleep(0.1)
        return False

    def _wait_for_confirmation(self, serial_conn, timeout=10):
        """Wait for Arduino confirmation"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            if serial_conn.in_waiting:
                response = serial_conn.readline().decode().strip()
                if "DONE" in response:
                    return True
            time.sleep(0.1)
        return False

