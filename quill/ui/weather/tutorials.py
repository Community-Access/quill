"""Quill Weather's tutorials: the descriptor the shared window is handed."""

from __future__ import annotations

from typing import Any

from quill.core.weather.tutorials import CATALOGUE
from quill.ui.tutorials_window import TutorialsApp
from quill.ui.tutorials_window import open_tutorials as _open
from quill.ui.weather.tutorial_checks import PROBE

TITLE = "Quill Weather Tutorials"


def _open_book(host: Any) -> None:
    """Open the rendered tutorial book in the browser."""
    host._open_weather_doc("tutorials")


APP = TutorialsApp(
    app_id="weather",
    title=TITLE,
    catalogue=CATALOGUE,
    progress_file="weather_tutorials.json",
    open_book=_open_book,
    probe=PROBE,
)


def open_tutorials(host: Any, *, slug: str = "") -> None:
    """Help > Tutorials...: open (or raise) Weather's lessons."""
    _open(host, APP, slug=slug)
