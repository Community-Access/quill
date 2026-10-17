"""The editors' "Add a correction: A becomes B?" window (D-21).

Dictation's controller asks the feedback port's ``confirm_correction`` the
second time the same word is corrected the same way
(:mod:`quill.core.windows_dictation.correction_learning`). In both editors
that is a yes/no window, **No** the default, shown after the phrase has been
handled (a modal window opened inside a recogniser callback would hold it
open). While it is up, the editor's "QUILL is no longer the window in front"
check stands aside (:func:`asking`), so answering does not stop dictation.

Nothing is added unless the answer is Yes.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import wx

from quill.ui.dialog_contract import show_message_box

__all__ = ["TITLE", "asking", "confirm_correction"]

TITLE = "Add a Correction"

_asking = False


def asking() -> bool:
    """Whether the question is on screen now."""
    return _asking


def _ask(parent: Any, question: str, on_yes: Callable[[], None]) -> None:
    global _asking
    _asking = True
    try:
        answer = show_message_box(
            f"{question} It goes into My Words and Phrases, under Corrections.",
            TITLE,
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION,
            parent,
        )
    finally:
        _asking = False
    if answer == wx.YES:
        on_yes()


def confirm_correction(parent: Any, question: str, on_yes: Callable[[], None]) -> None:
    """Ask *question*; run *on_yes* only on Yes. Deferred to after the phrase."""
    try:
        wx.CallAfter(_ask, parent, question, on_yes)
    except Exception:  # noqa: BLE001 - no event loop (tests): ask now
        _ask(parent, question, on_yes)
