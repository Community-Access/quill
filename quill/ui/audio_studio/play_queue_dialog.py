"""Audio Studio Play Queue dialog (Phase 2 port-in).

Lists the chapter play queue, with Add (file picker), Next, Remove, Clear, and
Close. Mutations update the shared :class:`PlayQueue` in place and call the
host's ``on_save`` callback so the queue persists. Mirrors the house dialog
style (``apply_modal_ids``, stable ``name``); the standalone shell opens it
with ``ShowModal``, embedded QUILL via ``_show_modal_dialog``.
"""

from __future__ import annotations

from collections.abc import Callable

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

_BOOK_WILDCARD = (
    "Audiobooks (*.m4b;*.mp3;*.m4a)|*.m4b;*.mp3;*.m4a|All files (*.*)|*.*"
)


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
        sizer.Add(self._list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        button_row = wx.BoxSizer(wx.HORIZONTAL)
        self._add_btn = wx.Button(self, label=str(_("&Add...")))
        self._next_btn = wx.Button(self, label=str(_("&Next")))
        self._remove_btn = wx.Button(self, label=str(_("&Remove")))
        self._clear_btn = wx.Button(self, label=str(_("Clea&r")))
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
        self._reload()
        apply_modal_ids(self, affirmative_id=wx.ID_CLOSE, cancel_id=wx.ID_CLOSE)

    def _reload(self) -> None:
        self._list.Clear()
        for entry in self._queue.entries:
            self._list.Append(f"{entry.title} -- {entry.path}")

    def _persist(self) -> None:
        self._reload()
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
        from pathlib import Path

        queue_add(self._queue, QueueEntry(path=str(path), title=Path(path).stem))
        self._persist()

    def _on_next(self, event: wx.CommandEvent) -> None:
        entry = queue_next(self._queue)
        if entry is None:
            return
        self._persist()

    def _on_remove(self, event: wx.CommandEvent) -> None:
        sel = self._list.GetSelection()
        if sel < 0 or sel >= len(self._queue.entries):
            return
        queue_remove(self._queue, self._queue.entries[sel].path)
        self._persist()

    def _on_clear(self, event: wx.CommandEvent) -> None:
        queue_clear(self._queue)
        self._persist()