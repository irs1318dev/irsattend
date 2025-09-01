"""View roster and add new students."""
import sqlite3

from textual import app, binding, containers, screen, widgets

from irsattend.model import config, database, emailer, qr_code_generator
from irsattend.view import modals


class ManagementScreen(screen.Screen):
    """Add, delete, and edit students."""
    dbase: database.DBase
    """Connection to Sqlite Database."""

    CSS_PATH = "../styles/management.tcss"
    BINDINGS = [
        binding.Binding("escape", "app.pop_screen", "Back to Main Screen", show=True),
    ]

    def __init__(self) -> None:
        """Initialize databae connection."""
        super().__init__()
        self.dbase = database.DBase(config.settings.db_path)

    def compose(self) -> app.ComposeResult:
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
                        "Add Student", variant="success", id="add-student")
                    yield widgets.Button(
                        "Import from CSV", variant="success", id="import-csv")
                    yield widgets.Button(
                        "Edit Selected", id="edit-student", disabled=True)
                    yield widgets.Button(
                        "Delete Selected",
                        variant="error",
                        id="delete-student",
                        disabled=True,
                    )
                    yield widgets.Static()
                    yield widgets.Label("Communication")
                    yield widgets.Button(
                        "Email QR Code to Selected", id="email-qr", disabled=True
                    )  # TODO implement email functionality
                    yield widgets.Button("Email All QR Codes", id="email-all-qr")
                    yield widgets.Static(
                        id="status-message", classes="status"
                    )  # To be used for error and success messages

        yield widgets.Footer()

    def on_mount(self) -> None:
        self.table = self.query_one(widgets.DataTable)
        self.table.cursor_type = "row"
        self.table.add_columns(
            "ID", "Last Name", "First Name", "Email", "Grad Year", "Attendance Count"
        )
        self.load_student_data()
        self.selected_student_id = None

    # Load students from db
    def load_student_data(self) -> None:
        self.table.clear()
        students = self.dbase.get_all_students()
        counts = self.dbase.get_attendance_counts()
        for student in students:
            self.table.add_row(
                student["student_id"],
                student["last_name"],
                student["first_name"],
                student["email"] or "N/A",
                str(student["grad_year"]) if student["grad_year"] else "N/A",
                str(counts.get(student["student_id"], 0)),
                key=student["student_id"],
            )

    # Handle selecting row
    def on_data_table_row_selected(self, event: widgets.DataTable.RowSelected) -> None:
        self.selected_student_id = event.row_key.value
        if self.selected_student_id is None:
            return
        self.query_one("#edit-student", widgets.Button).disabled = False
        self.query_one("#delete-student", widgets.Button).disabled = False
        student = self.dbase.get_student_by_id(self.selected_student_id)
        self.query_one("#email-qr", widgets.Button).disabled = not (
            student and student["email"]
        )

        if student:
            self.update_selected(
                f"[bold]Selected:[/bold]\n{student['first_name']} "
                f"{student['last_name']}\nID: {student['student_id']}")

    # Handle button press
    async def on_button_pressed(self, event: widgets.Button.Pressed) -> None:
        if event.button.id == "add-student":
            await self.action_add_student()
        elif event.button.id == "import-csv":
            await self.action_import_csv()
        elif event.button.id == "edit-student":
            await self.action_edit_student()
        elif event.button.id == "delete-student":
            await self.action_delete_student()
        elif event.button.id == "email-qr":
            self.action_email_qr(all_students=False)
        elif event.button.id == "email-all-qr":
            self.action_email_qr(all_students=True)

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
        if self.selected_student_id is None:
            return
        student = self.dbase.get_student_by_id(self.selected_student_id)
        if student is None:
            return
        attendance = self.dbase.get_attendance_count_by_id(self.selected_student_id)
        student["attendance"] = attendance

        def on_dialog_closed(data: dict | None):
            if data is None or self.selected_student_id is None:
                return
            # Remove attendance from data before updating student info
            attendance_count = data.pop("attendance", None)
            self.dbase.update_student(**data)
            # Might change the way this is done in the future, the current way is a pain
            if attendance_count is not None:
                current_attendance = attendance
                if attendance_count == 0:
                    self.dbase.remove_all_attendance_records(self.selected_student_id)
                elif attendance_count > 0:
                    difference = attendance_count - current_attendance
                    if difference > 0:
                        # This means we need to add more records
                        for _ in range(difference):
                            self.dbase.add_attendance_record(self.selected_student_id)
                    elif difference < 0:
                        # This means we need to remove records
                        for _ in range(abs(difference)):
                            self.dbase.remove_last_attendance_record(
                                self.selected_student_id
                            )
                    self.update_status("[green]Student updated successfully.[/]")
            else:
                self.update_status("[green]Student updated successfully.[/]")
            self.load_student_data()

        await self.app.push_screen(
            modals.StudentDialog(student_data=student), callback=on_dialog_closed
        )

    async def action_delete_student(self) -> None:
        if self.selected_student_id is None:
            return
        student = self.dbase.get_student_by_id(self.selected_student_id)
        if student is None:
            return
        student_name = f"{student['first_name']} {student['last_name']}"

        def on_confirm_closed(confirmed: bool | None):
            if confirmed:
                if self.selected_student_id is not None:
                    self.dbase.delete_student(self.selected_student_id)
                self.load_student_data()
                self.update_status("[green]Student deleted successfully.[/]")
                self.selected_student_id = None
                self.query_one("#edit-student", widgets.Button).disabled = True
                self.query_one("#delete-student", widgets.Button).disabled = True
                self.query_one("#selection-indicator", widgets.Static).update(
                    "No student selected"
                )

        await self.app.push_screen(
            modals.DeleteConfirmDialog(student_name, student["student_id"]),
            callback=on_confirm_closed,
        )

    def action_email_qr(self, all_students: bool) -> None:
        if all_students:
            students_to_email = self.dbase.get_all_students()
        elif self.selected_student_id:
            students_to_email = [self.dbase.get_student_by_id(self.selected_student_id)]
        else:
            return

        # This has to be ran in a worker to not block the UI
        self.run_worker(self.send_emails_worker(students_to_email), exclusive=False)

    async def send_emails_worker(self, students_to_email: list) -> None:
        # status_widget = self.query_one("#status-message", Static)
        success_count = 0
        fail_count = 0

        for student in students_to_email:
            if not student["email"]:
                fail_count += 1
                continue
            try:
                qr_code_path = qr_code_generator.generate_qr_code_image(
                    student["student_id"], f"{student['student_id']}.png" #, "QRCode"
                )
                if qr_code_path is None:
                    self.update_status(
                        f"[red]Error generating QR code for"
                        f"{student['first_name']} {student['last_name']}[/]"
                    )
                    return
                full_name = f"{student['first_name']} {student['last_name']}"
                sent, msg = emailer.send_email(
                    student["email"], full_name, qr_code_path)
                if sent:
                    success_count += 1
                else:
                    fail_count += 1
                    self.update_status(f"[red]Error sending to {student['email']}: {msg}[/]")
                # Remove temp file
                if qr_code_path is not None and qr_code_path.exists():
                    qr_code_path.unlink()

            except Exception as e:
                fail_count += 1
                self.update_status(
                    f"[red]Error processing {student['first_name']} "
                    f"{student['last_name']}: {str(e)}[/]")
                raise(e)

        # Add final msg after all emails are sent
        final_msg = f"[green]Sent {success_count} emails.[/]"
        if fail_count > 0:
            final_msg += (
                f" [red]Failed to send {fail_count} "
                "(check SMTP config/student emails).[/]"
            )
        self.update_status(final_msg)

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