"""What the Station Played, behaviourally: the command, the window, the wiring.

The handlers are called against a small host double with the playlist fetch
faked at ``station_playlist._fetch`` -- never a table of names -- and the
window is built for real on the session wx.App. The source list is BlindRadio's
idea (serrebidev, MIT).
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from quill.core import app_keymaps
from quill.core.radio import station_playlist
from quill.core.radio import surface_help as radio_help
from quill.ui.radio import station_playlist_commands as commands
from quill.ui.radio.station_playlist_dialog import (
    StationPlaylistDialog,
    as_song_play,
    describe_played,
)

_FIXTURES = Path(__file__).parents[1] / "core" / "radio" / "fixtures" / "station_playlist"
_KEXP_URL = "https://kexp.streamguys1.com/kexp160.aac"


class _Tasks:
    """Runs the work at once and answers like the task manager."""

    def __init__(self) -> None:
        self.names: list[str] = []

    def submit(self, name: str, work: Any, *, on_success: Any, on_failure: Any) -> None:
        self.names.append(name)
        try:
            result = work()
        except Exception as error:  # noqa: BLE001 - delivered like the real one
            on_failure(name, error)
            return
        on_success(name, result)


def _host(wx_module: Any, *, url: str = _KEXP_URL, safe: bool = False, playing: bool = True) -> Any:
    said: list[str] = []
    shown: list[Any] = []
    copied: list[str] = []
    station = SimpleNamespace(name="KEXP", stream_url=url) if playing else None

    def show_modal(dialog: Any, _title: str) -> int:
        shown.append(dialog)
        return 0

    return SimpleNamespace(
        frame=None,
        _wx=wx_module,
        _announce=said.append,
        said=said,
        shown=shown,
        copied=copied,
        _safe_mode=safe,
        _task_manager=_Tasks(),
        _radio_controller=SimpleNamespace(state=SimpleNamespace(station=station)),
        _show_modal_dialog=show_modal,
        _copy_to_clipboard=lambda text: copied.append(text) or True,
    )


@pytest.fixture
def requests(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    asked: list[str] = []
    payload = (_FIXTURES / "kexp.json").read_text(encoding="utf-8")
    monkeypatch.setattr(station_playlist, "_fetch", lambda url: asked.append(url) or payload)
    return asked


def test_nothing_playing_says_so_and_asks_nothing(wx_session_app, requests) -> None:
    import wx

    host = _host(wx, playing=False)
    commands.open_station_playlist(host)
    assert host.said == [commands.NOTHING_PLAYING]
    assert requests == []


def test_a_station_with_no_playlist_is_told_in_one_sentence(wx_session_app, requests) -> None:
    import wx

    host = _host(wx, url="https://example.com/stream.mp3")
    commands.open_station_playlist(host)
    assert host.said == [station_playlist.NO_PLAYLIST]
    assert requests == [] and host._task_manager.names == []


def test_safe_mode_refuses_and_asks_nothing(wx_session_app, requests) -> None:
    import wx

    host = _host(wx, safe=True)
    commands.open_station_playlist(host)
    assert host.said == [commands.SAFE_MODE]
    assert requests == []


def test_the_list_opens_newest_first_with_where_it_came_from(
    wx_session_app, wx_call_after, requests
) -> None:
    import wx

    wx_call_after()
    host = _host(wx)
    commands.open_station_playlist(host)

    assert host._task_manager.names == ["radio-station-playlist"]
    assert "ordering=-airdate" in requests[0]
    assert host.said == ["Asking KEXP for the playlist..."]
    [dialog] = host.shown
    assert dialog.GetTitle() == "What the Station Played: KEXP"
    songs = dialog.FindWindowByName("Songs")
    assert songs.GetCount() == 2
    assert songs.GetString(0).startswith("Telegram by Eggshells, started ")
    source = dialog.FindWindowByName("Where this list comes from")
    assert "KEXP" in source.GetValue() and "not what Quill Radio heard" in source.GetValue()


def test_an_empty_answer_says_so_and_opens_nothing(
    wx_session_app, wx_call_after, monkeypatch
) -> None:
    import wx

    wx_call_after()
    monkeypatch.setattr(station_playlist, "_fetch", lambda _url: '{"results": []}')
    host = _host(wx)
    commands.open_station_playlist(host)
    assert host.shown == []
    assert host.said[-1] == "KEXP lists no recent songs for this station right now."


def test_a_failure_is_one_plain_sentence(wx_session_app, wx_call_after, monkeypatch) -> None:
    import wx

    wx_call_after()

    def offline(_url: str) -> str:
        raise station_playlist.StationPlaylistError("offline")

    monkeypatch.setattr(station_playlist, "_fetch", offline)
    host = _host(wx)
    commands.open_station_playlist(host)
    assert host.shown == []
    assert host.said[-1] == "Could not get the playlist from KEXP. Try again in a moment."


def _dialog(wx_session_app: Any, **overrides: Any) -> tuple[StationPlaylistDialog, list[str]]:
    said: list[str] = []
    songs = (
        station_playlist.PlayedSong("Telegram", "Eggshells", is_current=True),
        station_playlist.PlayedSong("I Will Survive", "Gloria Gaynor", when_label="9 minutes ago"),
    )
    source = station_playlist.match_source(_KEXP_URL)
    assert source is not None
    options: dict[str, Any] = {
        "playlist": station_playlist.StationPlaylist(source=source, songs=songs),
        "station_name": "KEXP",
        "show_modal_dialog": lambda *_a: 0,
        "copy_to_clipboard": lambda _t: True,
        "announce": said.append,
        "send_to_clip_library": lambda _t, _n: True,
    }
    options.update(overrides)
    return StationPlaylistDialog(None, **options), said


def test_copy_and_clip_library_use_the_display_line(wx_session_app) -> None:
    copied: list[str] = []
    kept: list[tuple[str, str]] = []
    dialog, said = _dialog(
        wx_session_app,
        copy_to_clipboard=lambda text: copied.append(text) or True,
        send_to_clip_library=lambda text, name: kept.append((text, name)) or True,
    )
    try:
        dialog.on_copy()
        dialog.on_clip()
        assert copied == ["Telegram by Eggshells"]
        assert kept == [("Telegram by Eggshells", "KEXP")]
        assert said == [
            "Copied Telegram by Eggshells.",
            "Kept Telegram by Eggshells in the Clip Library.",
        ]
    finally:
        dialog.dialog.Destroy()


def test_song_details_and_lyrics_reuse_song_history_lookups(wx_session_app) -> None:
    asked: list[Any] = []
    dialog, _said = _dialog(
        wx_session_app,
        request_facts=lambda song, show: (asked.append(song), show("From 2025.")),
        request_lyrics=asked.append,
    )
    try:
        dialog.songs.SetSelection(1)
        dialog.on_song_facts()
        dialog.on_lyrics()
        assert [(s.title, s.artist) for s in asked] == [
            ("I Will Survive", "Gloria Gaynor"),
            ("I Will Survive", "Gloria Gaynor"),
        ]
        assert dialog.facts.GetValue() == "From 2025."
    finally:
        dialog.dialog.Destroy()


def test_row_labels_say_when() -> None:
    started = datetime(2026, 11, 8, 2, 42, tzinfo=UTC)
    local = started.astimezone().strftime("%H:%M")
    assert describe_played(station_playlist.PlayedSong("A", "B", started_at=started)) == (
        f"A by B, started {local}"
    )
    assert describe_played(station_playlist.PlayedSong("A", is_current=True)) == "A, playing now"
    assert describe_played(station_playlist.PlayedSong("A", "B", when_label="2 hours ago")) == (
        "A by B, 2 hours ago"
    )
    play = as_song_play(station_playlist.PlayedSong("A", "B", started_at=started))
    assert (play.title, play.artist, play.last_heard) == ("A", "B", started.isoformat())


def test_the_command_has_a_key_no_other_radio_command_claims() -> None:
    radio = app_keymaps.APP_KEYMAPS["radio"]
    assert radio["radio.station_playlist"] == "Alt+Shift+H"
    claimants = [cmd for cmd, key in radio.items() if key.lower() == "alt+shift+h"]
    assert claimants == ["radio.station_playlist"]


def test_the_palette_runs_the_command(monkeypatch) -> None:
    from quill.ui.radio import (
        lineups_commands,
        local_media_commands,
        palette_commands,
        transport_keys,
    )

    for module, name in (
        (local_media_commands, "register"),
        (lineups_commands, "register"),
        (transport_keys, "register_commands"),
    ):
        monkeypatch.setattr(module, name, lambda *a, **k: None)
    called: list[Any] = []
    monkeypatch.setattr(commands, "open_station_playlist", called.append)
    registered: dict[str, Any] = {}

    class _Commands:
        def try_register(self, command_id: str, _title: str, handler: Any, *_a, **_k) -> None:
            registered[command_id] = handler

    class _Host:
        commands = _Commands()

        def __getattr__(self, name: str) -> Any:
            return lambda *a, **k: ""

    host = _Host()
    palette_commands.register_radio_commands(host)
    registered["radio.station_playlist"]()
    assert called == [host]


def test_the_window_answers_f1() -> None:
    title = "What the Station Played: KEXP"
    assert radio_help.is_known_title(title)
    assert "Song History" in radio_help.purpose_for_title(title)
