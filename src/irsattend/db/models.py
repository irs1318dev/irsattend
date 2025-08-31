# Main database schema

STUDENT_TABLE_SCHEMA = """
CREATE TABLE IF NOT EXISTS students (
    student_id TEXT PRIMARY KEY,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    email TEXT NOT NULL,
    grad_year INTEGER NOT NULL
);
"""
# TODO: Add unique constraint to email field. Constraint was removed for development
#   and testing.

# TODO: Add field(s) for year joined and status (e.g., active, inactive, alumni)

ATTENDANCE_TABLE_SCHEMA = """
CREATE TABLE IF NOT EXISTS attendance (
    attendance_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    timestamp DATETIME NOT NULL,
    FOREIGN KEY (student_id) REFERENCES students (student_id)
);
"""

