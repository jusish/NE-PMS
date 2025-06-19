import cv2
import time
from modules.gate_control import GateController
from modules.database_utils import DatabaseManager
from modules.logger import ParkingLogger
from modules.image_manager import ImageManager
from modules.ocr_utilis import PlateRecognizer


class CarEntrySystem:
    def __init__(self):
        self.plate_recognizer = PlateRecognizer('models/runs/detect/train/weights/best.pt')
        self.gate_controller = GateController()
        self.db = DatabaseManager()
        self.logger = ParkingLogger()
        self.image_manager = ImageManager()

        # Configuration
        self.entry_cooldown = 300  # seconds
        self.max_distance = 50  # cm
        self.min_distance = 0  # cm
        self.gate_open_time = 15  # seconds

        # State variables
        self.last_saved_plate = None
        self.last_entry_time = 0

        # Initialize camera
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            self.logger.log_error("Cannot open camera")
            raise Exception("Camera initialization failed")

    def run(self):
        """Main entry system loop"""
        self.logger.log_info("Entry system started")
        print("[ENTRY SYSTEM] Ready. Press 'q' to exit.")

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
                cv2.imshow('Entry System', frame)

                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

        except KeyboardInterrupt:
            self.logger.log_info("Entry system stopped by user")
        finally:
            self._cleanup()

    def _process_frame(self, frame):
        """Process frame for license plate detection"""
        detected_plates, results = self.plate_recognizer.detect_plates(frame)

        for plate_data in detected_plates:
            plate = plate_data['plate']
            consensus_plate = self.plate_recognizer.get_consensus_plate(plate)

            if consensus_plate:
                self._handle_entry(consensus_plate, plate_data, frame)

            # Show preview windows
            cv2.imshow('Detected Plate', plate_data['image'])
            cv2.imshow('Processed', plate_data['processed'])

    def _handle_entry(self, plate, plate_data, frame):
        """Handle vehicle entry logic"""
        current_time = time.time()

        # Check for existing unpaid record
        if self.db.has_unpaid_record(plate):
            self.logger.log_info(f"Denied entry - unpaid record exists for {plate}")
            print(f"[ENTRY DENIED] Unpaid record exists for {plate}")
            self.db.add_denial_incident(plate, "Unpaid parking record")
            self.gate_controller.trigger_alert()
            return

        # Check cooldown
        if (plate == self.last_saved_plate and
                (current_time - self.last_entry_time) < self.entry_cooldown):
            self.logger.log_info(f"Denied entry - cooldown active for {plate}")
            print(f"[ENTRY DENIED] Cooldown active for {plate}")
            self.db.add_denial_incident(plate, "Cooldown period active")
            self.gate_controller.trigger_alert()
            return

        # Process entry
        try:
            entry_id = self.db.add_entry(plate)
            self.logger.log_entry(plate, entry_id)
            print(f"[ENTRY SUCCESS] Logged plate {plate}")

            # Save images
            self.image_manager.save_plate_image(plate_data['image'], plate, 'entry')
            self.image_manager.save_full_frame(frame, plate, 'entry')

            # Open gate
            self.gate_controller.open_gate(self.gate_open_time)

            # Update state
            self.last_saved_plate = plate
            self.last_entry_time = current_time

        except Exception as e:
            self.logger.log_error(f"Entry processing failed for {plate}: {e}")
            self.db.add_denial_incident(plate, f"Processing error: {str(e)}")

    def _cleanup(self):
        """Clean up resources"""
        self.cap.release()
        self.gate_controller.close()
        cv2.destroyAllWindows()
        self.logger.log_info("Entry system cleaned up")