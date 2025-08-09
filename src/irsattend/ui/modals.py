import csv
import hashlib
import os
from .. import config
from textual.app import ComposeResult
from textual.widgets import Label, Input, Static, Button
from textual.validation import ValidationResult, Validator
from textual.screen import ModalScreen
from textual.containers import Vertical, Horizontal

class NotEmpty(Validator):
    def validate(self, value: str) -> ValidationResult:
        if not value:
            return self.failure("Field cannot be empty.")
        return self.success()

class IsInteger(Validator):
    def validate(self, value: str) -> ValidationResult:
        if value and not value.isdigit():
            return self.failure("Must be a valid year (e.g., 2025).")
        return self.success()


class PasswordPrompt(ModalScreen):
    """A modal screen to ask for the management password."""

    def compose(self) -> ComposeResult:
        with Vertical(id="password-dialog"):
            yield Label("Enter Management Password")
            yield Input(password=True, id="password-input")
            yield Static("", id="password-error")
            with Horizontal(id="password-actions"):
                yield Button("Submit", variant="primary", id="submit-password")
                yield Button("Cancel", id="cancel-password")

    def on_mount(self) -> None:
        self.query_one("#password-input", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "submit-password":
            self.check_password()
        elif event.button.id == "cancel-password":
            self.app.pop_screen()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.check_password()

    def check_password(self) -> None:
        password = self.query_one("#password-input", Input).value
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        error_msg = self.query_one("#password-error", Static)
        if hashed_password == config.MANAGEMENT_PASSWORD_HASH:
            self.dismiss(True)  # Dismiss with success
        else:
            error_msg.update("[bold red]Incorrect Password[/]")
            self.query_one("#password-input", Input).value = ""

class StudentDialog(ModalScreen):
    """A dialog for adding or editing student details."""

    def __init__(self, student_data: dict | None = None) -> None:
        self.student_data = student_data
        super().__init__()
        if not student_data:
            self.add_class("add-mode")

    def compose(self) -> ComposeResult:
        title = "Edit Student" if self.student_data else "Add New Student"
        self.count = self.student_data['attendance'] if self.student_data and 'attendance' in self.student_data else 0
        with Vertical(id="student-dialog"):
            yield Label(title)
            yield Input(
                value=self.student_data['id'] if self.student_data else "",
                placeholder="Student ID (Barcode)",
                id="s-id",
                validators=[NotEmpty()]
            )
            yield Input(
                value=self.student_data['first_name'] if self.student_data else "",
                placeholder="First Name",
                id="s-fname",
                validators=[NotEmpty()]
            )
            yield Input(
                value=self.student_data['last_name'] if self.student_data else "",
                placeholder="Last Name",
                id="s-lname",
                validators=[NotEmpty()]
            )
            yield Input(
                value=self.student_data['email'] if self.student_data else "",
                placeholder="Email",
                id="s-email",
                validators=[NotEmpty()]
            )
            yield Input(
                value=str(self.student_data['grad_year']) if self.student_data and self.student_data['grad_year'] else "",
                placeholder="Graduation Year",
                id="s-gyear",
                validators=[NotEmpty(), IsInteger()]
            )
            yield Static()
            if self.student_data:
                with Horizontal():
                    yield Label("Attendance Count: " + str(self.count), id="attendance-label")
                    yield Button("+", variant="success", id="add-attendance")
                    yield Button("-", variant="error", id="remove-attendance")
            with Horizontal(id="attendance-actions"):
                yield Button("Save", variant="primary", id="save-student")
                yield Button("Cancel", id="cancel-student")

    def on_mount(self) -> None:
        # Disable ID editing for existing students
        if self.student_data:
            self.query_one("#s-id", Input).disabled = True

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "add-attendance":
            self.count += 1
            try:
                self.query_one("#attendance-label", Label).update(f"Attendance Count: {self.count}")
            except:
                pass
        elif event.button.id == "remove-attendance":
            if self.count > 0:
                self.count -= 1
                try:
                    self.query_one("#attendance-label", Label).update(f"Attendance Count: {self.count}")
                except:
                    pass
        elif event.button.id == "save-student":
            data = {
                "id": self.query_one("#s-id", Input).value,
                "first_name": self.query_one("#s-fname", Input).value,
                "last_name": self.query_one("#s-lname", Input).value,
                "email": self.query_one("#s-email", Input).value or None,
                "grad_year": int(self.query_one("#s-gyear", Input).value) if self.query_one("#s-gyear", Input).value else None,
                "attendance": self.count
            }
            self.dismiss(data)
        elif event.button.id == "cancel-student":
            self.dismiss(None)

class DeleteConfirmDialog(ModalScreen):
    """A confirmation dialog for deleting students."""

    def __init__(self, student_name: str, student_id: str) -> None:
        self.student_name = student_name
        self.student_id = student_id
        super().__init__()

    def compose(self) -> ComposeResult:
        with Vertical(id="delete-dialog"):
            yield Label("[bold red]Confirm Deletion[/bold red]")
            yield Static()
            yield Label(f"Are you sure you want to delete:")
            yield Label(f"[bold]{self.student_name}[/bold]")
            yield Label(f"ID: {self.student_id}")
            yield Static()
            yield Label("[yellow]This action cannot be undone![/yellow]")
            yield Static()
            with Horizontal():
                yield Button("Delete", variant="error", id="confirm-delete")
                yield Button("Cancel", variant="primary", id="cancel-delete")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm-delete":
            self.dismiss(True)
        elif event.button.id == "cancel-delete":
            self.dismiss(False)
            
class CSVImportDialog(ModalScreen):
    """A dialog for importing students from CSV."""

    def compose(self) -> ComposeResult:
        with Vertical(id="csv-import-dialog"):
            yield Label("[bold]Import Students from CSV[/bold]")
            yield Static()
            yield Label("CSV Format Requirements:")
            yield Static("The CSV file must have these column headers (first row):")
            yield Static('[yellow]"ID", "Last Name", "First Name", "Email", "Grad Year"[/yellow]')
            yield Static("[bold red]All fields are required - no empty values allowed.[/bold red]")
            yield Static()
            yield Label("Select CSV File:")
            yield Input(placeholder="Enter full path to CSV file", id="csv-path")
            yield Static("", id="csv-import-status")
            with Horizontal():
                yield Button("Import", variant="primary", id="start-import")
                yield Button("Cancel", id="cancel-import")

    def on_mount(self) -> None:
        self.query_one("#csv-path", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "start-import":
            self.start_import()
        elif event.button.id == "cancel-import":
            self.dismiss(None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.start_import()

    def start_import(self) -> None:
        csv_path = self.query_one("#csv-path", Input).value.strip()
        status_widget = self.query_one("#csv-import-status", Static)
        
        if not csv_path:
            status_widget.update("[red]Please enter a file path.[/]")
            return
            
        if not os.path.exists(csv_path):
            status_widget.update("[red]File not found.[/]")
            return
            
        try:
            imported_students = []
            
            with open(csv_path, 'r', newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                
                # Check if required columns exist
                required_columns = ["ID", "Last Name", "First Name", "Email", "Grad Year"]
                missing_columns = [col for col in required_columns if col not in reader.fieldnames]
                
                if missing_columns:
                    status_widget.update(f"[red]Missing columns: {', '.join(missing_columns)}[/]")
                    return
                
                for row_num, row in enumerate(reader, start=2):  # Start at 2 since row 1 is headers
                    # Check if all rows exist
                    field_validators = {
                        "ID": NotEmpty(),
                        "First Name": NotEmpty(),
                        "Last Name": NotEmpty(),
                        "Email": NotEmpty(),
                        "Grad Year": IsInteger()
                    }
                    
                    for field_name, validator in field_validators.items():
                        field_value = row[field_name].strip()
                        validation_result = validator.validate(field_value)
                        if not validation_result.is_valid:
                            status_widget.update(f"[red]Row {row_num}: {field_name} - {validation_result.failure_description}[/]")
                            return
                    
                    student_data = {
                        "id": row["ID"].strip(),
                        "first_name": row["First Name"].strip(),
                        "last_name": row["Last Name"].strip(),
                        "email": row["Email"].strip(),
                        "grad_year": int(row["Grad Year"].strip())
                    }
                    
                    imported_students.append(student_data)
            
            if not imported_students:
                status_widget.update("[red]No valid data found in CSV.[/]")
                return
                
            self.dismiss(imported_students)
            
        except Exception as e:
            status_widget.update(f"[red]Error reading CSV: {str(e)}[/]")
            