"""QUILL Transcribe's tutorials: the descriptor the shared window is handed (D-25).

The lessons are :mod:`quill.core.transcribe.tutorials`'s; the window is the
family's own (:mod:`quill.ui.tutorials_window`). None of the five lessons
carries a check -- dictation's outcomes are said out loud already -- so there
is no probe, and Follow Me has nothing to watch.
"""

from __future__ import annotations

from typing import Any

from quill.core.transcribe.tutorials import CATALOGUE, TITLE
from quill.ui.tutorials_window import TutorialsApp
from quill.ui.tutorials_window import open_tutorials as _open

__all__ = ["APP", "PROBE", "open_tutorials"]

#: No checks to answer (test_tutorial_catalogues reads this).
PROBE = None


def _open_book(host: Any) -> None:
    """Open the rendered tutorial book."""
    host.open_app_document(
        host._doc_candidates("quill-transcribe", "tutorials"),
        title=TITLE,
        cache_name="app-docs",
    )


APP = TutorialsApp(
    app_id="transcribe",
    title=TITLE,
    catalogue=CATALOGUE,
    progress_file="transcribe_tutorials.json",
    open_book=_open_book,
)


def open_tutorials(host: Any, *, slug: str = "") -> None:
    """Help > Tutorials...: open (or raise) QUILL Transcribe's lessons."""
    _open(host, APP, slug=slug)
