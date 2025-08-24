"""Manage configuration settings for the IRS Attend application."""
import argparse
import dataclasses
import enum
import pathlib
import shutil
import tomllib
from typing import Optional


DB_FILE_NAME = "irsattend.db"
CONFIG_FILE_NAME = "irsattend.toml"


class ConfigError(Exception):
    """Errors when setting or accessing settings."""
    class ErrorType(enum.Enum):
        NOT_A_FILE = 1
        PATH_DOES_NOT_EXIST = 2

    error_type: ErrorType

    def __init__(self, message: str, error_type: ErrorType) -> None:
        """Set error type."""
        super().__init__(message)
        self.error_type = error_type


@dataclasses.dataclass
class Settings:
    """Configuration data for irsattend application.
    
    password_hash is a SHA256 hash creaeted with the hashlib library. The
    default password is 1318.
    """
    db_path: Optional[pathlib.Path] = None
    config_path: Optional[pathlib.Path] = None
    qr_code_dir: Optional[pathlib.Path] = None
    password_hash: Optional[str] = (
        "095eaa09cd36d1f1e7a963c9ad618edab13f466882c9027ab81ffc18b0eb727e") # 1318
    camera_number = 0
    smtp_server: Optional[str] = None
    smtp_port: int = 465
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    email_sender_name: Optional[str] = None

    def update_from_args(self, args: argparse.Namespace) -> None:
        """Read settings."""
        if hasattr(args, "db_path"):
            self.db_path = self._get_full_path(args.db_path, DB_FILE_NAME)
        else:
            self.db_path = None
        if hasattr(args, "config_path"):
            self.config_path = self._get_full_path(args.config_path, CONFIG_FILE_NAME)
            self._read_config_file()
        else:
            self.config_path = None


    @staticmethod
    def _get_full_path(
        path: pathlib.Path,
        default_file_name: str
    ) -> Optional[pathlib.Path]:
        """Convert path arg to full filesystem path.
        
        If path is None, looks for file in current working directory. Otherwise
        converts relative paths to absolute paths. Returns None if path does not
        point to an existing file.
        """
        cwd = pathlib.Path.cwd()
        if path is None:
            full_path = cwd / default_file_name
        elif path.is_absolute():
            full_path = path
        else:
            full_path = cwd / path
        if not full_path.is_file():
            full_path = None
        return full_path
    
    def _read_config_file(self) -> None:
        """Read TOML configuration file."""
        if self.config_path is None:
            return
        app_settings = dataclasses.asdict(self)
        with open(self.config_path, "rb") as toml_file:
            file_settngs = tomllib.load(toml_file)
        for setting_name, value in file_settngs.items():
            if setting_name in app_settings:
                if isinstance(value, str) and value.lower() in ["", "none", "null"]:
                    value = None
                setattr(self, setting_name, value)

    def create_new_config_file(self, config_path: pathlib.Path) -> None:
        """Create a new configuration file with default settings."""
        if not config_path.exists():
            shutil.copy(
                pathlib.Path(__file__).parent / "example-config.toml",
                config_path
            )


# Store settings in a module-level variable, which will be available from any
# other module that imports irsattend.config. This pattern is sometimes referred
# to as a Singleton pattern, because there is only a single instance of the
# Settings class.
settings = Settings()










# DELETE THIS LATER
# # Main path where the app is running
# APP_ROOT = os.path.dirname(os.path.abspath(__file__))

# # Path to the SQLite database file
# DB_FILE = os.path.join(APP_ROOT, "irsattend.db")

# # Directory to store QR code images temporarily
# QR_CODE_DIR = os.path.join(APP_ROOT, "qr_codes")

# # --- Camera Display Settings ---
# # Number of the camera to use (0 is default for laptops)
# CAMERA_NUMBER = 0

# # --- Email Settings ---
# SMTP_SERVER = "server"
# SMTP_PORT = 465
# SMTP_USERNAME = "noreply@team1318.org"
# SMTP_PASSWORD = "password123"
# EMAIL_SENDER_NAME = "IRS 1318 Attendance"


# # --- Admin Password ---
# # We should probably move at least secrets to an environment file
# MANAGEMENT_PASSWORD_HASH = hashlib.sha256("irs1318".encode()).hexdigest()
