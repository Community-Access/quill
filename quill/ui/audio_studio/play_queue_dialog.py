"""Audio Studio Play Queue dialog (Phase 2 port-in).

Lists the chapter play queue, with Add (file picker), Next, Remove, Clear, and
Close. Mutations update the shared :class:`PlayQueue` in place and call the
host's ``on_save`` callback so the queue persists. Mirrors the house dialog
style (``apply_modal_ids``, stable ``name``); the standalone shell opens it
with ``ShowModal``, embedded QUILL via ``_show_modal_dialog``.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import wx

from quill.core.audio_studio.play_queue import (
    PlayQueue,
    QueueEntry,
)
from quill.core.audio_studio.play_queue import (
    add as queue_add,
)
from quill.core.audio_studio.play_queue import (
    clear as queue_clear,
)
from quill.core.audio_studio.play_queue import (
    next_entry as queue_next,
)
from quill.core.audio_studio.play_queue import (
    remove as queue_remove,
)
from quill.core.i18n import _
from quill.ui.dialog_contract import apply_modal_ids

_BOOK_WILDCARD = "Audiobooks (*.m4b;*.mp3;*.m4a)|*.m4b;*.mp3;*.m4a|All files (*.*)|*.*"


class PlayQueueDialog(wx.Dialog):
    """Browse and edit the play queue; mutations persist via ``on_save``."""

    def __init__(
        self,
        parent: wx.Window,
        queue: PlayQueue,
        *,
        on_save: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(
            parent,
            title=str(_("Play Queue")),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
            name="audio_studio.play_queue",
        )
        self._queue = queue
        self._on_save = on_save

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(
            wx.StaticText(self, label=str(_("Up next:"))),
            0,
            wx.ALL,
            8,
        )
        self._list = wx.ListBox(self, name="Play queue entries")
        self._list.SetHelpText(
            "The books waiting to play, in order; when one finishes, the next "
            "playable entry opens by itself. The current book is marked in "
            "words, a row whose file has moved says missing, and Delete "
            "removes the highlighted row."
        )
        sizer.Add(self._list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        button_row = wx.BoxSizer(wx.HORIZONTAL)
        self._add_btn = wx.Button(self, label=str(_("&Add...")))
        self._add_btn.SetHelpText(
            "Picks an audiobook file (M4B, MP3 or M4A) and appends it to the "
            "queue; a book already queued keeps its place rather than being "
            "added twice."
        )
        self._next_btn = wx.Button(self, label=str(_("&Next")))
        self._next_btn.SetHelpText(
            "Advances the queue's pointer to the next entry and marks it as "
            "current -- the book that plays when the current one finishes."
        )
        self._remove_btn = wx.Button(self, label=str(_("&Remove")))
        self._remove_btn.SetHelpText(
            "Takes the highlighted book out of the queue. The audio file on disk is untouched."
        )
        self._clear_btn = wx.Button(self, label=str(_("Clea&r")))
        self._clear_btn.SetHelpText("Empties the whole queue. No audio files are touched.")
        for btn in (self._add_btn, self._next_btn, self._remove_btn, self._clear_btn):
            button_row.Add(btn, 0, wx.RIGHT, 4)
        sizer.Add(button_row, 0, wx.ALL, 8)

        buttons = self.CreateSeparatedButtonSizer(wx.CLOSE)
        sizer.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)
        self.SetSizerAndFit(sizer)

        self._add_btn.Bind(wx.EVT_BUTTON, self._on_add)
        self._next_btn.Bind(wx.EVT_BUTTON, self._on_next)
        self._remove_btn.Bind(wx.EVT_BUTTON, self._on_remove)
        self._clear_btn.Bind(wx.EVT_BUTTON, self._on_clear)
        # Delete removes the highlighted entry (a screen-reader user expects the
        # key to work from the list, not only via the Remove button).
        self._list.Bind(wx.EVT_KEY_DOWN, self._on_list_key)
        self._reload()
        apply_modal_ids(self, affirmative_id=wx.ID_CLOSE, cancel_id=wx.ID_CLOSE)

    def _row_label(self, index: int, entry: QueueEntry) -> str:
        """One list row. The current entry and any entry whose file is gone are
        marked in words so a screen reader speaks the distinction, not just a
        visual cue."""
        tags = []
        if index == self._queue.current_index:
            tags.append(str(_("Current")))
        if not Path(entry.path).exists():
            tags.append(str(_("missing")))
        prefix = f"[{', '.join(tags)}] " if tags else ""
        return f"{prefix}{entry.title} -- {entry.path}"

    def _reload(self, *, select: int | None = None) -> None:
        self._list.Clear()
        for index, entry in enumerate(self._queue.entries):
            self._list.Append(self._row_label(index, entry))
        if self._queue.entries:
            # Selecting a row makes the screen reader speak it, which is how each
            # action (add/remove/next) announces its result. Clamp to range so a
            # remove near the end still lands on a valid row.
            target = 0 if select is None else max(0, min(select, len(self._queue.entries) - 1))
            self._list.SetSelection(target)
        elif self._add_btn:
            # Empty queue: move focus somewhere sensible so the screen reader is
            # not stranded on a now-empty list.
            self._add_btn.SetFocus()

    def _persist(self, *, select: int | None = None) -> None:
        self._reload(select=select)
        if self._on_save is not None:
            self._on_save()

    def _on_add(self, event: wx.CommandEvent) -> None:
        with wx.FileDialog(
            self,
            message=str(_("Add a book to the queue")),
            wildcard=_BOOK_WILDCARD,
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as picker:
            if picker.ShowModal() != wx.ID_OK:  # dialog_button_contract: exempt
                return
            path = picker.GetPath()
        queue_add(self._queue, QueueEntry(path=str(path), title=Path(path).stem))
        # Land on the entry that was just added (dedup may leave it where it was).
        added = next(
            (i for i, e in enumerate(self._queue.entries) if e.path == str(path)),
            len(self._queue.entries) - 1,
        )
        self._persist(select=added)

    def _on_next(self, event: wx.CommandEvent) -> None:
        entry = queue_next(self._queue)
        if entry is None:
            return
        self._persist(select=self._queue.current_index)

    def _on_remove(self, event: wx.CommandEvent) -> None:
        sel = self._list.GetSelection()
        if sel < 0 or sel >= len(self._queue.entries):
            return
        queue_remove(self._queue, self._queue.entries[sel].path)
        self._persist(select=sel)

    def _on_clear(self, event: wx.CommandEvent) -> None:
        queue_clear(self._queue)
        self._persist()

    def _on_list_key(self, event: wx.KeyEvent) -> None:
        if event.GetKeyCode() == wx.WXK_DELETE:
            self._on_remove(event)  # type: ignore[arg-type]
            return
        event.Skip()
