# IrsAttend
The Issaquah Robotics Society's Python program for managing attendance.

## Version 1.0.0

### Capabilities
	•	Scan both barcodes and QR codes from physical IDs or emailed codes
	•	Camera preview with braille
	•	Real-time attendance logging with success/failure messages
	•	Add, edit, and remove student records
	•	Manually add or remove attendance entries
	•	Import students in bulk from CSV files
	•	Email individual or all students their codes


### Run Instructions
**Prerequisites:** Requires [uv](https://docs.astral.sh/uv/getting-started/installation/) for package management.

1. Install dependencies:
   ```bash
   uv sync
   ```
2. Activate the virtual environment:
   - **macOS/Linux**:
     ```bash
     source .venv/bin/activate
     ```
   - **Windows**:
     ```powershell
     .venv\Scripts\activate
     ```
3. Run the application:
   ```bash
   python -m src.irsattend.main
   ```
