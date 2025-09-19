"""Confirmation Dialogs."""

from textual.app import ComposeResult
from textual.widgets import Label, Static, Button
from textual.screen import ModalScreen
from textual.containers import Vertical, Horizontal

class DeleteConfirmDialog(ModalScreen):
    """A confirmation dialog for deleting students."""
    CSS_PATH = "../styles/modal.tcss"

    student_name: str
    student_id: str

    def __init__(self, student_name: str, student_id: str) -> None:
        """Include student name and ID in confirmation dialog."""
        self.student_name = student_name
        self.student_id = student_id
        super().__init__(classes="confirm-dialog")

    def compose(self) -> ComposeResult:
        """Layout the dialog screen."""
        with Vertical(id="delete-dialog", classes="confirm-dialog"):
            yield Label("[bold red]Confirm Deletion[/bold red]")
            yield Static()
            yield Label("Are you sure you want to delete:")
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


class GeneralConfirmDialog(ModalScreen):
    """General confirmation dialog."""
    CSS_PATH = "../styles/modal.tcss"

    message: str
    """Message displayed to user in confirmation dialog."""

    def __init__(self, message: str) -> None:
        """Include task message in confirmation dialog."""
        super().__init__()
        self.message = message

    def compose(self) -> ComposeResult:
        """Layout the dialog box."""
        with Vertical(id="confirm-dialog", classes="confirm-dialog"):
            yield Label("[bold red]Confirm Action[/bold red]")
            yield Static()
            yield Label(f"Are you sure you want to {self.message}?")
            with Horizontal():
                yield Button("Delete", variant="error", id="confirm-action")
                yield Button("Cancel", variant="primary", id="cancel-action")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Take action if confirmed."""
        if event.button.id == "confirm-action":
            self.dismiss(True)
        elif event.button.id == "cancel-action":
            self.dismiss(False)