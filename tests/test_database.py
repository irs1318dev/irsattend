"""Test Sqlite database functionality."""
import datetime
import pathlib
import re

import polars as pl
import pytest
import rich  # noqa: F401

from irsattend.model import database


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
    assert len(tables) == 3
    assert "students" in tables
    assert "attendance" in tables
    # Must close connection or fixtures won't be able to delete Sqlite3 file when
    #   setting up for other tests.
    conn.close()  


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


def test_load_students_from_csv(dbase_with_students: database.DBase) -> None:
    """Load test students from a CSV file."""
    students = dbase_with_students.get_all_students()
    assert len(students) > 100
    id_pattern = re.compile(r"\w+-\w+-\d{4}-\d{3}")
    for student in students:
        assert id_pattern.fullmatch(student["student_id"]) is not None
        grad_year = student["grad_year"]
        assert isinstance(grad_year, int)
        assert 2020 <= grad_year <= 2030
        assert "@" in student["email"]
        assert "." in student["email"]


def test_attendance_table(dbase_with_apps) -> None:
    """Attendance table has many rows and 5 columns of data."""
    # Act
    rapdf = dbase_with_apps.get_attendance_dataframe()
    # Assert
    print(rapdf.shape)
    assert rapdf.shape[0] > 4000
    assert rapdf.shape[1] == 5


def test_attendance_counts(dbase_with_apps: database.DBase) -> None:
    """Get count of student appearances."""
    # Act
    season_counts = dbase_with_apps.get_attendance_counts(datetime.date(2025, 9, 1))
    build_counts = dbase_with_apps.get_attendance_counts(datetime.date(2026, 1, 1))
    # Assert
    assert len(season_counts) == len(build_counts)
    for student_id in season_counts:
        assert student_id in build_counts
        assert isinstance(season_counts[student_id], int)
        assert isinstance(build_counts[student_id], int)
        assert season_counts[student_id] >= build_counts[student_id]
        assert build_counts[student_id] >= 0


def test_attendance_report_data(dbase_with_apps: database.DBase) -> None:
    """Get info for student attendance report."""
    # Act
    cursor = dbase_with_apps.get_student_attendance_data()
    # Assert
    for row in cursor:
        rich.print(dict(row))


def test_to_dict(dbase_with_apps: database.DBase) -> None:
    """Save database contents to a JSON file."""
    # Act
    data = dbase_with_apps.to_dict()
    # Assert
    tables = ["students", "attendance"]
    assert len(data) == len(tables)
    assert all(col in data for col in tables)
    for table in tables:
        assert isinstance(data[table], list)
        assert len(data[table]) >= 10


def test_from_dict(
    dbase_with_apps: database.DBase,
    empty_database2: database.DBase
) -> None:
    """Import student data from a dictionay into an empty database."""
    # Arrange
    exported_data = dbase_with_apps.to_dict()
    # Act
    empty_database2.load_from_dict(exported_data)
    # Assert
    students = empty_database2.get_all_students(as_dict=True)
    assert len(students) == len(dbase_with_apps.get_all_students())
    attendance = empty_database2.get_all_attendance_records(as_dict=True)
    assert len(attendance) == len(dbase_with_apps.get_all_attendance_records())

