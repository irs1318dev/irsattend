import asyncio
from textual.message import Message
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Static, RichLog
from textual.containers import Vertical, Horizontal

from irsattend.scanner.camera import Camera
from irsattend.scanner.qr_code_reader import read_qr_codes
from irsattend.db import database as db
from irsattend import config


class MainView(Screen):

    CSS_PATH = "../styles/main.tcss"
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("m", "show_management", "Management"),  # TODO password modal to switch
    ]

    class QrCodeFound(Message):
        def __init__(self, code: str) -> None:
            self.code = code
            super().__init__()

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="main-container"):
            with Vertical(id="camera-container"):
                yield Static("Initializing Camera...", id="camera-view")
            with Vertical(id="log-container"):
                yield Static("Logs", classes="log-title")
                yield RichLog(id="attendance-log", highlight=True, markup=True)
        yield Footer()

    def on_mount(self) -> None:
        # This will be used so a code isnt scanned more then once when holding it up to the camera
        self.scanned = set()
        self.log_widget = self.query_one("#attendance-log")
        self.camera_view = self.query_one("#camera-view")

        try:
            self.camera = Camera()

            self.scan_task = self.run_worker(self.scan_qr_codes(), exclusive=False)
            self.log_widget.write(f"[green]Camera ready for scanning![/]")
        except IOError as e:
            self.camera_view.update(f"[bold red]Camera Error: {e}[/bold red]")
            self.log_widget.write(f"[bold red]Camera Error: {e}[/bold red]")
        except Exception as e:
            self.log_widget.write(f"[bold red]Camera Error: {e}[/bold red]")

    def on_unmount(self) -> None:
        if hasattr(self, "scan_task"):
            self.scan_task.cancel()
        if hasattr(self, "camera"):
            self.camera.release()

    # This has to be async to not block the UI
    async def scan_qr_codes(self) -> None:
        while True:
            try:
                ret, frame = self.camera.get_frame()
                if not ret:
                    await asyncio.sleep(0.1)
                    continue

                # Resize preview based on container size
                container_size = self.camera_view.size
                preview_width, preview_height = self.camera.calculate_preview_size(
                    container_size
                )

                # Convert frame to braille for display
                preview = self.camera.frame_to_braille(
                    frame, width=preview_width, height=preview_height
                )

                self.camera_view.update(preview)

                # Check for QR codes using reader
                results = read_qr_codes(frame)
                if results:
                    for result in results:
                        code_text = result.text
                        if code_text and code_text not in self.scanned:
                            self.scanned.add(code_text)
                            self.post_message(self.QrCodeFound(code_text))

                await asyncio.sleep(0.1)  # delay between scans
            except Exception as e:
                self.camera_view.update(f"[red]Camera error: {str(e)}[/]")
                await asyncio.sleep(1)
                break

    async def on_main_view_qr_code_found(self, message: QrCodeFound) -> None:
        student_id = message.code

        def remove_from_scanned():
            self.scanned.discard(student_id)

        student = db.get_student_by_id(student_id)

        if not student:
            self.log_widget.write(
                f"[yellow]Unknown ID scanned,\nplease talk to a mentor.[/]"
            )
            return

        student_name = f"{student['first_name']} {student['last_name']}"

        if db.has_attended_today(student_id):
            self.log_widget.write(f"[orange3]Already attended: {student_name}[/]")
        else:
            timestamp = db.add_attendance_record(student_id)
            self.log_widget.write(
                f"[green]Success: {student_name} checked in at {timestamp.strftime('%H:%M:%S')}[/]"
            )

        # Wait two seconds before removing from list
        # We want to remove from the list so that the same code can be scanned again
        # In case the student is unsure if they attended the meeting
        self.set_timer(2.0, remove_from_scanned)

    def action_show_management(self) -> None:
        from .management_view import ManagementView
        from .modals import PasswordPrompt

        def on_password_result(success: bool | None) -> None:
            if success:
                self.app.push_screen(ManagementView())

        self.app.push_screen(PasswordPrompt(), callback=on_password_result)

    def action_quit(self) -> None:
        self.app.action_quit()
