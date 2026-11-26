"""QUILL Lite: a failed open or save says what happened and offers the next step (FUX-16).

Both used to be an OK-only box with the exception's own text after the file
name ("Could not open notes.txt. [Errno 13] Permission denied: 'C:\\...'"),
and a failed save never said the text was still there. Now:

* the first sentence names the file and says, in plain words, what kind of
  thing went wrong and what was kept ("Nothing was opened", "your text is still
  open and unsaved"). The save words are QUILL's own
  (``command_failure.save_failure_sentence``), so the two editors say the same;
* the default button is the one step that fits: Retry when the same open may
  well work now (a locked file, a network folder), Choose Another File when the
  file is gone, Save As for any failed save;
* the error's own text is behind Show Details and Copy Details, redacted, and
  nothing is sent anywhere.

Plain functions over the window rather than a mixin: the window module is at
its size cap, and these are called from four places in three mixins.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

__all__ = ["report_open_failure", "report_save_failure"]


def _authored(exc: BaseException) -> str:
    """The exception's text when QUILL wrote it for people, else ''."""
    from quill.ui.richedit_rtf_surface import RichEditRtfError

    return str(exc).strip() if type(exc) is RichEditRtfError else ""


def _show(
    window: Any,
    message: str,
    caption: str,
    exc: BaseException,
    context: str,
    next_label: str,
    next_help: str,
) -> bool:
    from quill.core.command_failure import failure_details
    from quill.core.lite import APP_NAME
    from quill.ui.next_step_box import show_next_step

    cue = getattr(window, "_cue_error", None)
    if callable(cue):
        cue()
    recorder = getattr(window, "_show_failure_box", None)
    if callable(recorder):  # the test stub's recorder (tests/unit/apps/conftest.py)
        return bool(recorder(message, caption, next_label=next_label, error=exc))
    return show_next_step(
        window,
        message,
        caption,
        next_label=next_label,
        next_help=next_help,
        details=failure_details(exc, app=APP_NAME, context=context),
        announce=getattr(window, "_announce", None),
    )


def report_open_failure(
    window: Any, path: Path, exc: BaseException, *, retry: Callable[[], object] | None = None
) -> bool:
    """Say why *path* did not open; True when the person took the next step.

    Retry is offered when *retry* is given and the file is still there;
    otherwise Choose Another File, which is the Open dialog.
    """
    from quill.core.command_failure import MISSING, plain_failure

    words = plain_failure(exc)
    reason = _authored(exc) or words.reason
    message = f"Could not open {path.name}. {reason} Nothing was opened."
    if retry is not None and words.kind != MISSING:
        label, help_text = "&Retry", f"Tries to open {path.name} again."
    else:
        label, help_text = "Choose Another &File...", "Opens the Open dialog."
    if not _show(window, message, "Open failed", exc, f"Opening {path.name}", label, help_text):
        return False
    if retry is not None and label == "&Retry":
        retry()
    else:
        window.cmd_open()
    return True


def report_save_failure(window: Any, destination: Path, exc: BaseException) -> bool:
    """Say why *destination* was not saved, and offer Save As."""
    from quill.core.command_failure import plain_failure, save_failure_sentence
    from quill.core.lite import APP_NAME

    if isinstance(exc, (OSError, UnicodeEncodeError)):
        message = save_failure_sentence(destination.name, exc, app=APP_NAME)
    else:
        reason = _authored(exc) or plain_failure(exc).reason
        message = (
            f"{APP_NAME} could not save {destination.name}. {reason} "
            "Try Save As -- your text is still open and unsaved."
        )
    if not _show(
        window,
        message,
        "Save failed",
        exc,
        f"Saving {destination.name}",
        "Save &As...",
        "Saves the document somewhere else, under a name you choose.",
    ):
        return False
    window.cmd_save_as()
    return True
