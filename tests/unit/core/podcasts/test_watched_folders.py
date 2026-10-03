"""Watched folders (qc.md 5d, C2-02): the record, the scan, the settled rule."""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

from quill.core.podcasts import watched_folders as wf
from quill.core.podcasts.models import PodcastShow
from quill.core.podcasts.subscriptions import PodcastLibrary, load_library, save_library
from quill.core.podcasts.watched_folder_words import arrival_sentence, row_text


def _audio(path: Path, payload: bytes = b"ID3 audio bytes", *, age: float = 60.0) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    old = time.time() - age
    os.utime(path, (old, old))
    return path


def _look(library: PodcastLibrary, folder: wf.WatchedFolder, dest: Path):
    result = wf.plan(folder, wf.known_hashes(library), dest_root=dest)
    return result, wf.apply(library, folder, result)


def test_a_new_file_arrives_once_and_the_original_stays(tmp_path: Path) -> None:
    source = tmp_path / "Voice Memos"
    original = _audio(source / "Tuesday meeting.mp3")
    library = PodcastLibrary()
    folder = wf.WatchedFolder(path=str(source), min_seconds=0)
    library.watched_folders.append(folder)

    _result, added = _look(library, folder, tmp_path / "managed")
    assert len(added) == 1
    show, episode = added[0]
    assert show.is_local and show.title == "Voice Memos"
    assert original.exists(), "Leave it where it is must leave it"
    assert Path(episode.downloaded_path) != original
    assert Path(episode.downloaded_path).exists()

    _again, added_again = _look(library, folder, tmp_path / "managed")
    assert added_again == [], "a file already dealt with never arrives twice"


def test_the_same_recording_renamed_is_one_episode(tmp_path: Path) -> None:
    source = tmp_path / "Lectures"
    _audio(source / "one.mp3", b"same bytes")
    library = PodcastLibrary()
    folder = wf.WatchedFolder(path=str(source), min_seconds=0)
    library.watched_folders.append(folder)
    _look(library, folder, tmp_path / "managed")

    _audio(source / "one renamed.mp3", b"same bytes")
    result, added = _look(library, folder, tmp_path / "managed")
    assert added == []
    assert "one renamed.mp3" in result.seen


def test_a_file_still_being_written_waits(tmp_path: Path) -> None:
    source = tmp_path / "Recorder"
    _audio(source / "long.mp3", age=0.0)
    library = PodcastLibrary()
    folder = wf.WatchedFolder(path=str(source), min_seconds=0)
    result, added = _look(library, folder, tmp_path / "managed")
    assert added == [] and result.still_arriving == 1


def test_play_from_where_it_is_makes_no_copy(tmp_path: Path) -> None:
    source = tmp_path / "Books"
    original = _audio(source / "chapter.m4b")
    library = PodcastLibrary()
    folder = wf.WatchedFolder(path=str(source), original="reference", min_seconds=0)
    _r, added = _look(library, folder, tmp_path / "managed")
    assert Path(added[0][1].downloaded_path) == original
    assert not (tmp_path / "managed").exists()


def test_move_takes_the_original_into_casts_folder(tmp_path: Path) -> None:
    source = tmp_path / "Inbox"
    original = _audio(source / "note.mp3")
    library = PodcastLibrary()
    folder = wf.WatchedFolder(path=str(source), original="move", min_seconds=0)
    _r, added = _look(library, folder, tmp_path / "managed")
    assert not original.exists()
    assert Path(added[0][1].downloaded_path).exists()


def test_each_subfolder_can_be_its_own_group(tmp_path: Path) -> None:
    source = tmp_path / "Audiobooks"
    _audio(source / "Book One" / "01.mp3", b"a")
    _audio(source / "Book Two" / "01.mp3", b"b")
    library = PodcastLibrary()
    folder = wf.WatchedFolder(path=str(source), subfolder_groups=True, min_seconds=0)
    _r, added = _look(library, folder, tmp_path / "managed")
    assert sorted(show.title for show, _ep in added) == ["Book One", "Book Two"]
    assert set(folder.group_shows) == {"Book One", "Book Two"}


def test_unticked_file_types_and_subfolders_are_left_alone(tmp_path: Path) -> None:
    source = tmp_path / "Raw"
    _audio(source / "take.wav", b"w")
    _audio(source / "deeper" / "x.mp3", b"m")
    library = PodcastLibrary()
    folder = wf.WatchedFolder(
        path=str(source), extensions=(".mp3",), include_subfolders=False, min_seconds=0
    )
    _r, added = _look(library, folder, tmp_path / "managed")
    assert added == []


def test_a_missing_folder_says_so_rather_than_nothing(tmp_path: Path) -> None:
    folder = wf.WatchedFolder(path=str(tmp_path / "gone"), name="Voice Memos")
    result = wf.plan(folder, set(), dest_root=tmp_path / "managed")
    assert "Voice Memos is unavailable" in result.problem


def test_the_library_keeps_its_watched_folders(tmp_path: Path) -> None:
    library = PodcastLibrary()
    library.watched_folders.append(
        wf.WatchedFolder(path="D:/Lectures", name="Lectures", tell="batch", speed=1.5)
    )
    save_library(tmp_path, library)
    loaded = load_library(tmp_path).watched_folders
    assert [(f.name, f.tell, f.speed) for f in loaded] == [("Lectures", "batch", 1.5)]


def test_an_old_watched_folder_string_is_migrated_without_reimporting(tmp_path: Path) -> None:
    source = tmp_path / "Old"
    _audio(source / "already.mp3", b"x")
    show = PodcastShow(id="s1", title="Old", feed_url="", is_local=True)
    show.watched_folder = str(source)
    from quill.core.podcasts.models_episode import PodcastEpisode

    show.episodes.append(
        PodcastEpisode(guid="g", title="Already", audio_url="", downloaded_path="x/already.mp3")
    )
    library = PodcastLibrary(shows=[show])
    assert wf.migrate(library) == 1
    folder = library.watched_folders[0]
    assert folder.show_id == "s1" and show.watched_folder == ""
    _r, added = _look(library, folder, tmp_path / "managed")
    assert added == []


def test_what_an_arrival_says(tmp_path: Path) -> None:
    folder = wf.WatchedFolder(path=str(tmp_path), name="Voice Memos")
    show = PodcastShow(id="s", title="Voice Memos", feed_url="", is_local=True)
    from quill.core.podcasts.models_episode import PodcastEpisode

    ep = PodcastEpisode(guid="g", title="Tuesday meeting", audio_url="", duration_seconds=42 * 60)
    assert (
        arrival_sentence(folder, [(show, ep)]) == "New in Voice Memos: Tuesday meeting, 42 minutes."
    )
    folder.tell = "batch"
    assert arrival_sentence(folder, [(show, ep), (show, ep)]) == "2 new recordings in Voice Memos."
    folder.tell = "quiet"
    assert arrival_sentence(folder, [(show, ep)]) == ""
    library = PodcastLibrary()
    assert row_text(library, folder).startswith("Voice Memos, watching, 0 files, nothing new yet")


def test_a_file_settles_only_when_it_stops_growing(tmp_path: Path) -> None:
    now = [100.0]
    tracker = wf.SettleTracker(5.0, clock=lambda: now[0])
    path = tmp_path / "rec.mp3"
    path.write_bytes(b"a")
    tracker.note(str(path))
    now[0] += 3
    path.write_bytes(b"ab")
    assert tracker.due() == []  # grew: the quiet period starts again
    now[0] += 4
    assert tracker.due() == []
    now[0] += 2
    assert tracker.due() == [str(path)]
    assert tracker.pending() == 0


@pytest.mark.parametrize("path", ["\\\\server\\share", "//server/share"])
def test_a_network_path_is_recognised(path: str) -> None:
    assert wf.is_network_path(path)
