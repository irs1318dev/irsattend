"""First screen that is displayed on app startup."""
import pathlib

import textual
from textual import app, binding, containers, reactive, screen, widgets

from irsattend import config
from irsattend.db import database


class IntroView(screen.Screen):
    """IRSAttend App Introduction Screen."""

    CSS_PATH = "../styles/intro.tcss"

    message = reactive.reactive("Initial Message!")

    def compose(self) -> app.ComposeResult:
        """Add widgets to screen."""
        yield widgets.Header()
        with containers.HorizontalGroup():
            yield widgets.Button("Take Attendance", id="take-attendance")
            yield widgets.Button("Register New Students", id="register-students")
            yield widgets.Button("View Attendance Records", id="view-records")
        with containers.HorizontalGroup():
            yield widgets.Label("Current Database: ", classes="irs-label")
            yield widgets.Label(str(config.settings.db_path))
            yield widgets.Button(
                "Configure Database", classes="right", id="config-database")
        with containers.HorizontalGroup():
            yield widgets.Label("Configuration File: ", classes="irs-label")
            yield widgets.Label(str(config.settings.config_path))
            yield widgets.Button("Edit Settings", classes="right", id="edit-settings")
        yield widgets.Label(
            "Nothing to see here!", id="intro-status-message", classes="irs-alert")
        yield widgets.Footer()

    def watch_message(self) -> None:
        """Update the status message on changes."""
        status_label = self.query_one("#intro-status-message", widgets.Label)
        status_label.update(self.message)
    
    @textual.on(widgets.Button.Pressed, "#take-attendance")
    def take_attendance(self):
        """Put application in attenance mode, so students can scan QR codes."""
        self.message = "Taking attendance is not yet implemented."

    @textual.on(widgets.Button.Pressed, "#register-students")
    def register_students(self):
        """Go to register students screen."""
        self.message = "Registering students is not yet implemented."

    @textual.on(widgets.Button.Pressed, "#view-records")
    def view_records(self):
        """View attendance records."""
        self.message = "Viewing attendance records is not yet implemented."

    @textual.on(widgets.Button.Pressed, "#config-database")
    def configure_database(self):
        """Select a different database file or create a new one."""
        self.message = "Configuring the database is not yet implemented."

    @textual.on(widgets.Button.Pressed, "#edit-settings")
    def edit_settings(self):
        """Go to the settings management screen."""
        self.message = "Editing settings is not yet implemented."
        