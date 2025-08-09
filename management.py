from textual.app import App, ComposeResult
from textual.containers import VerticalGroup, VerticalScroll, Container
from textual.binding import Binding
from textual.widgets import Header, Footer, DataTable, Static, Button

ROWS = [
    ("Date", "Student ID", "First name", "Last name", "Graduation Year", "Attendence #"),
    ("8/8/25", "_______", "Brianna", "Choy", 2027, "#")
]

class managementView(App):
    BINDINGS = [("q", "quit", "Close app")]
    CSS_PATH = "management.tcss"

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container(id = "grid"):
            with Container():
                yield DataTable()
            with VerticalScroll(id = "sideBar"):
                yield Button("Add Student(s)", classes = "green")
                yield Button("Import Student(s)", classes = "green")
                yield Button("Edit Student(s)", classes = "yellow")
                yield Button("Remove Student(s)", classes = "red")  
        yield Footer()
    
    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns(*ROWS[0])
        table.add_rows(ROWS[1:])
        table.zebra_stripes = True


app = managementView()
if __name__ == "__main__":
    app.run()