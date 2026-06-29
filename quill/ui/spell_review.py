"""Run the F7 spelling review over an arbitrary wx text control.

``MainFrame.open_spell_check_dialog`` runs the guided spelling review against the
main editor. This helper runs the same review (``ReviewSession`` +
``SpellingReviewDialog``) against any ``wx.TextCtrl`` — e.g. the Mastodon compose
box — so corrections are applied back into that control before its text is used.
Kept out of ``main_frame`` so the compose dialog need not import the frame.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def review_textctrl(
    wx: Any,
    parent: Any,
    text_ctrl: Any,
    *,
    dictionary: Any,
    announce_fn: Any,
    settings: Any,
    show_modal: Any,
    scope_label: str = "post",
    document_path: Path | None = None,
) -> None:
    """Spell-check ``text_ctrl`` in place via the guided review dialog.

    No-op when the control is empty or already clean. Corrections are written
    back into the control with ``Replace`` (the same call the editor path uses),
    so the caller reads the corrected value afterwards.
    """
    from quill.core.spelling.session import ReviewSession
    from quill.ui.spelling_review_dialog import SpellingReviewDialog

    text = text_ctrl.GetValue()
    if not text.strip():
        return
    session = ReviewSession(
        text=text,
        dictionary=set(dictionary),
        scope_start=0,
        scope_end=len(text),
    )
    if session.is_complete():
        announce_fn("No misspellings found.")
        return

    def _apply(start: int, old_end: int, replacement: str) -> None:
        text_ctrl.Replace(start, old_end, replacement)

    dlg = SpellingReviewDialog(
        parent=parent,
        session=session,
        apply_fn=_apply,
        announce_fn=announce_fn,
        document_path=document_path,
        project_root=Path.cwd(),
        settings=settings,
        scope_label=scope_label,
    )
    dlg.show(show_modal)
