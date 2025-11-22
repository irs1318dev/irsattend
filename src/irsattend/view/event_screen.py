"""Manage team events."""

from typing import Any

import dateutil.parser
import rich.text

import textual
from textual import app, binding, containers, reactive, screen, validation, widgets

from irsattend.binders import events
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
        

class EventsTable(widgets.DataTable):
    """Table of team events and number of students who attended."""

    dbase: database.DBase
    """Connection to Sqlite Database."""
    checkin_events: dict[str, events.CheckinEvent]
    """Event data that's displayed in the table."""

    def __init__(self, dbase: database.DBase, *args, **kwargs) -> None:
        """Set link to database."""
        super().__init__(*args, **kwargs)
        self.dbase = dbase
        self.checkin_events = {}

    def on_mount(self) -> None:
        """Initialize the table."""
        self.initialize_table()
        self.update_table()

    def initialize_table(self) -> None:
        """Load attendance totals into the data table."""
        self.cursor_type = "row"
        for col in [
            ("Date", "event_date"),
            ("Day of Week", "day_of_week"),
            ("Type", "event_type"),
            ("Count", "checkin_count"),
            ("Description", "description")
        ]:
            self.add_column(col[0], key=col[1])
    
    def update_table(self) -> None:
        """Populate the table with data."""
        self.clear(columns=False)
        self.checkin_events = {
            event.key: event
            for event in events.CheckinEvent.get_checkin_events(self.dbase)
        }
        for key, event in self.checkin_events.items():
            self.add_row(
                event.iso_date,
                rich.text.Text(event.weekday_name, justify="center"),
                event.event_type,
                event.checkin_count,
                event.description,
                key=key
            )

class StudentsTable(widgets.DataTable):
    """Table of students who checked in at the selected event."""

    dbase: database.DBase
    """Connection to Sqlite Database."""
    students: dict[str, events.EventStudent]
    """Students who checked in at that selected event."""
    event_key = reactive.reactive("")
    """Contains the currently selected event."""

    def __init__(self, dbase: database.DBase, *args, **kwargs) -> None:
        """Set link to database."""
        super().__init__(*args, **kwargs)
        self.dbase = dbase
        self.students = {}

    def on_mount(self) -> None:
        """Initialize the table."""
        self.initialize_table()

    def initialize_table(self) -> None:
        """Load attendance totals into the data table."""
        for col in [
            ("Student ID", "student_id"),
            ("First Name", "first_name"),
            ("Last Name", "last_name"),
            ("Graduation Year", "grad_year"),
            ("Check-in time", "timestamp")
        ]:
            self.add_column(col[0], key=col[1])
    
    def watch_event_key(self) -> None:
        """Add events to the event table."""
        if not self.event_key:
            return
        self.clear(columns=False)
        self.students = {
            student.student_id: student
            for student in events.EventStudent.get_students_for_event(
                self.dbase, self.event_key)
        }
        for key, student in self.students.items():
            self.add_row(
                student.student_id,
                student.first_name,
                student.last_name,
                student.grad_year,
                student.timestamp,
                key=key
            )


class EventScreen(screen.Screen):
    """Add, delete, and edit students."""

    CSS_PATH = "../styles/management.tcss"
    BINDINGS = [
        binding.Binding("escape", "app.pop_screen", "Back to Main Screen", show=True),
    ]
    dbase: database.DBase
    """Connection to Sqlite Database."""
    event_key: reactive.reactive[str | None] = reactive.reactive(None)
    """Contains the currently selected event."""

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
            yield widgets.Button("Add Event")
        events_table = EventsTable(dbase=self.dbase, id="events-table")
        yield events_table
        yield widgets.Static("Students at Selected Event", classes="separator")
        students_table = StudentsTable(dbase=self.dbase, id="events-students-table")
        students_table.data_bind(EventScreen.event_key)
        yield students_table
        yield widgets.Footer()

    @textual.on(widgets.DataTable.RowHighlighted)
    def on_events_table_row_highlighted(self, message: widgets.DataTable.RowSelected) -> None:
        """Set the new event key, which will trigger a student table update."""
        self.event_key = message.row_key.value

    @textual.on(widgets.DataTable.RowSelected)
    def on_events_table_row_selected(self, message: widgets.DataTable.RowSelected) -> None:
        """Set the new event key, which will trigger a student table update."""
        self.event_key = message.row_key.value





class EventDialog(screen.ModalScreen):
    """Edit or add events."""

    CSS_PATH = "../styles/modal.tcss"

    def __init__(self, student_data: dict[str, Any] | None = None) -> None:
        self.student_data = student_data
        super().__init__()
        if not student_data:
            self.add_class("add-mode")


    def compose(self) -> app.ComposeResult:
        """Add the datatable and other controls to the screen."""
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