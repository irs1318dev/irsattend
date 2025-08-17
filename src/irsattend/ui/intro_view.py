"""First screen that is displayed on app startup."""
import pathlib

from textual import app, binding, screen, widgets

from irsattend import config
from irsattend.db import database


class IntroView(screen.Screen):
    """IRSAttend App Introduction Screen."""

    CSS_PATH = "../styles/main.tcss"
    BINDINGS = [
        binding.Binding(key="CRTRL+q", action="quit", description="Quit Application")
    ]

    def compose(self) -> app.ComposeResult:
        """Add widgets to screen."""
        yield widgets.Header()
        yield widgets.Markdown("### Current Configuration")
        yield widgets.Markdown(repr(config.settings))
        yield widgets.Footer()