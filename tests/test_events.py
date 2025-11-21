"""Test Sqlite event functionality."""

import datetime
import json
import pathlib
from typing import TYPE_CHECKING

import pytest
import rich  # noqa: F401

from irsattend.model import database, schema


DATA_FOLDER = pathlib.Path(__file__).parent / "data"


def test_get_events(full_dbase: database.DBase) -> None:
    """Get events as Event objects."""
    # Act
    events = full_dbase.get_events()
    # Assert
    assert all(isinstance(evt, schema.Event) for evt in events)
    assert isinstance(events[0].day_of_week, int)
    assert 1 <= events[0].day_of_week <= 7