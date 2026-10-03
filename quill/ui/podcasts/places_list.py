"""The Places list control: flat, counted, and the listener's own (qc.md 4.3).

A ``wx.ListBox`` of the places in the listener's order, each row with its
live count ("Inbox (12)"). Arrow keys move between places; Enter or Right
moves into the content pane; Delete hides a place; F2 renames it;
Alt+Shift+Up and Alt+Shift+Down move it (Radio's chord, caught in the frame's
char hook because Windows routes Alt+arrow to the menu system before a list
sees it); the Applications key offers what the place can do as a whole.

The control knows nothing about the library: the frame hands it rows and
reads back a place id, so the list can be tested with a fake box.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

__all__ = ["PlacesList"]


class PlacesList:
    """The box, and the ids behind its rows."""

    def __init__(
        self,
        parent: Any,
        *,
        wx: Any,
        on_enter: Callable[[str], None],
        on_change: Callable[[str], None],
        on_hide: Callable[[str], None],
        on_rename: Callable[[str], None],
        on_menu: Callable[[str], None],
    ) -> None:
        self._wx = wx
        self._ids: list[str] = []
        self._on_enter = on_enter
        self._on_change = on_change
        self._on_hide = on_hide
        self._on_rename = on_rename
        self._on_menu = on_menu
        self.label = wx.StaticText(parent, label="P&laces:")
        self.box = wx.ListBox(parent, choices=[], style=wx.LB_SINGLE)
        self.box.SetHelpText(
            "The places in your library, each with its count: the Inbox, New "
            "Episodes, Continue Listening, Favorites, Personal Audio, the Play "
            "Queue, Downloads, Notifications and your Podcasts. Enter or Right "
            "Arrow moves into the place; Delete hides a row; F2 renames it; "
            "Alt+Shift+Up and Down move it; the Applications key offers what the "
            "whole place can do. View > Places restores anything hidden."
        )
        self.box.Bind(wx.EVT_LISTBOX, self._on_selected)
        self.box.Bind(wx.EVT_LISTBOX_DCLICK, self._on_activated)
        self.box.Bind(wx.EVT_KEY_DOWN, self._on_key)
        for context_event in (wx.EVT_CONTEXT_MENU, wx.EVT_RIGHT_UP):
            self.box.Bind(context_event, self._on_context)

    # -- rows ------------------------------------------------------------------- #

    def set_rows(self, rows: list[tuple[str, str]], *, keep: str = "") -> None:
        """``(place id, label)`` per row; the selection stays on *keep* if present."""
        self._ids = [place_id for place_id, _label in rows]
        self.box.Set([label for _place_id, label in rows])
        if not self._ids:
            return
        index = self._ids.index(keep) if keep in self._ids else 0
        self.box.SetSelection(index)

    def relabel(self, place_id: str, label: str) -> None:
        if place_id in self._ids:
            index = self._ids.index(place_id)
            if self.box.GetString(index) != label:
                self.box.SetString(index, label)

    @property
    def selected(self) -> str:
        index = self.box.GetSelection()
        return self._ids[index] if 0 <= index < len(self._ids) else ""

    def select(self, place_id: str) -> bool:
        if place_id not in self._ids:
            return False
        self.box.SetSelection(self._ids.index(place_id))
        return True

    def focus(self) -> None:
        try:
            self.box.SetFocus()
        except Exception:  # noqa: BLE001 - mid-teardown
            pass

    # -- events ------------------------------------------------------------------ #

    def _on_selected(self, event: Any) -> None:
        if self.selected:
            self._on_change(self.selected)
        event.Skip()

    def _on_activated(self, _event: Any) -> None:
        if self.selected:
            self._on_enter(self.selected)

    def _on_key(self, event: Any) -> None:
        wx = self._wx
        code = event.GetKeyCode()
        place_id = self.selected
        if not place_id:
            event.Skip()
            return
        if code in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER, wx.WXK_RIGHT):
            self._on_enter(place_id)
            return
        if code in (wx.WXK_DELETE, wx.WXK_NUMPAD_DELETE):
            self._on_hide(place_id)
            return
        if code == wx.WXK_F2:
            self._on_rename(place_id)
            return
        event.Skip()

    def _on_context(self, event: Any) -> None:
        if self.selected:
            self._on_menu(self.selected)
        if hasattr(event, "Skip"):
            event.Skip(False)
