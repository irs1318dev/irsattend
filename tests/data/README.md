# Test Data

## `data/private` Folder
1. test-config.toml: A TOML configuration file with valid email account settings. See irsattend/model/config.py to see TOML file settings. Required settings for testing:
    * qr_code_dir: A subfolder of tests/data/private, for testing QR code generation.
    * Valid email settings are required to test sending QR codes.
2. test-roster-settings.yaml: A valid google sheet roster settings file. For testing roster updates.

## test-data.py
A Marimo notebook with code that generated atts.csv and testattend.db.