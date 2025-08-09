from textual.app import App, ComposeResult
from textual.widgets import Label
import signal
import sys
from .db import database
from .ui.main_view import MainView
from .ui.management_view import ManagementView

class IRSAttend(App):
    CSS_PATH = "../styles/modal.tcss"
    TITLE = "IRS 1318 Attendance System"
    SCREENS = {
        "main": MainView,
        "management": ManagementView,
    }

    def __init__(self):
        super().__init__()

    def on_mount(self) -> None:
        """Called when the app is first mounted."""
        # Create the database tables if they don't exist
        database.create_tables()
        self.push_screen("main")
        
    def action_quit(self) -> None:
        self.exit()

def run_app():
    """Function to run the app, used for the setup.py entry_point."""
    app = IRSAttend()
    app.run()

if __name__ == "__main__":
    run_app()