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
from typing import Any, Optional, Sequence

import sqlite3


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


STUDENT_TABLE_SCHEMA = """
CREATE TABLE IF NOT EXISTS students (
    student_id TEXT PRIMARY KEY,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    grad_year INTEGER NOT NULL
);
"""
# TODO: Add field(s) for year joined and status (e.g., active, inactive, alumni)


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
    event_date: datetime.date
    event_type: EventType
    description: Optional[str]

    def __init__(
            self,
            event_date: datetime.date | str,
            event_type: EventType,
            description: Optional[str] = None
    ) -> None:
        """ensure event_date is converted to datetime.date."""
        if isinstance(event_date, str):
            event_date = datetime.date.fromisoformat(event_date)
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
    def from_dict(event: dict[str, Any]) -> "Event":
        """Convert a dictionary to an Event."""
        if isinstance(event["event_date"], str):
            event_date = datetime.date.fromisoformat(event["event_date"])
        else:
            event_date = event["event_date"]
        return Event(event_date, event["event_type"], event["description"])
    
    @staticmethod
    def from_list(events: Sequence[dict[str, Any] | sqlite3.Row]) -> list["Event"]:
        """Convert a list of dictionaries or Row objects to a list of Events."""
        return [
            Event(event["event_date"], event["event_type"], event["description"])
            for event in events
        ]

 
