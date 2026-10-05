"""The File Changed on Disk question, with an answer you can keep (bad.md F5).

QUILL used to reload a clean tab in place, silently, whatever the format. For
a text file a build regenerates that is convenient; for a ``.docx`` rewritten
by Word it replaced the document with its own bytes decoded into replacement
characters and marked the result clean -- and said nothing, so the first sign
was a document that no longer read as words.

Every external change asks now. That is the right default and the wrong only
option: somebody whose build rewrites the file they are reading every few
seconds should be able to answer once, so the question carries a **"do not ask
me again for this format"** checkbox. The answer is remembered by file suffix,
because "stop asking me about .docx" is a statement about how Word behaves
rather than about one document.

Three things this dialog is careful about.

**The checkbox belongs to the two answers that are policies.** Reload and Keep
Mine describe what should happen to this tab whenever this format changes;
"Open the disk version in a new tab" is a one-off comparison, and remembering
it would mean tabs appearing on their own, so that answer never records
anything however the box is left.

**Escape is Keep Mine, not Cancel.** There is no neutral answer to "the file
changed": something has to happen to the buffer, and the safe something is to
leave what is open alone. A dialog whose Escape does nothing at all would
leave the watcher asking again on the next poll.

**The buttons say what they do**, not Yes and No, because a listener hearing
"Yes" has to reconstruct the question to know which of two irreversible things
it means.
"""

from __future__ import annotations

from dataclasses import dataclass

import wx

from quill.core.external_change import REMEMBER_KEEP, REMEMBER_RELOAD, format_key
from quill.ui.dialog_contract import apply_modal_ids, set_accessible_name, show_modal_dialog

__all__ = [
    "KEEP",
    "NEW_TAB",
    "RELOAD",
    "SAVE_AS",
    "ExternalChangeAnswer",
    "ask_external_change",
]

_PAD = 8

RELOAD = "reload"
KEEP = "keep"
NEW_TAB = "new_tab"
#: QUILL Lite's third answer (2026-10-04): one document per window and no
#: read-only second copy to compare in, so it offers Save As instead -- yours
#: under a new name, theirs untouched. Never remembered, like NEW_TAB.
SAVE_AS = "save_as"


@dataclass(frozen=True, slots=True)
class ExternalChangeAnswer:
    """What the person chose, and whether to stop asking for this format."""

    action: str
    remember: bool = False

    @property
    def remembered_value(self) -> str:
        """The value to store for this format, or ``""`` to store nothing."""
        if not self.remember:
            return ""
        if self.action == RELOAD:
            return REMEMBER_RELOAD
        if self.action == KEEP:
            return REMEMBER_KEEP
        return ""


def _describe_format(file_name: str) -> str:
    suffix = format_key(file_name)
    return f"{suffix} files" if suffix else "files without an extension"


def ask_external_change(
    parent: object,
    file_name: str,
    *,
    buffer_dirty: bool,
    alternative: str = NEW_TAB,
    default_keep: bool = False,
    forget_hint: str = "File > Forget Remembered File-Change Answers undoes this.",
) -> ExternalChangeAnswer:
    """Ask what to do about *file_name* having changed on disk.

    ``buffer_dirty`` only changes the wording: the three answers are the same
    either way, but what Reload costs is not -- with unsaved edits it discards
    them, and with none it simply shows the newer text.

    *alternative* is the third answer: :data:`NEW_TAB` (QUILL) or
    :data:`SAVE_AS` (QUILL Lite). *default_keep* puts the focus, and so Enter,
    on Keep Mine rather than Reload. *forget_hint* says where the app asking
    takes a "do not ask me again" answer back.
    """
    saving = alternative == SAVE_AS
    third = (
        "Save As keeps your version under a new name and leaves the disk version alone."
        if saving
        else "Opening the disk version in a new tab lets you compare the two."
    )
    dialog = wx.Dialog(parent, title="File Changed on Disk")
    root = wx.BoxSizer(wx.VERTICAL)

    if buffer_dirty:
        story = (
            f"'{file_name}' was changed on disk while you have unsaved edits.\n\n"
            "Reloading replaces your edits with the version on disk.\n"
            "Keeping yours means the disk version is overwritten when you save.\n" + third
        )
    else:
        story = (
            f"'{file_name}' was changed on disk by another program.\n\n"
            "Reloading shows the new version, keeping the cursor where it is.\n"
            "Keeping yours leaves this tab exactly as it is.\n" + third
        )
    message = wx.StaticText(dialog, label=story)
    message.SetHelpText(
        "What happened to the file you are editing, and what each answer below would do about it."
    )
    root.Add(message, 0, wx.ALL, _PAD)

    remember = wx.CheckBox(dialog, label=f"&Do not ask me again for {_describe_format(file_name)}")
    remember.SetHelpText(
        "Answer this once for every file of this format. Reload and Keep Mine can "
        "be remembered; the third answer is a one-off and is never remembered. " + forget_hint
    )
    set_accessible_name(remember, f"Do not ask me again for {_describe_format(file_name)}")
    root.Add(remember, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, _PAD)

    buttons = wx.BoxSizer(wx.HORIZONTAL)
    reload_button = wx.Button(dialog, wx.ID_OK, "&Reload from Disk")
    reload_button.SetHelpText(
        "Read the file again, through the reader for its format, and show what is on disk now."
    )
    keep_button = wx.Button(dialog, wx.ID_CANCEL, "&Keep Mine")
    keep_button.SetHelpText(
        "Leave this tab as it is. The version on disk is ignored until you save over it or reload."
    )
    if saving:
        new_tab_button = wx.Button(dialog, wx.ID_APPLY, "Save &As...")
        new_tab_button.SetHelpText(
            "Save what is open under a new name. The file on disk is left as the "
            "other program wrote it."
        )
    else:
        new_tab_button = wx.Button(dialog, wx.ID_APPLY, "Open Disk Version in a &New Tab")
        new_tab_button.SetHelpText(
            "Open what is on disk as a second, separate tab so both versions are open "
            "at once. This tab is left alone."
        )
    for button in (reload_button, keep_button, new_tab_button):
        buttons.Add(button, 0, wx.RIGHT, _PAD)
    root.Add(buttons, 0, wx.EXPAND | wx.ALL, _PAD)

    def _on_new_tab(_event: object) -> None:
        dialog.EndModal(wx.ID_APPLY)

    new_tab_button.Bind(wx.EVT_BUTTON, _on_new_tab)

    dialog.SetSizerAndFit(root)
    apply_modal_ids(dialog, affirmative_id=wx.ID_OK, cancel_id=wx.ID_CANCEL)
    if default_keep:
        # Enter answers the focused button: here, the answer that changes nothing.
        keep_button.SetDefault()
        keep_button.SetFocus()
    else:
        reload_button.SetFocus()
    try:
        result = show_modal_dialog(dialog, "File Changed on Disk")
        wants_remember = bool(remember.GetValue())
        if result == wx.ID_OK:
            return ExternalChangeAnswer(RELOAD, wants_remember)
        if result == wx.ID_APPLY:
            return ExternalChangeAnswer(SAVE_AS if saving else NEW_TAB, False)
        return ExternalChangeAnswer(KEEP, wants_remember)
    finally:
        dialog.Destroy()
