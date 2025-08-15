import os
from textual.app import ComposeResult
from textual.screen import Screen
from textual.binding import Binding
from textual.widgets import Header, Footer, DataTable, Static, Button, Label
from textual.containers import Vertical, Horizontal, ScrollableContainer

from ..emailer import send_email
from ..scanner.qr_code_generator import generate_qr_code_image
from .modals import CSVImportDialog, DeleteConfirmDialog, StudentDialog
from ..db import database as db


class ManagementView(Screen):
    CSS_PATH = "../styles/management.tcss"
    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back to Main Screen", show=True),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            with Vertical(id="student-list-container"):
                yield Label("Student List")
                yield DataTable(id="student-table")
            with Vertical(id="actions-container"):
                yield Label("Actions")
                with ScrollableContainer():
                    yield Static(
                        "No student selected",
                        id="selection-indicator",
                        classes="selection-info",
                    )
                    yield Static()
                    yield Button("Add Student", variant="success", id="add-student")
                    yield Button("Import from CSV", variant="success", id="import-csv")
                    yield Button("Edit Selected", id="edit-student", disabled=True)
                    yield Button(
                        "Delete Selected",
                        variant="error",
                        id="delete-student",
                        disabled=True,
                    )
                    yield Static()
                    yield Label("Communication")
                    yield Button(
                        "Email QR Code to Selected", id="email-qr", disabled=True
                    )  # TODO implement email functionality
                    yield Button("Email All QR Codes", id="email-all-qr")
                    yield Static(
                        id="status-message", classes="status"
                    )  # To be used for error and success messages

        yield Footer()

    def on_mount(self) -> None:
        self.table = self.query_one(DataTable)
        self.table.cursor_type = "row"
        self.table.add_columns(
            "ID", "Last Name", "First Name", "Email", "Grad Year", "Attendance Count"
        )
        self.load_student_data()
        self.selected_student_id = None

    # Load students from db
    def load_student_data(self) -> None:
        self.table.clear()
        students = db.get_all_students()
        counts = db.get_attendance_counts()
        for student in students:
            self.table.add_row(
                student["id"],
                student["last_name"],
                student["first_name"],
                student["email"] or "N/A",
                str(student["grad_year"]) if student["grad_year"] else "N/A",
                str(counts.get(student["id"], 0)),
                key=student["id"],
            )

    # Handle selecting row
    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        self.selected_student_id = event.row_key.value
        self.query_one("#edit-student", Button).disabled = False
        self.query_one("#delete-student", Button).disabled = False
        student = db.get_student_by_id(self.selected_student_id)
        self.query_one("#email-qr", Button).disabled = not (
            student and student["email"]
        )

        if student:
            selection_text = f"[bold]Selected:[/bold]\n{student['first_name']} {student['last_name']}\nID: {student['id']}"
            self.query_one("#selection-indicator", Static).update(selection_text)

    # Handle button press
    async def on_button_pressed(self, event: Button.Pressed) -> None:
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
        def on_dialog_closed(data: dict | None):
            if data:
                data.pop("attendance", None)
                try:
                    student_id = db.add_student(**data)
                    self.load_student_data()
                    self.query_one("#status-message", Static).update(
                        f"[green]Student added successfully. ID: {student_id}[/]"
                    )
                except Exception:
                    self.query_one("#status-message", Static).update(
                        f"[red]Error adding student (duplicate email?)[/]"
                    )

        await self.app.push_screen(StudentDialog(), callback=on_dialog_closed)

    async def action_edit_student(self) -> None:
        if self.selected_student_id:
            student = dict(db.get_student_by_id(self.selected_student_id))
            attendance = db.get_attendance_count_by_id(self.selected_student_id)
            student["attendance"] = attendance

            def on_dialog_closed(data: dict | None):
                if data:
                    # Remove attendance from data before updating student info
                    attendance_count = data.pop("attendance", None)
                    db.update_student(**data)
                    # Might change the way this is done in the future, the current way is a pain
                    if attendance_count is not None:
                        current_attendance = attendance
                        if attendance_count == 0:
                            db.remove_all_attendance_records(self.selected_student_id)
                        elif attendance_count > 0:
                            difference = attendance_count - current_attendance
                            if difference > 0:
                                # This means we need to add more records
                                for _ in range(difference):
                                    db.add_attendance_record(self.selected_student_id)
                            elif difference < 0:
                                # This means we need to remove records
                                for _ in range(abs(difference)):
                                    db.remove_last_attendance_record(
                                        self.selected_student_id
                                    )

                            self.query_one("#status-message", Static).update(
                                "[green]Student updated successfully.[/]"
                            )
                    else:
                        self.query_one("#status-message", Static).update(
                            "[green]Student updated successfully.[/]"
                        )
                    self.load_student_data()

            await self.app.push_screen(
                StudentDialog(student_data=student), callback=on_dialog_closed
            )

    async def action_delete_student(self) -> None:
        if self.selected_student_id:
            student = db.get_student_by_id(self.selected_student_id)
            if student:
                student_name = f"{student['first_name']} {student['last_name']}"

                def on_confirm_closed(confirmed: bool | None):
                    if confirmed:
                        db.delete_student(self.selected_student_id)
                        self.load_student_data()
                        self.query_one("#status-message", Static).update(
                            "[green]Student deleted successfully.[/]"
                        )
                        self.selected_student_id = None
                        self.query_one("#edit-student", Button).disabled = True
                        self.query_one("#delete-student", Button).disabled = True
                        self.query_one("#selection-indicator", Static).update(
                            "No student selected"
                        )

                await self.app.push_screen(
                    DeleteConfirmDialog(student_name, student["id"]),
                    callback=on_confirm_closed,
                )

    def action_email_qr(self, all_students: bool) -> None:
        if all_students:
            students_to_email = db.get_all_students()
        elif self.selected_student_id:
            students_to_email = [db.get_student_by_id(self.selected_student_id)]
        else:
            return

        # This has to be ran in a worker to not block the UI
        self.run_worker(self.send_emails_worker(students_to_email), exclusive=False)

    async def send_emails_worker(self, students_to_email: list) -> None:
        status_widget = self.query_one("#status-message", Static)
        success_count = 0
        fail_count = 0

        for student in students_to_email:
            if not student["email"]:
                fail_count += 1
                continue

            try:
                qr_code_path = generate_qr_code_image(
                    student["id"], f"{student['id']}.png", "QRCode"
                )
                full_name = f"{student['first_name']} {student['last_name']}"

                sent, msg = send_email(student["email"], full_name, qr_code_path)
                if sent:
                    success_count += 1
                else:
                    fail_count += 1
                    status_widget.update(
                        f"[red]Error sending to {student['email']}: {msg}[/]"
                    )

                # Remove temp file
                if os.path.exists(qr_code_path):
                    os.remove(qr_code_path)

            except Exception as e:
                fail_count += 1
                status_widget.update(
                    f"[red]Error processing {student['first_name']} {student['last_name']}: {str(e)}[/]"
                )

        # Add final msg after all emails are sent
        final_msg = f"[green]Sent {success_count} emails.[/]"
        if fail_count > 0:
            final_msg += f" [red]Failed to send {fail_count} (check SMTP config/student emails).[/]"
        status_widget.update(final_msg)

    async def action_import_csv(self) -> None:
        def on_import_closed(imported_students: list | None):
            if imported_students:
                success_count = 0
                error_count = 0

                for student_data in imported_students:
                    success = db.add_student(**student_data)
                    if success:
                        success_count += 1
                    else:
                        error_count += 1

                self.load_student_data()

                if error_count == 0:
                    self.query_one("#status-message", Static).update(
                        f"[green]Successfully imported {success_count} students.[/]"
                    )
                else:
                    error_msg = f"[green]Imported {success_count} students.[/] [red]Failed to import {error_count} students. (If they are duplicates, you can ignore this message.)[/]"
                    self.query_one("#status-message", Static).update(error_msg)

        await self.app.push_screen(CSVImportDialog(), callback=on_import_closed)
