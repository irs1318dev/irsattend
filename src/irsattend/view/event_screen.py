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
        yield widgets.DataTable(id="events-table")
        yield widgets.Footer()

    def on_mount(self) -> None:
        """Load data into the table."""
        self.load_table()

    @textual.on(widgets.Button.Pressed, "#events-scan")
    def action_scan_for_events(self) -> None:
        self.dbase.scan_for_new_events()

    def load_table(self) -> None:
        """Load attendance totals into the data table."""
        table = self.query_one("#events-table", widgets.DataTable)
        for col in [
            ("Date", "event_date"), ("Type", "event_type"), ("Attended", "total")
        ]:
            table.add_column(col[0], key=col[1])
        attend_data = self.dbase.get_event_attendance()
        for row in attend_data:
            table.add_row(
                row["event_date"], row["event_type"], row["total"])