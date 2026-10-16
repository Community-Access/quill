"""The disk-backed time-shift buffer: its cap, its folder, and its clean-up (xradio2.md 4.3)."""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.radio import timeshift as ts

GIB = 1024 * 1024 * 1024


def test_the_default_is_an_hour_on_disk() -> None:
    plan = ts.plan(ts.DEFAULT_MINUTES, free_bytes=100 * GIB)
    assert plan.on_disk
    assert plan.back_bytes == 60 * 60 * ts.ASSUMED_BYTES_PER_SECOND
    assert not plan.reduced


def test_memory_only_keeps_the_old_fifty_mebibytes() -> None:
    plan = ts.plan(0, free_bytes=100 * GIB)
    assert not plan.on_disk
    assert plan.back_bytes == 50 * 1024 * 1024


def test_the_cap_never_takes_more_than_half_the_spare_room() -> None:
    """A buffer that fills a disk is a worse failure than a short buffer."""
    free = GIB + 200 * 1024 * 1024
    plan = ts.plan(300, free_bytes=free)
    assert plan.on_disk and plan.reduced
    assert plan.back_bytes == (free - GIB) // 2


def test_a_nearly_full_disk_goes_back_to_memory() -> None:
    plan = ts.plan(300, free_bytes=GIB + 10)
    assert not plan.on_disk and plan.reduced


def test_unknown_free_space_keeps_the_chosen_cap() -> None:
    assert ts.plan(120, free_bytes=None).back_bytes == 120 * 60 * ts.ASSUMED_BYTES_PER_SECOND


@pytest.mark.parametrize(
    ("stored", "expected"), [(30, 30), ("120", 120), (7, 60), ("x", 60), (None, 60)]
)
def test_a_stored_length_is_normalised(stored: object, expected: int) -> None:
    assert ts.normalise_minutes(stored) == expected


def test_every_choice_maps_back_to_its_row() -> None:
    for index, (minutes, _label) in enumerate(ts.CHOICES):
        assert ts.choice_index(minutes) == index


def test_disk_options_name_the_folder_and_ask_mpv_to_delete_its_file(tmp_path: Path) -> None:
    options = dict(ts.mpv_cache_options(ts.plan(60, free_bytes=None), tmp_path))
    assert options["cache-on-disk"] == "yes"
    assert options["cache-dir"] == str(tmp_path)
    assert options["cache-unlink-files"] == "whendone"
    assert options["demuxer-max-back-bytes"] == str(60 * 60 * ts.ASSUMED_BYTES_PER_SECOND)


def test_memory_options_turn_the_disk_off() -> None:
    options = dict(ts.mpv_cache_options(ts.plan(0, free_bytes=None), None))
    assert options["cache-on-disk"] == "no"
    assert "cache-dir" not in options


def test_the_sweep_removes_what_earlier_sessions_left(tmp_path: Path) -> None:
    old = tmp_path / "session-1-aaaa"
    old.mkdir()
    (old / "mpv-cache-1").write_bytes(b"x" * 10)
    mine = tmp_path / "session-2-bbbb"
    mine.mkdir()
    (tmp_path / "stray.tmp").write_bytes(b"x")
    removed = ts.sweep_orphans(tmp_path, keep=mine)
    assert removed == 2
    assert not old.exists()
    assert mine.exists(), "the running session's own folder is never swept"


def test_the_sweep_of_a_missing_root_is_a_no_op(tmp_path: Path) -> None:
    assert ts.sweep_orphans(tmp_path / "absent") == 0


class _Mpv:
    def __init__(self) -> None:
        self.options: dict[str, str] = {}

    def set_str(self, name: str, value: str) -> int:
        self.options[name] = value
        return 0


def test_a_session_sweeps_at_start_and_removes_its_folder_at_exit(tmp_path: Path) -> None:
    leftover = tmp_path / "session-99-dead"
    leftover.mkdir()
    (leftover / "cache").write_bytes(b"x")
    mpv = _Mpv()
    session = ts.TimeshiftSession(mpv.set_str, root=tmp_path)
    plan = session.configure(60)
    assert not leftover.exists(), "a crash's leftovers go at the next start"
    assert plan.on_disk
    assert mpv.options["cache-on-disk"] == "yes"
    assert session.session_dir is not None
    assert mpv.options["cache-dir"] == str(session.session_dir)
    session.prepare()
    assert session.session_dir.is_dir()
    (session.session_dir / "mpv-cache").write_bytes(b"x" * 100)
    session.close()
    assert not session.session_dir.exists(), "nothing outlives the session"


def test_a_session_set_to_memory_writes_no_folder(tmp_path: Path) -> None:
    mpv = _Mpv()
    session = ts.TimeshiftSession(mpv.set_str, root=tmp_path)
    session.configure(0)
    session.prepare()
    assert mpv.options["cache-on-disk"] == "no"
    assert list(tmp_path.iterdir()) == []


def test_a_session_whose_folder_cannot_be_reached_falls_back_to_memory(tmp_path: Path) -> None:
    blocker = tmp_path / "file-not-folder"
    blocker.write_bytes(b"x")
    mpv = _Mpv()
    session = ts.TimeshiftSession(mpv.set_str, root=blocker / "below")
    session.configure(60)
    session.prepare()
    # The folder cannot be made under a file; playback must still have a buffer.
    assert mpv.options["cache-on-disk"] == "no"
    assert mpv.options["demuxer-max-back-bytes"] == str(ts.MEMORY_BYTES)
    assert not session.current_plan.on_disk


def test_the_root_is_the_machine_local_cache(quill_data_dir: Path) -> None:
    from quill.core.paths import machine_local_dir

    assert ts.default_root() == machine_local_dir() / ts.FOLDER_NAME
