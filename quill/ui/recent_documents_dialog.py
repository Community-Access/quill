"""The Recent Documents window, shared by QUILL and QUILL Lite.

Both editors already had **File > Open Recent**, a submenu, and that turned out
to be the problem: a submenu is found only by somebody who walks the File menu
and happens to arrow onto it, and a listener asking for "the ability to open
recent documents" had not. So this is the same list as a window with a chord of
its own (Alt+Shift+0, beside the Alt+Shift+1 to 9 that reopen the first nine)
and every verb the list needs in one place: open, pin, remove a row, show the
file in its folder, clear, and how many to remember.

The rules -- what pinning keeps, what Clear clears, how a row is worded -- are
:mod:`quill.core.recent_documents`, wx-free and shared, so the window cannot
answer one way in QUILL and another in QUILL Lite. The *list itself* is not
shared: each editor hands in its own and saves what comes back.

**Clear asks first, with No as the default.** It is the only verb here that
cannot be put back by doing it again, so Enter on the question keeps the list.

**A missing file is a row, not an omission.** It says "not found", Open says
why it cannot, and Remove from List is the way to tidy it -- the same choice the
session chooser makes, for the same reason: a file that has moved is the one
case where saying nothing is misleading.
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

import wx

from quill.core import recent_documents as rd
from quill.ui.dialog_contract import (
    apply_listbox_activation,
    apply_modal_ids,
    set_accessible_name,
    show_modal_dialog,
)

__all__ = [
    "RecentDocumentsAnswer",
    "RecentDocumentsWindow",
    "confirm_clear_recent",
    "show_recent_documents",
]

TITLE = "Recent Documents"
_PAD = 8
_PIN_LABEL = "&Pin"
_UNPIN_LABEL = "Un&pin"


@dataclass(slots=True)
class RecentDocumentsAnswer:
    """What to open, and the lists and preferences to save back.

    ``changed`` says whether anything other than ``open_path`` moved, so a
    caller saves exactly when there is something to save.
    """

    open_path: str = ""
    recent: tuple[str, ...] = ()
    pinned: tuple[str, ...] = ()
    limit: int = rd.DEFAULT_LIMIT
    auto_clear_missing: bool = False
    changed: bool = False


def confirm_clear_recent(parent: wx.Window, removed: int, kept: int) -> bool:
    """Ask before Clear. No is the default, so Enter keeps the list."""
    noun = "document" if removed == 1 else "documents"
    message = f"Clear {removed} {noun} from the recent list? No file is deleted."
    if kept:
        message += " Pinned documents stay."
    dialog = wx.MessageDialog(
        parent, message, "Clear Recent Documents", wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION
    )
    try:
        return show_modal_dialog(dialog, "Clear Recent Documents") == wx.ID_YES
    finally:
        dialog.Destroy()


def _reveal(path: str) -> None:
    from quill.core.file_manager import reveal_command

    subprocess.Popen(reveal_command(path))  # noqa: S603 - a fixed, tested argv


class RecentDocumentsWindow:
    """The window and its verbs. Built by :func:`show_recent_documents`.

    The verbs are methods so a test can press them on a real window without a
    modal loop, which is the only way a modal's buttons can be tested at all.
    """

    def __init__(
        self,
        parent: wx.Window | None,
        recent: Sequence[str],
        pinned: Sequence[str],
        *,
        limit: int,
        auto_clear_missing: bool,
        announce: Callable[[str], None] | None = None,
        confirm_clear: Callable[[wx.Window, int, int], bool] = confirm_clear_recent,
        reveal: Callable[[str], None] = _reveal,
    ) -> None:
        self.recent = list(recent)
        self.pinned = list(pinned)
        self.open_path = ""
        self.changed = False
        self._announce = announce
        self._confirm_clear = confirm_clear
        self._reveal = reveal
        self._rows: tuple[rd.RecentEntry, ...] = ()

        dialog = wx.Dialog(parent, title=TITLE, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.dialog = dialog
        root = wx.BoxSizer(wx.VERTICAL)

        list_label = wx.StaticText(dialog, label="&Documents, pinned first, then newest:")
        self.listbox = wx.ListBox(dialog, size=(560, 260))
        set_accessible_name(self.listbox, "Documents, pinned first, then newest")
        self.listbox.SetHelpText(
            "Every document you opened recently, pinned ones first. Enter opens the one "
            "you are on. Delete takes it off this list without touching the file. A row "
            "that says not found is a file that has moved or been deleted."
        )
        root.Add(list_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        root.Add(self.listbox, 1, wx.EXPAND | wx.ALL, _PAD)

        verbs = wx.BoxSizer(wx.HORIZONTAL)
        self.open_button = wx.Button(dialog, wx.ID_OK, "&Open")
        self.open_button.SetHelpText("Open the document you are on in the list.")
        self.pin_button = wx.Button(dialog, label=_PIN_LABEL)
        self.pin_button.SetHelpText(
            "Pin the document you are on so it stays at the top of the list however many "
            "others you open. On a pinned document this button unpins it."
        )
        self.remove_button = wx.Button(dialog, label="&Remove from List")
        self.remove_button.SetHelpText(
            "Take the document you are on off the recent list. The file itself is not touched."
        )
        self.folder_button = wx.Button(dialog, label="Open Containing &Folder")
        self.folder_button.SetHelpText(
            "Show the document you are on in File Explorer, in the folder it lives in."
        )
        self.clear_button = wx.Button(dialog, label="C&lear Unpinned...")
        self.clear_button.SetHelpText(
            "Empty the recent list, after asking. Pinned documents stay, and no file is deleted."
        )
        for button in (
            self.open_button,
            self.pin_button,
            self.remove_button,
            self.folder_button,
            self.clear_button,
        ):
            verbs.Add(button, 0, wx.RIGHT, _PAD // 2)
        root.Add(verbs, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, _PAD)

        limit_label = wx.StaticText(dialog, label="Remember &up to this many documents:")
        self.limit_spin = wx.SpinCtrl(
            dialog, min=rd.LIMIT_MIN, max=rd.LIMIT_MAX, initial=rd.clamp_limit(limit)
        )
        set_accessible_name(self.limit_spin, "Remember up to this many documents")
        self.limit_spin.SetHelpText(
            "How many recently opened documents to remember, from 1 to 50. Pinned "
            "documents are kept on top of this number."
        )
        root.Add(limit_label, 0, wx.LEFT | wx.RIGHT, _PAD)
        root.Add(self.limit_spin, 0, wx.ALL, _PAD)

        self.auto_clear = wx.CheckBox(dialog, label="Forget &missing files when the app starts")
        self.auto_clear.SetValue(bool(auto_clear_missing))
        self.auto_clear.SetHelpText(
            "When checked, a document that has been deleted from this computer's own "
            "drives leaves the list at the next start. Files on a USB drive or a "
            "network share are kept, because they are usually just unplugged."
        )
        root.Add(self.auto_clear, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, _PAD)

        self.status = wx.StaticText(dialog, label="")
        self.status.SetHelpText("What the last button you pressed did.")
        root.Add(self.status, 0, wx.LEFT | wx.RIGHT, _PAD)

        # No access key on Close: Escape already answers it (GATE-14).
        close = wx.Button(dialog, wx.ID_CANCEL, "Close")
        close.SetHelpText("Close this window. Changes to the list are kept.")
        root.Add(close, 0, wx.EXPAND | wx.ALL, _PAD)

        dialog.SetSizerAndFit(root)
        apply_modal_ids(dialog, affirmative_id=wx.ID_OK, cancel_id=wx.ID_CANCEL)
        dialog.SetDefaultItem(self.open_button)

        self.open_button.Bind(wx.EVT_BUTTON, lambda _e: self.open_selected())
        self.pin_button.Bind(wx.EVT_BUTTON, lambda _e: self.toggle_pin_selected())
        self.remove_button.Bind(wx.EVT_BUTTON, lambda _e: self.remove_selected())
        self.folder_button.Bind(wx.EVT_BUTTON, lambda _e: self.open_folder_selected())
        self.clear_button.Bind(wx.EVT_BUTTON, lambda _e: self.clear())
        self.listbox.Bind(wx.EVT_LISTBOX, lambda _e: self._sync_buttons())
        apply_listbox_activation(self.listbox, lambda _e: self.open_selected())
        self.listbox.Bind(wx.EVT_KEY_DOWN, self._on_list_key)
        self._refill()

    # -- the list ---------------------------------------------------------

    def _refill(self, keep: str = "", index: int = 0) -> None:
        """Rebuild the rows, keeping the selection on *keep* or near *index*."""
        self._rows = rd.entries(self.recent, self.pinned)
        self.listbox.Set([row.label for row in self._rows] or ["No recent documents"])
        has_rows = bool(self._rows)
        self.listbox.Enable(True)
        for button in (self.open_button, self.pin_button, self.remove_button, self.folder_button):
            button.Enable(has_rows)
        self.clear_button.Enable(any(not row.pinned for row in self._rows))
        if not has_rows:
            self.listbox.SetSelection(0)
            return
        target = next(
            (i for i, row in enumerate(self._rows) if keep and rd.same_file(row.path, keep)),
            min(index, len(self._rows) - 1),
        )
        self.listbox.SetSelection(target)
        self._sync_buttons()

    def _sync_buttons(self) -> None:
        row = self.selected()
        pinned = row is not None and row.pinned
        self.pin_button.SetLabel(_UNPIN_LABEL if pinned else _PIN_LABEL)

    def selected(self) -> rd.RecentEntry | None:
        index = self.listbox.GetSelection()
        if index == wx.NOT_FOUND or index >= len(self._rows):
            return None
        return self._rows[index]

    def _say(self, text: str) -> None:
        """Put *text* in the status line and say it: an unfocused label is silent."""
        self.status.SetLabel(text)
        if self._announce is not None:
            self._announce(text)

    def _on_list_key(self, event: wx.KeyEvent) -> None:
        if event.GetKeyCode() in (wx.WXK_DELETE, wx.WXK_NUMPAD_DELETE):
            self.remove_selected()
            return
        event.Skip()

    # -- the verbs --------------------------------------------------------

    def open_selected(self) -> bool:
        """End the window on the row you are on, unless its file has gone."""
        row = self.selected()
        if row is None:
            return False
        if not row.exists:
            self._say(f"{row.name} is no longer in {row.folder}. Remove from List takes it off.")
            self.listbox.SetFocus()
            return False
        self.open_path = row.path
        if self.dialog.IsModal():
            self.dialog.EndModal(wx.ID_OK)
        return True

    def toggle_pin_selected(self) -> None:
        row = self.selected()
        if row is None:
            return
        self.pinned, now = rd.toggle_pin(self.pinned, row.path)
        self.changed = True
        self._refill(keep=row.path)
        self._say(f"Pinned {row.name}." if now else f"Unpinned {row.name}.")
        self.listbox.SetFocus()

    def remove_selected(self) -> None:
        row = self.selected()
        if row is None:
            return
        index = self.listbox.GetSelection()
        self.recent = rd.forget(self.recent, row.path)
        self.pinned = rd.forget(self.pinned, row.path)
        self.changed = True
        self._refill(index=index)
        self._say(f"Removed {row.name} from the list. The file is not touched.")
        self.listbox.SetFocus()

    def clear(self) -> None:
        kept = rd.clear_unpinned(self.recent, self.pinned)
        removed = sum(1 for row in self._rows if not row.pinned)
        if not removed:
            self._say("There is nothing to clear: every document here is pinned.")
            return
        if not self._confirm_clear(self.dialog, removed, len(self.pinned)):
            self.listbox.SetFocus()
            return
        self.recent = kept
        self.changed = True
        self._refill()
        self._say(rd.describe_cleared(removed, len(self.pinned)))
        self.listbox.SetFocus()

    def open_folder_selected(self) -> None:
        row = self.selected()
        if row is None:
            return
        if row.exists:
            self._reveal(row.path)
            self._say(f"Showing {row.name} in its folder.")
        elif Path(row.folder).is_dir():
            self._reveal(row.folder)
            self._say(f"{row.name} is not there any more. Showing the folder it was in.")
        else:
            self._say(f"{row.name} and its folder are both gone.")

    def show(self) -> None:
        """Show the window modally, through the announcing shared helper."""
        self.listbox.SetFocus()
        show_modal_dialog(self.dialog, TITLE)

    def answer(self) -> RecentDocumentsAnswer:
        limit = rd.clamp_limit(self.limit_spin.GetValue())
        recent = self.recent[:limit]
        return RecentDocumentsAnswer(
            open_path=self.open_path,
            recent=tuple(recent),
            pinned=tuple(self.pinned),
            limit=limit,
            auto_clear_missing=self.auto_clear.GetValue(),
            changed=self.changed or len(recent) != len(self.recent),
        )


def show_recent_documents(
    parent: wx.Window | None,
    recent: Sequence[str],
    pinned: Sequence[str],
    *,
    limit: int,
    auto_clear_missing: bool,
    announce: Callable[[str], None] | None = None,
) -> RecentDocumentsAnswer:
    """Show the window and return what to open and what to save.

    The caller saves ``recent``, ``pinned``, ``limit`` and ``auto_clear_missing``
    into its own store -- every one of them, whatever was pressed, since a pin
    or a removal is kept even when the window is closed without opening.
    """
    window = RecentDocumentsWindow(
        parent,
        recent,
        pinned,
        limit=limit,
        auto_clear_missing=auto_clear_missing,
        announce=announce,
    )
    try:
        window.show()
        return window.answer()
    finally:
        window.dialog.Destroy()
