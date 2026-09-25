"""QUILL Lite's tutorials: the descriptor the shared window is handed.

The window, the progress store and the step renderer are
:mod:`quill.ui.tutorials_window`, shared with Quill Radio, QUILL Cast, Quill
Weather and QUILL. The lessons are :mod:`quill.core.lite.tutorials`. This module
is the join, and is deliberately the whole of QUILL Lite's tutorial code.

**No check probe.** A step may carry a ``check`` -- the name of a question about
the app's live state that the window watches for ("something is playing now",
"your saved places grew") -- and none of QUILL Lite's eight lessons does. That is
not an omission. Those checks are worth having in an app whose verbs act on
something outside the document; here every step's outcome is a sentence the app
already says, and a step that says what you should **hear** is a step you can
check yourself. Inventing machinery to watch for "you pressed Ctrl+S" would be
answering a question nobody had.
"""

from __future__ import annotations

import sys
import webbrowser
from pathlib import Path
from typing import Any

from quill.core.lite.tutorials import CATALOGUE
from quill.ui.tutorials_window import TutorialsApp
from quill.ui.tutorials_window import open_tutorials as _open

TITLE = "QUILL Lite Tutorials"


def _book_path() -> Path | None:
    """The rendered tutorial book, wherever this build keeps its documents.

    A packaged build stages ``docs\\`` beside the exe; a checkout has
    ``standalone/quilllite/docs``. HTML first because it is what a browser
    renders properly, Markdown as the fallback so a dev run is not empty-handed.

    The lookup is three lines rather than a call to the app shell's
    ``_doc_candidates`` because QUILL Lite has no app shell: a document window is
    a ``wx.MDIChildFrame``, not an ``AppShell``, so the helper Radio, Cast and
    Weather share has no host here to hang off.
    """
    stem = "tutorials"
    roots: list[Path] = []
    if getattr(sys, "frozen", False):
        roots.append(Path(sys.executable).resolve().parent / "docs")
    roots.append(Path(__file__).resolve().parents[2] / "standalone" / "quilllite" / "docs")
    for root in roots:
        for suffix in (".html", ".md"):
            candidate = root / f"{stem}{suffix}"
            if candidate.is_file():
                return candidate
    return None


def _open_book(host: Any) -> None:
    """Open the rendered tutorial book in the browser.

    Best effort, and quiet about the one way it fails: a build with no staged
    documents. Saying "the book is missing" to somebody who pressed a button
    labelled "Open the book" tells them nothing they can act on, so the window
    keeps its own copy of the lessons either way -- which is the point of the
    book and the window being one source.
    """
    book = _book_path()
    if book is None:
        return
    try:
        webbrowser.open(book.as_uri())
    except Exception:  # noqa: BLE001 - no browser is not a failed tutorial
        return


APP = TutorialsApp(
    app_id="quilllite",
    title=TITLE,
    catalogue=CATALOGUE,
    progress_file="quilllite_tutorials.json",
    open_book=_open_book,
)


def open_tutorials(host: Any, *, slug: str = "") -> None:
    """Help > Tutorials... (Ctrl+Alt+F1): open, or raise, QUILL Lite's lessons."""
    _open(host, APP, slug=slug)
