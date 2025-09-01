"""Test command-line args and settings."""
import argparse
import dataclasses
import pathlib

import rich

import irsattend
from irsattend.model import config
from irsattend.view import main_app


DATA_PATH = pathlib.Path(__file__).parent / "data"


def test_read_config() -> None:
    """Read the configuration from a TOML file."""
    # Arrange
    args = argparse.Namespace(config_path=DATA_PATH / "irsattend.toml")
    # Act
    config.settings.update_from_args(args)
    # Assert
    assert config.settings.qr_code_dir == "qr_codes"
    assert config.settings.email_sender_name == "IRS Attendance System"


