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
    parser.set_defaults(func=None)
    subparsers = parser.add_subparsers()
    sync_parser = subparsers.add_parser(
        "sync-roster",
        help="Synchronize attendance data with the student roster."
    )
    sync_group = sync_parser.add_mutually_exclusive_group(required=True)
    sync_group.add_argument(
        "-i", "--student-ids",
        help="Send student IDs to the team's Google Sheet roster.",
        type=pathlib.Path
    )
    sync_group.add_argument(
        "-a", "--attendance-data",
        help="Send attendance to the team's Google Sheet roster.",
        type=pathlib.Path
    )
    sync_parser.set_defaults(func=sync_data)
    return parser


def sync_data(args: argparse.Namespace) -> None:
    """Synchronize attendance data with other applications."""
    if args.student_ids is not None:
        print("Sync student IDs!")
    elif args.attendance_data is not None:
        print("Syncing attendance data!")



def set_config(args: Optional[argparse.Namespace] = None) -> argparse.Namespace:
    """Assign config settings from command line args."""
    if args is None:
        parser = build_parser()
        args = parser.parse_args()
    config.settings.update_from_args(args)
    return args


def run_app() -> None:
    """Function to run the app, used for the setup.py entry_point."""
    args = set_config()
    if args.func is None:
        app = irsattend.view.main_app.IRSAttend()
        app.run()
    else:
        args.func(args)

if __name__ == "__main__":
    run_app()