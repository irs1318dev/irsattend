"""Test Sqlite database functionality."""
import datetime
import json
import pathlib

import polars as pl
import pytest
import rich  # noqa: F401

from irsattend.model import database, db_tables


DATA_FOLDER = pathlib.Path(__file__).parent / "data"


# def test_merge() -> None:
#     """Test merging two databases."""
#     # Arrange
#     incoming_db_path = pathlib.Path(DATA_FOLDER / "rookies-0_2_0.db")
#     main_db_path = pathlib.Path(DATA_FOLDER / "main-0_2_0.db")
#     incoming_db = database.DBase(incoming_db_path)
#     main_db = database.DBase(main_db_path)
#     # Act
#     main_db.merge_database(incoming_db)


# def test_export_excel() -> None:
#     """Export to excel."""
#     main_db = database.DBase(DATA_FOLDER / "main-0_2_0.db")
#     attendance_df = main_db.get_attendance_dataframe()
#     attendance_df.write_excel(DATA_FOLDER / "main-0_2_0.xlsx")

def test_empty_database(empty_database: database.DBase) -> None:
    """Create an empty IrsAttend database."""
    # Assert
    query = "SELECT name FROM sqlite_schema WHERE type = 'table';"
    with empty_database.get_db_connection() as conn:
        tables = set(row["name"] for row in conn.execute(query))
    conn.close()  
    assert len(tables) == 4
    assert "students" in tables
    assert "attendance" in tables
    # Must close connection or fixtures won't be able to delete Sqlite3 file when
    #   setting up for other tests.



def test_nonexistant_database_raises_error(empty_output_folder: pathlib.Path) -> None:
    """Raise an error if a database doesn't exist."""
    # Act, Assert
    with pytest.raises(database.DBaseError):
        database.DBase(empty_output_folder / "irsattend.db")


def test_existing_database_raises_error_on_create_new(empty_database) -> None:
    """Raise an error if create_new = True and database file already exists."""
    # Act, Assert
    with pytest.raises(database.DBaseError):
        database.DBase(empty_database.db_path, create_new=True)


def test_attendance_table(full_dbase: database.DBase) -> None:
    """Attendance table has many rows and 5 columns of data."""
    # Act
    rapdf = full_dbase.get_attendance_dataframe()
    # Assert
    assert rapdf.shape[0] > 4000
    assert rapdf.shape[1] == 6

def test_attendance_counts(full_dbase: database.DBase) -> None:
    """Get count of student appearances."""
    # Act
    season_counts = full_dbase.get_attendance_counts(datetime.date(2025, 9, 1))
    build_counts = full_dbase.get_attendance_counts(datetime.date(2026, 1, 1))
    # Assert
    assert len(season_counts) == len(build_counts)
    for student_id in season_counts:
        assert student_id in build_counts
        assert isinstance(season_counts[student_id], int)
        assert isinstance(build_counts[student_id], int)
        assert season_counts[student_id] >= build_counts[student_id]
        assert build_counts[student_id] >= 0


def test_attendance_report_data(full_dbase: database.DBase) -> None:
    """Get info for student attendance report."""
    # Act
    cursor = full_dbase.get_student_attendance_data()
    # Assert
    for row in cursor:
        rich.print(dict(row))
    cursor.connection.close()


def test_to_dict(full_dbase: database.DBase) -> None:
    """Save database contents to a JSON file."""
    # Act
    data = full_dbase.to_dict()
    # Assert
    tables = ["students", "attendance", "events"]
    assert len(data) == len(tables)
    assert all(col in data for col in tables)
    for table in tables:
        assert isinstance(data[table], list)
        assert len(data[table]) >= 10

    with open(full_dbase.db_path.parent / "testdata.json", "wt") as jfile:
        json.dump(data, jfile, indent=2)


def test_from_dict(
    full_dbase: database.DBase,
    empty_database2: database.DBase
) -> None:
    """Import student data from a dictionay into an empty database."""
    # Arrange
    exported_data = full_dbase.to_dict()
    # Act
    empty_database2.load_from_dict(exported_data)
    # Assert
    students = empty_database2.get_all_students(as_dict=True)
    assert len(students) == len(full_dbase.get_all_students())
    attendance = empty_database2.get_all_attendance_records(as_dict=True)
    assert len(attendance) == len(full_dbase.get_all_attendance_records())


def test_scan_event(noevents_dbase: database.DBase) -> None:
    """Scan attendance records for missing events."""
    # Act
    atts = noevents_dbase.scan_for_new_events()


def test_event_attendance(full_dbase: database.DBase) -> None:
    """Get event attendance data."""
    # Act
    attend_data = full_dbase.get_event_attendance()
    # Assert
    assert len(attend_data) > 20
    field_names = ["event_date", "day_of_week", "event_type", "total", "description"]
    for field in field_names:
        assert field in attend_data[0]
    assert len(attend_data[0]) == len(field_names)
    prior_event_date = datetime.date.fromisoformat(attend_data[0]["event_date"])
    # Event dates are in chronological order.
    for event in attend_data[1:]:
        current_date = datetime.date.fromisoformat(event["event_date"])
        assert current_date >= prior_event_date
        prior_event_date = current_date
        assert 1 <= event["day_of_week"] <= 7
        assert event["total"] >= 0
    rich.print(attend_data)


def test_add_event(noevents_dbase: database.DBase) -> None:
    """Add an event to the events table."""
    # Arrange
    edate = datetime.date(2026, 1, 10)
    desc = "Multiteam kickoff event at Auburn H.S."
    # Act
    noevents_dbase.add_event(db_tables.EventType.KICKOFF, edate, desc)
    # Assert
    events = noevents_dbase.get_events(as_dict=True)
    assert len(events) == 1
    assert events[0]["event_type"] == db_tables.EventType.KICKOFF
    assert events[0]["event_date"] == edate.isoformat()
    assert events[0]["description"] == desc


def test_add_duplicate_event_does_nothing(noevents_dbase: database.DBase) -> None:
    """Do not add any records to the events table when event is a duplicate."""
    # Arrange
    edate = datetime.date(2026, 1, 10)
    desc = "Multiteam kickoff event at Auburn H.S."
    noevents_dbase.add_event(db_tables.EventType.KICKOFF, edate, desc)
    # Act
    noevents_dbase.add_event(db_tables.EventType.KICKOFF, edate, "duplicate")
    # Assert
    events = noevents_dbase.get_events(as_dict=True)
    assert len(events) == 1
    assert events[0]["description"] == desc


def test_add_checkin(
    attendance_test_data: dict[str, list],
    noevents_dbase: database.DBase
) -> None:
    """Add a student checkin."""
    # Arrange
    students = attendance_test_data["students"]
    # Act
    noevents_dbase.add_attendance_record(
        students[0]["student_id"],
        timestamp="2025-11-15 09:00:00",
        event_type=db_tables.EventType.COMPETITION
    )
    # Assert
    checkins = noevents_dbase.get_all_attendance_records(as_dict=True)
    assert len(checkins) == 1
    assert checkins[0]["student_id"] == students[0]["student_id"]
    assert checkins[0]["event_type"] == db_tables.EventType.COMPETITION.value
    assert checkins[0]["event_date"] == "2025-11-15"