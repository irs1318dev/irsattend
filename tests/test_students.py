"""Test Sqlite student functionality."""

import pathlib

import rich  # noqa: F401

from irsattend.model import database, students_mod

DATA_FOLDER = pathlib.Path(__file__).parent / "data"


def test_get_students(full_dbase: database.DBase) -> None:
    """Get events as Event objects."""
    # Act
    students = students_mod.Student.get_all(full_dbase)
    # Assert
    assert all(isinstance(student, students_mod.Student) for student in students)
    assert isinstance(students[0].grad_year, int)


