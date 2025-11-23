"""Test Sqlite event functionality."""

import pathlib

import rich  # noqa: F401

from irsattend.model import database, schema


DATA_FOLDER = pathlib.Path(__file__).parent / "data"


def test_get_students(full_dbase: database.DBase) -> None:
    """Get events as Event objects."""
    # Act
    students = schema.Student.get_students(full_dbase)
    # Assert
    assert all(isinstance(student, schema.Student) for student in students)
    assert isinstance(students[0].grad_year, int)
