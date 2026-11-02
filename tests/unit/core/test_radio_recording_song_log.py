"""Splitting a finished recording into songs from its song log.

The recorder keeps the song changes it heard beside the recording
(``<name>.songs.json``); Split into Songs reads them and cuts the recording
into a folder of "Artist - Title" files, keeping the recording. Everything
here runs on a fake ffmpeg that writes what the segment muxer would.
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Sequence
from pathlib import Path

from quill.core.radio import recording_song_log as song_log
from quill.core.radio.recording_split import SongChange, SplitOutcome


class _FakeFfmpeg:
    """Writes one file per piece into the pattern's folder, sharing out the
    source's bytes; *returncode* other than 0 is a failed run."""

    def __init__(self, *, returncode: int = 0) -> None:
        self.returncode = returncode
        self.calls: list[list[str]] = []

    def __call__(
        self, args: Sequence[str], *, timeout_seconds: float = 0.0
    ) -> subprocess.CompletedProcess[str]:
        self.calls.append(list(args))
        source = Path(args[args.index("-i") + 1])
        pattern = Path(args[-1])
        count = len(args[args.index("-segment_times") + 1].split(",")) + 1
        share = max(1, source.stat().st_size // count)
        if self.returncode == 0:
            for index in range(count):
                (pattern.parent / pattern.name.replace("%03d", f"{index:03d}")).write_bytes(
                    b"\xff" * share
                )
        return subprocess.CompletedProcess(list(args), self.returncode, "", "boom")


def _recording(tmp_path: Path, name: str = "Morning Show 2026-11-01.mp3") -> Path:
    path = tmp_path / name
    path.write_bytes(b"\xff" * 30_000)
    return path


def _log(path: Path, *, interrupted: bool = False) -> None:
    song_log.save_song_log(
        path,
        first_title="Artist One - First Song",
        changes=[SongChange(200.0, "Artist Two - Second: Song?"), SongChange(420.0, "Third")],
        duration=600.0,
        interrupted=interrupted,
    )


def test_the_log_sits_beside_the_recording_and_round_trips(tmp_path: Path) -> None:
    path = _recording(tmp_path)
    assert song_log.save_song_log(
        path,
        first_title="A - One",
        changes=[SongChange(3.0, "B - Flicker"), SongChange(130.0, "C - Two")],
        duration=300.0,
        lead_trim=10.0,
    )
    assert song_log.sidecar_path(path).name == "Morning Show 2026-11-01.mp3.songs.json"
    log = song_log.load_song_log(path)
    assert log is not None
    # The pre-roll trim is taken off once; a change inside the trimmed lead is dropped.
    assert log.changes == (SongChange(120.0, "C - Two"),)
    assert log.duration == 290.0
    assert song_log.companions(path) == [song_log.sidecar_path(path)]


def test_nothing_heard_writes_no_log(tmp_path: Path) -> None:
    path = _recording(tmp_path)
    assert not song_log.save_song_log(path, first_title="", changes=[], duration=60.0)
    assert song_log.load_song_log(path) is None
    assert song_log.companions(path) == []


def test_an_unreadable_or_foreign_log_is_ignored(tmp_path: Path) -> None:
    path = _recording(tmp_path)
    song_log.sidecar_path(path).write_text(json.dumps({"version": 99}), encoding="utf-8")
    assert song_log.load_song_log(path) is None
    song_log.sidecar_path(path).write_text("not json", encoding="utf-8")
    assert song_log.load_song_log(path) is None


def test_the_songs_are_named_artist_then_title_in_a_folder_beside_it(tmp_path: Path) -> None:
    path = _recording(tmp_path)
    _log(path)
    runner = _FakeFfmpeg()
    outcome = song_log.split_finished(path, ffmpeg="ffmpeg", runner=runner)
    assert outcome.split
    folder = tmp_path / "Morning Show 2026-11-01 songs"
    assert [file.name for file in outcome.files] == [
        "Artist One - First Song.mp3",
        "Artist Two - Second Song.mp3",
        "Third.mp3",
    ]
    assert all(file.parent == folder for file in outcome.files)
    # The recording is kept, and it is a stream copy.
    assert path.is_file()
    assert "-c copy" in " ".join(runner.calls[0])
    assert "-segment_times 200.000,420.000" in " ".join(runner.calls[0])


def test_splitting_twice_never_overwrites_the_first_songs(tmp_path: Path) -> None:
    path = _recording(tmp_path)
    _log(path)
    song_log.split_finished(path, ffmpeg="ffmpeg", runner=_FakeFfmpeg())
    again = song_log.split_finished(path, ffmpeg="ffmpeg", runner=_FakeFfmpeg())
    assert again.files[0].name == "Artist One - First Song (2).mp3"


def test_a_recording_with_no_log_says_plainly_there_is_nothing_to_split(tmp_path: Path) -> None:
    path = _recording(tmp_path)
    runner = _FakeFfmpeg()
    outcome = song_log.split_finished(path, ffmpeg="ffmpeg", runner=runner)
    assert not outcome.split
    assert runner.calls == []
    assert not (tmp_path / "Morning Show 2026-11-01 songs").exists()
    assert song_log.describe_splits([outcome]) == (
        "Morning Show 2026-11-01.mp3 has no song changes recorded, "
        "so there is nothing to split it at."
    )


def test_a_recording_whose_stream_dropped_is_not_split(tmp_path: Path) -> None:
    path = _recording(tmp_path)
    _log(path, interrupted=True)
    outcome = song_log.split_finished(path, ffmpeg="ffmpeg", runner=_FakeFfmpeg())
    assert not outcome.split
    assert "the stream dropped" in song_log.describe_splits([outcome])


def test_a_failed_split_leaves_no_folder_and_the_recording_whole(tmp_path: Path) -> None:
    path = _recording(tmp_path)
    _log(path)
    before = path.read_bytes()
    outcome = song_log.split_finished(path, ffmpeg="ffmpeg", runner=_FakeFfmpeg(returncode=1))
    assert not outcome.split
    assert path.read_bytes() == before
    assert not (tmp_path / "Morning Show 2026-11-01 songs").exists()
    assert sorted(p.name for p in tmp_path.iterdir()) == [
        path.name,
        song_log.sidecar_path(path).name,
    ]
    assert song_log.describe_splits([outcome]).startswith("Did not split Morning Show")


def test_one_split_names_the_count_and_the_folder(tmp_path: Path) -> None:
    path = _recording(tmp_path)
    _log(path)
    outcome = song_log.split_finished(path, ffmpeg="ffmpeg", runner=_FakeFfmpeg())
    assert song_log.describe_splits([outcome]) == (
        "Split Morning Show 2026-11-01.mp3 into 3 songs, "
        "in the folder Morning Show 2026-11-01 songs."
    )


def test_several_splits_are_counted_in_one_sentence(tmp_path: Path) -> None:
    song = tmp_path / "x.mp3"
    split = SplitOutcome(True, tmp_path / "a.mp3", (song, song, song))
    split_too = SplitOutcome(True, tmp_path / "b.mp3", (song, song))
    bare = SplitOutcome(False, tmp_path / "c.mp3", (), song_log.NO_SONG_CHANGES)
    broken = SplitOutcome(False, tmp_path / "d.mp3", (), "FFmpeg reported an error splitting it")
    assert song_log.describe_splits([split, split_too, bare, broken]) == (
        "Split 2 of 4 recordings into 5 songs. 1 has no song changes recorded. "
        "1 could not be split."
    )
