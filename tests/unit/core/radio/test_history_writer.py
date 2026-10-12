from __future__ import annotations

import threading
import time
from pathlib import Path

from quill.core.radio.history_writer import RadioHistorySnapshotWriter


def test_blocked_write_does_not_block_submit_and_coalesces_to_latest_snapshot(
    tmp_path: Path,
) -> None:
    entered = threading.Event()
    release = threading.Event()
    lock = threading.Lock()
    writes: list[int] = []
    active = 0
    maximum_active = 0

    def write(_data_dir: Path, snapshot: dict[str, object]) -> None:
        nonlocal active, maximum_active
        with lock:
            active += 1
            maximum_active = max(maximum_active, active)
            writes.append(int(snapshot["generation"]))
        if len(writes) == 1:
            entered.set()
            assert release.wait(3)
        with lock:
            active -= 1

    writer = RadioHistorySnapshotWriter(write)
    try:
        started = time.monotonic()
        assert writer.submit(tmp_path, {"generation": 1}) == 1
        assert time.monotonic() - started < 0.2
        assert entered.wait(2)
        assert writer.submit(tmp_path, {"generation": 2}) == 2
        assert writer.submit(tmp_path, {"generation": 3}) == 3
        started = time.monotonic()
        assert not writer.close(0.02)
        assert time.monotonic() - started < 0.2
        release.set()
        assert writer.flush(3)
        assert writes == [1, 3]
        assert maximum_active == 1
    finally:
        release.set()
        writer.close(3)


def test_failed_write_is_reported_and_latest_generation_is_not_successful(
    tmp_path: Path,
) -> None:
    failed = threading.Event()
    errors: list[tuple[int, Exception]] = []

    def write(_data_dir: Path, _snapshot: dict[str, object]) -> None:
        raise OSError("disk unavailable")

    def on_failure(generation: int, error: Exception) -> None:
        errors.append((generation, error))
        failed.set()

    writer = RadioHistorySnapshotWriter(write)
    try:
        generation = writer.submit(tmp_path, {"generation": 1}, on_failure=on_failure)
        assert failed.wait(2)
        assert errors[0][0] == generation
        assert isinstance(errors[0][1], OSError)
        assert not writer.flush(2)
    finally:
        writer.close(2)
