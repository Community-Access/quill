"""The ``radio.station_playlist`` command: ask the station what it played.

Playback > What the Station Played (Alt+Shift+H in Quill Radio, beside Song
History's Ctrl+Shift+H). It looks at the playing station's stream address,
works out whether that station publishes its own playlist
(``quill/core/radio/station_playlist.py``), asks for it off the UI thread, and
opens the list. A station that publishes none is told so in one sentence,
without any request being made.

Kept out of ``main_frame_radio`` for the GATE-11 budget, like
``lyrics_commands``; it takes the *host* (the frame mixing in ``RadioMixin``)
and uses only ``_radio_controller``, ``_announce``, ``_safe_mode``,
``_task_manager``, ``_wx`` and the modal/clipboard helpers.

The idea comes from BlindRadio by serrebidev (MIT).
"""

from __future__ import annotations

from typing import Any

from quill.core.radio import station_playlist

NOTHING_PLAYING = "Play a station first, then ask what it played."
SAFE_MODE = "Station playlists are off in Safe Mode."
NO_PLAYLIST = station_playlist.NO_PLAYLIST


def _station(host: Any) -> Any:
    controller = getattr(host, "_radio_controller", None)
    state = getattr(controller, "state", None)
    return getattr(state, "station", None)


def open_station_playlist(host: Any) -> None:
    """Fetch the playing station's published playlist and show it."""
    station = _station(host)
    stream_url = str(getattr(station, "stream_url", "") or "")
    if station is None or not stream_url:
        host._announce(NOTHING_PLAYING)
        return
    if getattr(host, "_safe_mode", False):
        host._announce(SAFE_MODE)
        return
    source = station_playlist.match_source(stream_url)
    if source is None:
        host._announce(NO_PLAYLIST)
        return
    name = str(getattr(station, "name", "") or "")
    who = _who(source)
    host._announce(f"Asking {who} for the playlist...")

    def _work(**_kwargs: Any) -> Any:
        return station_playlist.fetch_station_playlist(stream_url)

    def _ok(_op: str, result: object) -> None:
        host._wx.CallAfter(_arrived, host, name, source, result)

    def _failed(_op: str, _error: BaseException) -> None:
        host._wx.CallAfter(
            host._announce,
            f"Could not get the playlist from {who}. Try again in a moment.",
        )

    host._task_manager.submit("radio-station-playlist", _work, on_success=_ok, on_failure=_failed)


def _arrived(host: Any, station_name: str, source: Any, result: object) -> None:
    if not isinstance(result, station_playlist.StationPlaylist):
        host._announce(NO_PLAYLIST)
        return
    if not result.songs:
        who = _who(source)
        host._announce(
            f"{who[:1].upper()}{who[1:]} lists no recent songs for this station right now."
        )
        return
    show(host, result, station_name)


def _who(source: Any) -> str:
    """The publisher's name, short enough for a sentence ("Triton Digital")."""
    return str(source.name).split(",", 1)[0]


def show(host: Any, playlist: station_playlist.StationPlaylist, station_name: str) -> None:
    """Open the list. The lookups are Song History's own, reused."""
    from quill.ui.radio import lyrics_commands, song_facts, song_history_commands
    from quill.ui.radio.station_playlist_dialog import StationPlaylistDialog

    dialog = StationPlaylistDialog(
        host.frame,
        playlist=playlist,
        station_name=station_name,
        show_modal_dialog=host._show_modal_dialog,
        copy_to_clipboard=host._copy_to_clipboard,
        announce=host._announce,
        send_to_clip_library=lambda text, name: song_history_commands.send_to_clip_library(
            host, text, name
        ),
        request_facts=lambda song, done: song_facts.request(host, song, done),
        request_lyrics=lambda song: lyrics_commands.lyrics_for_song(host, song),
    )
    dialog.show()
