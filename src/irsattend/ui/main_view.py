import asyncio
from textual.message import Message
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Static, RichLog
from textual.containers import Vertical, Horizontal

from ..scanner.camera import Camera
from ..scanner.barcode_reader import read_barcodes
from ..db import database as db
from .. import config

class MainView(Screen):

    CSS_PATH = "../styles/main.tcss"
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("m", "show_management", "Management"), # TODO password modal to switch
    ]
    
    class BarcodeFound(Message):
        def __init__(self, code: str, format: str) -> None:
            self.code = code
            self.format = format
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

            self.scan_task = self.run_worker(self.scan_barcodes(), exclusive=False)
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
    async def scan_barcodes(self) -> None:
        while True:
            try:
                ret, frame = self.camera.get_frame()
                if not ret:
                    await asyncio.sleep(0.1)
                    continue

                # Convert frame to braille for display
                preview = self.camera.frame_to_braille(frame, width=100, height=30)
                
                self.camera_view.update(preview)

                # Check for barcodes using reader
                results = read_barcodes(frame)
                if results:
                    for result in results:
                        code_text = result.text
                        code_format = result.format.name
                        if code_text and code_text not in self.scanned:
                            self.scanned.add(code_text)
                            self.post_message(self.BarcodeFound(code_text, code_format))

                await asyncio.sleep(0.1)  # delay between scans
            except Exception as e:
                self.camera_view.update(f"[red]Camera error: {str(e)}[/]")
                await asyncio.sleep(1)
                break
            
    async def on_main_view_barcode_found(self, message: BarcodeFound) -> None:
        student_id = message.code
        format = message.format
        
        def remove_from_scanned():
            self.scanned.discard(student_id)
        
        # Check if we are allowing physical IDs
        if format == "Code39" and not config.ALLOW_PHYSICAL_ID:
            self.log_widget.write(f"[red]You cannot use your physical ID.[/]")
            self.set_timer(2.0, remove_from_scanned)
            return
        
        student = db.get_student_by_id(student_id)

        if not student:
            self.log_widget.write(f"[yellow]Unknown ID scanned,\nplease talk to a mentor.[/]")
            return

        student_name = f"{student['first_name']} {student['last_name']}"

        if db.has_attended_today(student_id):
            self.log_widget.write(f"[orange3]Already attended: {student_name}[/]")
        else:
            timestamp = db.add_attendance_record(student_id)
            self.log_widget.write(f"[green]Success: {student_name} checked in at {timestamp.strftime('%H:%M:%S')}[/]")

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