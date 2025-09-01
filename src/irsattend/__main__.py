"""Start the IRS Attendance App."""
import argparse
import pathlib
from typing import Optional

from irsattend.model import config
import irsattend.view.main_app


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


def set_config(args: Optional[argparse.Namespace] = None) -> None:
    """Assign config settings from command line args."""
    if args is None:
        parser = build_parser()
        args = parser.parse_args()
    config.settings.update_from_args(args)


def run_app() -> None:
    """Function to run the app, used for the setup.py entry_point."""
    set_config()
    app = irsattend.view.main_app.IRSAttend()
    app.run()

if __name__ == "__main__":
    run_app()