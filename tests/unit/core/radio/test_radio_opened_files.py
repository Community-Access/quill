"""Files Windows hands Quill Radio: the command line, the hand-off, the Opened files list.

Everything here is :mod:`quill.core.radio.opened_files` -- wx-free, with the
second process's queue replaced by a list and the disk by ``tmp_path``.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from quill.core.radio import local_media
from quill.core.radio import opened_files as of
from quill.core.radio.local_media import LocalMediaLibrary
from quill.core.radio.play_queue import REPEAT_ALL, REPEAT_OFF

# -- the command line ---------------------------------------------------------------


def test_files_on_the_command_line_come_back_absolute_and_in_order(tmp_path: Path) -> None:
    request = of.parse_argv(["b.mp3", str(tmp_path / "a.flac")], cwd=str(tmp_path))
    assert request.paths == (str(tmp_path / "b.mp3"), str(tmp_path / "a.flac"))
    assert request.enqueue is False


def test_switches_are_never_files_and_enqueue_is_noted(tmp_path: Path) -> None:
    request = of.parse_argv(["--safe-mode", "--enqueue", '"song.mp3"', ""], cwd=str(tmp_path))
    assert request.paths == (str(tmp_path / "song.mp3"),)
    assert request.enqueue is True


def test_no_files_is_an_empty_request() -> None:
    assert of.parse_argv([]).paths == ()
    assert of.parse_argv(["--safe-mode"]).paths == ()


# -- a second launch hands its files over ------------------------------------------------


def _recorder() -> tuple[list[tuple[object, str, str]], object]:
    calls: list[tuple[object, str, str]] = []

    def enqueue(path: object, *, action: str = "open", slot: str = "") -> None:
        calls.append((path, action, slot))

    return calls, enqueue


def test_a_bare_second_launch_still_asks_the_window_forward() -> None:
    calls, enqueue = _recorder()
    assert of.hand_over([], slot="radio", enqueue=enqueue) == 0
    assert calls == [(None, "open", "radio")]


def test_a_second_launch_hands_over_every_file_to_play(tmp_path: Path) -> None:
    calls, enqueue = _recorder()
    count = of.hand_over(["a.mp3", "b.mp3"], slot="radio", enqueue=enqueue, cwd=str(tmp_path))
    assert count == 2
    assert calls == [
        (tmp_path / "a.mp3", of.PLAY, "radio"),
        (tmp_path / "b.mp3", of.PLAY, "radio"),
    ]


def test_the_add_verb_hands_over_files_to_add(tmp_path: Path) -> None:
    calls, enqueue = _recorder()
    of.hand_over(["--enqueue", "a.mp3"], slot="radio", enqueue=enqueue, cwd=str(tmp_path))
    assert calls == [(tmp_path / "a.mp3", of.ENQUEUE, "radio")]


def test_the_real_queue_carries_the_action_through(quill_data_dir: Path, tmp_path: Path) -> None:
    from quill.core.ipc import drain_open_requests

    of.hand_over(["--enqueue", "a.mp3"], slot="radio-test", cwd=str(tmp_path))
    of.hand_over(["b.mp3"], slot="radio-test", cwd=str(tmp_path))
    of.hand_over([], slot="radio-test")
    show, play, add = of.split_requests(drain_open_requests(slot="radio-test"))
    assert show is True
    assert play == [str(tmp_path / "b.mp3")]
    assert add == [str(tmp_path / "a.mp3")]


def test_split_requests_sorts_show_play_and_add() -> None:
    requests = [
        None,
        SimpleNamespace(path=Path("x.mp3"), action="play"),
        SimpleNamespace(path=Path("y.mp3"), action="ENQUEUE"),
        SimpleNamespace(path=Path("z.mp3"), action="open"),
    ]
    show, play, add = of.split_requests(requests)
    assert show is True
    assert play == ["x.mp3", "z.mp3"]
    assert add == ["y.mp3"]


# -- what was named --------------------------------------------------------------------


def _touch(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x")
    return path


def test_expand_sorts_files_folders_playlists_and_trouble(tmp_path: Path) -> None:
    song = _touch(tmp_path / "song.mp3")
    album = tmp_path / "Album"
    _touch(album / "track 10.flac")
    _touch(album / "track 2.flac")
    _touch(album / "cover.jpg")
    empty = tmp_path / "Empty"
    empty.mkdir()
    playlist = _touch(tmp_path / "mix.m3u8")
    report = _touch(tmp_path / "report.docx")
    gone = tmp_path / "gone.mp3"
    expanded = of.expand([str(p) for p in (song, album, empty, playlist, report, gone, song)])
    assert expanded.media == [
        str(song),
        str(album / "track 2.flac"),
        str(album / "track 10.flac"),
    ], "a folder plays in reading order, and a file named twice plays once"
    assert expanded.playlists == [str(playlist)]
    assert expanded.unsupported == [str(report)]
    assert expanded.missing == [str(gone)]
    assert expanded.empty_folders == [str(empty)]


def test_trouble_is_one_plain_sentence_per_kind() -> None:
    assert of.problem_sentence(of.Expanded()) == ""
    one = of.Expanded(missing=[r"E:\Music\a.mp3"], unsupported=[r"E:\notes.docx"])
    assert of.problem_sentence(one) == (
        "Quill Radio could not find a.mp3. Quill Radio cannot play notes.docx."
    )
    many = of.Expanded(missing=["a", "b"], unsupported=["c", "d", "e"], empty_folders=[r"E:\X"])
    assert of.problem_sentence(many) == (
        "Quill Radio could not find 2 of the files. "
        "Quill Radio cannot play 3 of the files. There is no music or video in X."
    )


# -- which files belong together ------------------------------------------------------------


def test_files_close_together_are_one_selection() -> None:
    batch = of.OpenBatch()
    assert not batch.joins(100.0), "the first ever hand-off starts a list"
    batch.touch(100.0)
    assert batch.joins(100.0 + of.BATCH_SECONDS)
    batch.touch(102.0)
    assert batch.joins(104.5), "the window slides with each file"
    assert not batch.joins(102.0 + of.BATCH_SECONDS + 0.1)


# -- the Opened files list -----------------------------------------------------------------


def test_the_first_opened_files_make_a_temporary_list() -> None:
    library = LocalMediaLibrary()
    playlist, ids = of.replace_opened(library, ["a.mp3", "b.mp3"], now=1.0)
    assert playlist.name == of.OPENED_FILES_NAME
    assert playlist.temporary is True
    assert [item.path for item in playlist.items] == ["a.mp3", "b.mp3"]
    assert ids == playlist.ids()
    assert of.opened_playlist(library) is playlist


def test_opening_again_replaces_the_list_and_starts_it_afresh() -> None:
    library = LocalMediaLibrary()
    playlist, _ids = of.replace_opened(library, ["a.mp3", "b.mp3"])
    playlist.shuffle, playlist.repeat, playlist.last_item_id = True, REPEAT_ALL, 2
    again, ids = of.replace_opened(library, ["c.mp3"])
    assert again is playlist and len(library.playlists) == 1
    assert [item.path for item in again.items] == ["c.mp3"]
    assert ids == again.ids()
    assert (again.shuffle, again.repeat, again.last_item_id) == (False, REPEAT_OFF, 0)


def test_a_saved_list_is_never_replaced() -> None:
    library = LocalMediaLibrary()
    first, _ids = of.replace_opened(library, ["a.mp3"])
    first.temporary = False  # Save as Playlist
    first.name = "Road Trip"
    second, _ids = of.replace_opened(library, ["b.mp3"])
    assert second is not first
    assert [item.path for item in first.items] == ["a.mp3"]
    assert second.name == of.OPENED_FILES_NAME


def test_a_saved_playlist_called_opened_files_is_left_alone() -> None:
    library = LocalMediaLibrary()
    library.add_playlist(of.OPENED_FILES_NAME)
    playlist, _ids = of.replace_opened(library, ["a.mp3"])
    assert playlist.name == f"{of.OPENED_FILES_NAME} 2"


def test_append_adds_to_the_end_and_skips_what_is_there() -> None:
    library = LocalMediaLibrary()
    of.replace_opened(library, ["a.mp3"])
    playlist, ids = of.append_opened(library, ["A.MP3", "b.mp3"])
    assert [item.path for item in playlist.items] == ["a.mp3", "b.mp3"]
    assert ids == [playlist.items[1].id]


def test_an_imported_playlist_is_found_again_rather_than_copied() -> None:
    library = LocalMediaLibrary()
    mix = library.add_playlist("mix")
    for path in ("a.mp3", "b.mp3"):
        mix.items.append(mix.make_item(path))
    assert of.find_imported(library, "Mix", ["A.mp3", "b.mp3"]) is mix
    assert of.find_imported(library, "mix", ["b.mp3", "a.mp3"]) is None
    assert of.find_imported(library, "other", ["a.mp3", "b.mp3"]) is None


def test_temporary_survives_a_save_and_is_said_in_the_summary(tmp_path: Path) -> None:
    library = LocalMediaLibrary()
    playlist, _ids = of.replace_opened(library, [str(_touch(tmp_path / "a.mp3"))])
    reread = local_media.parse(local_media.serialize(library))
    assert reread.playlists[0].temporary is True
    assert local_media.summary(reread.playlists[0]).endswith(", not saved")
    playlist.temporary = False
    assert "temporary" not in local_media.serialize(library)["playlists"][0]  # type: ignore[index]
