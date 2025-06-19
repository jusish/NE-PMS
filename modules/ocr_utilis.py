# modules/ocr_utils.py
import cv2
import pytesseract
from ultralytics import YOLO
from collections import Counter
import re


class PlateRecognizer:
    def __init__(self, model_path='../models/runs/detect/train/weights/best.pt'):
        self.model = YOLO(model_path)
        self.plate_buffer = []
        self.capture_threshold = 3

    def preprocess_image(self, plate_img):
        """Preprocess license plate image for better OCR"""
        gray = cv2.cvtColor(plate_img, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
        return thresh

    def extract_text(self, processed_img):
        """Extract text from preprocessed image"""
        text = pytesseract.image_to_string(
            processed_img,
            config='--psm 8 --oem 3 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
        ).strip().replace(' ', '')
        return text

    def validate_rwandan_plate(self, text):
        """Validate Rwandan license plate format (RAxxxA)"""
        if not text.startswith('RA') or len(text) < 7:
            return None

        plate = text[:7]
        prefix, digits, suffix = plate[:3], plate[3:6], plate[6]

        if prefix.isalpha() and digits.isdigit() and suffix.isalpha():
            return plate
        return None

    def detect_plates(self, frame):
        """Detect license plates in frame and return validated plates"""
        results = self.model(frame)[0]
        detected_plates = []

        for box in results.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            plate_img = frame[y1:y2, x1:x2]

            processed = self.preprocess_image(plate_img)
            text = self.extract_text(processed)
            plate = self.validate_rwandan_plate(text)

            if plate:
                detected_plates.append({
                    'plate': plate,
                    'image': plate_img,
                    'processed': processed,
                    'bbox': (x1, y1, x2, y2)
                })

        return detected_plates, results

    def get_consensus_plate(self, plate):
        """Add plate to buffer and return consensus when threshold is met"""
        self.plate_buffer.append(plate)

        if len(self.plate_buffer) >= self.capture_threshold:
            consensus = Counter(self.plate_buffer).most_common(1)[0][0]
            self.plate_buffer.clear()
            return consensus
        return None
