import cv2
import time
from modules.gate_control import GateController
from modules.database_utils import DatabaseManager
from modules.logger import ParkingLogger
from modules.image_manager import ImageManager
from modules.ocr_utilis import PlateRecognizer


class CarExitSystem:
    def __init__(self):
        self.plate_recognizer = PlateRecognizer('models/runs/detect/train/weights/best.pt')
        self.gate_controller = GateController()
        self.db = DatabaseManager()
        self.logger = ParkingLogger()
        self.image_manager = ImageManager()

        # Configuration
        self.max_distance = 50  # cm
        self.min_distance = 0  # cm
        self.gate_open_time = 15  # seconds
        self.exit_window_minutes = 5  # Grace period for exit after payment

        # Initialize camera
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            self.logger.log_error("Cannot open camera")
            raise Exception("Camera initialization failed")

    def run(self):
        """Main exit system loop"""
        self.logger.log_info("Exit system started")
        print("[EXIT SYSTEM] Ready. Press 'q' to exit.")

        try:
            while True:
                ret, frame = self.cap.read()
                if not ret:
                    self.logger.log_error("Frame capture failed")
                    break

                # Check distance sensor
                distance = self.gate_controller.read_distance() or (self.max_distance + 1)

                if self.min_distance <= distance <= self.max_distance:
                    self._process_frame(frame)

                # Display feed
                cv2.imshow('Exit System', frame)

                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

        except KeyboardInterrupt:
            self.logger.log_info("Exit system stopped by user")
        finally:
            self._cleanup()

    def _process_frame(self, frame):
        """Process frame for license plate detection"""
        detected_plates, results = self.plate_recognizer.detect_plates(frame)

        for plate_data in detected_plates:
            plate = plate_data['plate']
            consensus_plate = self.plate_recognizer.get_consensus_plate(plate)

            if consensus_plate:
                self._handle_exit(consensus_plate, plate_data, frame)

            # Show preview windows
            cv2.imshow('Detected Plate', plate_data['image'])
            cv2.imshow('Processed', plate_data['processed'])

    def _handle_exit(self, plate, plate_data, frame):
        """Handle vehicle exit logic"""
        # Check for recent paid exit
        if self.db.has_recent_paid_exit(plate, self.exit_window_minutes):
            self.logger.log_exit(plate, True)
            print(f"[EXIT GRANTED] Valid exit for {plate}")

            # Save images
            self.image_manager.save_plate_image(plate_data['image'], plate, 'exit')
            self.image_manager.save_full_frame(frame, plate, 'exit')

            # Open gate
            self.gate_controller.open_gate(self.gate_open_time)

        else:
            self.logger.log_exit(plate, False)
            print(f"[EXIT DENIED] No valid payment found for {plate}")
            self.db.add_denial_incident(plate, "No valid payment")
            self.gate_controller.trigger_alert()

    def _cleanup(self):
        """Clean up resources"""
        self.cap.release()
        self.gate_controller.close()
        cv2.destroyAllWindows()
        self.logger.log_info("Exit system cleaned up")