"""**Downloads...** -- the queue, and everything you can do to it.

The window behind *View > Downloads*. A queue you cannot see is a progress bar
with extra steps: the questions people actually have are *"is it still going?"*,
*"did that one work?"* and *"where did it go?"*, and all three are answered here.

Four decisions:

* **Finished rows stay.** A queue that tidies itself away as it succeeds cannot
  answer "did that actually download?", which is the question asked most. They
  are cleared when *you* say so.
* **Every row is a whole sentence, with its state last.** "Chapter 4,
  Middlemarch, downloading now". State last because when you are arrowing a
  queue you already know what the items are -- what you are looking for is where
  each one has got to.
* **Open Containing Folder is the point of finishing.** A download you cannot
  find is a download that did not really happen, so a saved row keeps its path
  and can hand you to it.
* **Buttons say what they will do to the row you are on**, and are unavailable
  when they would do nothing -- Cancel on something already saved, Open on
  something that never arrived.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from quill.core.radio.download_queue import DONE, RUNNING, WAITING, DownloadQueue, QueueItem
from quill.ui.dialog_contract import apply_listbox_activation, apply_modal_ids

TITLE = "Downloads"

#: Shown when there is nothing queued. A finished queue is a good state, and
#: saying so beats an empty list that reads like a failure.
NOTHING = "Nothing has been queued for download yet."


class DownloadQueueDialog:
    """Watch the queue, and cancel, remove, clear or open anything in it."""

    def __init__(
        self,
        parent: Any,
        *,
        queue: DownloadQueue,
        cancel: Callable[[QueueItem], bool] | None = None,
        clear_all: Callable[[], int] | None = None,
        announce: Callable[[str], None] | None = None,
        show_modal_dialog: Callable[[Any, str], int] | None = None,
        open_folder: Callable[[str], bool] | None = None,
        open_preferences: Callable[[], None] | None = None,
        transport_host: object | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._transport_host = transport_host
        self._queue = queue
        self._cancel = cancel
        self._clear_all = clear_all
        self._announce = announce or (lambda _m: None)
        self._show_modal_dialog = show_modal_dialog
        self._open_folder = open_folder
        self._open_preferences = open_preferences
        self._rows: list[QueueItem] = []

        self._dialog = wx.Dialog(
            parent, title=TITLE, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        root = wx.BoxSizer(wx.VERTICAL)

        self._heading = wx.StaticText(self._dialog, label="")
        root.Add(self._heading, 0, wx.ALL, 10)

        root.Add(wx.StaticText(self._dialog, label="&Downloads:"), 0, wx.LEFT | wx.RIGHT, 10)
        self._list = wx.ListBox(self._dialog, style=wx.LB_SINGLE)
        self._list.SetName("Everything queued for download, and where each one has got to")
        root.Add(self._list, 1, wx.EXPAND | wx.ALL, 10)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        self._open_btn = wx.Button(self._dialog, label="&Open Containing Folder")
        self._cancel_btn = wx.Button(self._dialog, label="&Cancel This One")
        self._remove_btn = wx.Button(self._dialog, label="&Remove From List")
        self._clear_btn = wx.Button(self._dialog, label="Clear &Finished")
        self._clear_all_btn = wx.Button(self._dialog, label="Clear &All")
        for button in (
            self._open_btn,
            self._cancel_btn,
            self._remove_btn,
            self._clear_btn,
            self._clear_all_btn,
        ):
            buttons.Add(button, 0, wx.RIGHT, 6)
        if open_preferences is not None:
            # Where things land and whether closing keeps the queue going are
            # decided in Download Preferences; the queue window is where the
            # question occurs to people, so the door is here too.
            prefs_btn = wx.Button(self._dialog, label="&Preferences...")
            prefs_btn.SetName("Download Preferences: folders, filing, and background downloads")
            prefs_btn.Bind(wx.EVT_BUTTON, lambda _e: open_preferences())
            buttons.Add(prefs_btn, 0, wx.RIGHT, 6)
        buttons.Add(wx.Button(self._dialog, wx.ID_CANCEL, "Cl&ose"), 0)
        root.Add(buttons, 0, wx.ALL, 10)

        self._dialog.SetSizer(root)
        self._dialog.SetMinSize((680, 420))
        self._dialog.Fit()
        apply_modal_ids(self._dialog, cancel_id=wx.ID_CANCEL, cancel_label="Close")

        # The transport keyboard, when the surface that opened this one knows
        # about the player. It was installed in the browse tree and nowhere
        # else, so every other Radio dialog was a window where the keys that
        # work everywhere stopped working.
        if self._transport_host is not None:
            from quill.ui.radio import transport_keys

            transport_keys.install(self._dialog, self._transport_host, wx=wx)

        self._open_btn.Bind(wx.EVT_BUTTON, lambda _e: self.open_selected())
        self._cancel_btn.Bind(wx.EVT_BUTTON, lambda _e: self.cancel_selected())
        self._remove_btn.Bind(wx.EVT_BUTTON, lambda _e: self.remove_selected())
        self._clear_btn.Bind(wx.EVT_BUTTON, lambda _e: self.clear_finished())
        self._clear_all_btn.Bind(wx.EVT_BUTTON, lambda _e: self.clear_everything())
        self._list.Bind(wx.EVT_LISTBOX, lambda _e: self._sync_buttons())
        # Enter on a saved row opens where it went -- the one thing you want
        # from a finished download (GATE-13: a ListBox emits no activate event).
        apply_listbox_activation(self._list, lambda _e: self.open_selected())

        self.refresh()
        self._list.SetFocus()

    @property
    def dialog(self) -> Any:
        return self._dialog

    def refresh(self) -> None:
        """Redraw from the queue, keeping the cursor on the same row.

        By identity rather than index: rows are removed and the list is
        rebuilt while somebody is reading it, and an index would silently move
        them onto a different download.
        """
        selected = self.selected()
        self._rows = list(self._queue.items)
        self._list.Set([item.row_label() for item in self._rows])
        self._heading.SetLabel(self._queue.summary() if self._rows else NOTHING)
        if self._rows:
            index = next(
                (i for i, item in enumerate(self._rows) if selected and item.id == selected.id),
                0,
            )
            self._list.SetSelection(min(index, len(self._rows) - 1))
        self._sync_buttons()
        self._dialog.Layout()

    def selected(self) -> QueueItem | None:
        index = self._list.GetSelection()
        if index < 0 or index >= len(self._rows):
            return None
        return self._rows[index]

    def _sync_buttons(self) -> None:
        """Enable only what would actually do something to this row."""
        item = self.selected()
        self._open_btn.Enable(bool(item and item.state == DONE and item.path))
        self._cancel_btn.Enable(bool(item and item.state in (WAITING, RUNNING)))
        self._remove_btn.Enable(bool(item and item.state != RUNNING))
        finished = any(i.is_finished for i in self._rows)
        self._clear_btn.Enable(finished)
        self._clear_all_btn.Enable(bool(self._rows))

    def open_selected(self) -> bool:
        """Show where a finished download went."""
        item = self.selected()
        if item is None or item.state != DONE or not item.path:
            self._announce("That one has not been saved yet.")
            return False
        folder = str(Path(item.path).parent)
        if self._open_folder is not None:
            opened = bool(self._open_folder(folder))
        else:
            # The shared, tested argv -- the split "/select," form Explorer
            # ignores, opening Documents instead, is a bug this repo already hit
            # once and does not need to hit twice.
            import subprocess

            from quill.core.file_manager import reveal_command

            try:
                subprocess.Popen(reveal_command(item.path))  # noqa: S603
                opened = True
            except OSError:
                opened = False
        self._announce(
            f"Showing {item.name} in {folder}." if opened else "That folder could not be opened."
        )
        return opened

    def cancel_selected(self) -> bool:
        item = self.selected()
        if item is None or self._cancel is None:
            return False
        if not self._cancel(item):
            return False
        self._announce(f"Cancelled {item.name}. Anything already saved is kept.")
        self.refresh()
        return True

    def remove_selected(self) -> bool:
        """Take a row off the list without touching what is on disk."""
        item = self.selected()
        if item is None:
            return False
        if not self._queue.remove(item):
            self._announce("That one is downloading now. Cancel it first.")
            return False
        self._announce(f"Removed {item.name} from the list. Any saved file is untouched.")
        self.refresh()
        return True

    def clear_finished(self) -> int:
        removed = self._queue.clear_finished()
        self._announce(f"Cleared {removed} finished." if removed else "Nothing finished to clear.")
        self.refresh()
        return removed

    def clear_everything(self) -> int:
        """Empty the list, stopping anything still going."""
        removed = self._clear_all() if self._clear_all is not None else self._queue.clear_all()
        self._announce(
            f"Cleared the download list. {removed} removed. Anything already saved is kept."
        )
        self.refresh()
        return removed

    def show(self) -> int:
        """Show the window, and always destroy it afterwards (A11Y-4)."""
        try:
            if self._show_modal_dialog is not None:
                return int(self._show_modal_dialog(self._dialog, TITLE))
            return int(self._dialog.ShowModal())  # dialog_button_contract: exempt
        finally:
            self._dialog.Destroy()
