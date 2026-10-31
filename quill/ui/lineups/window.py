"""The Lineups window: your Lineups, the items in the one selected, and every verb.

A peer window in both apps -- its own taskbar entry and menu bar, on the Window
menu and in the Ctrl+Tab order. Two lists in reading order: **Lineups**, then
the **Items** of the one selected (moving the selection loads them at once).
Enter on a Lineup plays it; Enter on an item plays from there and carries on.

**Nothing moves the cursor but the listener.** Rows are identified by their
reference, never by position, and every reload -- a refresh, an edit in the
other app, an undo -- rewrites only the rows whose words changed and puts the
selection back on the same items. When the selected item itself leaves, the
cursor goes to the row that took its place, never to the top, and the reason is
said first (Cast's tree learned that the hard way; ``library_tree_updates``).

**Rules run in the background**: when the window opens, when a store the rules
read changes (either app's), every ten minutes for the time-based Keep choices,
and on Refresh Now (F5). A refresh with the window in focus says what changed in
one sentence; a timed one with nothing to report says nothing.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from quill.core.lineups import describe
from quill.core.lineups.fields import ItemFacts
from quill.core.lineups.merge import Catalogue
from quill.core.lineups.model import Lineup, LineupBook
from quill.core.lineups.ops import Operation, Outcome
from quill.core.lineups.refs import (
    KIND_EPISODE,
    KIND_LOCAL,
    KIND_RECORDING,
    KIND_SHOW,
    KIND_STATION,
    KIND_YT_CHANNEL,
    KIND_YT_PLAYLIST,
    KIND_YT_VIDEO,
    ItemRef,
    Presence,
)
from quill.core.lineups.store import LineupStore, LineupStoreError
from quill.ui.dpi import dip, dip_size
from quill.ui.lineups import menus
from quill.ui.lineups.commands import LineupsCommandsMixin
from quill.ui.lineups.commands_play import LineupsArrangePlayMixin
from quill.ui.lineups.host import LineupsHost
from quill.ui.lineups.refreshing import LineupsRefreshMixin

__all__ = ["EMPTY_SENTENCE", "SHOW_FILTERS", "TITLE", "LineupsWindow"]

TITLE = "Lineups"

EMPTY_SENTENCE = (
    "You have no lineups yet. New Lineup makes an empty one to fill with Add to "
    "Lineup from anywhere in the app; Start from an Example gives you one with rules."
)

#: ``(label, kinds)`` for the Show filter; ``()`` means every kind.
SHOW_FILTERS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("All kinds", ()),
    ("Episodes and podcasts", (KIND_EPISODE, KIND_SHOW)),
    ("Stations and places", (KIND_STATION, "place")),
    ("YouTube", (KIND_YT_VIDEO, KIND_YT_PLAYLIST, KIND_YT_CHANNEL)),
    ("Local media and recordings", (KIND_LOCAL, KIND_RECORDING)),
)

_TICK_MS = 2000


class LineupsWindow(LineupsCommandsMixin, LineupsArrangePlayMixin, LineupsRefreshMixin):
    """The Lineups peer window for one app."""

    def __init__(self, host: LineupsHost, *, lineup_id: str = "") -> None:
        import wx

        self._wx = wx
        self._lineups_host = host
        self._host = host.app
        self._windows = host.windows
        self._store = LineupStore(host.data_dir)
        self._book: LineupBook = self._load_book()
        self._catalogue: Catalogue | None = None
        self._stamp = self._store.stamp()
        self._source_stamps = self._sources_stamp()
        self._refreshing = False
        self._refresh_again: bool | None = None
        self._last_timed = host.now()
        self._new: dict[str, int] = {}
        self._lineup_ids: list[str] = []
        self._visible: list[ItemRef] = []
        self._row_text: list[str] = []
        self._clip: tuple[ItemRef, ...] = ()
        self._menu_id_refs: list[Any] = []
        self._menu_items: dict[str, Any] = {}
        self._win = wx.Frame(None, title=TITLE, style=wx.DEFAULT_FRAME_STYLE)
        self.dialog = self._win
        self._surface = wx.Panel(self._win, style=wx.TAB_TRAVERSAL)
        self._win.SetMinSize(dip_size(self._win, 760, 520))
        self._build()
        self._menu_items = menus.install_menu_bar(self, wx, self.run)
        outer = wx.BoxSizer(wx.VERTICAL)
        outer.Add(self._surface, 1, wx.EXPAND)
        self._win.SetSizer(outer)
        self._status_bar = self._win.CreateStatusBar()
        self._keys = menus.key_table()
        self._win.Bind(wx.EVT_CHAR_HOOK, self._on_char_hook)
        self._win.Bind(wx.EVT_CLOSE, self._on_close)
        self._timer = wx.Timer(self._win)
        self._win.Bind(wx.EVT_TIMER, lambda _e: self._tick(), self._timer)
        from quill.ui.surface_lifetime import stop_timer_on_destroy

        stop_timer_on_destroy(self._win, self._timer)
        self.reload(
            select_lineup=lineup_id or (self._book.lineups[0].id if self._book.lineups else "")
        )

    # -- building -------------------------------------------------------------------

    def _build(self) -> None:
        wx = self._wx
        surface = self._surface
        root = wx.BoxSizer(wx.VERTICAL)
        self._intro = wx.StaticText(surface, label=EMPTY_SENTENCE)
        root.Add(self._intro, 0, wx.ALL, 10)
        empty_buttons = wx.BoxSizer(wx.HORIZONTAL)
        self._new_btn = wx.Button(surface, label="&New Lineup...")
        self._new_btn.SetHelpText(
            "Name a new, empty lineup. Fill it with Add to Lineup from any list in the "
            "app, or give it rules with Edit Rules."
        )
        self._new_btn.Bind(wx.EVT_BUTTON, lambda _e: self.run("new_lineup"))
        empty_buttons.Add(self._new_btn, 0, wx.RIGHT, 6)
        self._example_btn = wx.Button(surface, label="Start from an E&xample...")
        self._example_btn.SetHelpText(
            "Choose a ready-made lineup, such as Morning or New This Week, and make it "
            "your own. Its rules are yours to change."
        )
        self._example_btn.Bind(wx.EVT_BUTTON, lambda _e: self.run("new_example"))
        empty_buttons.Add(self._example_btn)
        root.Add(empty_buttons, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        lists = wx.BoxSizer(wx.HORIZONTAL)
        left = wx.BoxSizer(wx.VERTICAL)
        self._lineups_label = wx.StaticText(surface, label="&Lineups:")
        left.Add(self._lineups_label, 0, wx.BOTTOM, 4)
        self._lineups = wx.ListBox(surface, style=wx.LB_SINGLE)
        self._lineups.SetName("Lineups")
        self._lineups.SetHelpText(
            "Your lineups, with how many items each holds and how long it plays. Enter "
            "plays the lineup; Tab moves to the Show filter, then its items. Alt+Enter "
            "edits its rules, F2 renames, Delete deletes it after asking, and "
            "Alt+Shift+Up and Down move it."
        )
        self._lineups.SetMinSize(dip_size(self._lineups, 240, 300))
        left.Add(self._lineups, 1, wx.EXPAND)
        lists.Add(left, 0, wx.EXPAND | wx.RIGHT, 10)

        right = wx.BoxSizer(wx.VERTICAL)
        show_row = wx.BoxSizer(wx.HORIZONTAL)
        self._show_label = wx.StaticText(surface, label="Sh&ow:")
        show_row.Add(self._show_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        self._show = wx.Choice(surface, choices=[label for label, _kinds in SHOW_FILTERS])
        self._show.SetSelection(0)
        self._show.SetHelpText(
            "Show only some kinds of item. Moving items while a kind is hidden moves "
            "them among the items you can see."
        )
        show_row.Add(self._show, 0)
        right.Add(show_row, 0, wx.BOTTOM, 6)
        self._items_label = wx.StaticText(surface, label="I&tems:")
        right.Add(self._items_label, 0, wx.BOTTOM, 4)
        # One column and no header: a lone "Item" header is noise some readers
        # announce on every visit (review N6). The column follows the width.
        style = wx.LC_REPORT | wx.LC_NO_HEADER | wx.BORDER_SIMPLE
        self._items = wx.ListCtrl(surface, style=style)
        self._items.InsertColumn(0, "Item", width=dip(self._items, 620))
        self._items.Bind(wx.EVT_SIZE, self._on_items_size)
        self._items.SetName("Items")
        self._items.SetHelpText(
            "Rules add items, and each rule says when its items go: when they stop "
            "matching, when you have finished them, after some days, or never. Moving "
            "an item changes the order but not how long it stays. Keep (Ctrl+K) holds "
            "an item whatever the rules say. Delete puts it in Removed Items, and no "
            "rule brings it back. Enter plays from here; Alt+Enter says why an item "
            "is here; Alt+Shift+Up and Down move it."
        )
        right.Add(self._items, 1, wx.EXPAND)
        lists.Add(right, 1, wx.EXPAND)
        root.Add(lists, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        surface.SetSizer(root)

        self._lineups.Bind(wx.EVT_LISTBOX, lambda _e: self._on_lineup_chosen())
        self._lineups.Bind(wx.EVT_CONTEXT_MENU, lambda _e: self._lineup_menu())
        self._show.Bind(wx.EVT_CHOICE, lambda _e: self.reload())
        self._items.Bind(wx.EVT_LIST_ITEM_ACTIVATED, lambda _e: self.run("play"))
        self._items.Bind(wx.EVT_CONTEXT_MENU, lambda _e: self._item_menu())

    def _on_items_size(self, event: Any) -> None:
        event.Skip()
        width = self._items.GetClientSize().width
        if width > 50:
            self._items.SetColumnWidth(0, width - 4)

    # -- the book and the file ----------------------------------------------------------

    def _load_book(self) -> LineupBook:
        try:
            return self._store.load()
        except Exception as exc:  # noqa: BLE001 - an unreadable file must not stop the window
            self._lineups_host.announce(f"Your lineups could not be read: {exc}.")
            return LineupBook()

    def apply(self, operation: Operation) -> Outcome | None:
        """Run one edit on the file as it is now; ``None`` (and said why) on failure."""
        try:
            book, outcome = self._store.update(operation)
        except LineupStoreError as exc:
            self._lineups_host.announce(str(exc))
            return None
        self._book = book
        self._stamp = self._store.stamp()
        return outcome

    def _sources_stamp(self) -> tuple[tuple[int, int], ...]:
        stamps = []
        for path in self._lineups_host.watched_files():
            try:
                info = path.stat()
                stamps.append((info.st_size, info.st_mtime_ns))
            except OSError:
                stamps.append((0, 0))
        return tuple(stamps)

    # -- what is selected -------------------------------------------------------------------

    def current_lineup(self) -> Lineup | None:
        index = self._lineups.GetSelection()
        if 0 <= index < len(self._lineup_ids):
            return self._book.find(self._lineup_ids[index])
        return None

    def selected_refs(self) -> list[ItemRef]:
        refs: list[ItemRef] = []
        row = self._items.GetFirstSelected()
        while row >= 0:
            if row < len(self._visible):
                refs.append(self._visible[row])
            row = self._items.GetNextSelected(row)
        return refs

    def focused_ref(self) -> ItemRef | None:
        row = self._items.GetFocusedItem()
        if row < 0:
            row = self._items.GetFirstSelected()
        return self._visible[row] if 0 <= row < len(self._visible) else None

    def visible_refs(self) -> list[ItemRef]:
        return list(self._visible)

    def facts_for(self, ref: ItemRef) -> tuple[Presence, ItemFacts | None]:
        if self._catalogue is None:
            return Presence.UNLISTED, None
        return self._catalogue.lookup(ref)

    def lineups_focused(self) -> bool:
        return self._wx.Window.FindFocus() is self._lineups

    def items_focused(self) -> bool:
        return self._wx.Window.FindFocus() is self._items

    # -- filling ------------------------------------------------------------------------------

    def _lengths(self, lineup: Lineup) -> dict[ItemRef, int]:
        lengths: dict[ItemRef, int] = {}
        for row in lineup.rows:
            _presence, facts = self.facts_for(row.ref)
            lengths[row.ref] = facts.length_seconds if facts is not None and not facts.live else 0
        return lengths

    def reload(
        self, *, select_lineup: str = "", select: Sequence[ItemRef] | None = None, focus: str = ""
    ) -> None:
        """Rebuild both lists from the book, keeping the cursor by identity."""
        current = self.current_lineup()
        wanted = select_lineup or (current.id if current is not None else "")
        if not self._book.find(wanted) and self._book.lineups:
            index = max(0, min(self._lineups.GetSelection(), len(self._book.lineups) - 1))
            wanted = self._book.lineups[index].id
        start = self._lineups_host.start_lineup_id()
        labels = [
            describe.lineup_row_text(
                lineup,
                total_seconds=sum(self._lengths(lineup).values()),
                new=self._new.get(lineup.id, 0),
                is_start=lineup.id == start,
            )
            for lineup in self._book.lineups
        ]
        current_labels = [self._lineups.GetString(i) for i in range(self._lineups.GetCount())]
        if len(labels) != len(current_labels):
            self._lineups.Set(labels)
        else:
            # Same rows: rewrite only those whose words changed, so the row the
            # reader is on is not re-announced and nothing scrolls (review M4).
            for index, (old, new) in enumerate(zip(current_labels, labels, strict=True)):
                if old != new:
                    self._lineups.SetString(index, new)
        self._lineup_ids = [lineup.id for lineup in self._book.lineups]
        if wanted in self._lineup_ids:
            self._lineups.SetSelection(self._lineup_ids.index(wanted))
        lineup = self.current_lineup()
        keep = list(select) if select is not None else self.selected_refs()
        cursor = None if select is not None else self.focused_ref()
        old_rows = self._items.GetFirstSelected()
        self._fill_items(lineup)
        rows = [self._visible.index(ref) for ref in keep if ref in self._visible]
        if not rows and keep and self._visible:
            rows = [min(max(old_rows, 0), len(self._visible) - 1)]  # the row that took its place
        # The cursor stays on the row it was on, not the first selected (review M3).
        focus_row = self._visible.index(cursor) if cursor in self._visible else None
        self._select_rows(rows, focus_row=focus_row)
        self._show_state(focus)
        self._update_status(lineup)
        self._sync_checks(lineup)

    def _fill_items(self, lineup: Lineup | None) -> None:
        kinds = SHOW_FILTERS[max(0, self._show.GetSelection())][1]
        rows = [
            row
            for row in (lineup.rows if lineup is not None else ())
            if not kinds or row.ref.kind in kinds
        ]
        wanted = []
        for row in rows:
            presence, facts = self.facts_for(row.ref)
            wanted.append(describe.row_text(row, facts, presence))
        name = lineup.name if lineup is not None else ""
        label = f"I&tems in {name}:" if name else "I&tems:"
        if lineup is not None and not lineup.rows:
            label = f"I&tems in {name} (empty):"
        if self._items_label.GetLabel() != label:
            self._items_label.SetLabel(label)
            self._items.SetName(label.replace("&", "").rstrip(":"))
        old = len(self._row_text)
        # Only rows whose words changed are rewritten: rewriting an unchanged row
        # makes some readers re-announce it, and the cursor must not twitch.
        for index in range(min(old, len(wanted))):
            if wanted[index] != self._row_text[index]:
                self._items.SetItem(index, 0, wanted[index])
        for index in range(old, len(wanted)):
            self._items.InsertItem(index, wanted[index])
        for index in range(old - 1, len(wanted) - 1, -1):
            self._items.DeleteItem(index)
        self._row_text = wanted
        self._visible = [row.ref for row in rows]

    def _select_rows(self, rows: list[int], *, focus_row: int | None = None) -> None:
        count = self._items.GetItemCount()
        row = self._items.GetFirstSelected()
        while row >= 0:
            if row not in rows:
                self._items.Select(row, False)
            row = self._items.GetNextSelected(row)
        for row in rows:
            if 0 <= row < count:
                self._items.Select(row, True)
        target = focus_row if focus_row is not None else (rows[0] if rows else None)
        if target is not None and 0 <= target < count:
            self._items.Focus(target)
            self._items.EnsureVisible(target)

    def _show_state(self, focus: str) -> None:
        empty = not self._book.lineups
        changed = self._intro.IsShown() != empty
        self._intro.Show(empty)
        self._new_btn.Show(empty)
        self._example_btn.Show(empty)
        for control in (
            self._lineups_label,
            self._lineups,
            self._show_label,
            self._show,
            self._items_label,
            self._items,
        ):
            control.Show(not empty)
        if changed:
            self._surface.Layout()
        target = {"lineups": self._lineups, "items": self._items, "new": self._new_btn}.get(focus)
        if empty and focus:
            target = self._new_btn
        if target is not None and target.IsShown():
            target.SetFocus()

    def _update_status(self, lineup: Lineup | None) -> None:
        if lineup is None:
            text = "No lineups yet." if not self._book.lineups else ""
        else:
            refreshed = ""
            if lineup.refreshed_at:
                import time

                refreshed = time.strftime("%H:%M", time.localtime(lineup.refreshed_at))
            text = describe.summary_text(lineup, self._lengths(lineup), refreshed=refreshed)
        if self._status_bar.GetStatusText() != text:
            self._status_bar.SetStatusText(text)

    def summary_sentence(self) -> str:
        lineup = self.current_lineup()
        return self._status_bar.GetStatusText() if lineup is not None else "No lineup is selected."

    def _sync_checks(self, lineup: Lineup | None) -> None:
        start = self._lineups_host.start_lineup_id()
        focused = self.focused_ref()
        row = lineup.row_for(focused) if lineup is not None and focused is not None else None
        states = {
            "start_here": bool(lineup is not None and lineup.id == start),
            "skip_live": bool(lineup is not None and lineup.skip_live),
            "keep": bool(row is not None and row.held == "kept"),
        }
        for verb, on in states.items():
            item = self._menu_items.get(verb)
            if item is not None and item.IsChecked() != on:
                item.Check(on)

    def _on_lineup_chosen(self) -> None:
        lineup = self.current_lineup()
        if lineup is not None:
            self._new.pop(lineup.id, None)  # "2 new" clears once the lineup has been looked at
        self.reload(select=[lineup.rows[0].ref] if lineup is not None and lineup.rows else [])

    # -- keys and menus ---------------------------------------------------------------------

    def run(self, verb: str) -> None:
        """Run one command by its verb -- a menu item, a key or a button."""
        handler = getattr(self, f"cmd_{verb}", None)
        if callable(handler):
            handler()

    def _on_char_hook(self, event: Any) -> None:
        wx = self._wx
        code = event.GetKeyCode()
        if code == wx.WXK_ESCAPE or (code == wx.WXK_F4 and event.ControlDown()):
            self._win.Close()  # a frame has no Escape-to-close of its own
            return
        chord = menus.chord_of_event(event, wx)
        if chord == "Enter" and (self.items_focused() or self.lineups_focused()):
            self.run("play_all" if self.lineups_focused() else "play")
            return
        if chord == "Ctrl+Space" and self.items_focused():
            # The list's own key for picking rows one at a time (review M2). Done
            # here, not Skipped: a Skipped key goes on to the menu bar, whose
            # Ctrl+Space is Pause. Pause keeps Ctrl+Space everywhere else.
            row = self._items.GetFocusedItem()
            if row >= 0:
                self._items.Select(row, not self._items.IsSelected(row))
            return
        verb = self._keys.get(chord)
        list_focused = self.items_focused() or self.lineups_focused()
        if verb is None:
            event.Skip()
            return
        if chord in menus.LIST_ONLY_KEYS and not list_focused:
            return  # not Skipped: the menu bar would run it on the wrong thing (R1)
        if self.lineups_focused():
            # On the Lineups list a key means the lineup itself -- Delete deletes
            # it, Alt+Enter edits its rules. Keys only: a menu item always means
            # what its label says (review M1).
            verb = {"remove": "delete_lineup", "why": "edit_rules", "play": "play_all"}.get(
                verb, verb
            )
        self.run(verb)

    def _item_menu(self) -> None:
        if self.focused_ref() is None:
            return
        lineup = self.current_lineup()
        row = lineup.row_for(self.focused_ref()) if lineup is not None else None  # type: ignore[arg-type]
        checked = frozenset({"keep"}) if row is not None and row.held == "kept" else frozenset()
        rows = [(v, label) for v, label in menus.ITEM_POPUP if v != "paste_before" or self._clip]
        rows = [(v, label) for v, label in rows if v != "paste_after" or self._clip]
        menu = menus.popup(self, self._wx, rows, self.run, keys={"play": "Enter"}, checked=checked)
        try:
            self._items.PopupMenu(menu)
        finally:
            menu.Destroy()

    def _lineup_menu(self) -> None:
        lineup = self.current_lineup()
        if lineup is None:
            return
        start = self._lineups_host.start_lineup_id()
        checked = frozenset({"start_here"}) if lineup.id == start else frozenset()
        keys = {"play_all": "Enter", "edit_rules": "Alt+Enter", "delete_lineup": "Delete"}
        menu = menus.popup(
            self, self._wx, list(menus.LINEUP_POPUP), self.run, keys=keys, checked=checked
        )
        try:
            self._lineups.PopupMenu(menu)
        finally:
            menu.Destroy()

    # -- showing and closing -------------------------------------------------------------

    def focus_default_control(self) -> None:
        if not self._book.lineups:
            self._new_btn.SetFocus()
        elif self._items.GetItemCount():
            self._items.SetFocus()
        else:
            self._lineups.SetFocus()

    def show(self) -> None:
        from quill.ui.dialog_contract import show_modeless_surface

        self._lineups_host.install_keys(self._win)
        if self._windows is not None:
            self._windows.register(self._win, TITLE)
        # Focus is placed before the window shows, so the dialog contract keeps
        # it rather than focusing the first control and then this (review M6).
        # A button is not "explicit" focus to the contract, so the empty window
        # says so (R7).
        self.focus_default_control()
        if not self._book.lineups:
            self._win._quill_keep_initial_focus = True
        show_modeless_surface(self._win, TITLE, announce=self._lineups_host.announce)
        self._timer.Start(_TICK_MS)
        self.request_refresh(speak=False)
        if not self._book.lineups:
            self._wx.CallLater(600, lambda: self._lineups_host.announce(EMPTY_SENTENCE))

    def select_lineup(self, lineup_id: str) -> None:
        self.reload(select_lineup=lineup_id, focus="items")

    def _on_close(self, event: Any) -> None:
        from quill.ui.dialog_contract import announce_surface_exit

        self._timer.Stop()
        previous = self._windows.previous_key(self._win) if self._windows is not None else None
        if self._windows is not None:
            self._windows.unregister(self._win)
        _OPEN.pop(self._lineups_host.app_key, None)
        announce_surface_exit(TITLE, self._lineups_host.announce)
        event.Skip()
        self._win.Destroy()
        if previous and self._windows is not None:
            self._windows.activate(previous)


#: The open window per app ("radio", "cast"): one Lineups window per app.
_OPEN: dict[str, LineupsWindow] = {}


def open_window(host: LineupsHost, *, lineup_id: str = "") -> LineupsWindow:
    """Open the Lineups window, or bring the open one forward (on *lineup_id*)."""
    existing = _OPEN.get(host.app_key)
    if existing is not None and existing._win:
        windows = host.windows
        if windows is not None:
            windows.activate_title(TITLE)
        else:
            existing._win.Raise()
        if lineup_id:
            existing.select_lineup(lineup_id)
        return existing
    window = LineupsWindow(host, lineup_id=lineup_id)
    _OPEN[host.app_key] = window
    window.show()
    return window


def open_window_of(app_key: str) -> LineupsWindow | None:
    """The open Lineups window of *app_key*, for "Add to Lineup" to refresh."""
    window = _OPEN.get(app_key)
    return window if window is not None and window._win else None
