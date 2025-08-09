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

# Management Panel Functions

def add_student(id: str, first_name: str, last_name: str, email: str, grad_year: int) -> bool:
    """Add a new student to the database.
    Returns True/False on success/fail."""
    try:
        with get_db_connection() as conn:
            conn.execute(
                "INSERT INTO students (id, first_name, last_name, email, grad_year) VALUES (?, ?, ?, ?, ?)",
                (id, first_name, last_name, email, grad_year)
            )
            conn.commit()
        return True
    except sqlite3.IntegrityError: # Catch duplicates
        return False

# For now, its a good idea to not allow editing of student IDs
def update_student(id: str, first_name: str, last_name: str, email: str, grad_year: int) -> None:
    """Edit student."""
    with get_db_connection() as conn:
        conn.execute(
            """UPDATE students
               SET first_name = ?, last_name = ?, email = ?, grad_year = ?
               WHERE id = ?""",
            (first_name, last_name, email, grad_year, id)
        )
        conn.commit()
        
def delete_student(student_id: str):
    """Delete a student and their attendance records."""
    with get_db_connection() as conn:
        conn.execute("DELETE FROM students WHERE id = ?", (student_id,))
        conn.commit()
        
def get_all_students() -> List[sqlite3.Row]:
    """Retrieve all students from the database."""
    with get_db_connection() as conn:
        cursor = conn.execute("SELECT * FROM students ORDER BY last_name, first_name")
        return cursor.fetchall()
        
def get_attendance_counts() -> Dict[str, int]:
    """Get a dictionary of student IDs and their attendance counts."""
    with get_db_connection() as conn:
        cursor = conn.execute(
            """SELECT student_id, COUNT(id) as count
               FROM attendance
               GROUP BY student_id"""
        )
        return {row['student_id']: row['count'] for row in cursor.fetchall()}
        
# Attendance Functions
        
def add_attendance_record(student_id: str) -> Optional[datetime]: # Will also be used in mgmt to manually add a record
    """Add an attendance record for a student.
    Returns the timestamp of when added if successful."""
    timestamp = datetime.now()
    with get_db_connection() as conn:
        conn.execute(
            "INSERT INTO attendance (student_id, timestamp) VALUES (?, ?)",
            (student_id, timestamp)
        )
        conn.commit()
    return timestamp

def has_attended_today(student_id: str) -> bool:
    """Check if a student has already been marked present today.
    Must be used before add_attendance_record."""

    # Get the start of today (for v2, we can add other ways to calculate meetings)
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    with get_db_connection() as conn:
        cursor = conn.execute(
            "SELECT 1 FROM attendance WHERE student_id = ? AND timestamp >= ?",
            (student_id, today_start)
        )
        return cursor.fetchone() is not None