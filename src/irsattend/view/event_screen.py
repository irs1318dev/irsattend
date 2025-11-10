"""Manage team events."""
import sqlite3
from typing import Optional

import textual
import textual.css.query
from textual import app, binding, containers, screen, widgets

from irsattend.model import config, database, emailer, qr_code_generator
from irsattend.view import modals, confirm_dialogs


class EventScreen(screen.Screen):
    """Add, delete, and edit students."""

    dbase: database.DBase
    """Connection to Sqlite Database."""
    _selected_student_id: Optional[str]
    """Currently selected student."""

    CSS_PATH = "../styles/management.tcss"
    BINDINGS = [
        binding.Binding("escape", "app.pop_screen", "Back to Main Screen", show=True),
    ]

    def __init__(self) -> None:
        """Initialize the databae connection."""
        super().__init__()
        if config.settings.db_path is None:
            raise database.DBaseError("No database file selected.")
        self.dbase = database.DBase(config.settings.db_path)

    def compose(self) -> app.ComposeResult:
        """Add the datatable and other controls to the screen."""
        yield widgets.Header()
        yield widgets.Button("Scan for Meetings", id="events-scan")
        yield widgets.DataTable(id="attendance-table")
        yield widgets.Footer()

    @textual.on(widgets.Button.Pressed, "#events-scan")
    def action_scan_for_events(self) -> None:
        self.dbase.scan_for_new_events()