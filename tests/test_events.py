"""Test Sqlite event functionality."""

import pathlib
import datetime

import rich  # noqa: F401

from irsattend.model import database, schema
from irsattend.binders import events


DATA_FOLDER = pathlib.Path(__file__).parent / "data"


def test_get_events(full_dbase: database.DBase) -> None:
    """Get events as Event objects."""
    # Act
    events = schema.Event.get_all(full_dbase)
    # Assert
    assert all(isinstance(evt, schema.Event) for evt in events)
    assert isinstance(events[0].day_of_week, int)
    assert 1 <= events[0].day_of_week <= 7


def test_select_event(full_dbase: database.DBase) -> None:
    """Select a single event by date and type and handle missing event."""
    # Arrange
    expected_event = schema.Event.get_all(full_dbase)[-1]
    # Act
    event = schema.Event.select(
        full_dbase, expected_event.event_date, expected_event.event_type.value
    )
    # Assert
    assert isinstance(event, schema.Event)
    assert event.event_type == expected_event.event_type.value
    assert event.event_date == expected_event.event_date


def test_select_missing_event(full_dbase: database.DBase) -> None:
    """Select a non-existent event."""
    # Act
    event = schema.Event.select(
        full_dbase, datetime.date(2019, 12, 31), schema.EventType.OUTREACH.value
    )
    # Assert
    assert event is None


def test_update_event_description(full_dbase: database.DBase) -> None:
    """Change a record in the events table."""
    # Arrange
    event_to_update = schema.Event.get_all(full_dbase)[0]
    key_date = event_to_update.event_date
    key_type = event_to_update.event_type.value
    assert event_to_update.event_type == schema.EventType.MEETING
    assert event_to_update.description is None
    # Act
    event_to_update.update_description(full_dbase, "Test Opportunity")
    updated_event = schema.Event.select(full_dbase, key_date, key_type)
    # Assert
    assert updated_event is not None
    assert updated_event.description == "Test Opportunity"


def test_event_attendance(full_dbase: database.DBase) -> None:
    """Get event attendance data."""
    # Act
    event_checkins = events.CheckinEvent.get_checkin_events(full_dbase)
    # Assert
    assert len(event_checkins) > 20
    assert all(isinstance(event, events.CheckinEvent) for event in event_checkins)


def test_add_duplicate_event(full_dbase: database.DBase) -> None:
    """Add an event to the database."""
    # Arrange
    dupe_event = schema.Event.get_all(full_dbase)[0]
    # Act, Assert
    assert not dupe_event.add(full_dbase)  # Returns False if event already exists.


def test_add_new_event(full_dbase: database.DBase) -> None:
    """Add a new event to the database."""
    # Arrange
    new_event = schema.Event(
        event_date=datetime.date(2024, 12, 25),
        event_type=schema.EventType.OUTREACH,
        description="Christmas Outreach",
    )
    # Act, Assert
    assert new_event.add(full_dbase)  # Returns True if event was added.
    assert (
        schema.Event.select(
            full_dbase, datetime.date(2024, 12, 25), schema.EventType.OUTREACH.value
        )
        is not None
    )


def test_event_exists(full_dbase: database.DBase) -> None:
    """Check existence of an event in the database."""
    # Arrange
    existing_event = schema.Event.get_all(full_dbase)[0]
    missing_event = schema.Event(
        event_date=datetime.date(2025, 1, 1),
        event_type=schema.EventType.MEETING,
        description="New Year Meeting",
    )
    # Act, Assert
    assert existing_event.exists(full_dbase)
    assert not missing_event.exists(full_dbase)


def test_update_event_date(full_dbase: database.DBase) -> None:
    """Update the date of an existing event."""
    # Arrange
    event_to_update = schema.Event(
        datetime.date(2024, 1, 15),
        schema.EventType.NONE,
        description="Test Event for Date Update",
    )
    event_to_update.add(full_dbase)
    old_date = event_to_update.event_date
    new_date = old_date + datetime.timedelta(days=1)
    # Act
    event_to_update.update_event_date(full_dbase, new_date)
    updated_event = schema.Event.select(
        full_dbase, new_date, event_to_update.event_type.value
    )
    # Assert
    assert updated_event is not None
    assert updated_event.event_date == new_date
    assert not event_to_update.exists(full_dbase)


def test_update_event_type(full_dbase: database.DBase) -> None:
    """Update the type of an existing event."""
    # Arrange
    event_to_update = schema.Event.get_all(full_dbase)[0]
    event_to_update.add(full_dbase)
    new_type = schema.EventType.COMPETITION.value
    assert (
        schema.Checkin.get_count(full_dbase, event_to_update.event_date, new_type) == 0
    )
    # Act
    checkins_updated = event_to_update.update_event_type(full_dbase, new_type)
    updated_event = schema.Event.select(
        full_dbase, event_to_update.event_date, new_type
    )
    # Assert
    assert updated_event is not None
    assert updated_event.event_type == new_type
    assert checkins_updated >= 0
    assert (
        schema.Checkin.get_count(full_dbase, event_to_update.event_date, new_type)
        == checkins_updated
    )
    assert not event_to_update.exists(full_dbase)
