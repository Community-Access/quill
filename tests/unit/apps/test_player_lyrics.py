"""Quill Media Player's timed lyrics: Follow Playback, Current line, Say Current Line."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from quill.apps import player_lyrics
from quill.core.lyrics import lrclib
from quill.core.lyrics.lrclib import Lyrics
from quill.ui.media.lyrics_window import BEFORE_FIRST, BREAK, LyricsWindow

_SYNCED = "[00:01.00] First line\n[00:05.00] Second line\n[00:09.00]\n[00:12.00] Last line\n"


@pytest.fixture
def window(wx_app):
    import wx

    parent = wx.Frame(None)
    clock = {"ms": 0}
    said: list[str] = []
    win = LyricsWindow(
        parent,
        song="Song by Artist",
        lyrics=Lyrics(track="Song", artist="Artist", synced=_SYNCED, plain="First line"),
        position_ms=lambda: clock["ms"],
        announce=said.append,
    )
    win.clock = clock  # type: ignore[attr-defined]
    win.said = said  # type: ignore[attr-defined]
    yield win
    win.close()  # the window's own close path stops its clock
    parent.Destroy()


def _caret_line(win: LyricsWindow) -> int:
    ok, _col, line = win.text.PositionToXY(win.text.GetInsertionPoint())
    return line


def test_follow_on_moves_the_caret_to_the_line_being_sung(window) -> None:
    assert window.is_synced and window._follow.GetValue()
    window.clock["ms"] = 5_500

    assert window.tick() is True

    assert _caret_line(window) == 1
    assert window._current.GetValue() == "Second line"
    assert window.said == []  # nothing is spoken as lines change


def test_follow_off_holds_still_and_turning_it_on_catches_up(window) -> None:
    window.clock["ms"] = 1_500
    window.tick()
    window._follow.SetValue(False)

    window.clock["ms"] = 12_500
    window.tick()
    assert _caret_line(window) == 0  # held still
    assert window._current.GetValue() == "Last line"  # but the line is current

    window._follow.SetValue(True)
    window._catch_up()  # what EVT_CHECKBOX runs
    assert _caret_line(window) == 3


def test_before_the_words_and_in_a_break(window) -> None:
    window.tick()
    assert window._current.GetValue() == BEFORE_FIRST
    window.clock["ms"] = 10_000
    window.tick()
    assert window._current.GetValue() == BREAK


def test_say_current_line_speaks_only_when_asked(window) -> None:
    window.clock["ms"] = 5_000
    window.tick()
    assert window.said == []
    window.say_current_line()
    assert window.said == ["Second line"]


def test_words_without_timings_disable_follow_and_say_why(wx_app) -> None:
    import wx

    parent = wx.Frame(None)
    win = LyricsWindow(
        parent,
        song="Song by Artist",
        lyrics=Lyrics(plain="Only plain words\nhere"),
        position_ms=lambda: 0,
    )
    try:
        assert not win.is_synced
        assert win.text.GetValue() == "Only plain words\nhere"
        assert not win._follow.IsEnabled()
        assert not win._follow.GetValue()
        assert win.tick() is False
    finally:
        win.frame.Destroy()
        parent.Destroy()


# -- the command -------------------------------------------------------------------


class _Tasks:
    def submit(self, name: str, work: Any, *, on_success: Any, on_failure: Any) -> None:
        try:
            result = work()
        except Exception as error:  # noqa: BLE001
            on_failure(name, error)
            return
        on_success(name, result)


def _frame(wx_app: Any, path: Path | None) -> Any:
    import wx

    said: list[str] = []
    return SimpleNamespace(
        frame=wx.Frame(None),
        _announce=said.append,
        said=said,
        _safe_mode=False,
        _task_manager=_Tasks(),
        _player=SimpleNamespace(length_ms=lambda: 241_000, playhead_ms=lambda: 9_500),
        _playlist=[],
        _playlist_index=-1,
        _book_path=path,
        _lyrics_window=None,
    )


def test_open_lyrics_with_nothing_open(wx_app) -> None:
    frame = _frame(wx_app, None)
    try:
        player_lyrics.open_lyrics(frame)
        assert frame.said == [player_lyrics.NOTHING_OPEN]
    finally:
        frame.frame.Destroy()


def test_open_lyrics_uses_the_file_name_when_there_are_no_tags(wx_app, monkeypatch) -> None:
    lrclib.clear_cache()
    monkeypatch.setattr(lrclib, "MIN_INTERVAL_SECONDS", 0.0)
    urls: list[str] = []
    record = {"trackName": "Your Song", "artistName": "Elton John", "syncedLyrics": _SYNCED}
    monkeypatch.setattr(lrclib, "_fetch", lambda url: urls.append(url) or json.dumps([record]))
    frame = _frame(wx_app, Path("C:/music/Elton John - Your Song.mp3"))
    try:
        player_lyrics.open_lyrics(frame)

        window = frame._lyrics_window
        assert window is not None and window.is_synced
        assert frame.said == ["Looking up lyrics for Your Song by Elton John..."]
        # Opening ticked once already: the playhead is 9.5 s, in the break.
        assert window._current.GetValue() == BREAK
        assert "track_name=Your+Song" in urls[0]
    finally:
        if frame._lyrics_window is not None:
            frame._lyrics_window.close()
        frame.frame.Destroy()


def test_a_file_name_that_is_not_artist_dash_title_is_not_guessed(wx_app, monkeypatch) -> None:
    monkeypatch.setattr(lrclib, "_fetch", lambda url: pytest.fail("no request expected"))
    frame = _frame(wx_app, Path("C:/music/track07.mp3"))
    try:
        player_lyrics.open_lyrics(frame)
        assert frame.said == [player_lyrics.NO_TAGS]
    finally:
        frame.frame.Destroy()


def test_the_current_track_of_a_multi_file_book_is_the_one_looked_up() -> None:
    frame = SimpleNamespace(
        _playlist=[("One", ("track", ("C:/a/01.mp3", 0))), ("Two", ("track", ("C:/a/02.mp3", 0)))],
        _playlist_index=1,
        _book_path=Path("C:/a"),
    )
    assert player_lyrics.current_audio_path(frame) == Path("C:/a/02.mp3")
