"""AutoCorrect Entries: see, add, change, turn off and remove misspelling corrections.

One window, shared by QUILL (Insert > AutoCorrect Entries...) and QUILL Lite
(Tools > AutoCorrect Entries...), on the same key in both,
Ctrl+Alt+Shift+F12. It edits the abbreviation library it is handed -- the
corrections that are yours are entries in that library under the AutoCorrect
category (:mod:`quill.core.autocorrect`) -- and the caller saves the library
through the shared store when the window closes, exactly as Manage
Abbreviations does. There is no second file.

The list holds every correction, built-in and yours, one row each, read in a
sentence: "teh becomes the, built in". A filter box above it narrows the list
as you type, which is how a list of several hundred is usable by ear. Enter or
Space on a row edits it. Four buttons act on the row you are on:

* **Add...** a correction of your own, or change a built-in one by adding the
  same word with a different correction.
* **Edit...** the row you are on. Editing a built-in row saves your version
  beside it; Remove later brings the built-in one back.
* **Turn Off** / **Turn On** stops one correction without deleting it, which
  is the answer to "it keeps changing a word I meant": a built-in correction
  cannot be deleted, only turned off.
* **Remove** deletes a correction of yours, or puts a built-in one back the
  way it shipped after you changed or turned it off.

Every outcome is spoken (the reader would otherwise say only the button's own
name again), and the list row you were on is reselected after each change so
arrowing on carries on from the same place.

Hardened dialog: :meth:`show` and :meth:`close`, so callers never call
``ShowModal`` or ``Destroy`` themselves, and :func:`apply_modal_ids` with Close
on Escape.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import wx

from quill.core.abbreviations import AbbreviationLibrary
from quill.core.autocorrect import (
    ORIGIN_BUILT_IN,
    CorrectionRow,
    correction_rows,
    delete_correction,
    lookup,
    resume_correction,
    set_correction,
    stop_correction,
    validate_entry,
)
from quill.ui.dialog_contract import (
    apply_listbox_activation,
    apply_modal_ids,
    bind_close_button,
    show_message_box,
)

__all__ = ["TITLE", "AutocorrectEntriesDialog", "CorrectionEditDialog", "EditAnswer"]

TITLE = "AutoCorrect Entries"
EDIT_TITLE = "AutoCorrect Entry"

#: What the edit window hands back: (word, correction, match case).
EditAnswer = tuple[str, str, bool]
#: Opens the edit window: (parent, word, correction, match case) -> answer or None.
EditPrompt = Callable[[Any, str, str, bool], "EditAnswer | None"]


class CorrectionEditDialog:
    """The small window behind Add and Edit: the word, its correction, match case."""

    def __init__(self, parent: Any, word: str = "", fixed: str = "", case: bool = False) -> None:
        self.dialog = wx.Dialog(parent, title=EDIT_TITLE)
        root = wx.BoxSizer(wx.VERTICAL)
        word_label = wx.StaticText(self.dialog, label="&Word to correct:")
        self.word = wx.TextCtrl(self.dialog, value=word)
        self.word.SetHelpText(
            "The misspelling, exactly as you type it wrongly. One word of letters "
            "only; an apostrophe inside it is fine. It is matched in any case "
            "unless you check Match case exactly."
        )
        fixed_label = wx.StaticText(self.dialog, label="&Correct it to:")
        self.fixed = wx.TextCtrl(self.dialog, value=fixed)
        self.fixed.SetHelpText(
            "What the word becomes when you type a space or press Enter after it. "
            "It may be more than one word, on one line."
        )
        self.case = wx.CheckBox(self.dialog, label="&Match case exactly")
        self.case.SetValue(bool(case))
        self.case.SetHelpText(
            "Checked: only the word typed in exactly this case is corrected, and "
            "the correction goes in exactly as written. Unchecked, the usual "
            "choice: teh, Teh and the start of a sentence are all corrected, "
            "keeping your capital letter."
        )
        for control in (word_label, self.word, fixed_label, self.fixed, self.case):
            root.Add(control, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)
        buttons = wx.StdDialogButtonSizer()
        ok = wx.Button(self.dialog, wx.ID_OK, label="OK")
        ok.SetHelpText("Save this correction and go back to the list.")
        cancel = wx.Button(self.dialog, wx.ID_CANCEL, label="Cancel")
        cancel.SetHelpText("Go back to the list without saving anything.")
        buttons.AddButton(ok)
        buttons.AddButton(cancel)
        buttons.Realize()
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)
        self.dialog.SetSizerAndFit(root)
        apply_modal_ids(
            self.dialog,
            affirmative_id=wx.ID_OK,
            affirmative_label="OK",
            cancel_id=wx.ID_CANCEL,
            cancel_label="Cancel",
        )
        bind_close_button(self.dialog, cancel, modeless=False)
        ok.Bind(wx.EVT_BUTTON, self._on_ok)
        self.word.SetFocus()

    def show(self) -> int:
        return int(self.dialog.ShowModal())

    def close(self) -> None:
        self.dialog.Destroy()

    def _on_ok(self, _event: object) -> None:
        problem = validate_entry(self.word.GetValue(), self.fixed.GetValue())
        if problem is not None:
            show_message_box(problem, EDIT_TITLE, wx.OK | wx.ICON_INFORMATION, self.dialog)
            self.word.SetFocus()
            return
        self.dialog.EndModal(wx.ID_OK)

    def answer(self) -> EditAnswer:
        return (self.word.GetValue().strip(), self.fixed.GetValue().strip(), self.case.GetValue())


def _prompt_with_wx(parent: Any, word: str, fixed: str, case: bool) -> EditAnswer | None:
    """The real edit prompt: the window above, shown modally through the contract."""
    from quill.ui.dialog_contract import show_modal_dialog

    edit = CorrectionEditDialog(parent, word, fixed, case)
    try:
        if show_modal_dialog(edit.dialog, EDIT_TITLE) != wx.ID_OK:
            return None
        return edit.answer()
    finally:
        edit.dialog.Destroy()


class AutocorrectEntriesDialog:
    """The list of corrections and the four things you can do to one."""

    def __init__(
        self,
        parent: Any,
        library: AbbreviationLibrary,
        *,
        announce: Callable[[str], None] | None = None,
        prompt: EditPrompt | None = None,
    ) -> None:
        self._library = library
        self._announce = announce or (lambda _message: None)
        self._prompt = prompt or _prompt_with_wx
        self._rows: list[CorrectionRow] = []
        #: True once anything was added, changed, turned off or removed; the
        #: caller saves the library only then.
        self.changed = False
        self.dialog = wx.Dialog(
            parent, title=TITLE, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.dialog.SetMinSize(wx.Size(560, 420))
        root = wx.BoxSizer(wx.VERTICAL)

        root.Add(wx.StaticText(self.dialog, label="&Find:"), 0, wx.LEFT | wx.TOP, 8)
        self.filter = wx.TextCtrl(self.dialog)
        self.filter.SetHelpText(
            "Type part of a word to narrow the list to the corrections that "
            "contain it, either the misspelling or what it becomes. Clear it to "
            "see them all again."
        )
        root.Add(self.filter, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        root.Add(wx.StaticText(self.dialog, label="&Corrections:"), 0, wx.LEFT | wx.TOP, 8)
        self.list = wx.ListBox(self.dialog, style=wx.LB_SINGLE)
        self.list.SetHelpText(
            "Every correction, one per row: the misspelling, what it becomes, and "
            "whether it is built in or yours. A row that ends in stopped is turned "
            "off. Corrections happen only while Correct common misspellings as I "
            "type is on, and never in code or settings files."
        )
        root.Add(self.list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        row = wx.BoxSizer(wx.HORIZONTAL)
        self.add_button = wx.Button(self.dialog, label="&Add...")
        self.add_button.SetHelpText(
            "Add a correction of your own. Adding a word that is already built in "
            "changes what it becomes; Remove later puts the built-in one back."
        )
        self.edit_button = wx.Button(self.dialog, label="&Edit...")
        self.edit_button.SetHelpText(
            "Change the correction you are on: the misspelling, what it becomes, "
            "or whether case must match."
        )
        self.toggle_button = wx.Button(self.dialog, label="Turn &Off")
        self.toggle_button.SetHelpText(
            "Stop the correction you are on from happening, without deleting it, "
            "or start a stopped one again. Use this when a correction keeps "
            "changing a word you meant to type."
        )
        self.remove_button = wx.Button(self.dialog, label="&Remove")
        self.remove_button.SetHelpText(
            "Delete a correction of yours, or put a built-in one back the way it "
            "shipped after you changed or stopped it. A built-in correction cannot "
            "be deleted; Remove on one turns it off instead."
        )
        close = wx.Button(self.dialog, wx.ID_CANCEL, label="Close")
        close.SetHelpText("Close this window. Your changes are already kept.")
        for button in (self.add_button, self.edit_button, self.toggle_button, self.remove_button):
            row.Add(button, 0, wx.RIGHT, 4)
        row.AddStretchSpacer(1)
        row.Add(close, 0)
        root.Add(row, 0, wx.EXPAND | wx.ALL, 8)

        self.dialog.SetSizer(root)
        self.dialog.Layout()
        apply_modal_ids(self.dialog, cancel_id=wx.ID_CANCEL, cancel_label="Close")
        bind_close_button(self.dialog, close, modeless=False)

        self.filter.Bind(wx.EVT_TEXT, lambda _e: self.refresh())
        self.list.Bind(wx.EVT_LISTBOX, lambda _e: self._sync_toggle_label())
        # Enter, Space or a double-click on a row edits it.
        apply_listbox_activation(self.list, lambda _e: self.edit_selected())
        self.add_button.Bind(wx.EVT_BUTTON, lambda _e: self.add())
        self.edit_button.Bind(wx.EVT_BUTTON, lambda _e: self.edit_selected())
        self.toggle_button.Bind(wx.EVT_BUTTON, lambda _e: self.toggle_selected())
        self.remove_button.Bind(wx.EVT_BUTTON, lambda _e: self.remove_selected())

        self.refresh()
        self.list.SetFocus()

    # -- the hardened-dialog pair ---------------------------------------- #

    def show(self) -> int:
        return int(self.dialog.ShowModal())

    def close(self) -> None:
        self.dialog.Destroy()

    # -- the list ------------------------------------------------------- #

    def refresh(self, keep: str = "") -> None:
        """Rebuild the rows under the filter, reselecting *keep* when it is there."""
        needle = self.filter.GetValue().strip().lower()
        rows = correction_rows(self._library)
        if needle:
            rows = [
                one
                for one in rows
                if needle in one.typed.lower() or needle in one.replacement.lower()
            ]
        self._rows = rows
        self.list.Set([one.describe() for one in rows])
        index = next((i for i, one in enumerate(rows) if one.typed.lower() == keep.lower()), -1)
        if index < 0 and rows:
            index = 0
        if index >= 0:
            self.list.SetSelection(index)
        self._sync_toggle_label()

    def selected(self) -> CorrectionRow | None:
        index = self.list.GetSelection()
        if index is None or index < 0 or index >= len(self._rows):
            return None
        return self._rows[index]

    def _sync_toggle_label(self) -> None:
        row = self.selected()
        stopped = row is not None and not row.active
        self.toggle_button.SetLabel("Turn O&n" if stopped else "Turn &Off")

    # -- the four actions ------------------------------------------------ #

    def add(self) -> None:
        answer = self._prompt(self.dialog, "", "", False)
        if answer is None:
            return
        self._save(answer, verb="Added")

    def edit_selected(self) -> None:
        row = self.selected()
        if row is None:
            self._announce("There is no correction selected")
            return
        answer = self._prompt(self.dialog, row.typed, row.replacement, row.case_sensitive)
        if answer is None:
            return
        word, _fixed, _case = answer
        if word.lower() != row.typed.lower() and row.origin != ORIGIN_BUILT_IN:
            # Renaming one of yours: the old word goes, the new one is added.
            delete_correction(self._library, row.typed)
        self._save(answer, verb="Saved")

    def _save(self, answer: EditAnswer, *, verb: str) -> None:
        word, fixed, case = answer
        if validate_entry(word, fixed) is not None:
            return  # the edit window refuses these; a test double may not
        entry = set_correction(self._library, word, fixed, case_sensitive=case)
        self.changed = True
        self.refresh(keep=word)
        if entry is None:
            self._announce(f"{word} is back to the built-in correction, {fixed}")
            return
        self._announce(f"{verb}: {word} becomes {fixed}")

    def toggle_selected(self) -> None:
        row = self.selected()
        if row is None:
            self._announce("There is no correction selected")
            return
        if row.active:
            stop_correction(self._library, row.typed)
            message = f"Turned off: {row.typed} will no longer be corrected"
        else:
            resume_correction(self._library, row.typed)
            message = f"Turned on: {row.typed} becomes {row.replacement} again"
        self.changed = True
        self.refresh(keep=row.typed)
        self._announce(message)

    def remove_selected(self) -> None:
        row = self.selected()
        if row is None:
            self._announce("There is no correction selected")
            return
        outcome = delete_correction(self._library, row.typed)
        if outcome == "built-in":
            if row.active:
                stop_correction(self._library, row.typed)
                message = (
                    f"{row.typed} is built in and cannot be removed, so it is turned off "
                    "instead. Turn On starts it again."
                )
            else:
                message = f"{row.typed} is built in and already turned off"
        elif outcome == "restored":
            restored = lookup(self._library, row.typed)
            fixed = restored.replacement if restored is not None else row.replacement
            message = f"Restored the built-in correction: {row.typed} becomes {fixed}"
        else:
            message = f"Removed {row.typed}"
        self.changed = self.changed or outcome != "missing"
        self.refresh(keep=row.typed)
        self._announce(message)
