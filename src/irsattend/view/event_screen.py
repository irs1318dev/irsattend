"""Manage team events."""

import calendar
import datetime
from typing import Any, Optional

import dateutil.parser
import rich.text

import textual
from textual import app, binding, containers, reactive, screen, validation, widgets

from irsattend.model import config, database, schema


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
    events: dict[str, dict[str, Any]]
    """Event data that's displayed in the table."""
    # description = reactive.reactive(None)

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
        with containers.Horizontal(classes="menu"):
            yield widgets.Static("Future Button Bar")
        with containers.Horizontal():
            yield widgets.DataTable(id="events-table", classes="data-table")
            with containers.Vertical(classes="edit-pane"):
                yield widgets.Label("Date:")
                yield widgets.Input(
                    placeholder="MM/DD/YYYY",
                    validators=[DateValidator()],
                    id="event-date-input"
                )
                yield widgets.Label("Event Type:")
                yield widgets.Select(
                    [(etype.value.title(), etype.value) for etype in schema.EventType],
                    id="event-types-select"
                )
                yield widgets.Label("Description")
                yield widgets.Input(id="event-description-input")
        yield widgets.Footer()

    def on_mount(self) -> None:
        """Load data into the table."""
        self.load_table()

    def update_event_data(self) -> None:
        """Retrieve event data from the database."""
        self.events = {
            row["event_id"]: {
                key: val for key, val in dict(row).items() if key != "event_id"
            }
            for row in self.dbase.get_event_checkins()
        }

    def load_table(self) -> None:
        """Load attendance totals into the data table."""
        self.update_event_data()
        table = self.query_one("#events-table", widgets.DataTable)
        table.cursor_type = "row"
        for col in [
            ("ID", "event_id"),
            ("Date", "event_date"),
            ("Day of Week", "day_of_week"),
            ("Type", "event_type"),
            ("Attended", "total"),
            ("Description", "description")
        ]:
            table.add_column(col[0], key=col[1])
        for key, event in self.events.items():
            day_name = str(calendar.day_name[event["day_of_week"]-1])
            table.add_row(
                key,
                event["event_date"],
                rich.text.Text(day_name, justify="center"),
                event["event_type"],
                event["total"],
                event["description"],
                key=key
            )

    @textual.on(widgets.DataTable.RowSelected, "#events-table")
    def on_select_event(self, message: widgets.DataTable.RowSelected) -> None:
        """Select an event from the Events table."""
        date_input = self.query_one("#event-date-input", widgets.Input)
        if message.row_key.value is not None:
            short_date = (
                datetime.date.fromisoformat(
                    self.events[message.row_key.value]["event_date"]
                )
                .strftime("%m/%d/%Y")
            )

            date_input.value = short_date


class EventDialog(screen.ModalScreen):
    """Edit or add events."""

    CSS_PATH = "../styles/modal.tcss"

    def __init__(self, student_data: dict[str, Any] | None = None) -> None:
        self.student_data = student_data
        super().__init__()
        if not student_data:
            self.add_class("add-mode")
