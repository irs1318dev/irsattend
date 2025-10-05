"""Update the Google Sheet roster with attendance data."""
import pathlib

import rich  # noqa: F401

from irsattend.model import database, google_tools

SETTINGS_PATH = pathlib.Path(r"C:\Users\stacy\projects\attendance\roster-settings.yaml")

REAL_DBASE_PATH = pathlib.Path(
    r"C:\Users\stacy\projects\attendance\attend-main.db"
)


def test_open_settings_and_authorization(dbase_with_apps) -> None:
    """Import Google Sheet settings."""
    # Act
    updater = google_tools.SheetUpdater(SETTINGS_PATH, dbase_with_apps)
    # Arrange
    assert isinstance(updater.roster_sheet_name, str)
    assert updater.roster_sheet_name


def test_sheet_titles(dbase_with_apps) -> None:
    """Get the worksheet titles."""
    # Act
    updater = google_tools.SheetUpdater(SETTINGS_PATH, dbase_with_apps)
    # Assert
    rich.print(updater.get_mapped_col_data("student_id"))

def test_student_ids() -> None:
    """Get the worksheet titles."""
    # Arrange
    dbase = database.DBase(REAL_DBASE_PATH)
    updater = google_tools.SheetUpdater(SETTINGS_PATH, dbase)
    print()
    # Act
    updater.insert_student_ids()
    # Assert
    # rich.print(updater._get_student_ids_from_database())


def test_update_attendance_data() -> None:
    """Send attendance data to the roster."""
    # Arrange
    dbase = database.DBase(REAL_DBASE_PATH)
    updater = google_tools.SheetUpdater(SETTINGS_PATH, dbase)
    print()
    # Act
    updater.insert_attendance_info()


def test_db_backup() -> None:
    """Send attendance data to the roster."""
    # Arrange
    dbase = database.DBase(REAL_DBASE_PATH)
    updater = google_tools.SheetUpdater(SETTINGS_PATH, dbase)
    print()
    # Act
    updater.backup_database_file()






