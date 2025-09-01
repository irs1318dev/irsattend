"""Connect to the Sqlite database and run queries."""
import datetime
import pathlib
import random
import re
import sqlite3
from typing import Any, List, Optional, Dict

from irsattend.model import db_tables


class DBaseError(Exception):
    """Error occurred when working with database."""


class DBase:
    """Read and write to database."""
    db_path: pathlib.Path
    """Path to Sqlite database."""

    def __init__(
        self,
        db_path: Optional[pathlib.Path],
        create_new: bool = False
    ) -> None:
        """Set database path."""
        if db_path is None:
            raise DBaseError("db_path is None. Can't locate database file.")
        else:
            self.db_path = db_path
        if create_new:
            if self.db_path.exists():
                raise DBaseError(
                    f"Databae file at {db_path} does not exist and create_new is False.")
            else:
                self.create_tables()

    def get_db_connection(self) -> sqlite3.Connection:
        """Get connection to the SQLite database. Create DB if it doesn't exist."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def create_tables(self):
        """Creates the database tables if they don't already exist."""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute(db_tables.STUDENT_TABLE_SCHEMA)
        cursor.execute(db_tables.ATTENDANCE_TABLE_SCHEMA)
        conn.commit()
        conn.close()

    def generate_unique_student_id(
            self,
            first_name: str,
            last_name: str,
            grad_year: int
        ) -> str:
        """Generate a unique 8-digit student ID."""
        id_ = (
            f"{last_name.strip().lower()}-{first_name.strip().lower()}"
            f"-{grad_year}-{random.randint(1, 999):03}")
        no_punctuation_id = re.sub(r"[.!?;,:]+", "", id_)  # Remove punctuation
        final_id = re.sub(r"\s+", "_", no_punctuation_id)  # Remove internal whitespace
        return final_id

    def add_student(
        self,
        first_name: str,
        last_name: str,
        email: str,
        grad_year: int
    ) -> str:
        """Add a new student to the database.

        Returns:
            student_id
        
        Raises:
            sqlite3.IntegrityError if insert query is not successful.
        """
        student_id = self.generate_unique_student_id(first_name, last_name, grad_year)
        with self.get_db_connection() as conn:
            conn.execute("""
                INSERT INTO students
                            (student_id, first_name, last_name, email, grad_year)
                        VALUES (?, ?, ?, ?, ?);""",
                (student_id, first_name, last_name, email, grad_year),
            )
        return student_id
    
    def update_student(
        self,
        student_id: str,
        first_name: str,
        last_name: str,
        email: str,
        grad_year: int
    ) -> None:
        """Edit student."""
        with self.get_db_connection() as conn:
            conn.execute(
                """UPDATE students
                SET first_name = ?, last_name = ?, email = ?, grad_year = ?
                WHERE student_id = ?""",
                (first_name, last_name, email, grad_year, student_id),
            )
            conn.commit()

    def delete_student(self, student_id: str):
        """Delete a student and their attendance records."""
        with self.get_db_connection() as conn:
            conn.execute("DELETE FROM students WHERE student_id = ?", (student_id,))
            conn.commit()

    def get_all_students(self) -> List[sqlite3.Row]:
        """Retrieve all students from the database."""
        with self.get_db_connection() as conn:
            cursor = conn.execute("SELECT * FROM students ORDER BY last_name, first_name")
            return cursor.fetchall()

    def get_student_by_id(self, student_id: str) -> Optional[dict[str, Any]]:
        """Retrieve a student by their ID."""
        with self.get_db_connection() as conn:
            cursor = conn.execute("SELECT * FROM students WHERE student_id = ?", (student_id,))
            if cursor is None:
                return None
            return dict(cursor.fetchone())

    def get_attendance_counts(self) -> Dict[str, int]:
        """Get a dictionary of student IDs and their attendance counts."""
        with self.get_db_connection() as conn:
            cursor = conn.execute(
                """SELECT student_id, COUNT(student_id) as count
                FROM attendance
                GROUP BY student_id"""
            )
            return {row["student_id"]: row["count"] for row in cursor.fetchall()}

    def get_attendance_count_by_id(self, student_id: str) -> int:
        """Retrieve a student's attendance count by their ID."""
        with self.get_db_connection() as conn:
            cursor = conn.execute(
                """SELECT COUNT(student_id) as count
                FROM attendance WHERE student_id = ?""",
                (student_id,),
            )
            result = cursor.fetchone()
            return result["count"] if result else 0

    def remove_last_attendance_record(self, student_id: str) -> Optional[datetime.datetime]:
        """Remove the most recent attendance record for a student.
        Returns the timestamp of the removed record if successful."""
        with self.get_db_connection() as conn:
            cursor = conn.execute(
                """SELECT id, timestamp FROM attendance 
                WHERE student_id = ? 
                ORDER BY timestamp DESC 
                LIMIT 1""",
                (student_id,),
            )
            record = cursor.fetchone()

            if record:
                conn.execute(
                    "DELETE FROM attendance WHERE student_id = ?",
                    (record["student_id"],))
                conn.commit()
                return record["timestamp"]

            return None

    def remove_all_attendance_records(self, student_id: str) -> int:
        """Remove all attendance records for a student.
        Returns the number of records removed."""
        with self.get_db_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM attendance WHERE student_id = ?", (student_id,)
            )
            conn.commit()
            return cursor.rowcount

    def add_attendance_record(
        self,
        student_id: str,
    ) -> Optional[datetime.datetime]:  # Will also be used in mgmt to manually add a record
        """Add an attendance record for a student.
        Returns the timestamp of when added if successful."""
        timestamp = datetime.datetime.now()
        with self.get_db_connection() as conn:
            conn.execute(
                "INSERT INTO attendance (student_id, timestamp) VALUES (?, ?)",
                (student_id, timestamp),
            )
            conn.commit()
        return timestamp

    def has_attended_today(self, student_id: str) -> bool:
        """Check if a student has already been marked present today.
        Must be used before add_attendance_record."""

        # Get the start of today (for v2, we can add other ways to calculate meetings)
        today_start = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        with self.get_db_connection() as conn:
            cursor = conn.execute(
                "SELECT 1 FROM attendance WHERE student_id = ? AND timestamp >= ?",
                (student_id, today_start),
            )
            return cursor.fetchone() is not None
