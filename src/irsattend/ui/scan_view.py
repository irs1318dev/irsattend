
import asyncio

import cv2

from textual import app, containers, message, screen, widgets

from irsattend import config
from irsattend.db import database
from irsattend.scanner import qr_code_reader


class ScanView(screen.Screen):
    """UI for scanning QR codes while taking attendance."""

    CSS_PATH = "../styles/main.tcss"
    BINDINGS = [
        ("m", "show_management", "Management"),  # TODO password modal to switch
    ]

    def __init__(self) -> None:
        """Initialize databae connection."""
        super().__init__()
        self.dbase = database.DBase(config.settings.db_path)

    class QrCodeFound(message.Message):
        def __init__(self, code: str) -> None:
            self.code = code
            super().__init__()

    def compose(self) -> app.ComposeResult:
        yield widgets.Header()
        with containers.Vertical(id="log-container"):
            yield widgets.Static("Logs", classes="log-title")
            yield widgets.RichLog(id="attendance-log", highlight=True, markup=True)
        yield widgets.Footer()

    def on_mount(self) -> None:
        self.scanned = set()  # Prevent code from being scanned more than once.
        self.log_widget = self.query_one("#attendance-log", widgets.RichLog)
        self.scan_task = self.run_worker(self.scan_qr_codes(), exclusive=False)


    def on_unmount(self) -> None:
        if hasattr(self, "scan_task"):
            self.scan_task.cancel()
        # if hasattr(self, "camera"):
        #     self.camera.release()

    # This has to be async to not block the UI
    async def scan_qr_codes(self) -> None:
        """Open video window and capture QR codes."""
        vcap = cv2.VideoCapture(config.settings.camera_number)
        detector = cv2.QRCodeDetector()
        qr_data = None
        while True:
            _, img = vcap.read()
            cv2.imshow("QRCODEscanner", img)
            data, bbox, straight_code = detector.detectAndDecode(img)
            if data:
                print("QR-CODE:", data)
                qr_data = data
                if qr_data not in self.scanned:
                    self.scanned.add(qr_data)
                    self.post_message(self.QrCodeFound(qr_data))
                    await asyncio.sleep(1)  # Allow log to update.
            wait_key = cv2.waitKey(50)
            if wait_key in [ord("q"), ord("Q")]:
                break
        vcap.release()
        cv2.destroyAllWindows()

    async def on_scan_view_qr_code_found(self, message: QrCodeFound) -> None:
        """Add an attendance record to the database."""
        student_id = message.code
        student = self.dbase.get_student_by_id(student_id)
        if not student:
            self.log_widget.write(
                f"[yellow]Unknown ID scanned,\nplease talk to a mentor.[/]"
            )
            return
        student_name = f"{student['first_name']} {student['last_name']}"
        if self.dbase.has_attended_today(student_id):
            self.log_widget.write(f"[orange3]Already attended: {student_name}[/]")
        else:
            timestamp = self.dbase.add_attendance_record(student_id)
            if timestamp is not None:
                self.log_widget.write(
                    f"[green]Success: {student_name} "
                    f"checked in at {timestamp.strftime('%H:%M:%S')}[/]"
                )
        # Allow student to scan again after 15 seconds.
        self.set_timer(2, lambda: self.scanned.discard(student_id))

    def action_show_management(self) -> None:
        from .management_view import ManagementView
        from .modals import PasswordPrompt

        def on_password_result(success: bool | None) -> None:
            if success:
                self.app.push_screen(ManagementView())

        self.app.push_screen(PasswordPrompt(), callback=on_password_result)
