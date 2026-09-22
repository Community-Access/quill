"""Save changes to this one -- and an answer for all the rest.

Shared by QUILL and QuillLite, because Close Other Documents is the same
command in both and a person who learns the window in one presses the same keys
in the other.

**Why five buttons and not three.** Close Other Documents with sixty-eight
windows open asked sixty-eight separate questions, and there was no way to
answer them together: the command that exists to save a person sixty-eight
keystrokes charged them sixty-eight prompts instead. Word, Explorer and every
other bulk operation solve this the same way -- the prompt that can repeat
carries an answer that ends the repetition.

**The words are Word's, not "Yes to All".** For the reason the single prompt
already says Save and Don't Save (``quill/core/close_prompt.py``): "Yes to All"
makes somebody work out which of two irreversible answers "yes" was, and the
moment they are about to discard sixty-seven documents is the wrong one for
that arithmetic.

**The count is in the question.** "67 other documents also have unsaved
changes" is what makes Don't Save Any the obvious answer rather than a button
discovered on the fortieth press -- and a listener cannot see a stack of
windows to work it out from.

Cancel is Escape and carries no access key, per GATE-14: Escape already serves
it, and the letter it gives up resolves a collision elsewhere.
"""

from __future__ import annotations

import wx

from quill.core.close_prompt import (
    CANCEL,
    DISCARD,
    DISCARD_ALL,
    DISCARD_ALL_LABEL,
    DISCARD_LABEL,
    SAVE,
    SAVE_ALL,
    SAVE_ALL_LABEL,
    SAVE_LABEL,
    unsaved_changes_title,
)
from quill.ui.dialog_contract import apply_modal_ids, set_accessible_name, show_modal_dialog

__all__ = ["ask_bulk_unsaved"]

_PAD = 8


def _with_key(label: str, letter: str) -> str:
    """*label* with an ``&`` before *letter*, so the words stay shared.

    The five button words live in ``quill/core/close_prompt.py`` -- one table,
    so the two editors cannot word the same answer two ways. Which letter each
    one claims is local to this window, because that is a collision question
    and collisions are per-window (GATE-14).
    """
    index = label.find(letter)
    if index < 0:
        return label
    return f"{label[:index]}&{label[index:]}"


#: One wx id per answer. ``ID_OK`` and ``ID_CANCEL`` end the modal by
#: themselves; the other three are bound to ``EndModal`` below, or the button
#: looks dead.
_IDS = {
    wx.ID_OK: SAVE,
    wx.ID_YESTOALL: SAVE_ALL,
    wx.ID_NO: DISCARD,
    wx.ID_NOTOALL: DISCARD_ALL,
    wx.ID_CANCEL: CANCEL,
}


def ask_bulk_unsaved(parent: object, question: str) -> str:
    """Ask about one document, offering an answer for the rest.

    Returns one of the five answers in :mod:`quill.core.close_prompt`. The
    caller feeds it to a ``BulkSavePolicy``, which is what turns "to all" into
    a latched decision -- that rule is written once, there, rather than twice
    here and in each editor.
    """
    dialog = wx.Dialog(parent, title=unsaved_changes_title())  # type: ignore[arg-type]
    root = wx.BoxSizer(wx.VERTICAL)

    text = wx.StaticText(dialog, label=question)
    text.SetHelpText(
        "Which document has unsaved changes, what is about to happen to it, and "
        "how many more documents are waiting behind this question."
    )
    set_accessible_name(text, question)
    root.Add(text, 0, wx.ALL, _PAD * 2)

    buttons = wx.BoxSizer(wx.HORIZONTAL)
    save = wx.Button(dialog, wx.ID_OK, _with_key(SAVE_LABEL, "S"))
    save.SetHelpText("Save this document, then ask about the next one.")
    save_all = wx.Button(dialog, wx.ID_YESTOALL, _with_key(SAVE_ALL_LABEL, "A"))
    save_all.SetHelpText(
        "Save this document and every other one with unsaved changes, without "
        "asking again. A document that has never been saved still asks where to "
        "put it."
    )
    # &n rather than &D: Don't Save Any needs a letter too and the two must not
    # collide, because Windows cycles focus between duplicates instead of
    # pressing either (GATE-14).
    discard = wx.Button(dialog, wx.ID_NO, _with_key(DISCARD_LABEL, "n"))
    discard.SetHelpText("Close this document and lose its changes. Then ask about the next one.")
    discard_all = wx.Button(dialog, wx.ID_NOTOALL, _with_key(DISCARD_ALL_LABEL, "y"))
    discard_all.SetHelpText(
        "Close every remaining document and lose all their unsaved changes, "
        "without asking again. This cannot be undone."
    )
    # No access key: Escape serves Cancel already (GATE-14).
    cancel = wx.Button(dialog, wx.ID_CANCEL, "Cancel")
    cancel.SetHelpText("Stop here. Nothing else is closed and nothing more is lost.")

    for button in (save, save_all, discard, discard_all, cancel):
        buttons.Add(button, 0, wx.RIGHT, _PAD // 2)
    root.Add(buttons, 0, wx.ALL, _PAD)

    # The ids are read before the loop: a GetId() call in a default argument
    # is evaluated once per iteration but ruff (B008) is right that it reads as
    # if it were not, and this loop is where a lambda-capture bug would be
    # invisible -- every button would answer with the last one's id.
    for button, answer_id in (
        (save_all, wx.ID_YESTOALL),
        (discard, wx.ID_NO),
        (discard_all, wx.ID_NOTOALL),
    ):
        button.Bind(
            wx.EVT_BUTTON,
            lambda _event, _id=answer_id: dialog.EndModal(_id),
        )

    dialog.SetSizerAndFit(root)
    apply_modal_ids(
        dialog,
        affirmative_id=wx.ID_OK,
        affirmative_label=_with_key(SAVE_LABEL, "S"),
        cancel_id=wx.ID_CANCEL,
        cancel_label="Cancel",
    )
    # Save holds the default, so Enter is the answer that keeps the work. The
    # two destructive buttons are reachable and neither is one keystroke away
    # from somebody who pressed Enter without hearing the question -- the same
    # rule the recovery chooser's Discard Everything follows.
    dialog.SetDefaultItem(save)
    save.SetFocus()

    try:
        return _IDS.get(show_modal_dialog(dialog, unsaved_changes_title()), CANCEL)
    finally:
        dialog.Destroy()


#: Re-exported so a caller needs one import to handle every answer.
BULK_ANSWERS = (SAVE, SAVE_ALL, DISCARD, DISCARD_ALL, CANCEL)
