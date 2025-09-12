"""Connect to the Sqlite database and run queries."""
from collections.abc import Sequence
import datetime
import pathlib
import random
import re
import sqlite3
from typing import Any, Optional

import polars as pl

from irsattend.model import db_tables


class DBaseError(Exception):
    """Error occurred when working with database."""


def dict_factory(cursor: sqlite3.Cursor, row: Sequence) -> dict[str, Any]:
    """Create a dictionary row factory."""
    fields = [column[0] for column in cursor.description]
    return {key: value for key, value in zip(fields, row)}


class DBase:
    """Read and write to database."""
    db_path: pathlib.Path
    """Path to Sqlite database."""
    underscore_pattern: re.Pattern = re.compile(r"[\s\-]+")
    """Replace whitespace and dashes with an underscore."""
    remove_pattern: re.Pattern = re.compile(r"[.!?;,:']+")
    """Remove punctuation."""


    def __init__(
        self,
        db_path: pathlib.Path,
        create_new: bool = False
    ) -> None:
        """Set database path."""
        self.db_path = db_path
        if create_new:
            if self.db_path.exists():
                raise DBaseError(
                    f"Cannot create new database at {db_path}, file already exists.")
            else:
                self.create_tables()
        else:
            if not db_path.exists():
                raise DBaseError(
                    f"Database file at {db_path} does not exist."
                )

    def get_db_connection(self, as_dict=False) -> sqlite3.Connection:
        """Get connection to the SQLite database. Create DB if it doesn't exist."""
        conn = sqlite3.connect(self.db_path)
        if as_dict:
            conn.row_factory = dict_factory
        else:
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

    def _clean_name(self, name: str) -> str:
        """Replace dashes and spaces with an underscore and remove punctuation."""
        name = self.remove_pattern.sub("", name)
        return self.underscore_pattern.sub("_", name)

    def generate_unique_student_id(
            self,
            first_name: str,
            last_name: str,
            grad_year: int
        ) -> str:
        """Generate a unique 8-digit student ID."""
        first_name = self._clean_name(first_name)
        last_name = self._clean_name(last_name)
        return (
            f"{last_name.strip().lower()}-{first_name.strip().lower()}"
            f"-{grad_year}-{random.randint(1, 999):03}")

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

    def get_all_students(self) -> list[sqlite3.Row]:
        """Retrieve all students from the database."""
        with self.get_db_connection() as conn:
            cursor = conn.execute("""
                    SELECT student_id, last_name, first_name, grad_year, email
                      FROM students
                  ORDER BY student_id;
            """)
            return cursor.fetchall()
        
    def get_student_ids(self) -> list[str]:
        """Get a list of student IDs."""
        with self.get_db_connection() as conn:
            cursor = conn.execute(
                "SELECT student_id FROM students ORDER BY student_id;")
            return [row[0] for row in cursor]

    def get_student_by_id(self, student_id: str) -> Optional[sqlite3.Row]:
        """Retrieve a student by their ID."""
        with self.get_db_connection() as conn:
            cursor = conn.execute("SELECT * FROM students WHERE student_id = ?", (student_id,))
            if cursor is None:
                return None
            return cursor.fetchone()
        
    def import_students_from_csv(self, csv_path: pathlib.Path) -> None:
        """Load students from a CSV file."""
        studentdf = pl.read_csv(csv_path)
        for row in studentdf.iter_rows(named=True):
            self.add_student(**row)

    def get_attendance_counts(self) -> dict[str, int]:
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
                """SELECT student_id, timestamp FROM attendance 
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
        
    def get_attendance_dataframe(self) -> pl.DataFrame:
        """Get a Polars dataframe with attendance data."""
        return pl.read_database(
            "SELECT * FROM attendance ORDER BY timestamp;",
            self.get_db_connection()
        )
    
    def merge_database(self, incoming: "DBase") -> None:
        """Insert contents of another database."""
        current_student_ids = set(self.get_student_ids())
        incoming_students = incoming.get_all_students()
        with self.get_db_connection() as main_conn:
            for student in incoming_students:
                if student["student_id"] not in current_student_ids:
                    main_conn.execute("""
                    INSERT INTO students
                                (student_id, first_name, last_name, email, grad_year)
                        VALUES (:student_id, :first_name, :last_name, :email,
                               :grad_year)
                        ON CONFLICT(email) DO NOTHING;
                    """,
                    dict(student),
                )
        incoming_conn = incoming.get_db_connection(as_dict=True)
        incoming_attendance = incoming_conn.execute("SELECT * FROM attendance;")
        for appearance in incoming_attendance:
            try:
                with self.get_db_connection() as db_conn:
                    db_conn.execute("""
                            INSERT INTO attendance
                                        (student_id, event_type, timestamp)
                                VALUES (:student_id, :event_type, :timestamp);
                    """,
                    appearance
                    )
            except sqlite3.IntegrityError as err:
                print(err)