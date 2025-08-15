import argparse
import pathlib
import signal
import sys

from textual.app import App, ComposeResult
from textual.widgets import Label

from irsattend.db import database
from irsattend.ui.main_view import MainView
from irsattend.ui.management_view import ManagementView
from irsattend import config


class IRSAttend(App):
    CSS_PATH = "./styles/modal.tcss"
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

    # def action_quit(self) -> None:
    #     self.exit()

def build_parser():
    """Read command line arguments."""
    parser = argparse.ArgumentParser(prog="IRS Attendance Program")
    parser.add_argument("db_path", help="Path to attendance database", type=pathlib.Path)
    parser.add_argument("config_path", help="Path to config file", type=pathlib.Path)
    return parser

def set_args():
    parser = build_parser()
    args = parser.parse_args()
    config.config.update_from_args(args)

def run_app():
    """Function to run the app, used for the setup.py entry_point."""
    
    #app = IRSAttend()
    #app.run()

if __name__ == "__main__":
    run_app()
