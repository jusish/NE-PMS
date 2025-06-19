# modules/image_manager.py
import cv2
import os
from datetime import datetime


class ImageManager:
    def __init__(self, base_dir='images'):
        self.base_dir = base_dir
        self.entry_dir = os.path.join(base_dir, 'entry')
        self.exit_dir = os.path.join(base_dir, 'exit')

        os.makedirs(self.entry_dir, exist_ok=True)
        os.makedirs(self.exit_dir, exist_ok=True)

    def save_plate_image(self, plate_img, plate_number, event_type='entry'):
        """Save license plate image"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{plate_number}_{timestamp}.jpg"

        save_dir = self.entry_dir if event_type == 'entry' else self.exit_dir
        filepath = os.path.join(save_dir, filename)

        cv2.imwrite(filepath, plate_img)
        return filepath

    def save_full_frame(self, frame, plate_number, event_type='entry'):
        """Save full camera frame"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{plate_number}_full_{timestamp}.jpg"

        save_dir = self.entry_dir if event_type == 'entry' else self.exit_dir
        filepath = os.path.join(save_dir, filename)

        cv2.imwrite(filepath, frame)
        return filepath

