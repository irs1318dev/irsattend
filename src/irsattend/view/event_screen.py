"""Manage team events."""

import calendar
import datetime
from typing import Optional

import dateutil.parser
import rich.text

import textual
from textual import app, binding, containers, screen, validation, widgets

from irsattend.model import config, database


class DateValidator(validation.Validator):
    """Validate user input."""

    def validate(self, value: str) -> validation.ValidationResult:
        """Verify input is a valid date."""
        try:
            dateutil.parser.parse(value, dayfirst=False).date()
            return self.success()
        except dateutil.parser.ParserError as err:
            return self.failure(str(err))


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
        with containers.Horizontal():
            with containers.Vertical(classes="data-table"):
                yield widgets.Button("Scan for Meetings", id="events-scan")
                yield widgets.DataTable(id="events-table")
            with containers.Vertical(classes="edit-pane"):
                yield widgets.Label("Date")
                yield widgets.Input(
                    placeholder="MM/DD/YYYY",
                    validators=[DateValidator()]
                )
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
        table.cursor_type = "row"
        for col in [
            ("Date", "event_date"),
            ("Day of Week", "day_of_week"),
            ("Type", "event_type"),
            ("Attended", "total"),
            ("Description", "description")
        ]:
            table.add_column(col[0], key=col[1])
        attend_data = self.dbase.get_event_checkins()
        for row in attend_data:
            day_name = str(calendar.day_name[row["day_of_week"]-1])
            table.add_row(
                row["event_date"],
                rich.text.Text(day_name, justify="center"),
                row["event_type"],
                row["total"],
                row["description"]
            )
