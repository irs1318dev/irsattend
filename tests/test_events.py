"""Test Sqlite event functionality."""

import pathlib

import rich  # noqa: F401

from irsattend.model import database, schema
from irsattend.binders import events


DATA_FOLDER = pathlib.Path(__file__).parent / "data"


def test_get_events(full_dbase: database.DBase) -> None:
    """Get events as Event objects."""
    # Act
    events = schema.Event.get_events(full_dbase)
    # Assert
    assert all(isinstance(evt, schema.Event) for evt in events)
    assert isinstance(events[0].day_of_week, int)
    assert 1 <= events[0].day_of_week <= 7


def test_event_attendance(full_dbase: database.DBase) -> None:
    """Get event attendance data."""
    # Act
    event_checkins = events.CheckinEvent.get_checkin_events(full_dbase)
    # Assert
    assert len(event_checkins) > 20
    assert all(isinstance(event, events.CheckinEvent) for event in event_checkins)

