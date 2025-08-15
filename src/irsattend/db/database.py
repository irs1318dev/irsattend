# Main database connector

import sqlite3
import random
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


def generate_unique_student_id() -> str:
    """Generate a unique 8-digit student ID.
    Checks against existing IDs to ensure uniqueness."""
    max_attempts = 100

    for _ in range(max_attempts):
        # Generate ID
        student_id = str(random.randint(10000000, 99999999))

        # Check if ID already exists
        if get_student_by_id(student_id) is None:
            return student_id

    raise RuntimeError("Error generating ID")


# We can add more functions here to interact with the database

# We probably want Add Student, Remove Student, Edit Student, Get Student
# Get all Students, Get Attendance Record by Student ID & Timestamp, and others

# Management Panel Functions


def add_student(first_name: str, last_name: str, email: str, grad_year: int) -> str:
    """Add a new student to the database.
    Returns ID on success."""
    try:
        student_id = generate_unique_student_id()
        with get_db_connection() as conn:
            conn.execute(
                "INSERT INTO students (id, first_name, last_name, email, grad_year) VALUES (?, ?, ?, ?, ?)",
                (student_id, first_name, last_name, email, grad_year),
            )
            conn.commit()
        return student_id
    except sqlite3.IntegrityError as e:
        raise RuntimeError(f"Failed to add student: {e}")


def update_student(
    id: str, first_name: str, last_name: str, email: str, grad_year: int
) -> None:
    """Edit student."""
    with get_db_connection() as conn:
        conn.execute(
            """UPDATE students
               SET first_name = ?, last_name = ?, email = ?, grad_year = ?
               WHERE id = ?""",
            (first_name, last_name, email, grad_year, id),
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


def get_student_by_id(student_id: str) -> Optional[sqlite3.Row]:
    """Retrieve a student by their ID."""
    with get_db_connection() as conn:
        cursor = conn.execute("SELECT * FROM students WHERE id = ?", (student_id,))
        return cursor.fetchone()


def get_attendance_counts() -> Dict[str, int]:
    """Get a dictionary of student IDs and their attendance counts."""
    with get_db_connection() as conn:
        cursor = conn.execute(
            """SELECT student_id, COUNT(id) as count
               FROM attendance
               GROUP BY student_id"""
        )
        return {row["student_id"]: row["count"] for row in cursor.fetchall()}


def get_attendance_count_by_id(student_id: str) -> int:
    """Retrieve a student's attendance count by their ID."""
    with get_db_connection() as conn:
        cursor = conn.execute(
            """SELECT COUNT(id) as count
               FROM attendance WHERE student_id = ?""",
            (student_id,),
        )
        result = cursor.fetchone()
        return result["count"] if result else 0


def remove_last_attendance_record(student_id: str) -> Optional[datetime]:
    """Remove the most recent attendance record for a student.
    Returns the timestamp of the removed record if successful."""
    with get_db_connection() as conn:
        cursor = conn.execute(
            """SELECT id, timestamp FROM attendance 
               WHERE student_id = ? 
               ORDER BY timestamp DESC 
               LIMIT 1""",
            (student_id,),
        )
        record = cursor.fetchone()

        if record:
            conn.execute("DELETE FROM attendance WHERE id = ?", (record["id"],))
            conn.commit()
            return record["timestamp"]

        return None


def remove_all_attendance_records(student_id: str) -> int:
    """Remove all attendance records for a student.
    Returns the number of records removed."""
    with get_db_connection() as conn:
        cursor = conn.execute(
            "DELETE FROM attendance WHERE student_id = ?", (student_id,)
        )
        conn.commit()
        return cursor.rowcount


# Attendance Functions


def add_attendance_record(
    student_id: str,
) -> Optional[datetime]:  # Will also be used in mgmt to manually add a record
    """Add an attendance record for a student.
    Returns the timestamp of when added if successful."""
    timestamp = datetime.now()
    with get_db_connection() as conn:
        conn.execute(
            "INSERT INTO attendance (student_id, timestamp) VALUES (?, ?)",
            (student_id, timestamp),
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
            (student_id, today_start),
        )
        return cursor.fetchone() is not None
