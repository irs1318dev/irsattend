"""Database enumerations and table definitions.

## Students
Student names, email addresses, and graduation year.

## Checkins
Student IDs and datetimes that students check into the attendance system.

## Events
Event dates and types.

The day_of_week field is an integer ranging from 1 (Monday) to 7 (Sunday).
"""

import dataclasses
import datetime
import enum
from typing import Optional, TYPE_CHECKING


if TYPE_CHECKING:
    from irsattend.model import database


STUDENT_TABLE_SCHEMA = """
CREATE TABLE IF NOT EXISTS students (
    student_id TEXT PRIMARY KEY,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    grad_year INTEGER NOT NULL
);
"""


@dataclasses.dataclass
class Student:
    """An FRC student."""
    student_id: str
    first_name: str
    last_name: str
    grad_year: int
    email: str

    @staticmethod
    def get_students(dbase: "database.DBase") -> list["Student"]:
        """Retrieve a list of Student objects from the database."""
        query = """
            SELECT student_id, last_name, first_name, grad_year, email
             FROM students
         ORDER BY student_id;
        """
        conn = dbase.get_db_connection(as_dict=True)
        students = [
            Student(**student) for student in conn.execute(query)
        ]
        conn.close()
        return students


class EventType(enum.StrEnum):
    """Types of events at which we take attendance."""

    COMPETITION = "competition"
    KICKOFF = "kickoff"
    MEETING = "meeting"
    NONE = "none"
    OPPORTUNITY = "opportunity"
    OUTREACH = "outreach"
    VIRTUAL = "virtual"
    VOLUNTEERING = "volunteering"


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
    event_type: EventType
    timestamp: datetime.datetime

    def __init__(
            self,
            checkin_id: int,
            student_id: str,
            event_type: str | EventType,
            timestamp: datetime.datetime | str
    ) -> None:
        """Ensure timestamp is converted to datetime.datetime."""
        if isinstance(timestamp, str):
            timestamp = datetime.datetime.fromisoformat(timestamp)
        if isinstance(event_type, str):
            event_type = EventType(event_type)
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
    def get_count(
        dbase: "database.DBase",
        event_date: datetime.date,
        event_type: str
    ) -> int:
        """Count the number of checkins for a given event."""
        query = """
                SELECT COUNT(*) AS checkin_count
                  FROM checkins
                 WHERE event_date = ?
                   AND event_type = ?;
        """
        conn = dbase.get_db_connection()
        query_result = (
            conn.execute(
                query,
                (event_date.strftime("%Y-%m-%d"), event_type)
            )
            .fetchone()
        )
        conn.close()
        return query_result["checkin_count"]


EVENT_TABLE_SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
     event_date TEXT NOT NULL,
    day_of_week INT GENERATED ALWAYS AS (strftime('%u', event_date)) VIRTUAL,
     event_type TEXT NOT NULL,
    description TEXT,
    PRIMARY KEY (event_date, event_type) ON CONFLICT IGNORE
);
"""


class EventUpateError(Exception):
    """Raised when an event update fails."""
    pass


@dataclasses.dataclass
class Event:
    """An event at which we record attendance."""
    event_date: datetime.date
    event_type: EventType
    description: Optional[str]

    def __init__(
            self,
            event_date: datetime.date | str,
            event_type: str | EventType,
            description: Optional[str] = None,
    ) -> None:
        """Ensure event_date is converted to datetime.date."""
        if isinstance(event_date, str):
            event_date = datetime.date.fromisoformat(event_date)
        if isinstance(event_type, str):
            event_type = EventType(event_type)
        self.event_date = event_date
        self.event_type = event_type
        self.description = description

    @property
    def iso_date(self) -> str:
        """Event date as an iso-formatted string."""
        return self.event_date.strftime("%Y-%m-%d")
    
    @property
    def day_of_week(self) -> int:
        """Day of week as an integer with Monday = 1."""
        return self.event_date.weekday() + 1
    
    @property
    def weekday_name(self) -> str:
        """Day of week as a string: 'Monday', 'Tuesday', etc."""
        return self.event_date.strftime("%A")
    
    @property
    def key(self) -> str:
        """String that uniquely identifies the event."""
        return f"{self.iso_date}::{self.event_type.value}"
    
    def exists(
            self,
            dbase: "database.DBase"
    ) -> bool:
        """Check if the event exists in the database."""
        query = """
                SELECT 1
                  FROM events
                 WHERE event_date = ?
                   AND event_type = ?;
        """
        conn = dbase.get_db_connection()
        query_result = (
            conn.execute(
                query,
                (self.event_date.strftime("%Y-%m-%d"), self.event_type.value)
            )
            .fetchone()
        )
        conn.close()
        return query_result is not None
    
    def add(
            self,
            dbase: "database.DBase"
    ) -> bool:
        """Add the event to the database.
        
        Return True if the event was added, False if it already existed.
        """
        query = """
                INSERT INTO events
                            (event_date, event_type, description)
                     VALUES (:event_date, :event_type, :description);
        """
        with dbase.get_db_connection() as conn:
            cursor = conn.execute(query, {
                "event_date": self.event_date,
                "event_type": self.event_type.value,
                "description": self.description
            })
        row_count = cursor.rowcount
        conn.close()
        return row_count == 1
    
    def delete(
            self,
            dbase: "database.DBase"
    ) -> bool:
        """Delete the event from the database.
        
        Return True if the event was deleted, False if it did not exist.
        """
        query = """
                DELETE FROM events
                      WHERE event_date = :event_date
                        AND event_type = :event_type;
        """
        with dbase.get_db_connection() as conn:
            cursor = conn.execute(query, {
                "event_date": self.event_date,
                "event_type": self.event_type.value
            })
        row_count = cursor.rowcount
        conn.close()
        return row_count == 1

    @staticmethod
    def select(
        dbase: "database.DBase",
        event_date: datetime.date,
        event_type: str
    ) -> "Event | None":
        """Retrieve a single event."""
        query = """
                SELECT event_date, event_type, description
                  FROM events
                 WHERE event_date = ?
                   AND event_type = ?;
        """
        conn = dbase.get_db_connection(as_dict=True)
        query_result = (
            conn.execute(
                query,
                (event_date.strftime("%Y-%m-%d"), event_type)
            )
            .fetchone()
        )
        event = None if query_result is None else Event(**query_result)
        conn.close()
        return event
    
    @staticmethod
    def get_all(dbase: "database.DBase") -> list["Event"]:
        """Retrieve a list of Student objects from the database."""
        query = """
                SELECT event_date, event_type, description
                  FROM events
              ORDER BY event_date, event_type;
        """
        conn = dbase.get_db_connection(as_dict=True)
        events = [
            Event(**event) for event in conn.execute(query)
        ]
        conn.close()
        return events
    
    def update_description(
            self,
            dbase: "database.DBase",
            description: str
    ) -> None:
        """Update the event in the database."""
        query = """
                UPDATE events
                   SET description = :description
                 WHERE event_type = :event_type AND event_date = :event_date;
        """
        with dbase.get_db_connection() as conn:
            conn.execute(query, {
                "event_date": self.event_date,
                "event_type": self.event_type.value,
                "description": description
            })
        conn.close()
   
    def update_event_type(
            self,
            dbase: "database.DBase",
            new_type: str
    ) -> int:
        """Update the event type in the database.

        Returns:
          Number of checkins updated.

        Raises:
          EventUpdateError: If the update could not be performed.
        """
        if not self.exists(dbase):
            raise EventUpateError("Original event does not exist.")
        updated_event = Event(self.event_date, new_type, self.description)
        if not updated_event.add(dbase):
            raise EventUpateError(
                "Cannot update event; target event already exists.")
        # Update checkins to reference the new event date and type.
        checkins_query = """
                UPDATE checkins
                   SET event_type = :new_type
                 WHERE event_date = :event_date
                   AND event_type = :event_type;
        """
        with dbase.get_db_connection() as conn:
            cursor = conn.execute(checkins_query, {
                "event_date": self.event_date,
                "event_type": self.event_type.value,
                "old_date": self.event_date.isoformat(),
                "new_type": new_type
            })
            checkins_updated = cursor.rowcount
        conn.close()
        self.delete(dbase)
        return checkins_updated
    
    def update_event_date(
            self,
            dbase: "database.DBase",
            new_date: datetime.date
    ) -> None:
        """Update the event date in the database.

        Raises:
          EventUpdateError: If the update could not be performed.
        """
        if not self.exists(dbase):
            raise EventUpateError("Original event does not exist.")
        checkin_counts = Checkin.get_count(
            dbase, self.event_date, self.event_type.value)
        if checkin_counts > 0:
            raise EventUpateError(
                "Cannot change date; checkins exist for this event.")
        updated_event = Event(new_date, self.event_type.value, self.description)
        if not updated_event.add(dbase):
            raise EventUpateError(
                "Cannot update event; target event already exists.")
        self.delete(dbase)



 
