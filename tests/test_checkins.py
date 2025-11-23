"""Test Sqlite checkin functionality."""

import pathlib

import rich  # noqa: F401

from irsattend.model import database, schema


DATA_FOLDER = pathlib.Path(__file__).parent / "data"


def test_get_checkin_count(full_dbase: database.DBase) -> None:
    """Get number of checkins for an event."""
    # Arrange
    event = schema.Event.get_all(full_dbase)[0]
    # Act
    count = schema.Checkin.get_count(
        full_dbase, event.event_date, event.event_type.value
    )
    # Assert
    assert isinstance(count, int)
    assert count >= 0
    rich.print(f"\nCheckin count for event on {event.event_date}: {count}")
