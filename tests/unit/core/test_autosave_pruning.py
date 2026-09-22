"""QUILL's half of the recovery hygiene: expiry, and the untitled preference.

QUILL never piled up sixty-nine offers the way QuillLite did -- it offers one
snapshot, from the previous session only -- but it accumulated the *store* just
as silently: one directory per session, none ever removed, thirteen of them on a
real machine with the oldest eighty-six days old. Every one older than the
previous session is unreachable by design, so keeping them is not caution, it is
litter with no reader.

The untitled half is the same preference QuillLite grew, and QUILL can answer it
because an untitled document autosaves under a known key.
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from uuid import uuid4

import pytest

from quill.core.autosave import (
    UNTITLED_KEY,
    is_untitled_snapshot,
    prune_stale_autosave,
)

_DAY = 86400.0


@pytest.fixture
def autosave_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """An isolated autosave tree, so no test can reach a real one."""
    root = tmp_path / "autosave"
    root.mkdir()
    monkeypatch.setattr("quill.core.autosave.app_data_dir", lambda: tmp_path)
    return root


def _session(root: Path, age_days: float) -> Path:
    directory = root / str(uuid4())
    directory.mkdir()
    snapshot = directory / f"{UNTITLED_KEY}-20260101T000000000000Z-000.snap"
    snapshot.write_text("work", encoding="utf-8")
    written = time.time() - age_days * _DAY
    os.utime(snapshot, (written, written))
    os.utime(directory, (written, written))
    return directory


def test_it_deletes_directories_past_the_keep_window(autosave_root: Path) -> None:
    fresh = _session(autosave_root, 1)
    ancient = _session(autosave_root, 90)

    assert prune_stale_autosave(30) == 1

    assert fresh.exists()
    assert not ancient.exists()


def test_zero_days_keeps_everything(autosave_root: Path) -> None:
    """The pre-2026-09-21 behaviour, still reachable and still the default."""
    ancient = _session(autosave_root, 900)

    assert prune_stale_autosave(0) == 0

    assert ancient.exists()


def test_age_comes_from_the_newest_file_not_the_directory(autosave_root: Path) -> None:
    """On Windows a directory's mtime moves when a file is deleted from it.

    Autosave itself deletes the oldest snapshots once a session passes
    ``max_snapshots``, so a long-dead session would look freshly used and never
    expire -- which is the failure that leaves the store growing anyway.
    """
    directory = _session(autosave_root, 90)
    os.utime(directory, None)  # "touched" now, contents still ninety days old

    assert prune_stale_autosave(30) == 1
    assert not directory.exists()


def test_a_directory_it_cannot_read_is_left_alone(autosave_root: Path) -> None:
    """Housekeeping that can fail a launch is worse than housekeeping skipped."""
    stray = autosave_root / "not-a-session"
    stray.write_text("", encoding="utf-8")  # a file where a directory is expected

    assert prune_stale_autosave(30) == 0
    assert stray.exists()


def test_a_missing_autosave_tree_is_not_an_error(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("quill.core.autosave.app_data_dir", lambda: tmp_path / "nothing")
    assert prune_stale_autosave(30) == 0


def test_an_untitled_snapshot_is_recognisable_by_its_key() -> None:
    """What makes the preference expressible in QUILL at all."""
    assert is_untitled_snapshot(Path(f"{UNTITLED_KEY}-20260101T000000000000Z-000.snap"))
    assert not is_untitled_snapshot(Path("0123abcd-20260101T000000000000Z-000.snap"))


def test_latest_session_snapshot_can_skip_untitled_work(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from quill.core import recovery as recovery_mod

    monkeypatch.setattr("quill.core.autosave.app_data_dir", lambda: tmp_path)
    monkeypatch.setattr(recovery_mod, "app_data_dir", lambda: tmp_path)
    session = str(uuid4())
    directory = tmp_path / "autosave" / session
    directory.mkdir(parents=True)
    scratch = directory / f"{UNTITLED_KEY}-20260101T000000000000Z-000.snap"
    scratch.write_text("paste", encoding="utf-8")

    assert recovery_mod.latest_session_snapshot(session) == scratch
    assert recovery_mod.latest_session_snapshot(session, include_untitled=False) is None


def test_a_named_snapshot_is_offered_either_way(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from quill.core import recovery as recovery_mod

    monkeypatch.setattr("quill.core.autosave.app_data_dir", lambda: tmp_path)
    monkeypatch.setattr(recovery_mod, "app_data_dir", lambda: tmp_path)
    session = str(uuid4())
    directory = tmp_path / "autosave" / session
    directory.mkdir(parents=True)
    named = directory / "0123abcd-20260101T000000000000Z-000.snap"
    named.write_text("letter", encoding="utf-8")

    assert recovery_mod.latest_session_snapshot(session, include_untitled=False) == named
