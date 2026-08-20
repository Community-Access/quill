"""Opening a file that is no longer there, without a crash report (#1423).

QUILL's office, PDF and large-file reads go through
``MainFrame._run_background_task``, whose worker catches whatever the read
raises and surfaces it on the UI thread. The cheap synchronous read -- a small
`.txt`, `.md` or `.html` -- had no such path, so opening a file that had been
moved, deleted, or left on a drive that is not connected raised
``FileNotFoundError`` straight into the crash handler. The report that found
this was a OneDrive path: QUILL showed a **crash report** for a file that was
simply gone, which teaches a user that the app is broken when the truth is that
their file is not where it was.

Kept out of both ``main_frame.py`` (at its GATE-11 ceiling) and
``main_frame_simple_open.py`` (at its own), so the mixin holds a delegate and
the behaviour lives here where it can be tested without a frame.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any


def read_document_or_report(
    host: Any,
    selected_path: Path,
    suffix: str,
    csv_mode: str | None,
    finish: Callable[[object], None],
) -> bool:
    """Read *selected_path* and hand it to *finish*. ``True`` when it opened.

    *host* supplies ``_set_status`` and, optionally, ``_announce``; nothing
    else, so a test can pass a stub.

    A failure is reported in one sentence and swallowed. **Recent is
    deliberately left alone**: ``core.recent.prune_missing_recent_files``
    already owns that decision and is bound by rules this path cannot see
    (#14 -- only confirmed fixed drives are ever probed, so a detached USB or an
    offline share never loses its history, and the whole behaviour sits behind
    ``recent_files_auto_clear_missing``). Dropping an entry from here would
    overrule both.
    """
    from quill.io.open_read import DocumentUnavailableError, read_open_document

    try:
        finish(read_open_document(selected_path, suffix, csv_mode=csv_mode))
    except DocumentUnavailableError as error:
        # args[0] rather than str(error): the code prefix belongs in the log and
        # the crash bundle, not in a sentence read out to somebody.
        _report(host, str(error.args[0]))
        return False
    except OSError as error:
        _report(host, f"{selected_path.name} could not be opened. {error}.")
        return False
    return True


def _report(host: Any, message: str) -> None:
    """Say it once, in the status bar and out loud."""
    status = getattr(host, "_set_status", None)
    if callable(status):
        status(message)
    announce = getattr(host, "_announce", None)
    if callable(announce):
        announce(message)
