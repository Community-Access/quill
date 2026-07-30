"""Accessible "Browse Spotify" dialog for Quill Radio and QUILL Cast.

The result-building logic lives in :func:`build_browse_items`, a plain function
over a ``SpotifyClient`` so it is unit-testable with a fake client and no
network. :class:`SpotifyBrowseDialog` is a thin wxPython shell: a search field
plus an accessible results ListBox whose selected item plays via an injected
``on_play`` callback (Radio hands a ``spotify:`` RadioStation to the radio
player; Cast routes a ``spotify:episode:`` through the podcast player).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class BrowseItem:
    """One playable row: a screen-reader label and the ``spotify:`` URI to play."""

    label: str
    uri: str


def _track_label(track: Any) -> str:
    artist = getattr(track, "artist", "") or ""
    name = getattr(track, "name", "") or "Untitled"
    return f"{name} - {artist}" if artist else name


def _show_label(show: Any) -> str:
    publisher = getattr(show, "publisher", "") or ""
    name = getattr(show, "name", "") or "Untitled"
    return f"{name} - {publisher}" if publisher else name


def _episode_label(episode: Any) -> str:
    show_name = getattr(episode, "show_name", "") or ""
    name = getattr(episode, "name", "") or "Untitled"
    return f"{name} - {show_name}" if show_name else name


def build_browse_items(client: Any, query: str, *, kind: str) -> list[BrowseItem]:
    """Search Spotify and return playable rows for the app *kind*.

    ``kind="radio"`` returns tracks (music); ``kind="cast"`` returns podcast
    episodes and shows. An empty query returns the user's saved library instead
    of searching, so opening the dialog shows something immediately.
    """
    items: list[BrowseItem] = []
    query = query.strip()
    if kind == "cast":
        if query:
            results = client.search(query, types=("episode", "show"))
            episodes = list(getattr(results, "episodes", []))
            shows = list(getattr(results, "shows", []))
        else:
            saved = client.saved_library()
            episodes = list(getattr(saved, "episodes", []))
            shows = list(getattr(saved, "shows", []))
        items.extend(BrowseItem(_episode_label(e), e.uri) for e in episodes if e.uri)
        items.extend(BrowseItem(_show_label(s), s.uri) for s in shows if s.uri)
        return items
    # radio (music)
    if query:
        results = client.search(query, types=("track",))
        tracks = list(getattr(results, "tracks", []))
    else:
        saved = client.saved_library()
        tracks = list(getattr(saved, "tracks", []))
    items.extend(BrowseItem(_track_label(t), t.uri) for t in tracks if t.uri)
    return items


try:  # pragma: no cover - wx present in the app, absent in some test envs
    import wx

    from quill.ui.dialog_contract import apply_modal_ids, set_accessible_name

    class SpotifyBrowseDialog(wx.Dialog):
        """Search Spotify and play the selected item, accessibly.

        ``client`` is a ``SpotifyClient``; ``on_play(item)`` starts playback of a
        :class:`BrowseItem` (the app supplies the routing); ``announce`` speaks
        status; ``kind`` is ``"radio"`` or ``"cast"``.
        """

        def __init__(
            self,
            parent: wx.Window,
            *,
            client: Any,
            on_play: Callable[[BrowseItem], None],
            announce: Callable[[str], None],
            kind: str = "radio",
        ) -> None:
            title = "Browse Spotify"
            super().__init__(parent, title=title)
            self._client = client
            self._on_play = on_play
            self._announce = announce
            self._kind = kind
            self._items: list[BrowseItem] = []

            outer = wx.BoxSizer(wx.VERTICAL)
            row = wx.BoxSizer(wx.HORIZONTAL)
            label = wx.StaticText(self, label="&Search Spotify:")
            self._search = wx.TextCtrl(self, style=wx.TE_PROCESS_ENTER)
            set_accessible_name(self._search, "Search Spotify")
            search_btn = wx.Button(self, label="&Go")
            row.Add(label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
            row.Add(self._search, 1, wx.RIGHT, 6)
            row.Add(search_btn, 0)
            outer.Add(row, 0, wx.EXPAND | wx.ALL, 8)

            self._list = wx.ListBox(self, style=wx.LB_SINGLE)
            set_accessible_name(self._list, "Spotify results")
            outer.Add(self._list, 1, wx.EXPAND | wx.ALL, 8)

            self._status = wx.StaticText(self, label="")
            set_accessible_name(self._status, "Browse status")
            outer.Add(self._status, 0, wx.ALL, 8)

            buttons = wx.StdDialogButtonSizer()
            play_id = wx.ID_OK
            play_btn = wx.Button(self, play_id, "&Play")
            close_btn = wx.Button(self, wx.ID_CANCEL, "Cl&ose")
            buttons.AddButton(play_btn)
            buttons.AddButton(close_btn)
            buttons.Realize()
            outer.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)

            self.SetSizerAndFit(outer)
            apply_modal_ids(
                self,
                affirmative_id=play_id,
                affirmative_label="Play",
                cancel_id=wx.ID_CANCEL,
                cancel_label="Close",
            )
            search_btn.Bind(wx.EVT_BUTTON, self._on_search)
            self._search.Bind(wx.EVT_TEXT_ENTER, self._on_search)
            play_btn.Bind(wx.EVT_BUTTON, self._on_play_selected)
            self._list.Bind(wx.EVT_LISTBOX_DCLICK, self._on_play_selected)
            self._search.SetFocus()

        def _on_search(self, _event: wx.CommandEvent) -> None:
            query = self._search.GetValue().strip()
            try:
                self._items = build_browse_items(self._client, query, kind=self._kind)
            except Exception as exc:  # noqa: BLE001 - surfaced to the user
                self._status.SetLabel(f"Spotify search failed: {exc}")
                self._announce(f"Spotify search failed: {exc}")
                return
            self._list.Set([item.label for item in self._items])
            count = len(self._items)
            message = f"{count} result{'s' if count != 1 else ''}."
            self._status.SetLabel(message)
            self._announce(message)
            if count:
                self._list.SetSelection(0)
                self._list.SetFocus()

        def _on_play_selected(self, event: wx.CommandEvent) -> None:
            index = self._list.GetSelection()
            if index == wx.NOT_FOUND or index >= len(self._items):
                self._announce("Select a result to play.")
                if isinstance(event, wx.CommandEvent):
                    event.Skip(False)
                return
            item = self._items[index]
            self._on_play(item)
            self.EndModal(wx.ID_OK)

except ImportError:  # pragma: no cover - wx unavailable; pure logic still importable
    pass
