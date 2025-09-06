"""Convert IrsAttend database files to newer versions.

Each migration function creates an empty IrsAttend database and loads data into
it from an earlier version of IrsAttend.
"""
import pathlib

import sqlite3

from irsattend.model import database



def to_0_2_0(
    source_db_path: pathlib.Path,
    new_db_path: pathlib.Path
) -> None:
    """Migrate database from version 0.1.0 to 0.2.0.
    
    ## Attendance Table
    * Change the timestamp column to TEXT data type.
    * Add a calculated event_date column.
    * Add an event_type column.
    """
    if not source_db_path.exists():
        raise database.DBaseError(
            f"Source sqlite3 file does not exist at {source_db_path}")
    source_conn = sqlite3.connect(source_db_path)
    source_conn.row_factory = database.dict_factory
    newdb = database.DBase(new_db_path, create_new=True)

    for student in source_conn.execute("SELECT * FROM students;"):
        with newdb.get_db_connection() as new_conn:
            new_conn.execute("""
                INSERT INTO students
                            (student_id, first_name, last_name, email, grad_year)
                     VALUES (:student_id, :first_name, :last_name, :email, :grad_year);
                """,
                student,
            )

    for appearance in source_conn.execute("SELECT * FROM attendance;"):
        with newdb.get_db_connection() as new_conn:
            if "event_type" not in appearance:
                appearance["event_type"] = "meeting"
            new_conn.execute("""
                INSERT INTO attendance
                            (student_id, event_type, timestamp)
                     VALUES (:student_id, :event_type, :timestamp);
            """,
            appearance
            )