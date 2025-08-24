"""First screen that is displayed on app startup."""
from collections.abc import Iterable
import os
import pathlib
from typing import Optional

import textual
from textual import app, containers, message, reactive, screen, widgets

from irsattend import config


class DatabaseSelectorTree(widgets.DirectoryTree):
    """Custom directory tree that shows only .db and .sqlite3 files."""

    class DbFileSelected(message.Message):
        """Sent when a database file is selected."""
        dp_path: pathlib.Path

        def __init__(self, db_path) -> None:
            """Set the path to the database file."""
            super().__init__()
            self.db_path = db_path
    
    filename: Optional[str]

    def __init__(self, path: str, filename: Optional[str] = None) -> None:
        """Initialize with default DB file name."""
        super().__init__(path)
        self.filename = filename

    def filter_paths(self, paths: Iterable[pathlib.Path]) -> Iterable[pathlib.Path]:
        """Only show files that end in .db or .sqlite3."""
        return [
            path for path in paths
            if path.is_dir() or path.suffix in [".db", ".sqlite3"]
        ]
    
    def on_directory_tree_file_selected(
        self,
        event: widgets.DirectoryTree.FileSelected
    ) -> None:
        """Open the database file."""
        self.post_message(self.DbFileSelected(event.path))
        self.remove()

    def on_directory_tree_directory_selected(
            self,
            event: widgets.DirectoryTree.DirectorySelected
    ) -> None:
        """Create a new database file."""
        if self.filename is None:
            return
        self.post_message(self.DbFileSelected(event.path / self.filename))
        self.remove()

class DatabaseSelector(containers.Horizontal):
    """Select a database file."""

    def compose(self) -> app.ComposeResult:
        """Add widgets to screen."""
        with containers.VerticalGroup():
            yield widgets.Button("Cancel", id="cancel-db-select")
        yield DatabaseSelectorTree(os.getcwd())

    @textual.on(widgets.Button.Pressed, "#cancel-db-select")
    def remove_selector(self) -> None:
        """Remove the database selector widgets on cancel."""
        self.remove()

class DatabaseCreator(containers.Horizontal):
    """Create a new database file."""

    default_filename: str = "irsattend.db"

    def compose(self) -> app.ComposeResult:
        """Add widgets to screen."""
        with containers.VerticalGroup():
            yield widgets.Button("Cancel", id="cancel-db-create")
            yield widgets.Input(self.default_filename, id="db-filename")
        yield DatabaseSelectorTree(os.getcwd(), self.default_filename)

    @textual.on(widgets.Input.Changed, "#db-filename")
    def update_db_filename(self, event: widgets.Input.Changed) -> None:
        """Update directory tree's reference to filename."""
        self.query_one(DatabaseSelectorTree).filename = event.value

    @textual.on(widgets.Button.Pressed, "#cancel-db-create")
    def remove_selector(self) -> None:
        """Remove the database selector widgets on cancel."""
        self.remove()


class IntroView(screen.Screen):
    """IRSAttend App Introduction Screen."""

    CSS_PATH = "../styles/intro.tcss"
    BINDINGS = [
        ("a", "take_attendance", "Take Attendance"),
        ("r", "register_students", "Register Students"),
        ("v", "view_records", "View Attendance Records"),
        ("d", "configure_database", "Configure Database"),
        ("e", "edit_settings", "Edit App Settings")
    ]

    db_path = reactive.reactive(str(config.settings.db_path))
    message = reactive.reactive("Initial Message!")

    def compose(self) -> app.ComposeResult:
        """Add widgets to screen."""
        yield widgets.Header()

        # Main menu bar
        with containers.HorizontalGroup(classes="outer"):
            with containers.HorizontalGroup(id="top-menu"):
                yield widgets.Button("Take Attendance", id="take-attendance")
                yield widgets.Button("Register New Students", id="register-students")
                yield widgets.Button("View Attendance Records", id="view-records")
        
        # Database Controls
        with containers.HorizontalGroup(classes="outer"):
            yield widgets.Label("Current Database: ", classes="config-label")
            yield widgets.Label(str(config.settings.db_path), id="config-db-path")
            with containers.HorizontalGroup(id="database-buttons", classes="config"):
                yield widgets.Button("Create New Database File", id="create-database")
                yield widgets.Button("Select Database", id="select-database")

        # Configuration Controls
        with containers.HorizontalGroup(classes="outer"):
            yield widgets.Label("Configuration File: ", classes="config-label")
            yield widgets.Label(str(config.settings.config_path))
            with containers.HorizontalGroup(classes="config"):
                yield widgets.Button("Edit Settings", classes="dock-right", id="edit-settings")
        yield widgets.Label(
            "Nothing to see here!", id="intro-status-message", classes="app-alert")
        yield widgets.Footer()

    def watch_message(self) -> None:
        """Update the status message on changes."""
        status_label = self.query_one("#intro-status-message", widgets.Label)
        status_label.update(self.message)
    
    @textual.on(widgets.Button.Pressed, "#take-attendance")
    def action_take_attendance(self):
        """Put application in attenance mode, so students can scan QR codes."""
        self.message = "Taking attendance is not yet implemented."

    @textual.on(widgets.Button.Pressed, "#register-students")
    def action_register_students(self):
        """Go to register students screen."""
        self.message = "Registering students is not yet implemented."

    @textual.on(widgets.Button.Pressed, "#view-records")
    def action_view_records(self):
        """View attendance records."""
        self.message = "Viewing attendance records is not yet implemented."

    @textual.on(widgets.Button.Pressed, "#select-database")
    def action_select_database(self):
        """Select a different database file or create a new one."""
        self.mount(DatabaseSelector())

    def on_database_selector__tree_db_file_selected(
            self,
            message: DatabaseSelectorTree.DbFileSelected
    ) -> None:
        """Update db_path in config and intro screen."""
        config.settings.db_path = message.db_path
        (
            self.query_one("#config-db-path", widgets.Label)
            .update(str(config.settings.db_path))
        )

    @textual.on(widgets.Button.Pressed, "#create-database")
    def action_create_database(self):
        """Select a different database file or create a new one."""
        self.mount(DatabaseCreator())

    def on_database_creator__tree_db_directory_selected(
            self,
            message: DatabaseSelectorTree.DbFileSelected
    ) -> None:
        """Update db_path in config and intro screen."""
        config.settings.db_path = message.db_path
        (
            self.query_one("#config-db-path", widgets.Label)
            .update(str(config.settings.db_path))
        )


    @textual.on(widgets.Button.Pressed, "#edit-settings")
    def action_edit_settings(self):
        """Go to the settings management screen."""
        self.message = "Editing settings is not yet implemented."
        