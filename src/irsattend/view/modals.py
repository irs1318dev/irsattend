"""Modal dialog definitions."""


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
            yield widgets.Label("Deactivated on:")
            yield widgets.Input(
                value=(
                    self.student_data["deactivated_on"]
                    if self.student_data and self.student_data["deactivated_on"]
                    else ""
                ),
                placeholder="YYYY-MM-DD or leave blank if active",
                id="s-deactivated",
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
                "deactivated_on": (
                    self.query_one("#s-deactivated", widgets.Input).value
                    if self.query_one("#s-deactivated", widgets.Input).value
                    else None
                )
            }
            if self.student_data:
                data["student_id"] = self.student_data["student_id"]
            self.dismiss(data)
        elif event.button.id == "cancel-student":
            self.dismiss(None)

