"""Connect to the Sqlite database and run queries."""
from collections.abc import Sequence
import datetime
import pathlib
import random
import re
import sqlite3
from typing import Any, Optional

import polars as pl

from irsattend.model import config, db_tables


class DBaseError(Exception):
    """Error occurred when working with database."""


def dict_factory(cursor: sqlite3.Cursor, row: Sequence) -> dict[str, Any]:
    """Create a dictionary row factory."""
    fields = [column[0] for column in cursor.description]
    return {key: value for key, value in zip(fields, row)}


def adapt_date_iso(val: datetime.date) -> str:
    """Adapt datetime.date to ISO 8601 date."""
    return val.isoformat()


def adapt_datetime_iso(val: datetime.datetime) -> str:
    """Adapt datetime.datetime to timezone-naive ISO 8601 date."""
    return val.replace(tzinfo=None).isoformat()


# Sqlite converts Python datetime.date and datetime.datetime objects to
#   ISO-8601-formatted strings automatically. But as of Python 3.12, this
#   behavior is deprecated, which means the Python developers will remove this
#   behavior in a future version of Python and we should stop relying on it.
# The register_adapter function calls explicity tell Sqlite how to convert date
#   and datetime objects to text values that can be stored in Sqlite.
#   Omitting these two lines results in deprecation warnings when we run the
#   applicatin or tests.
sqlite3.register_adapter(datetime.date, adapt_date_iso)
sqlite3.register_adapter(datetime.datetime, adapt_datetime_iso)


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
        cursor.execute(db_tables.EVENT_TABLE_SCHEMA)
        conn.commit()
        conn.close()

    @classmethod
    def _clean_name(cls, name: str) -> str:
        """Replace dashes and spaces with an underscore and remove punctuation."""
        name = cls.remove_pattern.sub("", name)
        return cls.underscore_pattern.sub("_", name)

    @classmethod
    def generate_unique_student_id(
            cls,
            first_name: str,
            last_name: str,
            grad_year: int
        ) -> str:
        """Generate a unique 8-digit student ID."""
        first_name = cls._clean_name(first_name)
        last_name = cls._clean_name(last_name)
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

    def get_all_students(self, as_dict: bool = False) -> list[sqlite3.Row]:
        """Retrieve all students from the database."""
        with self.get_db_connection(as_dict) as conn:
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

    def get_student_attendance_data(self) -> sqlite3.Cursor:
        """Join students and attendance table and get current season data."""
        # An 'app' is an appearance.
        query = """
                WITH year_checkins AS (
                    SELECT student_id, COUNT(student_id) as checkins
                      FROM attendance
                     WHERE timestamp >= :year_start
                  GROUP BY student_id
                ),
                build_checkins AS (
                    SELECT student_id, COUNT(student_id) as checkins
                      FROM attendance
                     WHERE timestamp >= :build_start
                  GROUP BY student_id
                )
                SELECT s.student_id, s.last_name, s.first_name, s.grad_year,
                       COALESCE(y.checkins, 0) AS year_checkins,
                       COALESCE(b.checkins, 0) AS build_checkins
                  FROM students AS s
             LEFT JOIN year_checkins AS y
                    ON y.student_id = s.student_id
            LEFT JOIN build_checkins AS b
                    ON b.student_id = s.student_id
              ORDER BY last_name, first_name;
        """
        with self.get_db_connection() as conn:
            cursor = conn.execute(
                query, {
                    "year_start": config.settings.schoolyear_start_date,
                    "build_start": config.settings.buildseason_start_date
                })
        return cursor

    def get_attendance_counts(self, since: datetime.date) -> dict[str, int]:
        """Get a dictionary of student IDs and their attendance counts."""
        with self.get_db_connection() as conn:
            cursor = conn.execute("""
                    SELECT student_id, COUNT(student_id) as checkins
                      FROM attendance
                     WHERE timestamp >= ?
                  GROUP BY student_id
                  ORDER BY student_id;
            """,
            (since,)
            )
            return {row["student_id"]: row["checkins"] for row in cursor.fetchall()}

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
        timestamp: Optional[datetime.datetime] = None,
        event_type: db_tables.EventType = db_tables.EventType.MEETING
    ) -> Optional[datetime.datetime]:
        """Add an attendance record for a student.

        Returns:
            Date and time when attendance was recorded.
        """
        if timestamp is None:
            timestamp = datetime.datetime.now()
        with self.get_db_connection() as conn:
            conn.execute(
                """
                        INSERT INTO attendance
                                    (student_id, timestamp, event_type)
                             VALUES (?, ?);
                """,
                (student_id, timestamp, str(event_type)),
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
    
    def get_all_attendance_records(self, as_dict: bool = False) -> list[sqlite3.Row]:
        """Get all data from the attendance table."""
        query = """
                SELECT attendance_id, student_id, event_date, event_type, timestamp
                  FROM attendance
              ORDER BY timestamp;
        """
        with self.get_db_connection(as_dict) as conn:
            return conn.execute(query).fetchall()

    
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

    def to_dict(self) -> dict[str, list[dict[str, list[str | int | None]]]]:
        """Save database contents to a JSON file.
        
        Returns:
            Contents of the database as a Python dictionary. Format:
            {<table_name>: [{<col_name>: <col_value>}]}
        """
        db_data = {}
        db_data["students"] = self.get_all_students(as_dict=True)
        events = self.get_events(as_dict=True)
        excluded_columns = ["event_id", "day_of_week"]
        db_data["events"] = [
            {col: val for col, val in row.items() if col not in excluded_columns}
            for row in events
        ]
        attends = self.get_all_attendance_records(as_dict=True)
        excluded_columns = ["attendance_id", "event_date", "day_of_week"]
        db_data["attendance"] = [
            {col: val for col, val in row.items() if col not in excluded_columns}
            for row in attends
        ]
        return db_data
    
    def load_from_dict(
        self,
        db_data_dict: dict[str, list[dict[str, str | int | None]]]
    ) -> None:
        """Import data into the Sqlite database."""
        student_query = """
            INSERT INTO students
                        (student_id, first_name, last_name, email, grad_year)
                 VALUES (:student_id, :first_name, :last_name, :email, :grad_year);
        """
        attendance_query = """
            INSERT INTO attendance
                        (student_id, event_type, timestamp)
                 VALUES (:student_id, :event_type, :timestamp);
        """
        event_query = """
            INSERT INTO events
                        (event_date, event_type, description)
                 VALUES (:event_date, :event_type, :description);
        """
        with self.get_db_connection() as conn:
            conn.executemany(student_query, db_data_dict["students"])
            conn.executemany(attendance_query, db_data_dict["attendance"])
            conn.executemany(event_query, db_data_dict["events"])

    def get_events(
        self,
        as_dict: bool = False
    ) -> list[dict[str, Any] | sqlite3.Row]:
        """Get all records from the events table."""
        query = """
                SELECT event_id, event_date, event_type, description
                  FROM events
              ORDER BY event_date, event_type;
        """
        with self.get_db_connection(as_dict) as conn:
            return conn.execute(query).fetchall()

    def scan_for_new_events(
        self,
        event_type: db_tables.EventType = db_tables.EventType.MEETING
    ) -> int:
        """Scan attendance table for missing events, add them to events table.
        
        Returns:
            The number of rows added to the events table.
        """
        events = set(
            (row["event_date"], row["event_type"])
            for row in self.get_events(as_dict=True)
        )
        possible_new_event_query = """
            SELECT event_date, event_type
              FROM attendance
          GROUP BY event_date, event_type
          ORDER BY event_date;
        """
        with self.get_db_connection(as_dict=True) as conn:
            possible_events =  conn.execute(possible_new_event_query).fetchall()
        events_to_add: list[dict[str, str]] = []
        for poss_event in possible_events:
            if (poss_event["event_date"], poss_event["event_type"]) not in events:
                events_to_add.append({
                    "event_date": poss_event["event_date"],
                    "event_type": str(event_type)
                })
        insert_event_query = """
            INSERT INTO events
                        (event_date, event_type)
                 VALUES (:event_date, :event_type);
        """
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany(insert_event_query, events_to_add)
            rows_added = cursor.rowcount
        return rows_added

        
