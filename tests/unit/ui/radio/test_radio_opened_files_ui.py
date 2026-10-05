"""Files from File Explorer, in the running Quill Radio: played, listed, said once.

A fake player stands in for mpv (the same shape as the Local Media playback
tests); the library, the Opened files list, the queue and the playlist reader
are real. ``local_media_ui._submit`` runs inline when the app has no task
manager, so each hand-off finishes before the test looks.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from quill.core.radio import opened_files as of
from quill.core.radio.local_media import LocalMediaLibrary
from quill.ui.radio import local_media_manage as manage
from quill.ui.radio import local_media_playback as playback
from quill.ui.radio import local_media_ui as ui
from quill.ui.radio import opened_files_ui as opened
from quill.ui.radio.playback_state import RadioPlayerState


class _Player:
    def __init__(self) -> None:
        self._state = SimpleNamespace(state=RadioPlayerState.STOPPED, station=None)
        self.played: list[str] = []

    @property
    def state(self) -> SimpleNamespace:
        return self._state

    def play_station(self, station: object) -> None:
        self.played.append(Path(str(getattr(station, "stream_url", ""))).name)
        self._state = SimpleNamespace(state=RadioPlayerState.PLAYING, station=station)

    def stop(self) -> None:
        self._state = SimpleNamespace(state=RadioPlayerState.STOPPED, station=self._state.station)


class _App:
    def __init__(self) -> None:
        self._radio_controller = _Player()
        self._radio_history = SimpleNamespace()
        self._local_media_library = LocalMediaLibrary()
        self.said: list[str] = []
        self.forward = 0

    def _announce(self, text: str, *_args: object, **_kwargs: object) -> None:
        self.said.append(text)

    def _foreground_window(self) -> None:
        self.forward += 1


@pytest.fixture
def app(quill_data_dir: Path) -> _App:
    made = _App()
    playback.remember_app(made)
    return made


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    now = SimpleNamespace(value=1000.0)
    monkeypatch.setattr(opened.time, "monotonic", lambda: now.value)
    return now


def _songs(folder: Path, *names: str) -> list[str]:
    folder.mkdir(parents=True, exist_ok=True)
    paths = []
    for name in names:
        path = folder / name
        path.write_bytes(b"x")
        paths.append(str(path))
    return paths


def _opened_list(app: _App) -> Any:
    playlist = of.opened_playlist(app._local_media_library)
    assert playlist is not None
    return playlist


def test_one_file_plays_and_is_said_once(app: _App, clock: SimpleNamespace, tmp_path) -> None:
    (song,) = _songs(tmp_path, "my_song.mp3")
    opened.open_paths(app, [song])
    assert app._radio_controller.played == ["my_song.mp3"]
    assert app.said == ["Playing my song."]
    assert _opened_list(app).temporary


def test_several_files_make_a_list_that_next_walks(app: _App, clock, tmp_path) -> None:
    files = _songs(tmp_path, "a.mp3", "b.mp3", "c.mp3")
    opened.open_paths(app, files)
    assert app.said == ["Playing a, the first of 3 in Opened files."]
    assert playback.step(app, 1)
    assert playback.step(app, 1)
    assert app._radio_controller.played == ["a.mp3", "b.mp3", "c.mp3"]
    assert playback.step(app, -1)
    assert app._radio_controller.played[-1] == "b.mp3"


def test_explorer_selection_arriving_one_by_one_is_one_list(app: _App, clock, tmp_path) -> None:
    """Explorer starts the app once per selected file, a moment apart."""
    files = _songs(tmp_path, "a.mp3", "b.mp3", "c.mp3")
    for index, path in enumerate(files):
        clock.value = 1000.0 + index * 0.7
        opened.open_paths(app, [path])
    assert [item.file_name for item in _opened_list(app).items] == ["a.mp3", "b.mp3", "c.mp3"]
    assert app._radio_controller.played == ["a.mp3"], "the rest join; nothing restarts"
    assert app.said == ["Playing a."], "what is playing is said once"


def test_opening_later_replaces_the_list(app: _App, clock, tmp_path) -> None:
    first = _songs(tmp_path, "a.mp3", "b.mp3")
    opened.open_paths(app, first)
    clock.value += of.BATCH_SECONDS + 5
    (later,) = _songs(tmp_path, "z.mp3")
    opened.open_paths(app, [later])
    assert [item.file_name for item in _opened_list(app).items] == ["z.mp3"]
    assert len(app._local_media_library.playlists) == 1
    assert app._radio_controller.played[-1] == "z.mp3"


def test_a_folder_plays_like_add_a_folder(app: _App, clock, tmp_path) -> None:
    album = tmp_path / "Album"
    _songs(album, "track 10.mp3", "track 2.mp3", "notes.txt")
    opened.open_paths(app, [str(album)])
    names = [item.file_name for item in _opened_list(app).items]
    assert names == ["track 2.mp3", "track 10.mp3"]


def test_a_missing_or_unsupported_file_is_one_plain_sentence(app: _App, clock, tmp_path) -> None:
    notes = tmp_path / "notes.docx"
    notes.write_bytes(b"x")
    opened.open_paths(app, [str(tmp_path / "gone.mp3")])
    assert app.said == ["Quill Radio could not find gone.mp3."]
    opened.open_paths(app, [str(notes)])
    assert app.said[-1] == "Quill Radio cannot play notes.docx."
    assert app._radio_controller.played == []


def test_a_playlist_file_is_imported_once_and_played(app: _App, clock, tmp_path) -> None:
    _songs(tmp_path, "a.mp3", "b.mp3")
    m3u = tmp_path / "Mix.m3u8"
    m3u.write_text("#EXTM3U\na.mp3\nb.mp3\n", encoding="utf-8")
    opened.open_paths(app, [str(m3u)])
    opened.open_paths(app, [str(m3u)])
    lists = app._local_media_library.playlists
    assert [p.name for p in lists] == ["Mix"], "opened twice, imported once"
    assert not lists[0].temporary
    assert app._radio_controller.played == ["a.mp3", "a.mp3"]
    assert app.said[-1] == "Playing Mix. a."


def test_add_while_the_list_plays_goes_on_the_end(app: _App, clock, tmp_path) -> None:
    files = _songs(tmp_path, "a.mp3", "b.mp3")
    opened.open_paths(app, files[:1])
    opened.open_paths(app, files[1:], enqueue=True)
    assert [item.file_name for item in _opened_list(app).items] == ["a.mp3", "b.mp3"]
    assert app._radio_controller.played == ["a.mp3"]
    assert app.said[-1] == "Added 1 file to the end of the list playing now."


def test_add_with_nothing_playing_starts_it(app: _App, clock, tmp_path) -> None:
    (song,) = _songs(tmp_path, "a.mp3")
    opened.open_paths(app, [song], enqueue=True)
    assert app._radio_controller.played == ["a.mp3"]


def test_add_never_replaces_the_list(app: _App, clock, tmp_path) -> None:
    files = _songs(tmp_path, "a.mp3", "b.mp3")
    opened.open_paths(app, files[:1])
    app._radio_controller.stop()
    clock.value += 60
    opened.open_paths(app, files[1:], enqueue=True)
    assert [item.file_name for item in _opened_list(app).items] == ["a.mp3", "b.mp3"]


def test_the_ipc_queue_plays_files_and_a_bare_launch_comes_forward(app: _App, clock, tmp_path):
    (song,) = _songs(tmp_path, "a.mp3")
    queued: list[list[object]] = [
        [SimpleNamespace(path=Path(song), action="play")],
        [None],
        [],
    ]
    opened.drain_requests(app, "radio", drain=lambda slot: queued.pop(0))
    assert app._radio_controller.played == ["a.mp3"]
    assert app.forward == 0, "files play where the person is; the window stays put"
    opened.drain_requests(app, "radio", drain=lambda slot: queued.pop(0))
    assert app.forward == 1
    opened.drain_requests(app, "radio", drain=lambda slot: queued.pop(0))
    assert app.forward == 1


def test_launch_files_play_once_the_window_is_up(app: _App, clock, tmp_path) -> None:
    (song,) = _songs(tmp_path, "a.mp3")
    opened.open_launch_files(app, of.parse_argv([song]))
    opened.open_launch_files(app, of.parse_argv([]))
    assert app._radio_controller.played == ["a.mp3"]


def test_save_as_playlist_keeps_the_list(app: _App, clock, tmp_path, monkeypatch) -> None:
    album = tmp_path / "Abbey Road"
    files = _songs(album, "a.mp3", "b.mp3")
    opened.open_paths(app, files)
    playlist = _opened_list(app)
    asked: list[str] = []

    def answer(_host, _prompt, _title, value=""):
        asked.append(value)
        return ""

    monkeypatch.setattr(ui, "ask_text", answer)
    assert manage.save_opened(app, playlist.id)
    assert asked == ["Abbey Road"], "the folder's name is offered"
    assert playlist.name == "Abbey Road" and not playlist.temporary
    assert app.said[-1].startswith("Saved as Abbey Road.")
    clock.value += 60
    (later,) = _songs(tmp_path, "z.mp3")
    opened.open_paths(app, [later])
    assert [p.name for p in app._local_media_library.playlists] == ["Abbey Road", "Opened files"]
    assert not manage.save_opened(app, playlist.id), "a saved list says it is saved"


def test_renaming_the_opened_list_keeps_it_too(app: _App, clock, tmp_path, monkeypatch) -> None:
    opened.open_paths(app, _songs(tmp_path, "a.mp3"))
    playlist = _opened_list(app)
    monkeypatch.setattr(ui, "ask_text", lambda *_a, **_k: "Keepers")
    assert manage.rename_playlist(app, playlist.id)
    assert not playlist.temporary


def test_the_browse_menu_offers_save_on_the_opened_list_only() -> None:
    from quill.core.radio import browse_local_media as rows

    library = LocalMediaLibrary()
    temporary, _ids = of.replace_opened(library, ["a.mp3"])
    saved = library.add_playlist("Saved")
    verbs = [a.id for a in rows.menu_actions(rows.PLAYLIST, playlist=temporary)]
    assert rows.SAVE_OPENED in verbs and rows.RENAME not in verbs
    verbs = [a.id for a in rows.menu_actions(rows.PLAYLIST, playlist=saved)]
    assert rows.RENAME in verbs and rows.SAVE_OPENED not in verbs
