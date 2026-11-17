"""QUILL's own tutorials: the descriptor, and the checks only QUILL can answer.

The shared window is :mod:`quill.ui.tutorials_window`; the lessons are
:mod:`quill.core.quill_tutorials`. This is the seam between them, plus the
probe that answers "did you do the step?" for an editor rather than a player.

QUILL's questions are about documents: is one open, did the text change, did
you save, is a selection live. Two more are about the WordPress Workbench, for
the Practice Site lessons (WP-R-049): did a change reach the Practice Site
through the Workbench since the step was shown, and is the lesson material
there. Both read the open Workbench's own state -- its Change History and the
Practice Site's folder -- and never ask a site anything. Every probe reads a
named attribute defensively and answers ``None`` when it cannot, so a lesson is
quiet rather than stuck if a later refactor moves something.
"""

from __future__ import annotations

import sys
from typing import Any

TITLE = "QUILL Tutorials"

_CHECKS: dict[str, str] = {
    "document-open": "a document is open",
    "text-changed": "the document changed",
    "text-selected": "you have a selection",
    "document-saved": "the document is saved",
    "practice-site-changed": "the Workbench changed the Practice Site",
    "lesson-material-ready": "the lesson material is on the Practice Site",
}


def _workbench() -> Any:
    """The open WordPress Workbench's provider, or None.

    Read from the module only if something has already imported it: a
    Workbench nobody opened is not open, and a lesson poll should never be
    the thing that loads it.
    """
    module = sys.modules.get("quill.ui.wordpress_workbench_window")
    frame = getattr(module, "_OPEN", {}).get("wordpress") if module is not None else None
    return getattr(frame, "provider", None)


def _recorded() -> int | None:
    provider = _workbench()
    history = getattr(provider, "history", None)
    count = getattr(history, "recorded", None)
    return count if isinstance(count, int) else None


def _on_practice() -> bool | None:
    provider = _workbench()
    if provider is None:
        return None
    try:
        return bool(provider.is_practice(provider.current_site()))
    except Exception:  # noqa: BLE001 - a lesson poll never raises
        return None


def _material_ready() -> bool | None:
    provider = _workbench()
    if provider is None:
        return None
    try:
        from quill.core.wordpress.workbench_practice import practice_dir
        from quill.core.wordpress.workbench_practice_material import is_set_up

        return is_set_up(practice_dir(provider._base()))
    except Exception:  # noqa: BLE001 - see above
        return None


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
            "workbench_changes": _recorded(),
        }

    def answer(self, check: str, host: Any, baseline: dict[str, Any]) -> tuple[bool, str] | None:
        if check not in _CHECKS:
            return None
        said = _CHECKS[check]
        if check == "document-open":
            return (_length(host) is not None, said)
        if check == "text-selected":
            return (_has_selection(host) is True, said)
        if check == "practice-site-changed":
            # A new Workbench change while the Practice Site is the current site.
            before, now = baseline.get("workbench_changes"), _recorded()
            grew = now is not None and now > (before or 0)
            return (grew and _on_practice() is True, said)
        if check == "lesson-material-ready":
            return (_material_ready() is True, said)
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
    """Help > Tutorials...: open (or raise) QUILL's lessons.

    The Coding lesson is the Developer profile's (code.md 6.4): left out unless
    ``core.developer`` is on.
    """
    from dataclasses import replace

    from quill.core.tutorials.coding_lessons import CODING_TRACK_ID
    from quill.core.tutorials.model import without_track
    from quill.ui.tutorials_window import open_tutorials as _open

    chosen = app()
    features = getattr(host, "features", None)
    if not bool(getattr(features, "is_enabled", lambda _f: False)("core.developer")):
        chosen = replace(chosen, catalogue=without_track(chosen.catalogue, CODING_TRACK_ID))
    _open(host, chosen, slug=slug)
