"""Quill Radio's tutorials: the descriptor the shared window is handed.

Everything here is Radio-shaped and nothing here is a window: the lessons come
from :mod:`quill.core.radio.tutorials`, the machinery from
:mod:`quill.ui.tutorials_window`, and this is the seam between them.
"""

from __future__ import annotations

from typing import Any

from quill.core.radio.tutorials import CATALOGUE
from quill.ui.radio.tutorial_checks import PROBE
from quill.ui.tutorials_window import TutorialsApp
from quill.ui.tutorials_window import open_tutorials as _open

TITLE = "Quill Radio Tutorials"


def _open_book(host: Any) -> None:
    """Open the rendered tutorial book in the listener's browser."""
    from quill.apps import radio_help_docs

    radio_help_docs.open_doc(host, "tutorials")


APP = TutorialsApp(
    app_id="radio",
    title=TITLE,
    catalogue=CATALOGUE,
    progress_file="radio_tutorials.json",
    open_book=_open_book,
    probe=PROBE,
)


def open_tutorials(host: Any, *, slug: str = "") -> None:
    """Help > Tutorials...: open (or raise) Radio's lessons."""
    _open(host, APP, slug=slug)
