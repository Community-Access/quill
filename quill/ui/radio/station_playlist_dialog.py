"""What the Station Played: the station's own published list of recent songs.

Song History (Ctrl+Shift+H) is what Quill Radio heard while you listened. This
window is the other half: what the station *says* it played, from the playlist
it publishes itself (``quill/core/radio/station_playlist.py``). The two sit side
by side on the Playback menu and never mix -- the provenance line says plainly
whose list this is, the same way the What's Playing details window says where
a title came from.

A row reads like a Song History row ("Title by Artist, started 10:04"), and the
buttons are the ones Song History has where they are cheap to share: copy, keep
in the Clip Library, Song Details (MusicBrainz) and Lyrics (LRCLIB), all through
the same code Song History calls.

Accessibility notes:

* The songs are a plain ``wx.ListBox``: one item per song whose label already
  holds everything a screen reader needs. Focus starts there.
* The provenance sentence is a read-only text field with its own label, so it
  can be reached with Tab and read again rather than spoken once and lost.
* Nothing here announces what the screen reader already says. Actions report
  their outcome, because a button that silently worked sounds like one that
  silently failed.

The idea of showing a station's published history comes from BlindRadio by
serrebidev (MIT).
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from quill.core.radio.song_history import SongPlay
from quill.core.radio.station_playlist import PlayedSong, StationPlaylist
from quill.ui.dialog_contract import apply_modal_ids
from quill.ui.dpi import dip_size

#: The window title, and the prefix F1's surface catalogue knows it by.
TITLE_PREFIX = "What the Station Played"


def _clock(moment: datetime | None) -> str:
    if moment is None:
        return ""
    return moment.astimezone().strftime("%H:%M")


def describe_played(song: PlayedSong) -> str:
    """The list label for one published song (pure, so it is testable).

    "Playing now" for the row the station marks as current; otherwise the
    source's own words when it gives only words (the BBC's "3 minutes ago"),
    else the start time.
    """
    parts = [song.display()]
    if song.is_current:
        parts.append("playing now")
    elif song.when_label:
        parts.append(song.when_label)
    else:
        started = _clock(song.started_at)
        if started:
            parts.append(f"started {started}")
    return ", ".join(parts)


def as_song_play(song: PlayedSong) -> SongPlay:
    """The same song as a Song History row, so its lookups can be reused."""
    stamp = song.started_at.isoformat() if song.started_at is not None else ""
    return SongPlay(
        title=song.title,
        artist=song.artist,
        raw=song.display(),
        first_heard=stamp,
        last_heard=stamp,
    )


class StationPlaylistDialog:
    """The station's published recent songs, newest first, with provenance."""

    def __init__(
        self,
        parent: object,
        *,
        playlist: StationPlaylist,
        station_name: str,
        show_modal_dialog: Callable,
        copy_to_clipboard: Callable[[str], bool],
        announce: Callable[[str], None],
        send_to_clip_library: Callable[[str, str], bool],
        request_facts: Callable[[SongPlay, Callable[[str], None]], None] | None = None,
        request_lyrics: Callable[[SongPlay | None], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._playlist = playlist
        self._songs = list(playlist.songs)
        self._station_name = station_name
        self._show_modal = show_modal_dialog
        self._copy = copy_to_clipboard
        self._announce = announce
        self._send_to_clips = send_to_clip_library
        self._request_facts = request_facts
        self._request_lyrics = request_lyrics
        self.title = f"{TITLE_PREFIX}: {station_name}" if station_name else TITLE_PREFIX
        self.dialog = wx.Dialog(
            parent, title=self.title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.dialog.SetSize(dip_size(self.dialog, 620, 500))
        self._build_ui()

    def _build_ui(self) -> None:
        wx = self._wx
        panel = self.dialog
        root = wx.BoxSizer(wx.VERTICAL)

        count = len(self._songs)
        self._songs_label = wx.StaticText(
            panel, label=f"S&ongs, newest first ({count}):" if count != 1 else "S&ong (1):"
        )
        root.Add(self._songs_label, 0, wx.LEFT | wx.TOP, 8)
        self.songs = wx.ListBox(
            panel, choices=[describe_played(s) for s in self._songs], style=wx.LB_SINGLE
        )
        self.songs.SetName("Songs")
        self.songs.SetHelpText(
            "The songs the station says it played, newest first, with the time "
            "each one started when the station gives it."
        )
        if self._songs:
            self.songs.SetSelection(0)
        root.Add(self.songs, 2, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        source_label = wx.StaticText(panel, label="Where this list comes &from:")
        root.Add(source_label, 0, wx.LEFT, 8)
        self.source = wx.TextCtrl(
            panel, value=self._playlist.source.provenance(), style=wx.TE_MULTILINE | wx.TE_READONLY
        )
        self.source.SetName("Where this list comes from")
        self.source.SetHelpText(
            "Who published this list. It is the station's own record, not the "
            "songs Quill Radio heard; those are in Song History."
        )
        root.Add(self.source, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        facts_label = wx.StaticText(panel, label="Song de&tails:")
        root.Add(facts_label, 0, wx.LEFT, 8)
        self.facts = wx.TextCtrl(panel, value="", style=wx.TE_MULTILINE | wx.TE_READONLY)
        self.facts.SetName("Song details")
        self.facts.SetHelpText(
            "What MusicBrainz knows about the highlighted song, after you press Song Details."
        )
        root.Add(self.facts, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        self.copy_btn = wx.Button(panel, label="&Copy")
        self.copy_btn.SetHelpText(
            "Copies the highlighted song, title and artist, to the clipboard."
        )
        self.clip_btn = wx.Button(panel, label="Send to Clip &Library")
        self.clip_btn.SetHelpText(
            "Keeps the highlighted song in the Clip Library, the shared "
            "scrapbook every Quill app can read."
        )
        self.facts_btn = wx.Button(panel, label="Song &Details")
        self.facts_btn.SetHelpText(
            "Looks the song up on MusicBrainz: which release, what year, how "
            "long. Keyless and off in Safe Mode."
        )
        self.lyrics_btn = wx.Button(panel, label="L&yrics")
        self.lyrics_btn.SetHelpText(
            "Looks the highlighted song's words up on LRCLIB and opens them in "
            "the Lyrics window. Only when you press it; off in Safe Mode."
        )
        close_btn = wx.Button(panel, wx.ID_CLOSE, label="Close")
        close_btn.SetHelpText("Closes this list. Song History is unchanged.")
        for button in (self.copy_btn, self.clip_btn, self.facts_btn, self.lyrics_btn, close_btn):
            buttons.Add(button, 0, wx.RIGHT, 6)
        root.Add(buttons, 0, wx.ALL, 8)
        apply_modal_ids(self.dialog, affirmative_id=close_btn.GetId(), escape_id=close_btn.GetId())
        close_btn.Bind(wx.EVT_BUTTON, lambda _e: self.dialog.EndModal(wx.ID_CLOSE))

        self.dialog.SetSizer(root)
        self.songs.Bind(wx.EVT_LISTBOX, lambda _e: self._update_buttons())
        self.copy_btn.Bind(wx.EVT_BUTTON, self.on_copy)
        self.clip_btn.Bind(wx.EVT_BUTTON, self.on_clip)
        self.facts_btn.Bind(wx.EVT_BUTTON, self.on_song_facts)
        self.lyrics_btn.Bind(wx.EVT_BUTTON, self.on_lyrics)
        self._update_buttons()
        wx.CallAfter(self.songs.SetFocus)

    # -- state --

    def selected(self) -> PlayedSong | None:
        index = self.songs.GetSelection()
        if index < 0 or index >= len(self._songs):
            return None
        return self._songs[index]

    def _update_buttons(self) -> None:
        has_song = self.selected() is not None
        self.copy_btn.Enable(has_song)
        self.clip_btn.Enable(has_song)
        self.facts_btn.Enable(has_song and self._request_facts is not None)
        self.lyrics_btn.Enable(has_song and self._request_lyrics is not None)

    # -- actions --

    def on_copy(self, _event: object = None) -> None:
        song = self.selected()
        if song is None:
            return
        if self._copy(song.clip_text()):
            self._announce(f"Copied {song.display()}.")
        else:
            self._announce("Could not copy.")

    def on_clip(self, _event: object = None) -> None:
        song = self.selected()
        if song is None:
            return
        if self._send_to_clips(song.clip_text(), self._station_name):
            self._announce(f"Kept {song.display()} in the Clip Library.")
        else:
            self._announce("Already in the Clip Library.")

    def on_song_facts(self, _event: object = None) -> None:
        song = self.selected()
        if song is None or self._request_facts is None:
            return
        self.facts.SetValue("Looking up...")
        self._request_facts(as_song_play(song), self.facts.SetValue)

    def on_lyrics(self, _event: object = None) -> None:
        song = self.selected()
        if self._request_lyrics is not None:
            self._request_lyrics(as_song_play(song) if song is not None else None)

    def show(self) -> int:
        result = self._show_modal(self.dialog, self.title)
        self.dialog.Destroy()
        return int(result or 0)
