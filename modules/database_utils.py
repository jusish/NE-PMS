import sqlite3
import csv
import os
from datetime import datetime, timedelta
from contextlib import contextmanager


class DatabaseManager:
    def __init__(self, db_path='/home/hrh/Documents/Workspace/data/records.db'):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.init_database()

    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def init_database(self):
        """Initialize database tables"""
        with self.get_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS parking_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entry_time TEXT NOT NULL,
                    exit_time TEXT,
                    car_plate TEXT NOT NULL,
                    due_payment REAL DEFAULT 0,
                    payment_status INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS denial_incidents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    plate TEXT NOT NULL,
                    denial_time TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()

    def has_recent_denial(self, plate, reason, minutes=5):
        """Check if a denial incident for the plate and reason exists within the last `minutes`"""
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        with self.get_connection() as conn:
            cursor = conn.execute(
                '''SELECT id FROM denial_incidents 
                   WHERE plate = ? AND reason = ? 
                   AND datetime(denial_time) > datetime(?)''',
                (plate, reason, cutoff_time.strftime('%Y-%m-%d %H:%M:%S'))
            )
            return cursor.fetchone() is not None

    def add_denial_incident(self, plate, reason):
        """Add a denial incident to the database if no similar incident exists within cooldown"""
        if self.has_recent_denial(plate, reason):
            return None  # Cooldown active, do not log
        with self.get_connection() as conn:
            cursor = conn.execute(
                'INSERT INTO denial_incidents (plate, denial_time, reason) VALUES (?, ?, ?)',
                (plate, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), reason)
            )
            conn.commit()
            return cursor.lastrowid

    def add_entry(self, plate):
        """Add new parking entry"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                'INSERT INTO parking_records (entry_time, car_plate) VALUES (?, ?)',
                (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), plate)
            )
            conn.commit()
            return cursor.lastrowid

    def has_unpaid_record(self, plate):
        """Check if plate has unpaid parking record"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                'SELECT id FROM parking_records WHERE car_plate = ? AND payment_status = 0',
                (plate,)
            )
            return cursor.fetchone() is not None

    def get_unpaid_record(self, plate):
        """Get unpaid record for a plate"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                '''SELECT * FROM parking_records 
                   WHERE car_plate = ? AND payment_status = 0 
                   ORDER BY entry_time DESC LIMIT 1''',
                (plate,)
            )
            return cursor.fetchone()

    def update_exit_and_payment(self, plate, amount_due):
        """Update exit time and payment amount"""
        exit_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with self.get_connection() as conn:
            conn.execute(
                '''UPDATE parking_records 
                   SET exit_time = ?, due_payment = ?
                   WHERE car_plate = ? AND payment_status = 0''',
                (exit_time, amount_due, plate)
            )
            conn.commit()

    def mark_as_paid(self, plate):
        """Mark record as paid"""
        with self.get_connection() as conn:
            conn.execute(
                '''UPDATE parking_records 
                   SET payment_status = 1
                   WHERE car_plate = ? AND payment_status = 0''',
                (plate,)
            )
            conn.commit()

    def has_recent_paid_exit(self, plate, minutes=5):
        """Check if plate has recent paid exit within specified minutes"""
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        with self.get_connection() as conn:
            cursor = conn.execute(
                '''SELECT * FROM parking_records 
                   WHERE car_plate = ? AND payment_status = 1 
                   AND exit_time IS NOT NULL 
                   AND datetime(exit_time) > datetime(?)
                   ORDER BY exit_time DESC LIMIT 1''',
                (plate, cutoff_time.strftime('%Y-%m-%d %H:%M:%S'))
            )
            return cursor.fetchone() is not None

    def get_all_records(self):
        """Get all parking records"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                'SELECT * FROM parking_records ORDER BY entry_time DESC'
            )
            return cursor.fetchall()