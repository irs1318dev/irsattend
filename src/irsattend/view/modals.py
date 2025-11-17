"""Modal dialog definitions."""

from collections.abc import Sequence
import csv
import os

from textual import app, containers, screen, validation, widgets


class NotEmpty(validation.Validator):
    def validate(self, value: str) -> validation.ValidationResult:
        if not value:
            return self.failure("Field cannot be empty.")
        return self.success()


class IsInteger(validation.Validator):
    def validate(self, value: str) -> validation.ValidationResult:
        if value and not value.isdigit():
            return self.failure("Must be a valid year (e.g., 2025).")
        return self.success()


class StudentDialog(screen.ModalScreen):
    """A dialog for adding or editing student details."""

    CSS_PATH = "../styles/modal.tcss"

    def __init__(self, student_data: dict | None = None) -> None:
        self.student_data = student_data
        super().__init__()
        if not student_data:
            self.add_class("add-mode")

    def compose(self) -> app.ComposeResult:
        title = "Edit Student" if self.student_data else "Add New Student"
        self.count = (
            self.student_data["attendance"]
            if self.student_data and "attendance" in self.student_data
            else 0
        )
        with containers.Vertical(id="student-dialog"):
            yield widgets.Label(title)
            # Display read-only ID for existing students, but don't show input for new students
            if self.student_data:
                yield widgets.Label(f"Student ID: {self.student_data['student_id']}")
            yield widgets.Input(
                value=self.student_data["first_name"] if self.student_data else "",
                placeholder="First Name",
                id="s-fname",
                validators=[NotEmpty()],
            )
            yield widgets.Input(
                value=self.student_data["last_name"] if self.student_data else "",
                placeholder="Last Name",
                id="s-lname",
                validators=[NotEmpty()],
            )
            yield widgets.Input(
                value=self.student_data["email"] if self.student_data else "",
                placeholder="Email",
                id="s-email",
                validators=[NotEmpty()],
            )
            yield widgets.Input(
                value=(
                    str(self.student_data["grad_year"])
                    if self.student_data and self.student_data["grad_year"]
                    else ""
                ),
                placeholder="Graduation Year",
                id="s-gyear",
                validators=[NotEmpty(), IsInteger()],
            )
            yield widgets.Static()
            # if self.student_data:
            #     with Horizontal():
            #         yield Label(
            #             "Attendance Count: " + str(self.count), id="attendance-label"
            #         )
            #         yield Button("+", variant="success", id="add-attendance")
            #         yield Button("-", variant="error", id="remove-attendance")
            with containers.Horizontal(id="attendance-actions"):
                yield widgets.Button("Save", variant="primary", id="save-student")
                yield widgets.Button("Cancel", id="cancel-student")

    def on_mount(self) -> None:
        self.query_one("#s-fname", widgets.Input).focus()

    def on_button_pressed(self, event: widgets.Button.Pressed) -> None:
        if event.button.id == "add-attendance":
            self.count += 1
            self.query_one("#attendance-label", widgets.Label).update(
                f"Attendance Count: {self.count}"
            )

        elif event.button.id == "remove-attendance":
            if self.count > 0:
                self.count -= 1
                self.query_one("#attendance-label", widgets.Label).update(
                    f"Attendance Count: {self.count}"
                )

        elif event.button.id == "save-student":
            data = {
                "first_name": self.query_one("#s-fname", widgets.Input).value,
                "last_name": self.query_one("#s-lname", widgets.Input).value,
                "email": self.query_one("#s-email", widgets.Input).value or None,
                "grad_year": (
                    int(self.query_one("#s-gyear", widgets.Input).value)
                    if self.query_one("#s-gyear", widgets.Input).value
                    else None
                ),
                "attendance": self.count,
            }
            if self.student_data:
                data["student_id"] = self.student_data["student_id"]
            self.dismiss(data)
        elif event.button.id == "cancel-student":
            self.dismiss(None)


class CSVImportDialog(screen.ModalScreen):
    """A dialog for importing students from CSV."""

    CSS_PATH = "../styles/modal.tcss"

    def compose(self) -> app.ComposeResult:
        with containers.Vertical(id="csv-import-dialog"):
            yield widgets.Label("[bold]Import Students from CSV[/bold]")
            yield widgets.Static()
            yield widgets.Label("CSV Format Requirements:")
            yield widgets.Static("The CSV file must have these column headers (first row):")
            yield widgets.Static(
                '[yellow]"Last Name", "First Name", "Email", "Grad Year"[/yellow]'
            )
            yield widgets.Static(
                "[bold red]All fields are required - no empty values allowed.[/bold red]"
            )
            yield widgets.Static()
            yield widgets.Label("Select CSV File:")
            yield widgets.Input(placeholder="Enter full path to CSV file", id="csv-path")
            yield widgets.Static("", id="csv-import-status")
            with containers.Horizontal():
                yield widgets.Button("Import", variant="primary", id="start-import")
                yield widgets.Button("Cancel", id="cancel-import")

    def on_mount(self) -> None:
        self.query_one("#csv-path", widgets.Input).focus()

    def on_button_pressed(self, event: widgets.Button.Pressed) -> None:
        if event.button.id == "start-import":
            self.start_import()
        elif event.button.id == "cancel-import":
            self.dismiss(None)

    def on_input_submitted(self, event: widgets.Input.Submitted) -> None:
        self.start_import()

    def start_import(self) -> None:
        """Import information from a CSV file."""
        csv_path = self.query_one("#csv-path", widgets.Input).value.strip()
        status_widget = self.query_one("#csv-import-status", widgets.Static)
        if not csv_path:
            status_widget.update("[red]Please enter a file path.[/]")
            return
        if not os.path.exists(csv_path):
            status_widget.update("[red]File not found.[/]")
            return
        imported_students = []
        with open(csv_path, "r", newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            if not isinstance(reader.fieldnames, Sequence):
                return
            required_columns = [
                "Last Name",
                "First Name",
                "Email",
                "Grad Year",
            ]
            missing_columns = [
                col for col in required_columns if col not in reader.fieldnames
            ]
            if missing_columns:
                status_widget.update(
                    f"[red]Missing columns: {', '.join(missing_columns)}[/]"
                )
                return
            # Start at 2 since row 1 is headers
            for row_num, row in enumerate(reader, start=2):
                # Check if all rows exist
                field_validators = {
                    "First Name": NotEmpty(),
                    "Last Name": NotEmpty(),
                    "Email": NotEmpty(),
                    "Grad Year": IsInteger(),
                }
                for field_name, validator in field_validators.items():
                    field_value = row[field_name].strip()
                    validation_result = validator.validate(field_value)
                    if not validation_result.is_valid:
                        status_widget.update(
                            f"[red]Row {row_num}: {field_name} - "
                            f"{validation_result.failure_descriptions}[/]"
                        )
                        return
                student_data = {
                    "first_name": row["First Name"].strip(),
                    "last_name": row["Last Name"].strip(),
                    "email": row["Email"].strip(),
                    "grad_year": int(row["Grad Year"].strip()),
                }
                imported_students.append(student_data)
        if not imported_students:
            status_widget.update("[red]No valid data found in CSV.[/]")
            return
        self.dismiss(imported_students)
