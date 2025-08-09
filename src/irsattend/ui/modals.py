from textual.app import ComposeResult
from textual.widgets import ModalScreen, Vertical, Horizontal, Label, Input, Static, Button
from textual.validation import ValidationResult, Validator

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

    def compose(self) -> ComposeResult:
        title = "Edit Student" if self.student_data else "Add New Student"
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
                placeholder="Email (Optional)",
                id="s-email"
            )
            yield Input(
                value=str(self.student_data['grad_year']) if self.student_data and self.student_data['grad_year'] else "",
                placeholder="Graduation Year (Optional)",
                id="s-gyear",
                validators=[IsInteger()]
            )
            with Horizontal():
                yield Button("Save", variant="primary", id="save-student")
                yield Button("Cancel", id="cancel-student")

    def on_mount(self) -> None:
        # Disable ID editing for existing students
        if self.student_data:
            self.query_one("#s-id", Input).disabled = True

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save-student":
            data = {
                "id": self.query_one("#s-id", Input).value,
                "first_name": self.query_one("#s-fname", Input).value,
                "last_name": self.query_one("#s-lname", Input).value,
                "email": self.query_one("#s-email", Input).value or None,
                "grad_year": int(self.query_one("#s-gyear", Input).value) if self.query_one("#s-gyear", Input).value else None,
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