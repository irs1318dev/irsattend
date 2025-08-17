"""Main entry point for IRS Attend Application."""
import argparse
import pathlib
from typing import Optional

from textual import app

from irsattend import config
from irsattend.db import database
from irsattend.ui import intro_view # , main_view, management_view


class IRSAttend(app.App):
    CSS_PATH = "./styles/modal.tcss"
    TITLE = "IRS 1318 Attendance System"
    SCREENS = {
        "intro": intro_view.IntroView
        # "main": MainView,
        # "management": ManagementView,
    }

    def on_mount(self) -> None:
        """Called when the app is first mounted."""
        db_path = config.settings.db_path
        if db_path is None:
            dbase = database.DBase(
                pathlib.Path.cwd() / config.DB_FILE_NAME,
                create_new=True
            )
            config.settings.db_path = dbase.db_path
        self.push_screen("intro")


def build_parser() -> argparse.ArgumentParser:
    """Define command line arguments."""
    parser = argparse.ArgumentParser(prog="IRS Attendance Program")
    parser.add_argument(
        "-d", "--db_path",
        help="Path to attendance database",
        type=pathlib.Path,
        default=None
    )
    parser.add_argument(
        "-c", "--config_path",
        help="Path to config file",
        type=pathlib.Path,
        default=None
    )
    return parser


def set_args(args: Optional[argparse.Namespace] = None) -> None:
    """Read args from command line or use preset args (for testing)."""
    if args is None:
        parser = build_parser()
        args = parser.parse_args()
    config.settings.update_from_args(args)


def run_app() -> None:
    """Function to run the app, used for the setup.py entry_point."""
    set_args()
    app = IRSAttend()
    app.run()


if __name__ == "__main__":
    run_app()
