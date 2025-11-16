"""Database enumerations and table definitions.

## Students
Student names, email addresses, and graduation year.

## Attendence
Student IDs and datetimes that students check into the attendance system.

## Events
Event dates and types.

The day_of_week field is an integer ranging from 1 (Monday) to 7 (Sunday).
"""
import enum


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


ATTENDANCE_TABLE_SCHEMA = """
CREATE TABLE IF NOT EXISTS attendance (
    attendance_id INTEGER PRIMARY KEY AUTOINCREMENT,
       student_id TEXT NOT NULL,
       event_date TEXT GENERATED ALWAYS AS (date(timestamp)) VIRTUAL,
      day_of_week INT GENERATED ALWAYS AS (strftime('%u', event_date)) VIRTUAL,
       event_type TEXT,
        timestamp TEXT NOT NULL,
      FOREIGN KEY (student_id) REFERENCES students (student_id),
       CONSTRAINT single_event_constraint UNIQUE(student_id, event_date, event_type)
);
"""

EVENT_TABLE_SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
        event_id INTEGER PRIMARY KEY AUTOINCREMENT,
      event_date TEXT NOT NULL,
     day_of_week INT GENERATED ALWAYS AS (strftime('%u', event_date)) VIRTUAL,
      event_type TEXT NOT NULL,
     description TEXT,
      CONSTRAINT event_date_type_constraint UNIQUE(event_date, event_type)
);
"""

