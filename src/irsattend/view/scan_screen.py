"""Turn on camera and scan QR Codes."""

import asyncio
from typing import cast, Optional

import cv2

import textual
from textual import app, containers, message, screen, widgets
from textual.widgets import option_list

from irsattend.model import config, database, schema
from irsattend.view import pw_dialog


class ScanScreen(screen.Screen):
    """UI for scanning QR codes while taking attendance."""

    dbase: database.DBase
    """Sqlte database connection object."""
    log_widget: widgets.RichLog
    _scanned: set[str]
    """Recently scanned student IDs."""
    event_type: schema.EventType
    """Type of event at which we're taking attendance."""

    CSS_PATH = "../styles/main.tcss"
    BINDINGS = [
        (
            "q",
            "exit_scan_mode",
            "Quit QR Code Scan Mode.",
        ),  # TODO password modal to switch
    ]

    def __init__(self) -> None:
        """Initialize databae connection."""
        #
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
        """Request type of event then start the scanner."""
        self._scanned = set()  # Prevent code from being scanned more than once.
        self.log_widget = self.query_one("#attendance-log", widgets.RichLog)
        self.app.push_screen(
            EventTypeDialog(), callback=self.set_event_type_and_start_scanning
        )

    def set_event_type_and_start_scanning(
        self, event_type: Optional[schema.EventType]
    ) -> None:
        """Set the event type"""
        if event_type is None:
            self.app.pop_screen()
            return
        self.event_type = event_type
        self.dbase.add_event(event_type)
        self.scan_qr_codes()

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
            wait_key = cv2.waitKey(50)  # Wait 50 miliseconds for key press.
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
            timestamp = self.dbase.add_checkin_record(
                student_id, event_type=self.event_type
            )
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
            submit_callback=_exit_on_success, exit_on_cancel=False
        )


class EventTypeDialog(screen.ModalScreen[Optional[schema.EventType]]):
    """Select the event type when opening scan attendance screen."""

    CSS_PATH = "../styles/modal.tcss"

    def __init__(self) -> None:
        super().__init__()
        self.title = "Select Event Type"

    def compose(self) -> app.ComposeResult:
        """Arrange widgets within the dialog."""
        with containers.Vertical(id="event-type-dialog", classes="modal-dialog"):
            yield widgets.Label("Event Type")
            event_options = widgets.OptionList(
                *[option_list.Option(t.value.title(), id=t) for t in schema.EventType],
                id="event-type-option",
            )
            yield event_options
            with containers.Horizontal(classes="dialog-row"):
                yield widgets.Button("Ok", id="event-type-select-ok-button")
                yield widgets.Button("Cancel", id="event-type-select-cancel-button")
        type_map = {opt.id: idx for idx, opt in enumerate(event_options.options)}
        event_options.highlighted = type_map[schema.EventType.MEETING]

    @textual.on(widgets.Button.Pressed, "#event-type-select-ok-button")
    def on_ok_button_pressed(self) -> None:
        """Close the dialog and display the QR code scanning screen."""
        event_type_list = self.query_one("#event-type-option", widgets.OptionList)
        selected_index = event_type_list.highlighted
        if selected_index is not None:
            selected_event = cast(
                schema.EventType, event_type_list.options[selected_index].id
            )
            self.dismiss(selected_event)
        else:
            self.dismiss(None)

    @textual.on(widgets.Button.Pressed, "#event-type-select-cancel-button")
    def on_cancel_button_pressed(self) -> None:
        """Close the dialog and return to the main screen."""
        self.dismiss(None)
