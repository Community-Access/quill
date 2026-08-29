"""QUILL Cast's tutorials: the descriptor the shared window is handed."""

from __future__ import annotations

from typing import Any

from quill.core.podcasts.tutorials import CATALOGUE
from quill.ui.podcasts.tutorial_checks import PROBE
from quill.ui.tutorials_window import TutorialsApp
from quill.ui.tutorials_window import open_tutorials as _open

TITLE = "QUILL Cast Tutorials"


def _open_book(host: Any) -> None:
    """Open the rendered tutorial book in the browser."""
    host._open_podcasts_doc("tutorials")


APP = TutorialsApp(
    app_id="cast",
    title=TITLE,
    catalogue=CATALOGUE,
    progress_file="cast_tutorials.json",
    open_book=_open_book,
    probe=PROBE,
)


def open_tutorials(host: Any, *, slug: str = "") -> None:
    """Help > Tutorials...: open (or raise) Cast's lessons."""
    _open(host, APP, slug=slug)
