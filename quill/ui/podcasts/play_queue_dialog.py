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

        group_row = wx.BoxSizer(wx.HORIZONTAL)
        group_row.Add(
            wx.StaticText(self.dialog, label="&Group by:"),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            6,
        )
        self._group_choice = wx.Choice(
            self.dialog, choices=["Nothing", "Podcast", "Library folder"]
        )
        self._group_choice.SetName(
            "How the queue is read. Grouping never changes the play order, only how it is listed."
        )
        self._group_choice.SetSelection(self._group_index())
        group_row.Add(self._group_choice, 1, wx.EXPAND)
        root.Add(group_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)

        # Extended, not multiple (list.md 2.4): Shift and Ctrl behave the way
        # they do in every other list on the system, and a single click still
        # replaces the selection -- LB_MULTIPLE toggles on plain arrow keys,
        # which silently turns "move down the queue" into "select the queue".
        self._list = wx.ListBox(self.dialog, style=wx.LB_EXTENDED)
        self._list.SetName(
            "Play Queue in play order; Enter plays the selected episode now. "
            "Shift and arrow extend the selection, Ctrl and Space adds one, "
            "and Remove takes everything selected."
        )
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
            # Lineups: the order you listen in, saved (list.md 2.3).
            ("&Save Lineup...", self._on_save_lineup),
            ("Appl&y Lineup...", self._on_apply_lineup),
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
        self._group_choice.Bind(wx.EVT_CHOICE, lambda _e: self._on_group_changed())
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

    def _group_index(self) -> int:
        settings = getattr(self._library, "settings", None)
        mode = str(getattr(settings, "queue_group_mode", "none") or "none")
        return queue_ops.GROUP_MODES.index(mode) if mode in queue_ops.GROUP_MODES else 0

    def _on_group_changed(self) -> None:
        """Remember the choice, redraw, and say how the list now reads."""
        mode = queue_ops.GROUP_MODES[max(0, self._group_choice.GetSelection())]
        settings = getattr(self._library, "settings", None)
        if settings is not None:
            settings.queue_group_mode = mode
            self._on_library_changed()
        self._reload()
        self._list.SetSelection(0)
        groups = len([row for row in self._rows if row[0] is None])
        if mode == "none":
            self._announce(f"{len(self._library.queue)} episodes, ungrouped.")
        else:
            self._announce(f"{groups} group{'' if groups == 1 else 's'}.")

    def _reload(self, select: int | None = None) -> None:
        """Rebuild the visible list, which may now carry group headers.

        ``self._rows`` maps every visible line back to a queue index, or to
        ``None`` for a header. Every action reads the queue index from there
        rather than from the list position, so a header can never be played,
        moved or removed by an action that thought it was an episode.

        *select* is a **queue index**, not a row: an episode that moved should
        be followed, and in a grouped list its row number is not its position.
        """
        current_row = self._first_selected_row()
        mode = queue_ops.GROUP_MODES[max(0, self._group_choice.GetSelection())]
        labels: list[str] = []
        self._rows: list[tuple[int | None, str]] = []
        for group_label, indices in queue_ops.group_queue_by(self._library, mode):
            if group_label:
                count = len(indices)
                labels.append(f"{group_label}, group, {count} episode{'' if count == 1 else 's'}")
                self._rows.append((None, group_label))
            for index in indices:
                labels.append(("    " if group_label else "") + self._slot_label(index))
                self._rows.append((index, group_label))
        self._list.Set(labels)
        if not labels:
            return
        if select is None:
            self._select_only(max(0, min(current_row, len(labels) - 1)))
            return
        for row, (index, _label) in enumerate(self._rows):
            if index == select:
                self._select_only(row)
                return
        self._select_only(0)

    def _select_only(self, row: int) -> None:
        """Land on exactly one row.

        ``SetSelection`` *adds* on an extended list rather than replacing, so
        without clearing first a reload accumulates every row it ever landed
        on -- and the next Remove takes the lot. ``wx.ListBox`` offers no
        DeselectAll, only ``Deselect`` per row, so the clear is a loop over
        what is actually selected rather than over the whole list.
        """
        for selected in list(self._list.GetSelections()):
            self._list.Deselect(selected)
        self._list.SetSelection(row)

    # -- actions ---------------------------------------------------------------

    def _first_selected_row(self) -> int:
        """The topmost selected line, or -1.

        ``GetSelection`` answers ``wxNOT_FOUND`` on an extended-selection
        list, whatever is highlighted -- so every single-row verb here reads
        the selection list instead. Missing that is how making a list
        multi-select silently disables half its buttons.
        """
        selections = self._list.GetSelections()
        return min(selections) if selections else -1

    def _selected(self) -> int:
        """The queue index of the selected line, or -1 on a header or nothing.

        Headers answer -1 rather than the next episode's index: acting on a
        header because it happened to be selected is how somebody removes an
        episode they never chose.
        """
        row = self._first_selected_row()
        rows = getattr(self, "_rows", [])
        if not (0 <= row < len(rows)):
            return -1
        index = rows[row][0]
        return -1 if index is None else int(index)

    def _selected_indexes(self) -> list[int]:
        """Every selected episode's queue index, in queue order.

        Headers are dropped rather than mapped to the row beneath them, for
        the same reason :meth:`_selected` answers -1 on one: a selection
        somebody made by dragging past a group title must not act on an
        episode they never chose.
        """
        rows = getattr(self, "_rows", [])
        found: list[int] = []
        for row in self._list.GetSelections():
            if not (0 <= row < len(rows)):
                continue
            index = rows[row][0]
            if index is not None:
                found.append(int(index))
        return sorted(set(found))

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
        """Remove everything selected -- one row or twenty (list.md 2.4)."""
        from quill.core.counted import Counted

        indexes = self._selected_indexes()
        if not indexes:
            self._announce("Nothing is selected.")
            return
        # Back to front, because removing position 2 renumbers everything
        # after it: front to back would take out the wrong slots from the
        # second one onward, and quietly.
        removed = 0
        for index in reversed(indexes):
            if queue_ops.remove_at(self._library, index):
                removed += 1
                if self._marked_index == index:
                    self._marked_index = None
        if not removed:
            return
        self._on_library_changed()
        self._reload(select=min(indexes))
        counted = Counted(done=removed, _eligible=len(indexes))
        self._announce(counted.sentence("Removed", noun="episode"))

    def _on_clear(self) -> None:
        removed = queue_ops.clear_queue(self._library)
        self._marked_index = None
        self._on_library_changed()
        self._reload()
        self._announce(f"Queue cleared ({removed} item(s) removed)")

    # -- lineups ---------------------------------------------------------------

    def _on_save_lineup(self) -> None:
        """Keep this order under a name, so it can be put back next Tuesday."""
        from quill.core.podcasts.queue_lineups import find_lineup, save_lineup

        wx = self._wx
        if not self._library.queue:
            self._announce("The queue is empty, so there is no order to save.")
            return
        with wx.TextEntryDialog(self.dialog, "Lineup name:", "Save Lineup") as dialog:
            if dialog.ShowModal() != wx.ID_OK:  # dialog_button_contract: exempt
                return
            name = dialog.GetValue().strip()
        if not name:
            return
        replacing = find_lineup(self._library, name) is not None
        saved = save_lineup(self._library, name)
        if saved is None:
            self._announce("That lineup could not be saved.")
            return
        self._on_library_changed()
        verb = "Replaced" if replacing else "Saved"
        # Counted, because "saved" on its own does not say how much of the
        # queue went in -- and re-saving over a nine-episode lineup with two
        # episodes queued is exactly the moment somebody wants to know.
        self._announce(f"{verb} lineup {name}: {len(saved.items)} episode(s), in this order.")

    def _on_apply_lineup(self) -> None:
        """Put a saved order back at the front, leaving the rest alone."""
        from quill.core.podcasts.queue_lineups import apply_lineup, lineup_names

        wx = self._wx
        names = lineup_names(self._library)
        if not names:
            self._announce("No lineups have been saved yet. Use Save Lineup first.")
            return
        with wx.SingleChoiceDialog(
            self.dialog, "Apply which lineup?", "Apply Lineup", names
        ) as dialog:
            if dialog.ShowModal() != wx.ID_OK:  # dialog_button_contract: exempt
                return
            chosen = dialog.GetStringSelection()
        playlist = next((p for p in self._library.playlists if p.name == chosen), None)
        if playlist is None:
            return
        counted = apply_lineup(self._library, playlist)
        self._on_library_changed()
        self._reload(select=0)
        self._announce(counted.sentence("Applied", chosen, noun="episode"))

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
