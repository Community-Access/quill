"""Quill Radio's Lyrics command, behaviourally, with LRCLIB's _fetch faked.

Calls the handlers (lyrics_for_playing, lyrics_for_song) against a small host
double -- never a table of names: a command with a key, a label and a handler
can still have never once worked.
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any

import pytest

from quill.core.lyrics import lrclib
from quill.core.radio.song_history import SongPlay
from quill.ui.radio import lyrics_commands

_RECORD = {
    "trackName": "Your Song",
    "artistName": "Elton John",
    "albumName": "Elton John",
    "duration": 241,
    "instrumental": False,
    "plainLyrics": "It's a little bit funny\nthis feelin' inside",
    "syncedLyrics": "[00:09.06] It's a little bit funny",
}


class _Tasks:
    """Runs the work at once and answers on 'the UI thread', like TaskManager."""

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


def _host(wx_app: Any, *, playing: bool = True, title: str = "", safe: bool = False) -> Any:
    import wx

    frame = wx.Frame(None)
    said: list[str] = []
    station = SimpleNamespace(name="KXYZ") if playing else None
    return SimpleNamespace(
        frame=frame,
        _announce=said.append,
        said=said,
        _safe_mode=safe,
        _task_manager=_Tasks(),
        _radio_controller=SimpleNamespace(state=SimpleNamespace(station=station)),
        _radio_track_title=title,
        _radio_lyrics_window=None,
    )


@pytest.fixture(autouse=True)
def _fresh(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    lrclib.clear_cache()
    monkeypatch.setattr(lrclib, "MIN_INTERVAL_SECONDS", 0.0)
    requests: list[str] = []
    monkeypatch.setattr(lrclib, "_fetch", lambda url: requests.append(url) or json.dumps([_RECORD]))
    return requests


def _close(host: Any) -> None:
    window = host._radio_lyrics_window
    if window is not None:
        window.frame.Destroy()
    host.frame.Destroy()


def test_nothing_playing_says_so_and_asks_nothing(wx_app, _fresh) -> None:
    host = _host(wx_app, playing=False)
    try:
        lyrics_commands.lyrics_for_playing(host)
        assert host.said == [lyrics_commands.NOTHING_PLAYING]
        assert _fresh == []
    finally:
        _close(host)


def test_safe_mode_refuses_and_asks_nothing(wx_app, _fresh) -> None:
    host = _host(wx_app, title="Elton John - Your Song", safe=True)
    try:
        lyrics_commands.lyrics_for_playing(host)
        assert host.said == [lyrics_commands.SAFE_MODE]
        assert _fresh == []
    finally:
        _close(host)


def test_a_hit_opens_the_window_with_the_words_and_does_not_read_them(wx_app, _fresh) -> None:
    host = _host(wx_app, title='title="YOUR SONG",artist="Elton John",url="song_spot=x"')
    try:
        lyrics_commands.lyrics_for_playing(host)

        window = host._radio_lyrics_window
        assert window is not None
        assert window.text.GetValue() == _RECORD["plainLyrics"]
        assert window.frame.GetTitle() == "Lyrics: YOUR SONG by Elton John"
        assert not window.is_synced  # radio never follows: there is no position
        # Only the app's own news is spoken: not the title, not the words.
        assert host.said == ["Looking up lyrics for YOUR SONG by Elton John..."]
        assert host._task_manager.names == ["radio-lyrics"]
        assert "artist_name=Elton+John" in _fresh[0]
    finally:
        _close(host)


def test_a_miss_says_no_lyrics_found_and_opens_nothing(wx_app, monkeypatch) -> None:
    monkeypatch.setattr(lrclib, "_fetch", lambda url: "[]")
    host = _host(wx_app, title="Elton John - Your Song")
    try:
        lyrics_commands.lyrics_for_playing(host)
        assert host.said[-1] == "No lyrics found for Your Song."
        assert host._radio_lyrics_window is None
    finally:
        _close(host)


def test_an_instrumental_says_so_rather_than_not_found(wx_app, monkeypatch) -> None:
    record = {**_RECORD, "instrumental": True, "plainLyrics": None, "syncedLyrics": None}
    monkeypatch.setattr(lrclib, "_fetch", lambda url: json.dumps([record]))
    host = _host(wx_app, title="Elton John - Your Song")
    try:
        lyrics_commands.lyrics_for_playing(host)
        assert host.said[-1] == "Your Song is an instrumental; it has no lyrics."
        assert host._radio_lyrics_window is None
    finally:
        _close(host)


def test_a_network_failure_says_the_miss_sentence_not_the_error(wx_app, monkeypatch) -> None:
    def offline(url: str) -> str:
        raise lrclib.LyricsError("Could not reach LRCLIB: [Errno 11001] getaddrinfo failed")

    monkeypatch.setattr(lrclib, "_fetch", offline)
    host = _host(wx_app, title="Elton John - Your Song")
    try:
        lyrics_commands.lyrics_for_playing(host)
        assert host.said[-1] == "No lyrics found for Your Song."
        assert "getaddrinfo" not in " ".join(host.said)
    finally:
        _close(host)


def test_a_title_with_no_artist_is_not_guessed_at(wx_app, _fresh) -> None:
    host = _host(wx_app, title="Traffic and weather on the eights")
    try:
        lyrics_commands.lyrics_for_playing(host)
        assert host.said == [lyrics_commands.NO_ARTIST]
        assert _fresh == []
    finally:
        _close(host)


def test_song_history_with_nothing_selected_says_select_a_song(wx_app, _fresh) -> None:
    host = _host(wx_app)
    try:
        lyrics_commands.lyrics_for_song(host, None)
        assert host.said == ["Select a song first."]
        assert _fresh == []
    finally:
        _close(host)


def test_song_history_looks_up_a_song_heard_earlier_and_reuses_the_window(wx_app) -> None:
    host = _host(wx_app)
    try:
        lyrics_commands.lyrics_for_song(host, SongPlay(title="Your Song", artist="Elton John"))
        first = host._radio_lyrics_window
        lyrics_commands.lyrics_for_song(host, SongPlay(title="Your Song", artist="Elton John"))
        assert host._radio_lyrics_window is first  # one window, raised, not two
    finally:
        _close(host)


def test_closing_the_window_forgets_it(wx_app) -> None:
    host = _host(wx_app, title="Elton John - Your Song")
    try:
        lyrics_commands.lyrics_for_playing(host)
        window = host._radio_lyrics_window
        window._on_closed()
        assert host._radio_lyrics_window is None
        window.frame.Destroy()
    finally:
        host.frame.Destroy()
