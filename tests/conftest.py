"""Pytest fixtures."""
import json
import pathlib
import shutil

import pytest

from irsattend.model import database


TEST_FOLDER = pathlib.Path(__file__).parent
DATA_FOLDER = TEST_FOLDER / "data"
OUTPUT_FOLDER = TEST_FOLDER / "output"


@pytest.fixture()
def empty_output_folder() -> pathlib.Path:
    """Create an empty output folder prior to each test."""
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
    return database.DBase(OUTPUT_FOLDER / "testdatabase.db", create_new=True)


@pytest.fixture
def full_dbase(empty_database: database.DBase) -> database.DBase:
    """Database with students, appearances, and events."""
    with open(DATA_FOLDER / "testdata-full.json") as jfile:
        attendance_data = json.load(jfile)
    empty_database.load_from_dict(attendance_data)
    return empty_database


@pytest.fixture
def noevents_dbase(empty_database: database.DBase) -> database.DBase:
    """Database with students."""
    with open(DATA_FOLDER / "testdata-full.json") as jfile:
        attendance_data = json.load(jfile)
    attendance_data["events"] = []
    attendance_data["attendance"] = []
    empty_database.load_from_dict(attendance_data)
    return empty_database


@pytest.fixture
def empty_database2(empty_output_folder: pathlib.Path) -> database.DBase:
    """An empty IrsAttend database, with tables created."""
    return database.DBase(OUTPUT_FOLDER / "testdatabase2.db", create_new=True)


@pytest.fixture
def attendance_test_data() -> dict[str, list]:
    """Get test data as a dictionary.
    
    Dictionary has three keys: students, attendance, and events, where each
    key is a list of dictionaries.
    """
    with open(DATA_FOLDER / "testdata-full.json") as jfile:
        test_data = json.load(jfile)
    return test_data
