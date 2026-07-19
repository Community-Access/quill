from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

import quill.core.ipc as ipc
import quill.core.paths as paths_mod
from quill.core.ipc import (
    drain_open_requests,
    enqueue_open_request,
    release_primary_instance,
    try_claim_primary_instance,
)


@pytest.fixture(autouse=True)
def _isolate_ipc(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> object:
    """Route every test to an isolated tmp_path so ipc files never cross tests.

    paths.py now requires QUILL_DEV_BUILD=1 (or _DEV_BUILD=True) before
    QUILL_DATA_DIR is honoured; set both the env var and the module flag.
    """
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("QUILL_DEV_BUILD", "1")
    monkeypatch.setattr(paths_mod, "_DEV_BUILD", True)
    yield
    release_primary_instance()
    ipc._lock_handle = None


def test_claim_is_idempotent_then_releases(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    assert try_claim_primary_instance() is True
    # Same process claiming again is a no-op success, not a second instance.
    assert try_claim_primary_instance() is True
    release_primary_instance()
    assert try_claim_primary_instance() is True


def test_leftover_lock_file_with_no_holder_does_not_block(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # A lock file left behind by a previous run (no live process holding the OS
    # lock) must never block a new instance — this is the bug the OS lock fixes.
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    lock_path = tmp_path / "ipc" / "instance.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text('{"pid": 999999}', encoding="utf-8")
    assert try_claim_primary_instance() is True


def test_a_dead_holder_never_blocks(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # A child claims the lock then exits HARD (os._exit) without releasing —
    # simulating a crash/force-kill. The OS frees the lock on process death, so
    # we can claim with no PID bookkeeping or "self-heal" logic.
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    code = (
        "import os;"
        "from quill.core.ipc import try_claim_primary_instance;"
        "assert try_claim_primary_instance();"
        "os._exit(0)"
    )
    result = subprocess.run([sys.executable, "-c", code])
    assert result.returncode == 0
    assert try_claim_primary_instance() is True


def test_a_live_instance_blocks_a_second(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # While this process holds the lock, a genuinely separate process must not
    # be able to claim it.
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    assert try_claim_primary_instance() is True
    code = (
        "import sys;"
        "from quill.core.ipc import try_claim_primary_instance;"
        "sys.exit(0 if try_claim_primary_instance() else 3)"
    )
    result = subprocess.run([sys.executable, "-c", code])
    assert result.returncode == 3  # the second process could NOT claim


def test_enqueue_and_drain_open_requests(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    first = tmp_path / "one.md"
    second = tmp_path / "two.md"
    enqueue_open_request(first)
    enqueue_open_request(second)
    drained = drain_open_requests()
    assert [request.path for request in drained] == [first, second]
    assert drain_open_requests() == []


def test_enqueue_show_request(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    enqueue_open_request(None)
    assert drain_open_requests() == [None]


def test_slots_isolate_queues(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # A show request on one app's slot must not be drained by another app's
    # slot (#1152: Quill Radio, Quill Cast and QUILL share the data dir).
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    enqueue_open_request(None, slot="radio")
    assert drain_open_requests() == []  # QUILL's default slot sees nothing
    assert drain_open_requests(slot="cast") == []  # a different app sees nothing
    assert drain_open_requests(slot="radio") == [None]  # only the radio slot
    assert drain_open_requests(slot="radio") == []  # drained once


def test_slots_isolate_primary_claim(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # Two different apps can each be primary at once; the same app cannot.
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    lock_path = ipc._lock_file_path(slot="radio")
    assert lock_path.name == "instance-radio.lock"
    assert ipc._lock_file_path().name == "instance.lock"


def test_enqueue_and_drain_action(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    image = tmp_path / "scan.png"
    enqueue_open_request(image, action="ocr")
    drained = drain_open_requests()
    assert [request.action for request in drained] == ["ocr"]
    assert drained[0].path == image


def test_default_action_is_open(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    enqueue_open_request(tmp_path / "doc.md")
    drained = drain_open_requests()
    assert drained[0].action == "open"


def test_concurrent_enqueue_serializes_via_lock(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """H-4-core-2: two threads writing concurrently must each produce one valid JSONL line."""
    import threading

    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    barrier = threading.Barrier(2)
    errors: list[Exception] = []

    def _enqueue(path: Path) -> None:
        try:
            barrier.wait()
            enqueue_open_request(path)
        except Exception as exc:
            errors.append(exc)

    paths = [tmp_path / "a.md", tmp_path / "b.md"]
    threads = [threading.Thread(target=_enqueue, args=(p,)) for p in paths]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5)

    assert not errors, f"Thread errors: {errors}"
    drained = drain_open_requests()
    assert len(drained) == 2
    drained_paths = {r.path for r in drained}
    assert drained_paths == set(paths)
