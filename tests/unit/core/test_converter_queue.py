from __future__ import annotations

import json
from pathlib import Path

import pytest

from quill.core import converter_queue, persistence_outcome, storage
from quill.core.converter_queue import ConverterQueueEntry, ConverterQueueStore


def test_queue_round_trips_ordered_files_and_folder_roots(tmp_path: Path) -> None:
    song = tmp_path / "song.mp3"
    folder = tmp_path / "album"
    song.write_bytes(b"audio")
    folder.mkdir()
    current = [
        ConverterQueueEntry(song),
        ConverterQueueEntry(folder / "disc", folder),
    ]
    store = ConverterQueueStore(tmp_path)

    assert store.save(lambda: current)

    restored = ConverterQueueStore(tmp_path).load()
    assert [converter_queue.as_pair(item) for item in restored] == [
        converter_queue.as_pair(item) for item in current
    ]
    raw = json.loads(store.path.read_text(encoding="utf-8"))
    assert raw["version"] == converter_queue.SCHEMA
    assert raw["entries"][1] == {
        "source": str(folder / "disc"),
        "root": str(folder),
    }


def test_queue_preserves_a_future_version_and_unknown_fields(tmp_path: Path) -> None:
    store = ConverterQueueStore(tmp_path)
    store.path.write_text(
        json.dumps({
            "version": 7,
            "future_top": {"kept": True},
            "entries": [
                {
                    "source": "later.wav",
                    "root": None,
                    "future_row": 42,
                }
            ],
        }),
        encoding="utf-8",
    )
    current = store.load()
    current.insert(0, ConverterQueueEntry(Path("first.mp3")))

    assert store.save(lambda: current)

    raw = json.loads(store.path.read_text(encoding="utf-8"))
    assert raw["version"] == 7
    assert raw["future_top"] == {"kept": True}
    assert raw["entries"][1]["future_row"] == 42


def test_missing_paths_remain_editable_and_are_not_discarded(tmp_path: Path) -> None:
    path = tmp_path / "drive-removed.mp3"
    path.write_bytes(b"audio")
    store = ConverterQueueStore(tmp_path)
    assert store.save(lambda: [ConverterQueueEntry(path)])
    path.unlink()

    restored = ConverterQueueStore(tmp_path).load()

    assert len(restored) == 1
    assert restored[0].missing and not restored[0].available
    assert restored[0].label() == "drive-removed.mp3 (missing)"
    assert store.save(lambda: [])
    assert ConverterQueueStore(tmp_path).load() == []


def test_failed_save_offers_a_retry_that_writes_the_current_queue(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    outcomes: list[persistence_outcome.WriteOutcome] = []
    stop = persistence_outcome.subscribe(outcomes.append)
    store = ConverterQueueStore(tmp_path)
    current = [ConverterQueueEntry(tmp_path / "one.mp3")]
    real_write = storage.write_json_atomic

    def full(*_args: object, **_kwargs: object) -> None:
        raise OSError(28, "disk full")

    try:
        monkeypatch.setattr(storage, "write_json_atomic", full)
        assert store.save(lambda: current) is False
        failed = [outcome for outcome in outcomes if not outcome.ok]
        assert len(failed) == 1
        assert failed[0].what == "Quill Converter queue"
        assert failed[0].retry is not None

        current.insert(0, ConverterQueueEntry(tmp_path / "zero.mp3"))
        monkeypatch.setattr(storage, "write_json_atomic", real_write)
        failed[0].retry()

        restored = store.load()
        assert [item.source.name for item in restored] == ["zero.mp3", "one.mp3"]
    finally:
        stop()


def test_a_live_queue_lock_never_falls_through_to_an_unsafe_write(tmp_path: Path) -> None:
    store = ConverterQueueStore(tmp_path, timeout_s=0)
    store.lock_path.parent.mkdir(parents=True, exist_ok=True)
    store.lock_path.write_text("another process", encoding="utf-8")

    assert store.save(lambda: [ConverterQueueEntry(tmp_path / "song.mp3")]) is False
    assert not store.path.exists()
    assert store.lock_path.exists()


def test_stale_queue_lock_is_replaced_without_waiting(tmp_path: Path) -> None:
    store = ConverterQueueStore(tmp_path, clock=lambda: 100.0)
    store.lock_path.parent.mkdir(parents=True, exist_ok=True)
    store.lock_path.write_text("crashed process", encoding="utf-8")
    monkeypatch_stat = store.lock_path.stat()
    import os

    os.utime(store.lock_path, (monkeypatch_stat.st_atime, 80.0))

    assert store.save(lambda: [ConverterQueueEntry(tmp_path / "song.mp3")])
    assert not store.lock_path.exists()
