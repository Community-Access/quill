"""QUILL's own tutorials: the descriptor, and the checks only QUILL can answer.

The shared window is :mod:`quill.ui.tutorials_window`; the lessons are
:mod:`quill.core.quill_tutorials`. This is the seam between them, plus the
probe that answers "did you do the step?" for an editor rather than a player.

QUILL's questions are about documents: is one open, did the text change, did
you save, is a selection live. Every probe reads a named attribute defensively
and answers ``None`` when it cannot, so a lesson is quiet rather than stuck if
a later refactor moves something.
"""

from __future__ import annotations

from typing import Any

TITLE = "QUILL Tutorials"

_CHECKS: dict[str, str] = {
    "document-open": "a document is open",
    "text-changed": "the document changed",
    "text-selected": "you have a selection",
    "document-saved": "the document is saved",
}


def _editor(host: Any) -> Any:
    """The active editor control, whatever the shell calls it today."""
    for name in ("editor", "_editor", "text_ctrl"):
        control = getattr(host, name, None)
        if control is not None:
            return control
    getter = getattr(host, "current_editor", None)
    if callable(getter):
        try:
            return getter()
        except Exception:  # noqa: BLE001 - no editor is "cannot tell", not a failure
            return None
    return None


def _length(host: Any) -> int | None:
    editor = _editor(host)
    getter = getattr(editor, "GetValue", None) or getattr(editor, "GetText", None)
    if not callable(getter):
        return None
    try:
        return len(str(getter()))
    except Exception:  # noqa: BLE001 - see above
        return None


def _has_selection(host: Any) -> bool | None:
    editor = _editor(host)
    getter = getattr(editor, "GetStringSelection", None)
    if not callable(getter):
        return None
    try:
        return bool(str(getter()))
    except Exception:  # noqa: BLE001 - see above
        return None


def _modified(host: Any) -> bool | None:
    editor = _editor(host)
    getter = getattr(editor, "IsModified", None) or getattr(editor, "GetModify", None)
    if not callable(getter):
        return None
    try:
        return bool(getter())
    except Exception:  # noqa: BLE001 - see above
        return None


class QuillProbe:
    """QUILL's :class:`~quill.ui.tutorial_checks.CheckProbe`."""

    def known(self) -> frozenset[str]:
        return frozenset(_CHECKS)

    def snapshot(self, host: Any) -> dict[str, Any]:
        return {
            "length": _length(host),
            "selection": _has_selection(host),
            "modified": _modified(host),
        }

    def answer(self, check: str, host: Any, baseline: dict[str, Any]) -> tuple[bool, str] | None:
        if check not in _CHECKS:
            return None
        said = _CHECKS[check]
        if check == "document-open":
            return (_length(host) is not None, said)
        if check == "text-selected":
            return (_has_selection(host) is True, said)
        if check == "document-saved":
            # Saved means it *was* modified when the step began and is not now.
            return (baseline.get("modified") is True and _modified(host) is False, said)
        # text-changed
        before, now = baseline.get("length"), _length(host)
        return (before is not None and now is not None and now != before, said)


#: The one instance; it holds no state of its own.
PROBE = QuillProbe()


def _open_book(host: Any) -> None:
    """Open the rendered tutorial book, however this shell opens documents."""
    from pathlib import Path

    book = Path(__file__).resolve().parents[2] / "docs" / "user guide" / "tutorials.md"
    opener = getattr(host, "open_document_path", None) or getattr(host, "open_path", None)
    if callable(opener):
        opener(str(book))
        return
    import webbrowser

    webbrowser.open(book.as_uri())


def app() -> Any:
    """QUILL's :class:`~quill.ui.tutorials_window.TutorialsApp`.

    Built on demand rather than at import: the lessons are a few hundred
    objects, and an editor that never opens Help should not pay for them.
    """
    from quill.core.quill_tutorials import CATALOGUE
    from quill.ui.tutorials_window import TutorialsApp

    return TutorialsApp(
        app_id="quill",
        title=TITLE,
        catalogue=CATALOGUE,
        progress_file="quill_tutorials.json",
        open_book=_open_book,
        probe=PROBE,
    )


def open_tutorials(host: Any, *, slug: str = "") -> None:
    """Help > Tutorials...: open (or raise) QUILL's lessons."""
    from quill.ui.tutorials_window import open_tutorials as _open

    _open(host, app(), slug=slug)
