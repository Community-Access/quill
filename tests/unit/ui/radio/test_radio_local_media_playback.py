"""Playing a Local Media playlist: what follows what, and what is said.

A fake player stands in for mpv: it records what it was asked to play and
reports a state like the real controller does. Everything else is real -- the
library, the shared PlayQueue, the edits, the undo slot.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from quill.core.radio.local_media import LocalMediaLibrary
from quill.ui import undo_last_ui
from quill.ui.radio import local_media_edit_ui as edit_ui
from quill.ui.radio import local_media_playback as playback
from quill.ui.radio import local_media_ui as ui
from quill.ui.radio.playback_state import RadioPlayerState


class _Player:
    """Just enough of RadioPlayerController for the playlist to drive."""

    def __init__(self) -> None:
        self._state = SimpleNamespace(state=RadioPlayerState.STOPPED, station=None)
        self.played: list[str] = []

    @property
    def state(self) -> SimpleNamespace:
        return self._state

    def play_station(self, station: object) -> None:
        self.played.append(str(getattr(station, "stream_url", "")))
        self._state = SimpleNamespace(state=RadioPlayerState.PLAYING, station=station)

    def stop(self) -> None:
        self._state = SimpleNamespace(state=RadioPlayerState.STOPPED, station=self._state.station)

    def toggle_play_pause(self) -> None:
        paused = self._state.state is RadioPlayerState.PAUSED
        new = RadioPlayerState.PLAYING if paused else RadioPlayerState.PAUSED
        self._state = SimpleNamespace(state=new, station=self._state.station)


class _Host:
    def __init__(self, library: LocalMediaLibrary) -> None:
        self._radio_controller = _Player()
        self._radio_history = SimpleNamespace()
        self._local_media_library = library
        self.said: list[str] = []

    def _announce(self, text: str, *_args: object, **_kwargs: object) -> None:
        self.said.append(text)


@pytest.fixture
def host(tmp_path: Path, quill_data_dir: Path) -> _Host:
    library = LocalMediaLibrary()
    playlist = library.add_playlist("Road Trip")
    for index in range(1, 5):
        path = tmp_path / f"song{index}.mp3"
        path.write_bytes(b"x")
        playlist.items.append(playlist.make_item(path, title=f"Song {index}"))
    made = _Host(library)
    playback.remember_app(made)
    return made


def _names(host: _Host) -> list[str]:
    return [Path(url).stem for url in host._radio_controller.played]


def _finish(host: _Host) -> bool:
    return playback.handle_finished(host._radio_controller)


def _playlist(host: _Host):
    return host._local_media_library.playlists[0]


def test_enter_plays_from_an_item_and_a_natural_end_carries_on(host: _Host) -> None:
    playlist = _playlist(host)
    assert playback.play_item(host, playlist.id, playlist.items[1].id)
    assert host.said[-1] == "Playing Song 2, 2 of 4."
    assert _finish(host)
    assert _finish(host)
    assert _names(host) == ["song2", "song3", "song4"]
    assert not _finish(host), "the end of the playlist stops"
    assert host.said[-1] == "That was the end of Road Trip."
    assert playlist.last_item_id == playlist.items[3].id, "Continue Where I Left Off"


def test_next_and_previous_stop_at_the_ends_unless_repeating(host: _Host) -> None:
    playlist = _playlist(host)
    playback.play_item(host, playlist.id, playlist.items[0].id)
    assert playback.step(host, -1)
    assert host.said[-1] == "That is the first item in Road Trip."
    playback.play_item(host, playlist.id, playlist.items[3].id)
    playback.step(host, 1)
    assert host.said[-1] == "That is the last item in Road Trip."
    playlist.repeat = "all"
    playback.step(host, 1)
    assert _names(host)[-1] == "song1", "repeat all wraps"


def test_repeat_one_repeats_on_a_natural_end_but_next_moves_on(host: _Host) -> None:
    playlist = _playlist(host)
    playlist.repeat = "one"
    playback.play_item(host, playlist.id, playlist.items[0].id)
    _finish(host)
    assert _names(host) == ["song1", "song1"]
    playback.step(host, 1)
    assert _names(host)[-1] == "song2"


def test_shuffle_is_a_stable_order_and_previous_goes_back(host: _Host, monkeypatch) -> None:
    import random

    playlist = _playlist(host)
    monkeypatch.setattr(random, "shuffle", lambda rows: rows.reverse())
    playback.play_playlist(host, playlist.id, shuffle=True)
    assert _names(host) == ["song4"], "shuffle starts at the first of its order"
    _finish(host)
    _finish(host)
    assert _names(host) == ["song4", "song3", "song2"]
    playback.step(host, -1)
    assert _names(host)[-1] == "song3", "previous is the exact inverse of next"
    edit_ui.move(host, playlist, [0], 1)  # an edit while shuffled keeps the order
    _finish(host)
    assert _names(host)[-1] == "song2"


def test_play_next_and_up_next_come_before_the_playlist_resumes(host: _Host) -> None:
    playlist = _playlist(host)
    ids = [item.id for item in playlist.items]
    playback.play_item(host, playlist.id, ids[0])
    playback.add_up_next(host, playlist.id, [ids[3]])
    playback.play_next(host, playlist.id, [ids[2]])
    assert host.said[-1] == "Will play next."
    _finish(host)
    _finish(host)
    _finish(host)
    assert _names(host) == ["song1", "song3", "song4", "song2"]


def test_a_missing_file_is_skipped_and_said(host: _Host) -> None:
    playlist = _playlist(host)
    Path(playlist.items[1].path).unlink()
    playback.play_item(host, playlist.id, playlist.items[0].id)
    _finish(host)
    assert _names(host) == ["song1", "song3"]
    assert host.said[-1].startswith("Skipped 1 missing. Song 3")


def test_stop_after_this_item_fires_once(host: _Host) -> None:
    playlist = _playlist(host)
    playback.play_item(host, playlist.id, playlist.items[0].id)
    playback.toggle_stop_after(host)
    assert not _finish(host)
    assert host.said[-1] == "Stopped after that item, as you asked."
    playback.play_item(host, playlist.id, playlist.items[0].id)
    assert _finish(host), "a one-shot: it cleared itself"


def test_a_file_played_from_browse_finds_its_playlist(host: _Host) -> None:
    from quill.core.radio.browse_local_media import browse_local_playlist

    playlist = _playlist(host)
    leaves = browse_local_playlist(
        [playlist.id], safe_mode=False, library=host._local_media_library
    )
    host._radio_controller.play_station(leaves[2].station)  # Enter in the tree
    assert _finish(host)
    assert _names(host) == ["song3", "song4"]
    assert playback.where_suffix(host) == "4 of 4 in Road Trip"


def test_something_else_playing_is_left_alone(host: _Host) -> None:
    host._radio_controller.play_station(SimpleNamespace(stream_url="http://kfi", source=""))
    assert not _finish(host)
    assert not playback.step(host, 1), "next belongs to the chapter keys then"


def test_moves_say_the_new_position_and_undo_puts_it_back(host: _Host, tmp_path: Path) -> None:
    undo_last_ui._slot = None
    undo_last_ui.activate(tmp_path)
    try:
        playlist = _playlist(host)
        rows = edit_ui.move(host, playlist, [3], -1)
        assert rows == [2]
        assert host.said[-1] == "Moved to 3 of 4."
        assert edit_ui.move(host, playlist, [0], -1) == [0]
        assert host.said[-1] == "Already at the top."
        undo_last_ui.slot().take().undo()
        assert [item.title for item in playlist.items] == ["Song 1", "Song 2", "Song 3", "Song 4"]
        landing = edit_ui.remove_rows(host, playlist, [1, 2])
        assert landing == 1
        assert "still on your computer" in host.said[-1]
        undo_last_ui.slot().take().undo()
        assert [item.title for item in playlist.items] == ["Song 1", "Song 2", "Song 3", "Song 4"]
    finally:
        undo_last_ui._slot = None


def test_cut_marks_and_paste_moves_before_or_after(host: _Host) -> None:
    playlist = _playlist(host)
    edit_ui.cut_items(host, playlist, [0])
    assert [item.title for item in playlist.items][0] == "Song 1", "cut never removes"
    rows = edit_ui.paste(host, playlist, 4)  # Paste After the last item
    assert [item.title for item in playlist.items] == ["Song 2", "Song 3", "Song 4", "Song 1"]
    assert rows == [3] and host.said[-1] == "Moved to 4 of 4."
    edit_ui.copy_items(host, playlist, [0, 1])
    rows = edit_ui.paste(host, playlist, 1)
    assert [item.title for item in playlist.items][:4] == ["Song 2", "Song 2", "Song 3", "Song 3"]
    assert rows == [1, 2] and host.said[-1] == "Pasted 2 items to 2 of 6."


def test_the_summary_says_what_plays_and_how(host: _Host) -> None:
    playlist = _playlist(host)
    playback.play_item(host, playlist.id, playlist.items[2].id)
    playlist.shuffle = True
    sentence = playback.summary_sentence(host, playlist)
    assert sentence.startswith("Road Trip: 4 items.")
    assert "Playing 3 of 4: Song 3." in sentence
    assert sentence.endswith("Shuffle on. Repeat off.")
    assert ui.library(host) is host._local_media_library
