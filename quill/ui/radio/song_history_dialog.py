"""Song History: what each station has played, and optional background on a song.

What's Playing (Ctrl+T) speaks the current track and forgets it. This window is
the memory behind it: a per-station list of every title change the track-title
poll observed, newest first, with the time it was heard.

From a selected song a listener can copy it, keep it in the Clip Library, or ask
the configured AI provider for background on it. The background answer is always
introduced as model-written -- it sits inches away from the station's own
metadata in the same window, and the two must never be confused.

Accessibility notes, since this is the point of the app:

* The songs list is a plain ``wx.ListBox``: one focusable item per song, whose
  label already contains everything a screen reader needs to read ("Song by
  Artist, heard 10:04, played twice"). No columns to arrow across.
* Every action reports its outcome by announcement, because a button that
  silently succeeds is indistinguishable from one that silently failed.
* The background answer lands in a read-only but focusable multiline field, so
  it can be reviewed character by character and copied, rather than being
  spoken once and lost.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from quill.core.radio.song_history import BACKGROUND_DISCLAIMER, SongHistory, SongPlay
from quill.ui.dialog_contract import announce_surface_exit, apply_modal_ids


def _heard_at(iso: str) -> str:
    """A short local time for an ISO stamp ("" when unparseable)."""
    if not iso:
        return ""
    try:
        moment = datetime.fromisoformat(iso)
    except ValueError:
        return ""
    return moment.astimezone().strftime("%H:%M")


def describe_song(song: SongPlay) -> str:
    """The spoken list label for one logged song (pure, so it is testable).

    Times and repeat counts are words rather than punctuation because this
    string is read aloud verbatim: "10:04" reads as a time, but a bare "(2)"
    reads as nothing useful at all.
    """
    parts = [song.display()]
    heard = _heard_at(song.last_heard)
    if heard:
        parts.append(f"heard {heard}")
    if song.play_count == 2:
        parts.append("played twice")
    elif song.play_count > 2:
        parts.append(f"played {song.play_count} times")
    return ", ".join(parts)


class SongHistoryDialog:
    """Per-station song log with copy, Clip Library, and AI background."""

    def __init__(
        self,
        parent: object,
        *,
        history: SongHistory,
        current_station_key: str,
        show_modal_dialog: Callable,
        copy_to_clipboard: Callable[[str], bool],
        announce: Callable[[str], None],
        send_to_clip_library: Callable[[str, str], bool],
        request_background: Callable[[SongPlay, str, Callable[[str, str], None]], None],
        request_facts: Callable[[SongPlay, Callable[[str], None]], None] | None = None,
        on_changed: Callable[[], None],
        title: str = "Song History",
        transport_host: object | None = None,
        windows: object | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._transport_host = transport_host
        self._windows = windows
        self._modeless = windows is not None
        self._menu_id_refs: list[object] = []
        self._history = history
        self._show_modal = show_modal_dialog
        self._copy = copy_to_clipboard
        self._announce = announce
        self._send_to_clips = send_to_clip_library
        self._request_background = request_background
        #: Injected like the Background lookup above: the frame owns the task
        #: manager and Safe Mode, this window owns the box the answer lands in.
        self._request_facts = request_facts
        self._on_changed = on_changed
        self._title = title
        self._busy = False

        self._stations = history.known_stations()
        self._station_index = 0
        for index, station in enumerate(self._stations):
            if station.station_key == current_station_key:
                self._station_index = index
                break

        # Modeless parentless wx.Frame (a peer window in the taskbar, the
        # &Window menu and Ctrl+Tab) when standalone Radio supplies a
        # WindowManager; an unchanged modal wx.Dialog for embedded QUILL.
        if self._modeless:
            self._win = wx.Frame(None, title=title, style=wx.DEFAULT_FRAME_STYLE)
            self._surface = wx.Panel(self._win, style=wx.TAB_TRAVERSAL)
            self._build_surface_menu_bar()
            self._win.Bind(wx.EVT_CHAR_HOOK, self._on_char_hook)
            self._win.Bind(wx.EVT_CLOSE, self._on_close)
        else:
            self._win = wx.Dialog(
                parent,
                title=title,
                style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
            )
            self._surface = self._win
        self.dialog = self._win  # top-level window; child dialogs parent to it
        self._win.SetSize(wx.Size(620, 520))
        self._build_ui()
        self._reload_songs()

    # -- construction --

    def _build_surface_menu_bar(self) -> None:
        """Menu bar for the modeless frame: &Close + the shared &Window menu."""
        wx = self._wx
        menu_bar = wx.MenuBar()
        surface_menu = wx.Menu()
        close_id = wx.NewIdRef()
        surface_menu.Append(close_id, "&Close\tCtrl+W")
        self._win.Bind(wx.EVT_MENU, lambda _e: self._win.Close(), id=close_id)
        menu_bar.Append(surface_menu, "&Songs")
        self._windows.install(self._win, menu_bar)
        self._win.SetMenuBar(menu_bar)
        self._menu_id_refs.append(close_id)

    def _on_char_hook(self, event: object) -> None:
        # A frame has no automatic Escape->Cancel; wire it (and Ctrl+F4, the
        # document-window close key) to close, like every peer window.
        wx = self._wx
        if event.GetKeyCode() == wx.WXK_ESCAPE or (
            event.GetKeyCode() == wx.WXK_F4 and event.ControlDown()
        ):
            self._win.Close()
            return
        event.Skip()

    def _on_close(self, event: object) -> None:
        previous = self._windows.previous_key(self._win)
        self._windows.unregister(self._win)
        announce_surface_exit(self._title, self._announce)
        event.Skip()
        self._win.Destroy()
        if previous:
            self._windows.activate(previous)

    def _build_ui(self) -> None:
        wx = self._wx
        panel = self._surface
        root = wx.BoxSizer(wx.VERTICAL)

        station_label = wx.StaticText(panel, label="&Station:")
        root.Add(station_label, 0, wx.LEFT | wx.TOP, 8)
        self._station_choice = wx.Choice(
            panel, choices=[self._station_label(s) for s in self._stations]
        )
        self._station_choice.SetName("Station")
        if self._stations:
            self._station_choice.SetSelection(self._station_index)
        root.Add(self._station_choice, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        self._songs_label = wx.StaticText(panel, label="S&ongs:")
        root.Add(self._songs_label, 0, wx.LEFT, 8)
        self._songs = wx.ListBox(panel, style=wx.LB_SINGLE)
        self._songs.SetName("Songs")
        root.Add(self._songs, 2, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        background_label = wx.StaticText(panel, label="&Background:")
        root.Add(background_label, 0, wx.LEFT, 8)
        self._background = wx.TextCtrl(
            panel,
            value="",
            style=wx.TE_MULTILINE | wx.TE_READONLY,
        )
        self._background.SetName("Background")
        root.Add(self._background, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        self._copy_btn = wx.Button(panel, label="&Copy")
        self._copy_btn.SetHelpText(
            "Copies the highlighted song, title and artist, to the clipboard."
        )
        self._clip_btn = wx.Button(panel, label="Send to Clip &Library")
        self._clip_btn.SetHelpText(
            "Keeps the highlighted song in the Clip Library, the shared "
            "scrapbook every Quill app can read."
        )
        self._background_btn = wx.Button(panel, label="&Background")
        self._background_btn.SetHelpText(
            "Asks your configured AI provider for background on the song. The "
            "answer is model-written and says so -- it is not the station's "
            "own information."
        )
        self._facts_btn = wx.Button(panel, label="Song &Details")
        self._facts_btn.SetHelpText(
            "Looks the song up on MusicBrainz -- which release, what year, how "
            "long. Keyless and off in Safe Mode."
        )
        self._clear_btn = wx.Button(panel, label="Clea&r...")
        self._clear_btn.SetHelpText(
            "Erases the logged songs -- for this station or for every station; "
            "a confirmation asks which."
        )
        for button in (
            self._copy_btn,
            self._clip_btn,
            self._background_btn,
            self._facts_btn,
            self._clear_btn,
        ):
            btn_row.Add(button, 0, wx.RIGHT, 6)
        if not self._modeless:
            # Only the modal dialog carries a Close button: a real window
            # closes with Alt+F4/Ctrl+F4, Ctrl+W, or Escape (2026-08-23).
            close_btn = wx.Button(panel, wx.ID_CLOSE, label="C&lose")
            close_btn.SetHelpText("Closes Song History; logging continues while stations play.")
            btn_row.Add(close_btn, 0, wx.RIGHT, 6)
            apply_modal_ids(
                self._win,
                affirmative_id=close_btn.GetId(),
                escape_id=close_btn.GetId(),
            )
            close_btn.Bind(wx.EVT_BUTTON, lambda _e: self._win.EndModal(wx.ID_CLOSE))
        root.Add(btn_row, 0, wx.ALL, 8)

        # The transport keyboard, when the surface that opened this one knows
        # about the player. It was installed in the browse tree and nowhere
        # else, so every other Radio dialog was a window where the keys that
        # work everywhere stopped working. The WindowManager's Ctrl+Tab /
        # Ctrl+1..9 rows ride in the same table when this is a peer window.
        if self._transport_host is not None:
            from quill.ui.radio import transport_keys

            transport_keys.install(
                self._win,
                self._transport_host,
                wx=wx,
                extra_entries=self._windows.accelerator_entries() if self._modeless else (),
            )

        self._surface.SetSizer(root)
        if self._modeless:
            outer = wx.BoxSizer(wx.VERTICAL)
            outer.Add(self._surface, 1, wx.EXPAND)
            self._win.SetSizer(outer)

        self._station_choice.Bind(self._wx.EVT_CHOICE, lambda _e: self._reload_songs())
        self._facts_btn.Bind(self._wx.EVT_BUTTON, self._on_song_facts)
        self._songs.Bind(self._wx.EVT_LISTBOX, lambda _e: self._update_buttons())
        self._copy_btn.Bind(self._wx.EVT_BUTTON, self._on_copy)
        self._clip_btn.Bind(self._wx.EVT_BUTTON, self._on_clip)
        self._background_btn.Bind(self._wx.EVT_BUTTON, self._on_background)
        self._clear_btn.Bind(self._wx.EVT_BUTTON, self._on_clear)
        self._wx.CallAfter(self._songs.SetFocus)

    @staticmethod
    def _station_label(station: object) -> str:
        name = getattr(station, "station_name", "") or "Unknown station"
        count = len(getattr(station, "songs", []))
        return f"{name} ({count} songs)" if count != 1 else f"{name} (1 song)"

    # -- state --

    def _current_songs(self) -> list[SongPlay]:
        if not self._stations:
            return []
        index = self._station_choice.GetSelection()
        if index < 0 or index >= len(self._stations):
            return []
        return list(self._stations[index].songs)

    def _current_station_name(self) -> str:
        if not self._stations:
            return ""
        index = self._station_choice.GetSelection()
        if index < 0 or index >= len(self._stations):
            return ""
        return self._stations[index].station_name

    def _selected_song(self) -> SongPlay | None:
        songs = self._current_songs()
        index = self._songs.GetSelection()
        if index < 0 or index >= len(songs):
            return None
        return songs[index]

    def _reload_songs(self) -> None:
        songs = self._current_songs()
        self._songs.Set([describe_song(song) for song in songs])
        if songs:
            self._songs.SetSelection(0)
        self._songs_label.SetLabel(f"S&ongs ({len(songs)}):" if len(songs) != 1 else "S&ong (1):")
        self._background.SetValue("")
        self._update_buttons()

    def _update_buttons(self) -> None:
        has_song = self._selected_song() is not None
        self._copy_btn.Enable(has_song)
        self._clip_btn.Enable(has_song)
        self._background_btn.Enable(has_song and not self._busy)
        self._facts_btn.Enable(has_song and self._request_facts is not None)
        self._clear_btn.Enable(bool(self._stations))

    # -- actions --

    def _on_copy(self, _event: object) -> None:
        song = self._selected_song()
        if song is None:
            return
        if self._copy(song.clip_text()):
            self._announce(f"Copied {song.display()}.")
        else:
            self._announce("Could not copy.")

    def _on_clip(self, _event: object) -> None:
        song = self._selected_song()
        if song is None:
            return
        if self._send_to_clips(song.clip_text(), self._current_station_name()):
            self._announce(f"Kept {song.display()} in the Clip Library.")
        else:
            # remember() returns False for an exact duplicate, which is a
            # perfectly ordinary outcome and must not read as an error.
            self._announce("Already in the Clip Library.")

    def _on_song_facts(self, _event: object) -> None:
        """**Song Details**: which release, what year, how long.

        The difference between a list of titles and a history you can do
        something with. Opt-in, off the UI thread, and it degrades to "nothing
        more is known" rather than to an error message.
        """
        song = self._selected_song()
        if song is None or self._request_facts is None:
            return
        self._background.SetValue("Looking up...")
        self._request_facts(song, self._background.SetValue)

    def _on_background(self, _event: object) -> None:
        song = self._selected_song()
        if song is None or self._busy:
            return
        self._busy = True
        self._update_buttons()
        self._background.SetValue("Asking...")
        self._announce(f"Asking about {song.display()}...")
        self._request_background(song, self._current_station_name(), self._on_background_done)

    def _on_background_done(self, text: str, error: str) -> None:
        self._busy = False
        self._update_buttons()
        if error:
            self._background.SetValue(error)
            self._announce(error)
            return
        if not text:
            message = "The AI provider returned nothing."
            self._background.SetValue(message)
            self._announce(message)
            return
        self._background.SetValue(f"{BACKGROUND_DISCLAIMER}\n\n{text}")
        self._announce("Background ready.")
        self._background.SetFocus()

    def _on_clear(self, _event: object) -> None:
        wx = self._wx
        station_name = self._current_station_name() or "this station"
        dialog = wx.MessageDialog(
            self.dialog,
            f"Clear the song history for {station_name}?\n\n"
            "Choose No to clear the history for every station instead.",
            "Clear Song History",
            wx.YES_NO | wx.CANCEL | wx.ICON_QUESTION,
        )
        # Destructive question, so the safe answer is the default (the same rule
        # the rest of the radio follows).
        dialog.SetYesNoCancelLabels("This &station", "&All stations", "Cancel")
        answer = self._show_modal(dialog, "Clear Song History")
        dialog.Destroy()
        if answer == wx.ID_CANCEL:
            return
        if answer == wx.ID_YES:
            index = self._station_choice.GetSelection()
            if 0 <= index < len(self._stations):
                self._history.clear_station(self._stations[index].station_key)
            self._announce(f"Cleared the song history for {station_name}.")
        else:
            self._history.clear_all()
            self._announce("Cleared the song history for every station.")
        self._on_changed()
        self._stations = self._history.known_stations()
        self._station_choice.Set([self._station_label(s) for s in self._stations])
        if self._stations:
            self._station_choice.SetSelection(0)
        self._reload_songs()

    def show(self) -> int:
        if self._modeless:
            from quill.ui.dialog_contract import show_modeless_surface

            self._windows.register(self._win, self._title)
            show_modeless_surface(self._win, self._title, announce=self._announce)
            return 0
        result = self._show_modal(self._win, self._title)
        self._win.Destroy()
        return result
