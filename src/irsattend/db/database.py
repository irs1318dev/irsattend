# Main database connector

import sqlite3
from datetime import datetime
from typing import List, Optional, Tuple, Dict

from .. import config

# Main database connection
def get_db_connection():
    """Establishes a connection to the SQLite database
    Creates one if it doesn't exist."""
    conn = sqlite3.connect(config.DB_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

# Will be used to initialize the db when running the app
def create_tables():
    """Creates the database tables if they don't already exist."""
    from .models import STUDENT_TABLE_SCHEMA, ATTENDANCE_TABLE_SCHEMA
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(STUDENT_TABLE_SCHEMA)
    cursor.execute(ATTENDANCE_TABLE_SCHEMA)
    conn.commit()
    conn.close()
    
# We can add more functions here to interact with the database

# We probably want Add Student, Remove Student, Edit Student, Get Student
# Get all Students, Get Attendance Record by Student ID & Timestamp, and others

def add_attendance_record(student_id: str) -> Optional[datetime]:
    """Adds an attendance record for a student.
    Returns the timestamp of when added if successful."""
    timestamp = datetime.now()
    with get_db_connection() as conn:
        conn.execute(
            "INSERT INTO attendance (student_id, timestamp) VALUES (?, ?)",
            (student_id, timestamp)
        )
        conn.commit()
    return timestamp