"""Show attendance results."""
from textual import app, binding, screen, widgets

from irsattend.model import config, database


class AttendanceScreen(screen.Screen):
    """Add, delete, and edit students."""

    dbase: database.DBase
    """Connection to Sqlite Database."""
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
        yield widgets.Button("Do Stuff")
        yield widgets.DataTable(id="attendance-table")
        yield widgets.Footer()

    def on_mount(self) -> None:
        """Load data into the table."""
        self.load_table()

    def load_table(self) -> None:
        """Load attendance totals into the data table."""
        table = self.query_one("#attendance-table", widgets.DataTable)
        for col in [("Last Name", "last_name"), ("First Name", "first_name"),
                    ("Season Apps", "season_apps"), ("Build Apps", "build_apps")]:
            table.add_column(col[0], key=col[1])
        cursor = self.dbase.get_student_attendance_data() 
        for row in cursor:
            table.add_row(row[1], row[2], row[4], row[5], key=row[0])
        cursor.connection.close()