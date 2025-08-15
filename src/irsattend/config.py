import dataclasses
import hashlib
import os

import pathlib


@dataclasses.dataclass
class Config:
    """irsattend configuration data."""
    db_path: pathlib.Path = pathlib.Path("db_path")
    config_path: pathlib.Path = pathlib.Path("config_path")
    qr_code_dir: pathlib.Path = pathlib.Path("qr_code")
    smtp_server: str = "server"
    smtp_port: int = 465
    smtp_username: str = "noreply@team1318.org"
    smtp_password: str = "password123"
    email_sender_name: str = "IRS 1318 Attendance"


    def update_from_args(self, args):
        self.db_path = args.db_path
        self.config_path = args.config_path



config = Config()



# Main path where the app is running
APP_ROOT = os.path.dirname(os.path.abspath(__file__))

# Path to the SQLite database file
DB_FILE = os.path.join(APP_ROOT, "irsattend.db")

# Directory to store QR code images temporarily
QR_CODE_DIR = os.path.join(APP_ROOT, "qr_codes")

# --- Camera Display Settings ---
# Number of the camera to use (0 is default for laptops)
CAMERA_NUMBER = 0

# --- Email Settings ---
SMTP_SERVER = "server"
SMTP_PORT = 465
SMTP_USERNAME = "noreply@team1318.org"
SMTP_PASSWORD = "password123"
EMAIL_SENDER_NAME = "IRS 1318 Attendance"


# --- Admin Password ---
# We should probably move at least secrets to an environment file
MANAGEMENT_PASSWORD_HASH = hashlib.sha256("irs1318".encode()).hexdigest()
