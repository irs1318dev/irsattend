import os

# Main path where the app is running
APP_ROOT = os.path.dirname(os.path.abspath(__file__))

# Path to the SQLite database file
DB_FILE = os.path.join(APP_ROOT, "db", "irsattend.db")