"""Turn on camera and scan QR Codes."""
import asyncio

import cv2

import textual
from textual import app, containers, message, screen, widgets

from irsattend.model import config
from irsattend.model import database
from irsattend.view import pw_dialog


class ScanScreen(screen.Screen):
    """UI for scanning QR codes while taking attendance."""

    _scanned: set[str]
    """Recently scanned student IDs."""


    CSS_PATH = "../styles/main.tcss"
    BINDINGS = [
        ("q", "exit_scan_mode", "Quit QR Code Scan Mode."),  # TODO password modal to switch
    ]

    def __init__(self) -> None:
        """Initialize databae connection."""
        super().__init__()
        if config.settings.db_path is None:
            raise database.DBaseError("No database file selected.")
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
        self._scanned = set()  # Prevent code from being scanned more than once.
        self.log_widget = self.query_one("#attendance-log", widgets.RichLog)
        self.scan_task = self.scan_qr_codes()


    def on_unmount(self) -> None:
        if hasattr(self, "scan_task"):
            self.scan_task.cancel()
        # if hasattr(self, "camera"):
        #     self.camera.release()

    @textual.work(exclusive=False)
    async def scan_qr_codes(self) -> None:
        """Open video window and capture QR codes."""
        vcap = cv2.VideoCapture(config.settings.camera_number)
        detector = cv2.QRCodeDetector()
        qr_data = None
        while True:
            try:
                _, img = vcap.read()
                window_title = "Scan QR Codes (Click on window and press q to exit)"
                # Mirror view for display
                disp_img = cv2.flip(img, 1)
                cv2.imshow(window_title, disp_img)

                data, bbox, straight_code = detector.detectAndDecode(img)
            except cv2.error:
                continue
            if data:
                qr_data = data
                if qr_data not in self._scanned:
                    self._scanned.add(qr_data)
                    self.post_message(self.QrCodeFound(qr_data))
                    await asyncio.sleep(0.1)  # Allow log to update.
            wait_key = cv2.waitKey(50)
            if wait_key in [ord("q"), ord("Q")]:
                break
        vcap.release()
        cv2.destroyAllWindows()
        await self.run_action("exit_scan_mode")

    async def on_scan_screen_qr_code_found(self, message: QrCodeFound) -> None:
        """Add an attendance record to the database."""
        student_id = message.code
        student = self.dbase.get_student_by_id(student_id)
        if not student:
            self.log_widget.write(
                "[yellow]Unknown ID scanned,\nplease talk to a mentor.[/]"
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
        self.set_timer(2, lambda: self._scanned.discard(student_id))

    def action_exit_scan_mode(self) -> None:
        """Require a password to exit QR code scan mode."""
        def _exit_on_success(success: bool | None) -> None:
            if success:
                self.app.pop_screen()
            else:
                self.scan_qr_codes()
        
        pw_dialog.PasswordPrompt.show(
            submit_callback=_exit_on_success,
            exit_on_cancel=False
        )
