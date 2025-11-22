"""Connect to the Sqlite database and run queries."""

from collections.abc import Sequence
import datetime
import pathlib
import random
import re
import sqlite3
from typing import Any, cast, Optional

import polars as pl

from irsattend.model import config, schema


class DBaseError(Exception):
    """Error occurred when working with database."""


def dict_factory(cursor: sqlite3.Cursor, row: Sequence) -> dict[str, Any]:
    """Return Sqlite data as a dictionary."""
    fields = [column[0] for column in cursor.description]
    return {key: value for key, value in zip(fields, row)}


def adapt_date_iso(val: datetime.date) -> str:
    """Adapt datetime.date to ISO 8601 date."""
    return val.isoformat()


def convert_event_date(val: bytes) -> datetime.date:
    """Convert Sqlite event_date values to Date objects."""
    return datetime.date.fromisoformat(str(val))


def adapt_datetime_iso(val: datetime.datetime) -> str:
    """Adapt datetime.datetime to timezone-naive ISO 8601 date."""
    return val.replace(tzinfo=None).isoformat()


def adapt_event_type(val: schema.EventType) -> str:
    """Adapt schema.Eventtype objects to strings."""
    return val.value


def convert_event_type(val: bytes) -> schema.EventType:
    """Convert values from event_type columns to an EventType enum object."""
    return schema.EventType(str(val))


# Sqlite converts Python datetime.date and datetime.datetime objects to
#   ISO-8601-formatted strings automatically. But as of Python 3.12, this
#   behavior is deprecated, which means the Python developers will remove this
#   behavior in a future version of Python and we should stop relying on it.
# The register_adapter function calls explicity tell Sqlite how to convert date
#   and datetime objects to text values that can be stored in Sqlite.
#   Omitting these two lines results in deprecation warnings when we run the
#   application or tests.
sqlite3.register_adapter(datetime.date, adapt_date_iso)
sqlite3.register_adapter(datetime.datetime, adapt_datetime_iso)
# sqlite3.register_adapter(schema.EventType, adapt_event_type)
# sqlite3.register_converter("event_date", convert_event_date)
# sqlite3.register_converter("event_type", convert_event_type)


class DBase:
    """Read and write to database."""

    db_path: pathlib.Path
    """Path to Sqlite database."""
    underscore_pattern: re.Pattern = re.compile(r"[\s\-]+")
    """Replace whitespace and dashes with an underscore."""
    remove_pattern: re.Pattern = re.compile(r"[.!?;,:']+")
    """Remove punctuation."""

    def __init__(self, db_path: pathlib.Path, create_new: bool = False) -> None:
        """Set database path."""
        self.db_path = db_path
        if create_new:
            if self.db_path.exists():
                raise DBaseError(
                    f"Cannot create new database at {db_path}, file already exists."
                )
            else:
                self.create_tables()
        else:
            if not db_path.exists():
                raise DBaseError(f"Database file at {db_path} does not exist.")

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
        with self.get_db_connection() as conn:
            conn.execute(schema.STUDENT_TABLE_SCHEMA)
            conn.execute(schema.CHECKINS_TABLE_SCHEMA)
            conn.execute(schema.EVENT_TABLE_SCHEMA)
        conn.close()

    @classmethod
    def _clean_name(cls, name: str) -> str:
        """Replace dashes and spaces with an underscore and remove punctuation."""
        name = cls.remove_pattern.sub("", name)
        return cls.underscore_pattern.sub("_", name)

    @classmethod
    def generate_unique_student_id(
        cls, first_name: str, last_name: str, grad_year: int
    ) -> str:
        """Generate a unique 8-digit student ID."""
        first_name = cls._clean_name(first_name)
        last_name = cls._clean_name(last_name)
        return (
            f"{last_name.strip().lower()}-{first_name.strip().lower()}"
            f"-{grad_year}-{random.randint(1, 999):03}"
        )

    def add_student(
        self, first_name: str, last_name: str, email: str, grad_year: int
    ) -> str:
        """Add a new student to the database.

        Returns:
            student_id

        Raises:
            sqlite3.IntegrityError if insert query is not successful.
        """
        student_id = self.generate_unique_student_id(first_name, last_name, grad_year)
        with self.get_db_connection() as conn:
            conn.execute(
                """
                INSERT INTO students
                            (student_id, first_name, last_name, email, grad_year)
                        VALUES (?, ?, ?, ?, ?);""",
                (student_id, first_name, last_name, email, grad_year),
            )
        conn.close()
        return student_id

    def update_student(
        self,
        student_id: str,
        first_name: str,
        last_name: str,
        email: str,
        grad_year: int,
    ) -> None:
        """Edit student."""
        with self.get_db_connection() as conn:
            conn.execute(
                """UPDATE students
                SET first_name = ?, last_name = ?, email = ?, grad_year = ?
                WHERE student_id = ?""",
                (first_name, last_name, email, grad_year, student_id),
            )
        conn.close()

    def delete_student(self, student_id: str):
        """Delete a student and their attendance records."""
        with self.get_db_connection() as conn:
            conn.execute("DELETE FROM students WHERE student_id = ?", (student_id,))
        conn.close()

    def get_all_students(self) -> list[sqlite3.Row]:
        """Retrieve all students from the database."""
        return cast(list[sqlite3.Row], self._get_all_students())

    def get_all_students_dict(self) -> list[dict[str, Any]]:
        """Retrieve all students from the database."""
        return cast(list[dict[str, Any]], self._get_all_students(as_dict=True))

    def _get_all_students(
        self, as_dict: bool = False
    ) -> list[sqlite3.Row] | list[dict[str, Any]]:
        """Retrieve all students from the database."""
        conn = self.get_db_connection(as_dict)
        cursor = conn.execute(
            """
                SELECT student_id, last_name, first_name, grad_year, email
                    FROM students
                ORDER BY student_id;
        """
        )
        students = cursor.fetchall()
        conn.close()
        return students

    def get_student_ids(self) -> list[str]:
        """Get a list of student IDs."""
        conn = self.get_db_connection()
        cursor = conn.execute("SELECT student_id FROM students ORDER BY student_id;")
        student_ids = [row[0] for row in cursor]
        conn.close()
        return student_ids

    def get_student_by_id(self, student_id: str) -> Optional[sqlite3.Row]:
        """Retrieve a student by their ID."""
        conn = self.get_db_connection()
        cursor = conn.execute(
            "SELECT * FROM students WHERE student_id = ?", (student_id,)
        )
        student = None if cursor is None else cursor.fetchone()
        conn.close()
        return student

    def get_student_attendance_data(self) -> sqlite3.Cursor:
        """Join students and checkins table and get current season data."""
        # An 'app' is an appearance.
        query = """
                WITH year_checkins AS (
                    SELECT student_id, COUNT(student_id) as checkins
                      FROM checkins
                     WHERE timestamp >= :year_start
                  GROUP BY student_id
                ),
                build_checkins AS (
                    SELECT student_id, COUNT(student_id) as checkins
                      FROM checkins
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
        conn = self.get_db_connection()
        cursor = conn.execute(
            query,
            {
                "year_start": config.settings.schoolyear_start_date,
                "build_start": config.settings.buildseason_start_date,
            },
        )
        return cursor

    def get_checkin_counts(self, since: datetime.date) -> dict[str, int]:
        """Get a dictionary of student IDs and their checkin counts."""
        conn = self.get_db_connection()
        cursor = conn.execute(
            """
                SELECT student_id, COUNT(student_id) as checkins
                    FROM checkins
                    WHERE timestamp >= ?
                GROUP BY student_id
                ORDER BY student_id;
        """,
            (since,),
        )
        counts = {row["student_id"]: row["checkins"] for row in cursor.fetchall()}
        conn.close()
        return counts

    def get_checkin_count_by_id(self, student_id: str) -> int:
        """Retrieve a student's checkin count by their ID."""
        conn = self.get_db_connection()
        cursor = conn.execute(
            """SELECT COUNT(student_id) as count
            FROM checkins WHERE student_id = ?""",
            (student_id,),
        )
        checkin_count = cursor.fetchone()
        conn.close()
        return checkin_count["count"] if checkin_count else 0

    def remove_last_checkin_record(
        self, student_id: str
    ) -> Optional[datetime.datetime]:
        """Remove the most recent checkin record for a student.
        Returns the timestamp of the removed record if successful."""
        with self.get_db_connection() as conn:
            cursor = conn.execute(
                """SELECT student_id, timestamp FROM checkins
                WHERE student_id = ? 
                ORDER BY timestamp DESC 
                LIMIT 1""",
                (student_id,),
            )
            record = cursor.fetchone()

            if record:
                conn.execute(
                    "DELETE FROM checkins WHERE student_id = ?",
                    (record["student_id"],),
                )
                conn.commit()
                return record["timestamp"]
        conn.close()
        return None

    def remove_all_checkin_records(self, student_id: str) -> int:
        """Remove all checkin records for a student.
        Returns the number of records removed."""
        with self.get_db_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM checkins WHERE student_id = ?", (student_id,)
            )
            rowcount = cursor.rowcount
        conn.close()
        return rowcount

    def add_checkin_record(
        self,
        student_id: str,
        timestamp: Optional[datetime.datetime] = None,
        event_type: schema.EventType = schema.EventType.MEETING,
    ) -> Optional[datetime.datetime]:
        """Add an checkin record for a student.

        Returns:
            Date and time when checkin was recorded.
        """
        if timestamp is None:
            timestamp = datetime.datetime.now()
        with self.get_db_connection() as conn:
            conn.execute(
                """
                        INSERT INTO checkins
                                    (student_id, timestamp, event_type)
                             VALUES (?, ?, ?);
                """,
                (student_id, timestamp, str(event_type)),
            )
        conn.close()
        return timestamp

    def has_attended_today(self, student_id: str) -> bool:
        """Check if a student has already been marked present today.
        Must be used before add_checkin_record."""

        # Get the start of today (for v2, we can add other ways to calculate meetings)
        today_start = datetime.datetime.now().replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        conn = self.get_db_connection()
        cursor = conn.execute(
            "SELECT 1 FROM checkins WHERE student_id = ? AND timestamp >= ?",
            (student_id, today_start),
        )
        has_attended = cursor.fetchone() is not None
        conn.close()
        return has_attended

    def get_checkins_dataframe(self) -> pl.DataFrame:
        """Get a Polars dataframe with checkin data."""
        conn = self.get_db_connection()
        dframe = pl.read_database("SELECT * FROM checkins ORDER BY timestamp;", conn)
        conn.close()
        return dframe

    def get_all_checkins_records_dict(self) -> list[dict[str, Any]]:
        """Get all data from the checkin table."""
        query = """
                SELECT checkin_id, student_id, event_date, event_type, timestamp
                  FROM checkins
              ORDER BY timestamp;
        """
        conn = self.get_db_connection(as_dict=True)
        records = conn.execute(query).fetchall()
        conn.close()
        return records

    def merge_database(self, incoming: "DBase") -> None:
        """Insert contents of another database."""
        current_student_ids = set(self.get_student_ids())
        incoming_students = incoming.get_all_students()
        with self.get_db_connection() as main_conn:
            for student in incoming_students:
                if student["student_id"] not in current_student_ids:
                    main_conn.execute(
                        """
                    INSERT INTO students
                                (student_id, first_name, last_name, email, grad_year)
                        VALUES (:student_id, :first_name, :last_name, :email,
                               :grad_year)
                        ON CONFLICT(email) DO NOTHING;
                    """,
                        dict(student),
                    )
        main_conn.close()
        incoming_conn = incoming.get_db_connection(as_dict=True)
        incoming_checkins = incoming_conn.execute("SELECT * FROM checkins;")
        incoming_conn.close()
        db_conn: sqlite3.Connection | None = None
        for appearance in incoming_checkins:
            try:
                with self.get_db_connection() as db_conn:
                    db_conn.execute(
                        """
                            INSERT INTO checkins
                                        (student_id, event_type, timestamp)
                                VALUES (:student_id, :event_type, :timestamp);
                    """,
                        appearance,
                    )
            except sqlite3.IntegrityError as err:
                print(err)
            finally:
                if db_conn is not None:
                    db_conn.close()

    def to_dict(self) -> dict[str, list[dict[str, str | int | None]]]:
        """Save database contents to a JSON file.

        Returns:
            Contents of the database as a Python dictionary. Format:
            {<table_name>: [{<col_name>: <col_value>}]}
        """
        db_data = {}
        db_data["students"] = self.get_all_students_dict()
        events = self.get_events_dict()
        excluded_columns = ["event_id", "day_of_week"]
        db_data["events"] = [
            {col: val for col, val in row.items() if col not in excluded_columns}
            for row in events
        ]
        attends = self.get_all_checkins_records_dict()
        excluded_columns = ["checkin_id", "event_date", "day_of_week"]
        db_data["checkins"] = [
            {col: val for col, val in row.items() if col not in excluded_columns}
            for row in attends
        ]
        return db_data

    def load_from_dict(
        self, db_data_dict: dict[str, list[dict[str, str | int | None]]]
    ) -> None:
        """Import data into the Sqlite database."""
        student_query = """
            INSERT INTO students
                        (student_id, first_name, last_name, email, grad_year)
                 VALUES (:student_id, :first_name, :last_name, :email, :grad_year);
        """
        checkins_query = """
            INSERT INTO checkins
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
            conn.executemany(event_query, db_data_dict["events"])
        with conn:
            conn.executemany(checkins_query, db_data_dict["checkins"])
        conn.close()

    def add_event(
        self,
        event_type: schema.EventType,
        event_date: Optional[datetime.date] = None,
        description: Optional[str] = None,
    ) -> None:
        """Add an event to the events table.

        Nothing happens if there is already an event on the same date with the
        same type.
        """
        if event_date is None:
            event_date = datetime.date.today()
        query = """
                INSERT INTO events (event_date, event_type, description)
                     VALUES (?, ?, ?)
                ON CONFLICT DO NOTHING;
        """
        with self.get_db_connection() as conn:
            conn.execute(
                query,
                (event_date.strftime("%Y-%m-%d"), event_type.value, description))
        conn.close()

    def get_events_dict(self) -> list[dict[str, Any]]:
        """Get all records from the events table."""
        query = """
                SELECT event_date, event_type, description
                  FROM events
              ORDER BY event_date, event_type;
        """
        conn = self.get_db_connection(as_dict=True)
        events = conn.execute(query).fetchall()
        conn.close()
        return events
