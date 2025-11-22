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


EVENT_TABLE_SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
     event_date TEXT NOT NULL,
    day_of_week INT GENERATED ALWAYS AS (strftime('%u', event_date)) VIRTUAL,
     event_type TEXT NOT NULL,
    description TEXT,
    PRIMARY KEY (event_date, event_type) ON CONFLICT IGNORE
);
"""

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
    
    @staticmethod
    def get_events(dbase: "database.DBase") -> list["Event"]:
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

 
