"""Database checkins table and associated queries.

A checkin occurs when a student scans their QR code at the attendance station.
A checkin consists of a student_id, timestamp, event_type, and a few other
fields.
"""

import dataclasses
import datetime
from typing import TYPE_CHECKING

from irsattend.model import events_mod


if TYPE_CHECKING:
    from irsattend.model import database


CHECKINS_TABLE_SCHEMA = """
CREATE TABLE IF NOT EXISTS checkins (
       checkin_id INTEGER PRIMARY KEY AUTOINCREMENT,
       student_id TEXT NOT NULL,
       event_date TEXT GENERATED ALWAYS AS (date(timestamp)) VIRTUAL,
      day_of_week INT GENERATED ALWAYS AS (strftime('%u', event_date)) VIRTUAL,
       event_type TEXT,
        timestamp TEXT NOT NULL,
      FOREIGN KEY (student_id) REFERENCES students (student_id),
      FOREIGN KEY (event_date, event_type) REFERENCES events (event_date, event_type),
       CONSTRAINT single_event_constraint UNIQUE(student_id, event_date, event_type)
);
"""


@dataclasses.dataclass
class Checkin:
    checkin_id: int
    student_id: str
    event_type: events_mod.EventType
    timestamp: datetime.datetime

    def __init__(
        self,
        checkin_id: int,
        student_id: str,
        event_type: str | events_mod.EventType,
        timestamp: datetime.datetime | str,
    ) -> None:
        """Ensure timestamp is converted to datetime.datetime."""
        if isinstance(timestamp, str):
            timestamp = datetime.datetime.fromisoformat(timestamp)
        if isinstance(event_type, str):
            event_type = events_mod.EventType(event_type)
        self.checkin_id = checkin_id
        self.student_id = student_id
        self.event_type = event_type
        self.timestamp = timestamp

    @property
    def event_date(self) -> datetime.date:
        """Date of the event as a datetime.date object."""
        return self.timestamp.date()

    @property
    def day_of_week(self) -> int:
        """Day of week as an integer with Monday = 1."""
        return self.event_date.weekday() + 1

    @staticmethod
    def to_iso_date(date: datetime.date) -> str:
        """Convert a datetime.date to an iso-formatted string."""
        return date.strftime("%Y-%m-%d")

    @property
    def iso_date(self) -> str:
        """Event date as an iso-formatted string."""
        return self.to_iso_date(self.event_date)

    def add(self, dbase: "database.DBase") -> int | None:
        """Add the checkin record to the database.

        Returns:
            The checkin ID of the newly added record, or None if the insert
            failed.
        """
        query = """
                INSERT INTO checkins
                            (student_id, event_type, timestamp)
                     VALUES (:student_id, :event_type, :timestamp);
        """
        with dbase.get_db_connection() as conn:
            cursor = conn.execute(
                query,
                {
                    "student_id": self.student_id,
                    "event_type": self.event_type.value,
                    "timestamp": self.timestamp,
                },
            )
            checkin_id = cursor.lastrowid
        conn.close()
        return checkin_id

    @staticmethod
    def get_all(dbase: "database.DBase") -> list["Checkin"]:
        """Retrieve a list of Checkin objects from the database."""
        query = """
                SELECT checkin_id, student_id, event_type, timestamp
                  FROM checkins
              ORDER BY timestamp;
        """
        conn = dbase.get_db_connection(as_dict=True)
        checkins = [Checkin(**checkin) for checkin in conn.execute(query)]
        conn.close()
        return checkins

    @classmethod
    def get_checkedin_students(
        cls,
        dbase: "database.DBase",
        event_date: datetime.date,
        event_type: events_mod.EventType,
    ) -> list[str]:
        """Get a list of student IDs who checked in for a given event."""
        query = """
                SELECT student_id
                  FROM checkins
                 WHERE event_date = ?
                   AND event_type = ?;
        """
        conn = dbase.get_db_connection()
        student_ids = [
            row["student_id"] for row in conn.execute(query, (event_date, event_type))
        ]
        conn.close()
        return student_ids

    @staticmethod
    def get_counts_by_student(
        dbase: "database.DBase", since: datetime.date
    ) -> dict[str, int]:
        """Get a dictionary of student IDs and their checkin counts."""
        conn = dbase.get_db_connection()
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

    @staticmethod
    def get_count(
        dbase: "database.DBase", event_date: datetime.date, event_type: events_mod.EventType
    ) -> int:
        """Count the number of checkins for a given event."""
        query = """
                SELECT COUNT(*) AS checkin_count
                  FROM checkins
                 WHERE event_date = ?
                   AND event_type = ?;
        """
        conn = dbase.get_db_connection()
        query_result = conn.execute(
            query, (event_date.strftime("%Y-%m-%d"), event_type)
        ).fetchone()
        conn.close()
        return query_result["checkin_count"]

    def to_dict(self) -> dict:
        """Convert the Checkin dataclass to a JSON-serializable dictionary."""
        return {
            "checkin_id": self.checkin_id,
            "student_id": self.student_id,
            "event_type": self.event_type,
            "timestamp": self.timestamp.isoformat(),
        }
