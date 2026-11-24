"""Take some of another text's differences into the document (FUX-12).

Compare with File and Restore Previous Version's Compare end here when the
person chooses Take Changes. There is no new window: the review is the one
the family already has for a proposed text (``DiffReviewDialog``), so each
difference is a check box, its details say the old and the new lines, and
only the checked ones are applied, as one undo step.

The review is of the exact two texts that were compared. If the document
changed in between, the review does not open and that is said, so what goes
in is always what was read; the review itself is modal, so nothing can
change under it. When the person chose to ignore trailing whitespace, a line
that differs only there keeps the document's version and is not offered.
"""

from __future__ import annotations

from typing import Any

__all__ = ["can_take", "take_changes", "take_intro"]


def take_intro(source: str, *, single: bool = False) -> str:
    """The review's opening sentence when the changes come from *source*.

    A review of one change has Accept and Reject rather than check boxes,
    so it is told those two buttons.
    """
    if single:
        return (
            f"The one way {source} differs from your document. Accept takes it into "
            "your document as one undo step; Reject takes nothing."
        )
    return (
        f"Each way {source} differs from your document, one per line. A checked "
        "difference is taken into your document; uncheck any you want to keep as it "
        "is. Apply Checked takes only the checked ones, as one undo step; Reject All "
        "takes nothing."
    )


def can_take(frame: Any) -> bool:
    """Whether the document in front can take changes (not read-only)."""
    try:
        return not frame._document_is_read_only()
    except AttributeError:
        return True


def take_changes(
    frame: Any,
    left_text: str,
    right_text: str,
    source: str,
    *,
    ignore_trailing_whitespace: bool = False,
) -> None:
    """Review *right_text* against the document's *left_text* and apply the checked part.

    *frame* is QUILL's main frame (``editor``, ``_replace_document_text``,
    ``_announce``); *source* names where the other text came from.
    """
    from quill.core.ai.diff_review import build_diff_review
    from quill.core.compare_service import keep_trailing_whitespace
    from quill.ui.ai_diff_review_dialog import DiffReviewDialog

    frame._refuse_edit_if_read_only()
    if frame.editor.GetValue() != left_text:
        frame._announce("The document changed since the compare, so nothing was taken.")
        return
    if ignore_trailing_whitespace:
        right_text = keep_trailing_whitespace(left_text, right_text)
    hunks = build_diff_review(left_text, right_text).hunks
    if not hunks:
        frame._announce("No differences to take.")
        return
    single = len(hunks) == 1 and len(hunks[0].word_changes) < 2
    parent = frame._dialog_parent() if hasattr(frame, "_dialog_parent") else frame.frame
    DiffReviewDialog(
        parent,
        title=f"Take Changes from {source}",
        original_text=left_text,
        revised_text=right_text,
        on_apply=frame._replace_document_text,
        announce=frame._announce,
        intro=take_intro(source, single=single),
    ).show_modal()
    editor = frame.editor
    if hasattr(editor, "SetFocus"):
        import wx

        wx.CallAfter(editor.SetFocus)
