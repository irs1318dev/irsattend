"""First screen that is displayed on app startup."""
import pathlib

import textual
from textual import app, containers, reactive, screen, widgets

from irsattend import config
from irsattend.db import database
from irsattend.ui import management_view, scan_view
from irsattend.utils import files


class IntroView(screen.Screen):
    """IRSAttend App Introduction Screen."""

    CSS_PATH = "../styles/intro.tcss"
    BINDINGS = [
        ("a", "take_attendance", "Take Attendance"),
        ("r", "register_students", "Register Students"),
        ("v", "view_records", "View Attendance Records"),
    ]

    db_path = reactive.reactive(str(config.settings.db_path))
    message = reactive.reactive("Debugging messages will show up here!")

    def compose(self) -> app.ComposeResult:
        """Add widgets to screen."""
        yield widgets.Header()

        # Main menu bar
        with containers.HorizontalGroup(classes="outer"):
            with containers.HorizontalGroup(id="intro-top-menu"):
                yield widgets.Button(
                    "Take Attendance",
                    id="intro-take-attendance",
                    tooltip="Scan some QR Codes!",
                )
                yield widgets.Button(
                    "Register New Students",
                    id="intro-register-students",
                    tooltip="Get a new student's info and generate a QR code."
                )
                yield widgets.Button("View Attendance Records", id="intro-view-records")
        
        # Database Controls
        with containers.HorizontalGroup(classes="outer"):
            yield widgets.Label("Current Database: ", classes="config-row")
            yield widgets.Label(str(config.settings.db_path), id="intro-config-db-path")
            with containers.HorizontalGroup(id="intro-database-buttons", classes="config"):
                yield widgets.Button("Create New Database File", id="intro-create-database")
                yield widgets.Button("Select Database", id="intro-select-database")

        # Configuration Controls
        with containers.HorizontalGroup(classes="outer"):
            yield widgets.Label("Configuration File: ", classes="config-row")
            yield widgets.Label(str(config.settings.config_path), id="intro-settings-path")
            with containers.HorizontalGroup(classes="config"):
                yield widgets.Button(
                    "Create New Settings File",
                    classes="dock-right",
                    id="intro-create-settings"
        )
                yield widgets.Button(
                    "Select Settings File",
                    classes="dock-right",
                    id="intro-select-settings"
        )
        yield widgets.Label(
            "Nothing to see here!", id="intro-status-message", classes="app-alert")
        yield widgets.Footer()

    def watch_message(self) -> None:
        """Update the status message on changes."""
        status_label = self.query_one("#intro-status-message", widgets.Label)
        status_label.update(self.message)
    
    @textual.on(widgets.Button.Pressed, "#intro-take-attendance")
    def action_take_attendance(self):
        """Put application in attenance mode, so students can scan QR codes."""
        self.app.push_screen(scan_view.ScanView())

    @textual.on(widgets.Button.Pressed, "#intro-register-students")
    def action_register_students(self):
        """Go to register students screen."""
        self.app.push_screen(management_view.ManagementView())

    @textual.on(widgets.Button.Pressed, "#intro-view-records")
    def action_view_records(self):
        """View attendance records."""
        self.message = "Viewing attendance records is not yet implemented."

    @textual.on(widgets.Button.Pressed, "#intro-select-database")
    def action_select_database(self):
        """Select a different database file or create a new one."""
        self.mount(files.FileSelector(
            pathlib.Path.cwd(),
            [".db", ".sqlite3"],
            create=False,
            default_filename="irsattend.db",
            id="intro-select-database-file"
        ))

    @textual.on(widgets.Button.Pressed, "#intro-create-database")
    def action_create_database(self):
        """Select a different database file or create a new one."""
        self.mount(files.FileSelector(
            pathlib.Path.cwd(),
            [".db", ".sqlite3"],
            create=True,
            default_filename="irsattend.db",
            id="intro-create-database-file"
        ))

    @textual.on(widgets.Button.Pressed, "#intro-select-settings")
    def action_select_settings(self):
        """Go to the settings management screen."""
        self.mount(files.FileSelector(
            pathlib.Path.cwd(),
            [".toml"],
            create=False,
            default_filename="irsattend.toml",
            id="intro-select-settings-file"
        ))

    @textual.on(widgets.Button.Pressed, "#intro-create-settings")
    def action_create_settings(self):
        """Go to the settings management screen."""
        self.mount(files.FileSelector(
            pathlib.Path.cwd(),
            [".toml"],
            create=True,
            default_filename="irsattend.toml",
            id="intro-create-settings-file"
        ))

    def on_file_selector_file_selected(
            self,
            message: files.FileSelector.FileSelected
    ) -> None:
        """Update db_path in config and intro screen."""
        self.message = f"Selected DB file: {message.path, message.create, message.id}"
        match message.id:
            case "intro-select-database-file":
                self._select_database(message.path)
            case "intro-create-database-file":
                database.DBase(message.path, create_new=True)
                self._select_database(message.path)
            case "intro-select-settings-file":
                self._select_settings(message.path)
            case "intro-create-settings-file":
                config.settings.create_new_config_file(message.path)
                self._select_settings(message.path)

    def _select_database(self, db_path: pathlib.Path) -> None:
        """Select a new, existing database file."""
        config.settings.db_path = db_path
        (
            self.query_one("#intro-config-db-path", widgets.Label)
            .update(str(config.settings.db_path))
        )
    
    def _select_settings(self, config_path: pathlib.Path) -> None:
        """Select a new settings TOML file."""
        config.settings.config_path = config_path
        (
            self.query_one("#intro-settings-path", widgets.Label)
            .update(str(config.settings.config_path))
        )
