"""Database table definitions."""

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
    event_type TEXT,
    timestamp TEXT NOT NULL,
    FOREIGN KEY (student_id) REFERENCES students (student_id),
    CONSTRAINT single_event_constraint UNIQUE(student_id, event_date, event_type)
);
"""

