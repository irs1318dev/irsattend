import hashlib
import os

# Main path where the app is running
APP_ROOT = os.path.dirname(os.path.abspath(__file__))

# Path to the SQLite database file
DB_FILE = os.path.join(APP_ROOT, "irsattend.db")

# Directory to store barcode images temporarily
BAR_CODE_DIR = os.path.join(APP_ROOT, "barcodes")

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
MANAGEMENT_PASSWORD_HASH = hashlib.sha256('irs1318'.encode()).hexdigest()

# --- Attendance Settings ---
ALLOW_PHYSICAL_ID = False