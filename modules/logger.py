# modules/logger.py
import logging
import os
from datetime import datetime


class ParkingLogger:
    def __init__(self, log_dir='logs'):
        os.makedirs(log_dir, exist_ok=True)

        # Configure logging
        log_filename = os.path.join(log_dir, f'parking_{datetime.now().strftime("%Y%m%d")}.log')

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_filename),
                logging.StreamHandler()
            ]
        )

        self.logger = logging.getLogger('ParkingSystem')

    def log_entry(self, plate, entry_id):
        """Log vehicle entry"""
        self.logger.info(f"ENTRY - Plate: {plate}, ID: {entry_id}")

    def log_exit(self, plate, success=True):
        """Log vehicle exit"""
        status = "SUCCESS" if success else "DENIED"
        self.logger.info(f"EXIT - Plate: {plate}, Status: {status}")

    def log_payment(self, plate, amount, success=True):
        """Log payment transaction"""
        status = "SUCCESS" if success else "FAILED"
        self.logger.info(f"PAYMENT - Plate: {plate}, Amount: {amount}, Status: {status}")

    def log_error(self, message):
        """Log error message"""
        self.logger.error(message)

    def log_info(self, message):
        """Log info message"""
        self.logger.info(message)

