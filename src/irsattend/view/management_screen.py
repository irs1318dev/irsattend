"""View roster and add new students."""
import sqlite3
from typing import Optional

import textual
import textual.css.query
from textual import app, binding, containers, screen, widgets

from irsattend.model import config, database, emailer, qr_code_generator
from irsattend.view import modals, confirm_dialogs


class ManagementScreen(screen.Screen):
    """Add, delete, and edit students."""

    dbase: database.DBase
    """Connection to Sqlite Database."""
    _selected_student_id: Optional[str]
    """Currently selected student."""

    CSS_PATH = "../styles/management.tcss"
    BINDINGS = [
        binding.Binding("escape", "app.pop_screen", "Back to Main Screen", show=True),
    ]

    def __init__(self) -> None:
        """Initialize the databae connection."""
        super().__init__()
        if config.settings.db_path is None:
            raise database.DBaseError("No database file selected.")
        self.dbase = database.DBase(config.settings.db_path)

    def compose(self) -> app.ComposeResult:
        """Build the management screen's user interface."""
        yield widgets.Header()
        with containers.Horizontal():
            with containers.Vertical(id="student-list-container"):
                yield widgets.Label("Student List")
                yield widgets.DataTable(id="student-table")
            with containers.Vertical(id="actions-container"):
                yield widgets.Label("Actions")
                with containers.ScrollableContainer():
                    yield widgets.Static(
                        "No student selected",
                        id="selection-indicator",
                        classes="selection-info",
                    )
                    yield widgets.Static()
                    yield widgets.Button(
                        "Add Student", variant="success", id="add-student",
                        tooltip="Add a new student to the database.")
                    yield widgets.Button(
                        "Import from CSV", variant="success", id="import-csv",
                        tooltip="Import students from a CSV file.")
                    yield widgets.Button(
                        "Edit Selected", id="edit-student", disabled=True,
                        tooltip="Edit data for a student.")
                    yield widgets.Button(
                        "Delete Selected",
                        variant="error",
                        id="delete-student",
                        disabled=True,
                        tooltip="Deleted a student."
                    )
                    yield widgets.Static()
                    yield widgets.Label("Communication")
                    yield widgets.Button(
                        "Generate QR Codes",
                        id="generate-qr-codes",
                        tooltip=(
                            "Generate QR codes for all students and "
                            "save them to the QR code folder.")
                    )
                    yield widgets.Button(
                        "Email QR Code to Selected", id="email-qr", disabled=True,
                        tooltip="Email a QR code to the selected student."
                    )
                    yield widgets.Button(
                        "Email All QR Codes", id="email-all-qr",
                        tooltip="Email QR codes to ALL students.")
                    yield widgets.Static(id="status-message", classes="status")
        yield widgets.Footer()

    def on_mount(self) -> None:
        """Initialize the datatable widget."""
        self.table = self.query_one(widgets.DataTable)
        self.table.cursor_type = "row"
        self.table.add_columns(
            "ID", "Last Name", "First Name", "Email", "Grad Year", "Attendance Count"
        )
        self.load_student_data()
        self._selected_student_id = None

    def _add_progress_bar(self, total: int | None, name: str) -> widgets.ProgressBar:
        """Add a progress bar for sending emails or generating QR Codes."""
        pbar = widgets.ProgressBar(total, name=name, id="qr-progress-bar")
        container = self.query_one("#actions-container", containers.Vertical)
        container.mount(pbar)
        return pbar
    
    def _update_progress_bar(self, total: int, progress: int) -> None:
        """Update the progress bar."""
        try:
            pbar = self.query_one("#qr-progress-bar", widgets.ProgressBar)
        except textual.css.query.NoMatches:
            return
        pbar.update(total=total, progress=progress)
    
    def _advance_progress_bar(self) -> None:
        """Advanced the progress bar one step."""
        try:
            pbar = self.query_one("#qr-progress-bar", widgets.ProgressBar)
        except textual.css.query.NoMatches:
            return
        pbar.advance()

    def _remove_progress_bar(self) -> None:
        """Remove the progress bar if mounted."""
        try:
            pbar = self.query_one("#qr-progress-bar", widgets.ProgressBar)
        except textual.css.query.NoMatches:
            return
        pbar.remove()

    def load_student_data(self) -> None:
        """Load student data into the datatable widget."""
        self.table.clear()
        students = self.dbase.get_all_students()
        for student in students:
            self.table.add_row(
                student["student_id"],
                student["last_name"],
                student["first_name"],
                student["email"] or "N/A",
                str(student["grad_year"]) if student["grad_year"] else "N/A",
                key=student["student_id"],
            )

    def on_data_table_row_selected(self, event: widgets.DataTable.RowSelected) -> None:
        """Select a row in the datatable."""
        self._selected_student_id = event.row_key.value
        if self._selected_student_id is None:
            return
        self.query_one("#edit-student", widgets.Button).disabled = False
        self.query_one("#delete-student", widgets.Button).disabled = False
        student = self.dbase.get_student_by_id(self._selected_student_id)
        self.query_one("#email-qr", widgets.Button).disabled = not (
            student and student["email"]
        )

        if student:
            self.update_selected(
                f"[bold]Selected:[/bold]\n{student['first_name']} "
                f"{student['last_name']}\nID: {student['student_id']}")

    async def on_button_pressed(self, event: widgets.Button.Pressed) -> None:
        """Respond to button presses."""
        if event.button.id == "add-student":
            await self.action_add_student()
        elif event.button.id == "import-csv":
            await self.action_import_csv()
        elif event.button.id == "edit-student":
            await self.action_edit_student()
        elif event.button.id == "delete-student":
            await self.action_delete_student()
        elif event.button.id == "email-qr":
            await self.action_email_qr(all_students=False)
        elif event.button.id == "email-all-qr":
            await self.action_email_qr(all_students=True)
        elif event.button.id == "generate-qr-codes":
            self._add_progress_bar(None, "Generate QR Codes")
            self.generate_qr_codes()

    async def action_add_student(self) -> None:
        """Show the student dialog and add a new student."""
        def on_dialog_closed(data: dict | None):
            if data is None:
                return
            data.pop("attendance", None)
            try:
                student_id = self.dbase.add_student(**data)
            except sqlite3.IntegrityError as err:
                self.update_status(
                    "[red]Error adding student "
                    f"{data["first_name"]} {data["last_name"]}.[/]\n"
                    f"Error Description:\n{err}"
                )
            else:
                self.load_student_data()
                self.query_one("#status-message", widgets.Static).update(
                    f"[green]Student added successfully. ID: {student_id}[/]")
                    
        await self.app.push_screen(modals.StudentDialog(), callback=on_dialog_closed)

    async def action_edit_student(self) -> None:
        if self._selected_student_id is None:
            return
        student = self.dbase.get_student_by_id(self._selected_student_id)
        if student is None:
            return
        else:
            student_dict = dict(student)
        attendance = self.dbase.get_attendance_count_by_id(self._selected_student_id)
        student_dict["attendance"] = attendance

        def on_dialog_closed(data: dict | None):
            if data is None or self._selected_student_id is None:
                return
            # Remove attendance from data before updating student info
            attendance_count = data.pop("attendance", None)
            self.dbase.update_student(**data)
            # Might change the way this is done in the future, the current way is a pain
            if attendance_count is not None:
                current_attendance = attendance
                if attendance_count == 0:
                    self.dbase.remove_all_attendance_records(self._selected_student_id)
                elif attendance_count > 0:
                    difference = attendance_count - current_attendance
                    if difference > 0:
                        # This means we need to add more records
                        for _ in range(difference):
                            self.dbase.add_attendance_record(self._selected_student_id)
                    elif difference < 0:
                        # This means we need to remove records
                        for _ in range(abs(difference)):
                            self.dbase.remove_last_attendance_record(
                                self._selected_student_id
                            )
                    self.update_status("[green]Student updated successfully.[/]")
            else:
                self.update_status("[green]Student updated successfully.[/]")
            self.load_student_data()

        await self.app.push_screen(
            modals.StudentDialog(student_data=student_dict), callback=on_dialog_closed
        )

    async def action_delete_student(self) -> None:
        if self._selected_student_id is None:
            return
        student = self.dbase.get_student_by_id(self._selected_student_id)
        if student is None:
            return
        student_name = f"{student['first_name']} {student['last_name']}"

        def on_confirm_closed(confirmed: bool | None):
            if confirmed:
                if self._selected_student_id is not None:
                    self.dbase.delete_student(self._selected_student_id)
                self.load_student_data()
                self.update_status("[green]Student deleted successfully.[/]")
                self._selected_student_id = None
                self.query_one("#edit-student", widgets.Button).disabled = True
                self.query_one("#delete-student", widgets.Button).disabled = True
                self.query_one("#selection-indicator", widgets.Static).update(
                    "No student selected"
                )

        await self.app.push_screen(
            confirm_dialogs.DeleteConfirmDialog(student_name, student["student_id"]),
            callback=on_confirm_closed,
        )

    @textual.work(thread=True)
    async def generate_qr_codes(self) -> None:
        """Generate all QR codes."""
        if config.settings.qr_code_dir is None:
            self.update_status(
                "[red] Cannot generate QR codes because "
                "no QR code path is defined in config file.[/]")
            return
        qr_generator = qr_code_generator.generate_all_qr_codes(
            config.settings.qr_code_dir, self.dbase)
        total_students = next(qr_generator)[1]
        self.app.call_from_thread(lambda: self._update_progress_bar(total_students, 0))
        failed_codes = []
        for student_id, status in qr_generator:
            if not status:
                failed_codes.append(student_id)
            self.app.call_from_thread(self._advance_progress_bar)
        status_message = (
            f"[green]Created {total_students - len(failed_codes)} QR Codes in folder "
            f"{config.settings.qr_code_dir}\n"
        )
        if failed_codes:
            status_message += ("[red]Failed Codes: " + ", ".join(failed_codes) + "[/]")
        self.update_status(status_message)
        self.app.call_from_thread(self._remove_progress_bar)

    async def action_email_qr(self, all_students: bool) -> None:
        """Email QR codes to students."""

        def _email_all_students(confirmed: bool | None) -> None:
            if confirmed:
                self.send_emails_worker(students_to_email)
                self.update_status(
                f"[green]Emailed QR codes to {len(students_to_email)}[/]"
            )

        if all_students:
            students_to_email = self.dbase.get_all_students()
            self._add_progress_bar(len(students_to_email), "Send Emails")
        elif self._selected_student_id:
            student = self.dbase.get_student_by_id(self._selected_student_id)
            if student is None:
                self.update_status(
                    f"[red]Unable to locate student {self._selected_student_id}[/]"
                )
                return
            else:
                students_to_email = [student]
        else:
            self.update_status(
                "[red]No student selected.[/]"
            )
            return
        
        if all_students:
            await self.app.push_screen(
                confirm_dialogs.GeneralConfirmDialog("email all students"),
                callback=_email_all_students
            )
        else:
            self.send_emails_worker(students_to_email)

    @textual.work(thread=True)
    async def send_emails_worker(self, students: list[sqlite3.Row]) -> None:
        """Send QR emails to students."""
        if config.settings.qr_code_dir is None:
            self.update_status(
                "[red] Cannot send emails with QR codes because "
                "no QR code path is defined in config file.[/]")
            return
        email_sender = emailer.send_all_emails(config.settings.qr_code_dir, students)
        failed_codes = []
        for student_id, status in email_sender:
            if not status:
                failed_codes.append(student_id)
            self.app.call_from_thread(self._advance_progress_bar)
        status_message = (
            f"[green]Sent {len(students) - len(failed_codes)} email messages with "
            f"QR codes in folder {config.settings.qr_code_dir}\n"
        )
        if failed_codes:
            status_message += ("[red]Failed Emails: " + ", ".join(failed_codes) + "[/]")
        self.update_status(status_message)
        self.app.call_from_thread(self._remove_progress_bar)

    async def action_import_csv(self) -> None:
        def on_import_closed(imported_students: list | None):
            if imported_students:
                success_count = 0
                error_count = 0
                for student_data in imported_students:
                    success = self.dbase.add_student(**student_data)
                    if success:
                        success_count += 1
                    else:
                        error_count += 1

                self.load_student_data()

                if error_count == 0:
                    self.update_status(
                        f"[green]Successfully imported {success_count} students.[/]"
                    )
                else:
                    self.update_status(
                        f"[green]Imported {success_count} students.[/] "
                        f" [red]Failed to import {error_count} students. "
                        "(If they are duplicates, you can ignore this message.)[/]")

        await self.app.push_screen(modals.CSVImportDialog(), callback=on_import_closed)

    def update_status(self, message: str) -> None:
        """Update the text in the status widget."""
        self.query_one("#status-message", widgets.Static).update(message)

    def update_selected(self, message: str) -> None:
        self.query_one("#selection-indicator", widgets.Static).update(message)