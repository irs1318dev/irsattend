"""Pytest fixtures."""
import pathlib
import shutil

import pytest

from irsattend.model import database


TEST_FOLDER = pathlib.Path(__file__).parent
DATA_FOLDER = TEST_FOLDER / "data"
OUTPUT_FOLDER = TEST_FOLDER / "output"


@pytest.fixture
def empty_output_folder() -> pathlib.Path:
    """Create an empty output folder, or clear out folder if already exists."""
    if OUTPUT_FOLDER.exists():
        for item in OUTPUT_FOLDER.iterdir():
            if item.is_dir():
                shutil.rmtree(item, ignore_errors=True)
            else:
                item.unlink()
    else:
        OUTPUT_FOLDER.mkdir(parents=True)
    return OUTPUT_FOLDER


@pytest.fixture
def empty_database(empty_output_folder: pathlib.Path) -> database.DBase:
    """An empty IrsAttend database, with tables created."""
    return database.DBase(OUTPUT_FOLDER / "teststudents.db", create_new=True)


@pytest.fixture
def dbase_with_students(empty_database: database.DBase) -> database.DBase:
    """Database with students."""
    empty_database.import_students_from_csv(DATA_FOLDER / "test-students.csv")
    return empty_database


@pytest.fixture
def dbase_with_raps(request) -> database.DBase:
    """Database with students and RAPs (robotics appearances)."""
    dbname = "testattend.db"
    shutil.copyfile(DATA_FOLDER / dbname, OUTPUT_FOLDER / dbname)
    return database.DBase(OUTPUT_FOLDER / dbname)
