from textual.app import ComposeResult
from textual.screen import Screen
from textual.binding import Binding
from textual.widgets import Header, Footer, DataTable, Static, Button, Label
from textual.containers import Vertical, Horizontal

ROWS = [
    ("Date", "Student ID", "First name", "Last name", "Email", "Graduation Year", "Attendance Count"),
    ("8/8/25", "0000000", "Brianna", "Choy", "brianna@example.com", 2027, "#")
]

class ManagementView(Screen):
    CSS_PATH = "../styles/management.tcss"
    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back to Main Screen", show=True),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            with Vertical(id="student-list-container"):
                yield Label("Student List")
                yield DataTable(id="student-table")
            with Vertical(id="actions-container"):
                yield Label("Actions")
                yield Static("No student selected", id="selection-indicator", classes="selection-info")
                yield Static()
                yield Button("Add Student", variant="success", id="add-student")
                yield Button("Import from CSV", variant="success", id="import-csv")
                yield Button("Edit Selected", id="edit-student", disabled=True)
                yield Button("Delete Selected", variant="error", id="delete-student", disabled=True)
                yield Static()
                yield Label("Communication")
                yield Button("Email Barcode to Selected", id="email-qr", disabled=True) # TODO implement email functionality
                yield Button("Email All Barcodes", id="email-all-qr")
                yield Static(id="status-message", classes="status") # To be used for error and success messages

        yield Footer()
    
    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.cursor_type = "row"
        table.add_columns(*ROWS[0])
        table.add_rows(ROWS[1:])
        table.zebra_stripes = True
        
    # TODO implement db get and actions for buttons
    
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "add-student":
            await self.action_add_student() # TODO
        elif event.button.id == "import-csv":
            await self.action_import_csv() # TODO
        elif event.button.id == "edit-student":
            await self.action_edit_student() # TODO
        elif event.button.id == "delete-student":
            await self.action_delete_student() # TODO
        elif event.button.id == "email-qr":
            self.action_email_qr() # TODO
        elif event.button.id == "email-all-qr":
            self.action_email_qr_all() # TODO