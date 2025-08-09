import asyncio
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Static, RichLog
from textual.containers import Vertical, Horizontal

from ..scanner.camera import Camera
from ..scanner.barcode_reader import read_barcodes

class MainView(Screen):

    CSS_PATH = "../styles/main.tcss"
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("m", "show_management", "Management"), # TODO password modal to switch
    ]
    
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
                        if code_text:
                            # TODO process the scanned code
                            self.log_widget.write(f"[bold green]Scanned barcode: {code_text}[/]")

                await asyncio.sleep(0.1)  # delay between scans
            except Exception as e:
                self.camera_view.update(f"[red]Camera error: {str(e)}[/]")
                await asyncio.sleep(1)
                break
            
    def action_show_management(self) -> None:
        from .management_view import ManagementView
        self.app.push_screen(ManagementView())
        
    def action_quit(self) -> None:
        self.app.action_quit()