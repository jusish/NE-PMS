# process_payment.py
import sys
import serial
import time
from car_entry import CarEntrySystem
from car_exit import CarExitSystem
from modules.gate_control import GateController
from modules.payment_processor import PaymentProcessor
from modules.logger import ParkingLogger


class PaymentSystem:
    def __init__(self):
        self.gate_controller = GateController()
        self.payment_processor = PaymentProcessor()
        self.logger = ParkingLogger()

    def run(self):
        """Main payment processing loop"""
        if not self.gate_controller.arduino:
            self.logger.log_error("Arduino not connected for payment system")
            return

        self.logger.log_info("Payment system started")
        print("[PAYMENT SYSTEM] Listening for payment requests...")

        try:
            # Flush any previous data
            self.gate_controller.arduino.reset_input_buffer()

            while True:
                if self.gate_controller.arduino.in_waiting:
                    line = self.gate_controller.arduino.readline().decode().strip()
                    print(f"[SERIAL] Received: {line}")

                    plate, balance = self.payment_processor.parse_arduino_data(line)
                    if plate and balance is not None:
                        success = self.payment_processor.process_payment(
                            plate, balance, self.gate_controller.arduino
                        )
                        self.logger.log_payment(plate, balance, success)

                time.sleep(0.1)  # Small delay to prevent CPU spinning

        except KeyboardInterrupt:
            self.logger.log_info("Payment system stopped by user")
        except Exception as e:
            self.logger.log_error(f"Payment system error: {e}")
        finally:
            self.gate_controller.close()


mode = sys.argv[1].lower()

if mode == 'entry':
    system = CarEntrySystem()
    system.run()
elif mode == 'exit':
    system = CarExitSystem()
    system.run()
elif mode == 'payment':
    system = PaymentSystem()
    system.run()
else:
    print("Invalid mode. Use: entry, exit, or payment")