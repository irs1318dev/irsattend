"""Main entry point for IRS Attend Application."""
import pathlib

import textual
from textual import app, containers, reactive, widgets

from irsattend.model import config, database
from irsattend.view import file_widgets, management_screen, pw_dialog, scan_screen


class IRSAttend(app.App):
    """Main applicaiton and introduction screen."""

    CSS_PATH = "../styles/main.tcss"
    TITLE = "IRS 1318 Attendance System"
    BINDINGS = [
        ("a", "take_attendance", "Take Attendance"),
        ("r", "register_students", "Register Students"),
        ("v", "view_records", "View Attendance Records"),
    ]
    SCREENS = {
        "management": management_screen.ManagementScreen,
    }
    db_path: reactive.reactive[pathlib.Path | None] = reactive.reactive(None)
    config_path: reactive.reactive[pathlib.Path | None] = reactive.reactive(None)
    message = reactive.reactive("Debugging messages will show up here!")


    def on_mount(self) -> None:
        """Called when the app is first mounted."""
        self.db_path = config.settings.db_path
        self.config_path = config.settings.config_path

        def _exit_if_no_pw(success: bool | None) -> None:
            if not success or success is None:
                self.exit(message="Incorrect password.")

        pw_dialog.PasswordPrompt.show(
            submit_callback=_exit_if_no_pw,
            exit_on_cancel=True)

    def compose(self) -> app.ComposeResult:
        """Add widgets to screen."""
        yield widgets.Header()

        # Main menu bar
        with containers.HorizontalGroup(classes="outer"):
            with containers.HorizontalGroup(id="main-top-menu"):
                yield widgets.Button(
                    "Take Attendance",
                    id="main-take-attendance",
                    tooltip="Scan some QR Codes!",
                )
                yield widgets.Button(
                    "Register New Students",
                    id="main-register-students",
                    tooltip="Get a new student's info and generate a QR code."
                )
                yield widgets.Button("View Attendance Records", id="main-view-records")
        
        # Database Controls
        with containers.HorizontalGroup(classes="outer"):
            yield widgets.Label("Current Database: ", classes="config-row")
            yield widgets.Label(str(config.settings.db_path), id="main-config-db-path")
            with containers.HorizontalGroup(id="main-database-buttons", classes="config"):
                yield widgets.Button("Create New Database File", id="main-create-database")
                yield widgets.Button("Select Database", id="main-select-database")

        # Configuration Controls
        with containers.HorizontalGroup(classes="outer"):
            yield widgets.Label("Configuration File: ", classes="config-row")
            yield widgets.Label(str(config.settings.config_path), id="main-settings-path")
            with containers.HorizontalGroup(classes="config"):
                yield widgets.Button(
                    "Create New Settings File",
                    classes="dock-right",
                    id="main-create-settings"
        )
                yield widgets.Button(
                    "Select Settings File",
                    classes="dock-right",
                    id="main-select-settings"
        )
        yield widgets.Label(
            "Nothing to see here!", id="main-status-message", classes="app-alert")
        yield widgets.Footer()
        print("Compose is done!!")

    def watch_message(self) -> None:
        """Update the status message on changes."""
        status_label = self.query_one("#main-status-message", widgets.Label)
        status_label.update(self.message)
    
    @textual.on(widgets.Button.Pressed, "#main-take-attendance")
    def action_take_attendance(self):
        """Put application in attenance mode, so students can scan QR codes."""
        self.app.push_screen(scan_screen.ScanScreen())

    @textual.on(widgets.Button.Pressed, "#main-register-students")
    def action_register_students(self):
        """Go to register students screen."""
        self.app.push_screen(management_screen.ManagementScreen())

    @textual.on(widgets.Button.Pressed, "#main-view-records")
    def action_view_records(self):
        """View attendance records."""
        self.message = "Viewing attendance records is not yet implemented."

    @textual.on(widgets.Button.Pressed, "#main-select-database")
    def action_select_database(self):
        """Select a different database file or create a new one."""
        self.mount(file_widgets.FileSelector(
            pathlib.Path.cwd(),
            [".db", ".sqlite3"],
            create=False,
            default_filename="irsattend.db",
            id="main-select-database-file"
        ))

    @textual.on(widgets.Button.Pressed, "#main-create-database")
    def action_create_database(self):
        """Select a different database file or create a new one."""
        self.mount(file_widgets.FileSelector(
            pathlib.Path.cwd(),
            [".db", ".sqlite3"],
            create=True,
            default_filename="irsattend.db",
            id="main-create-database-file"
        ))

    @textual.on(widgets.Button.Pressed, "#main-select-settings")
    def action_select_settings(self):
        """Go to the settings management screen."""
        self.mount(file_widgets.FileSelector(
            pathlib.Path.cwd(),
            [".toml"],
            create=False,
            default_filename="irsattend.toml",
            id="main-select-settings-file"
        ))

    @textual.on(widgets.Button.Pressed, "#main-create-settings")
    def action_create_settings(self):
        """Go to the settings management screen."""
        self.mount(file_widgets.FileSelector(
            pathlib.Path.cwd(),
            [".toml"],
            create=True,
            default_filename="irsattend.toml",
            id="main-create-settings-file"
        ))

    def on_file_selector_file_selected(
            self,
            message: file_widgets.FileSelector.FileSelected
    ) -> None:
        """Update db_path in config and main screen."""
        self.message = f"Selected DB file: {message.path, message.create, message.id}"
        match message.id:
            case "main-select-database-file":
                self._select_database(message.path)
            case "main-create-database-file":
                database.DBase(message.path, create_new=True)
                self._select_database(message.path)
            case "main-select-settings-file":
                self._select_settings(message.path)
            case "main-create-settings-file":
                config.settings.create_new_config_file(message.path)
                self._select_settings(message.path)

    def _select_database(self, db_path: pathlib.Path) -> None:
        """Select a new, existing database file."""
        config.settings.db_path = db_path
        self.db_path = db_path

    def watch_db_path(self, db_path: str) -> None:
        """Update the database path label."""
        self.query_one("#main-config-db-path", widgets.Label).update(str(db_path))
    
    def _select_settings(self, config_path: pathlib.Path) -> None:
        """Select a new settings TOML file."""
        config.settings.config_path = config_path
        self.config_path = config_path

    def watch_config_path(self, config_path: str) -> None:
        """update the config path label."""
        self.query_one("#main-settings-path", widgets.Label).update(str(config_path))
