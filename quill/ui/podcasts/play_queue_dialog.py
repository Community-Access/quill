"""The Play Queue dialog: an ordered, accessibly-reorderable episode list.

Reordering offers both the single-slot nudge (Move Up / Move Down) and
mark-and-move (Mark for Move, then Move Marked Above / Below the selection)
-- the same pattern Interactive Rebase's commit list uses, because nudging
an item twenty slots one press at a time is keyboard-hostile. Stale slots
(an unsubscribed show, a pruned episode) display as such and are skipped at
play time; they never crash anything.
"""

from __future__ import annotations

from collections.abc import Callable

from quill.core.podcasts import queue as queue_ops
from quill.core.podcasts.models import PodcastEpisode, PodcastShow
from quill.core.podcasts.subscriptions import PodcastLibrary
from quill.ui.dialog_contract import apply_modal_ids


class PlayQueueDialog:
    """Play/reorder/remove queued episodes; ``show()`` blocks modally."""

    def __init__(
        self,
        parent: object,
        *,
        library: PodcastLibrary,
        announce_cb: Callable[[str], None] | None = None,
        on_library_changed: Callable[[], None] | None = None,
        on_play: Callable[[PodcastShow, PodcastEpisode], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._library = library
        self._announce = announce_cb or (lambda _m: None)
        self._on_library_changed = on_library_changed or (lambda: None)
        self._on_play = on_play
        self._marked_index: int | None = None

        self.dialog = wx.Dialog(
            parent, title="Play Queue", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.dialog.SetMinSize((560, 420))
        root = wx.BoxSizer(wx.VERTICAL)

        self._list = wx.ListBox(self.dialog)
        self._list.SetName("Play Queue in play order; Enter plays the selected episode now")
        root.Add(self._list, 1, wx.EXPAND | wx.ALL, 8)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        specs = (
            ("&Play Now", self._on_play_now),
            ("Move &Up", lambda: self._nudge(-1)),
            ("Move &Down", lambda: self._nudge(1)),
            ("&Mark for Move", self._on_mark),
            ("Move Marked &Above", lambda: self._move_marked(above=True)),
            ("Move Marked &Below", lambda: self._move_marked(above=False)),
            ("&Remove", self._on_remove),
            ("&Clear Queue", self._on_clear),
        )
        for label, handler in specs:
            button = wx.Button(self.dialog, label=label)
            button.Bind(wx.EVT_BUTTON, lambda _e, h=handler: h())
            buttons.Add(button, 0, wx.RIGHT, 4)
        root.Add(buttons, 0, wx.ALL, 8)

        close_row = wx.BoxSizer(wx.HORIZONTAL)
        close_btn = wx.Button(self.dialog, id=wx.ID_CANCEL, label="Close")
        close_row.AddStretchSpacer()
        close_row.Add(close_btn, 0)
        root.Add(close_row, 0, wx.EXPAND | wx.ALL, 8)

        self.dialog.SetSizer(root)
        self._list.Bind(wx.EVT_LISTBOX_DCLICK, lambda _e: self._on_play_now())
        self._list.Bind(wx.EVT_KEY_DOWN, self._on_list_key)
        self._reload()

    # -- rendering -------------------------------------------------------------

    def _slot_label(self, index: int) -> str:
        item = self._library.queue[index]
        resolved = queue_ops.resolve(self._library, item)
        marker = " (marked for move)" if index == self._marked_index else ""
        if resolved is None:
            return f"{index + 1}. (no longer available){marker}"
        show, episode = resolved
        return f"{index + 1}. {episode.title} — {show.title}{marker}"

    def _reload(self, select: int | None = None) -> None:
        current = self._list.GetSelection() if select is None else select
        self._list.Set([self._slot_label(i) for i in range(len(self._library.queue))])
        count = len(self._library.queue)
        if count:
            self._list.SetSelection(max(0, min(current, count - 1)))

    # -- actions ---------------------------------------------------------------

    def _selected(self) -> int:
        return self._list.GetSelection()

    def _on_play_now(self) -> None:
        index = self._selected()
        if not (0 <= index < len(self._library.queue)) or self._on_play is None:
            return
        resolved = queue_ops.resolve(self._library, self._library.queue[index])
        if resolved is None:
            self._announce("That episode is no longer available; removing its slot.")
            queue_ops.remove_at(self._library, index)
            self._on_library_changed()
            self._reload()
            return
        queue_ops.remove_at(self._library, index)
        self._on_library_changed()
        show, episode = resolved
        self._on_play(show, episode)
        self._announce(f"Playing {episode.title}")
        self._reload()

    def _nudge(self, delta: int) -> None:
        index = self._selected()
        if index < 0:
            return
        new_index = queue_ops.move(self._library, index, delta)
        if new_index != index:
            self._on_library_changed()
            if self._marked_index == index:
                self._marked_index = new_index
            self._reload(select=new_index)
            self._announce(f"Moved to position {new_index + 1} of {len(self._library.queue)}")

    def _on_mark(self) -> None:
        index = self._selected()
        if index < 0:
            return
        self._marked_index = index
        self._reload(select=index)
        self._announce(
            f"Marked position {index + 1}. Select where it should go, then "
            "Move Marked Above or Below."
        )

    def _move_marked(self, *, above: bool) -> None:
        anchor = self._selected()
        marked = self._marked_index
        if marked is None:
            self._announce("Nothing is marked. Use Mark for Move first.")
            return
        if anchor < 0 or anchor == marked:
            return
        new_index = queue_ops.move_relative_to(self._library, marked, anchor, above=above)
        self._marked_index = None
        self._on_library_changed()
        self._reload(select=new_index)
        self._announce(f"Moved to position {new_index + 1} of {len(self._library.queue)}")

    def _on_remove(self) -> None:
        index = self._selected()
        if queue_ops.remove_at(self._library, index):
            if self._marked_index == index:
                self._marked_index = None
            self._on_library_changed()
            self._reload(select=index)
            self._announce("Removed from the queue")

    def _on_clear(self) -> None:
        removed = queue_ops.clear_queue(self._library)
        self._marked_index = None
        self._on_library_changed()
        self._reload()
        self._announce(f"Queue cleared ({removed} item(s) removed)")

    def _on_list_key(self, event: object) -> None:
        wx = self._wx
        code = event.GetKeyCode()
        if code in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            self._on_play_now()
            return
        if code == wx.WXK_DELETE:
            self._on_remove()
            return
        event.Skip()

    # -- lifecycle ------------------------------------------------------------

    def show(self) -> None:
        from quill.ui.dialog_contract import show_modal_dialog

        wx = self._wx
        self.dialog.CentreOnParent()
        apply_modal_ids(self.dialog, escape_id=wx.ID_CANCEL)
        self._list.SetFocus()
        show_modal_dialog(self.dialog)
        self.dialog.Destroy()
