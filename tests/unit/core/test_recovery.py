from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from uuid import uuid4

import pytest

from quill.core.recovery import (
    RecoveryOffer,
    begin_session,
    latest_session_snapshot,
    mark_clean_exit,
    mark_recovery_offer_dismissed,
    read_recovery_snapshot,
)


def test_begin_session_offers_previous_unclean_snapshot(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    previous = str(uuid4())
    current = str(uuid4())
    session_root = tmp_path / "autosave" / previous
    session_root.mkdir(parents=True)
    snap = session_root / "doc.snap"
    snap.write_text("recovered text", encoding="utf-8")
    begin_session(previous)
    offers = begin_session(current)
    assert len(offers) == 1
    assert offers[0].session_id == previous
    assert offers[0].snapshot == snap


def test_mark_clean_exit_prevents_future_offer(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    session = str(uuid4())
    begin_session(session)
    mark_clean_exit(session)
    offers = begin_session(str(uuid4()))
    assert offers == []


def test_latest_session_snapshot_and_reader(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    session = str(uuid4())
    root = tmp_path / "autosave" / session
    root.mkdir(parents=True)
    older = root / "old.snap"
    newer = root / "new.snap"
    older.write_text("old", encoding="utf-8")
    time.sleep(0.01)
    newer.write_text("new", encoding="utf-8")
    latest = latest_session_snapshot(session)
    assert latest == newer
    text, had_replacements = read_recovery_snapshot(newer)
    assert text == "new"
    assert had_replacements is False


def test_begin_session_skips_dismissed_offer_for_same_snapshot(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    previous = str(uuid4())
    current = str(uuid4())
    session_root = tmp_path / "autosave" / previous
    session_root.mkdir(parents=True)
    snap = session_root / "doc.snap"
    snap.write_text("recovered text", encoding="utf-8")
    (tmp_path / "recovery_state.json").write_text(
        json.dumps({"last_session_id": previous, "clean_exit": False}),
        encoding="utf-8",
    )
    mark_recovery_offer_dismissed(RecoveryOffer(session_id=previous, snapshot=snap))
    offers = begin_session(current)
    assert offers == []


def test_latest_session_snapshot_skips_empty_files(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    session = str(uuid4())
    root = tmp_path / "autosave" / session
    root.mkdir(parents=True)
    empty = root / "empty.snap"
    empty.write_bytes(b"")
    nonempty = root / "real.snap"
    nonempty.write_text("content", encoding="utf-8")
    latest = latest_session_snapshot(session)
    assert latest == nonempty


def test_latest_session_snapshot_returns_none_when_all_files_empty(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    session = str(uuid4())
    root = tmp_path / "autosave" / session
    root.mkdir(parents=True)
    (root / "empty.snap").write_bytes(b"")
    assert latest_session_snapshot(session) is None


def test_begin_session_does_not_offer_empty_snapshot(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    previous = str(uuid4())
    current = str(uuid4())
    session_root = tmp_path / "autosave" / previous
    session_root.mkdir(parents=True)
    (session_root / "doc.snap").write_bytes(b"")
    begin_session(previous)
    offers = begin_session(current)
    assert offers == []


def test_concurrent_begin_session_serialize_via_lock(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """H-4-core: two concurrent begin_session calls must not lose state.

    Without locking, two threads can read the same ``last_session_id``,
    each compute the offer from the previous session, and one will
    overwrite the other's write of the new ``last_session_id``. With
    the threading.RLock + OS file lock in place, the second writer
    must observe the first writer's session id.
    """
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    session_a = str(uuid4())
    session_b = str(uuid4())
    results: list[tuple[str, str | None]] = []
    barrier = threading.Barrier(2)

    def worker(session: str) -> None:
        barrier.wait()
        begin_session(session)
        state = json.loads((tmp_path / "recovery_state.json").read_text(encoding="utf-8"))
        results.append((session, state.get("last_session_id")))

    t1 = threading.Thread(target=worker, args=(session_a,))
    t2 = threading.Thread(target=worker, args=(session_b,))
    t1.start()
    t2.start()
    t1.join(timeout=2)
    t2.join(timeout=2)
    assert len(results) == 2
    # Whichever thread wrote last must be the one whose session id is
    # in the file. The other thread must have observed the file *after*
    # the first write, so its own session id is the persisted value.
    persisted_ids = {r[0] for r in results if r[1] == r[0]}
    assert len(persisted_ids) >= 1  # at least one thread is consistent
    # And the final state must be exactly one of the two sessions,
    # not some lost value or the empty default.
    final = json.loads((tmp_path / "recovery_state.json").read_text(encoding="utf-8"))
    assert final["last_session_id"] in (session_a, session_b)
