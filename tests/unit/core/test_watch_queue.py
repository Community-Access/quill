"""Tests for the durable watch processing queue (WATCH-3)."""

from __future__ import annotations

from pathlib import Path

from quill.core.watch_queue import (
    STATE_DONE,
    STATE_FAILED,
    STATE_PROCESSING,
    STATE_QUEUED,
    STATE_SKIPPED,
    QueueItem,
    WatchQueue,
)


class _Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def test_enqueue_assigns_state_and_returns_item(tmp_path: Path) -> None:
    queue = WatchQueue()
    item = queue.enqueue(tmp_path / "a.txt", "p1", "open")
    assert item is not None
    assert item.state == STATE_QUEUED
    assert queue.pending_count() == 1


def test_prime_counts_unique_files_and_suppresses_enqueue(tmp_path: Path) -> None:
    queue = WatchQueue()
    a, b = tmp_path / "a.txt", tmp_path / "b.txt"
    queue.prime(a)
    queue.prime(b)
    queue.prime(a)  # a repeat is not double-counted
    assert queue.primed_count() == 2
    # A primed file is treated as already-known, so enqueue is a no-op.
    assert queue.enqueue(a, "p1", "open") is None
    assert queue.pending_count() == 0


def test_enqueue_deduplicates_same_source(tmp_path: Path) -> None:
    queue = WatchQueue()
    source = tmp_path / "a.txt"
    first = queue.enqueue(source, "p1", "open")
    second = queue.enqueue(source, "p2", "move")
    assert first is not None
    assert second is None
    assert len(queue.items()) == 1


def test_claim_next_transitions_to_processing(tmp_path: Path) -> None:
    queue = WatchQueue()
    queue.enqueue(tmp_path / "a.txt", "p1", "open")
    claimed = queue.claim_next()
    assert claimed is not None
    assert claimed.state == STATE_PROCESSING
    assert claimed.attempts == 1
    # Nothing else is runnable now.
    assert queue.claim_next() is None


def test_claim_next_respects_global_pause(tmp_path: Path) -> None:
    queue = WatchQueue()
    queue.enqueue(tmp_path / "a.txt", "p1", "open")
    queue.pause()
    assert queue.claim_next() is None
    queue.resume()
    assert queue.claim_next() is not None


def test_claim_next_respects_profile_pause(tmp_path: Path) -> None:
    queue = WatchQueue()
    queue.enqueue(tmp_path / "a.txt", "p1", "open")
    queue.enqueue(tmp_path / "b.txt", "p2", "open")
    queue.pause_profile("p1")
    claimed = queue.claim_next()
    assert claimed is not None
    assert claimed.profile_id == "p2"


def test_mark_done_is_terminal(tmp_path: Path) -> None:
    queue = WatchQueue()
    item = queue.enqueue(tmp_path / "a.txt", "p1", "open")
    assert item is not None
    queue.claim_next()
    queue.mark_done(item.item_id, "ok")
    assert queue.get(item.item_id).state == STATE_DONE


def test_mark_failed_retries_with_backoff_then_fails() -> None:
    clock = _Clock()
    queue = WatchQueue(max_attempts=2, base_backoff_seconds=10.0, clock=clock)
    item = queue.enqueue(Path("a.txt"), "p1", "open")
    assert item is not None

    first = queue.claim_next()
    assert first is not None and first.attempts == 1
    queue.mark_failed(item.item_id, "boom")
    requeued = queue.get(item.item_id)
    assert requeued.state == STATE_QUEUED
    # Backoff window not elapsed -> not yet claimable.
    assert queue.claim_next() is None

    clock.advance(11.0)
    second = queue.claim_next()
    assert second is not None and second.attempts == 2
    queue.mark_failed(item.item_id, "boom again")
    assert queue.get(item.item_id).state == STATE_FAILED


def test_manual_retry_requeues_failed_item() -> None:
    queue = WatchQueue(max_attempts=1)
    item = queue.enqueue(Path("a.txt"), "p1", "open")
    assert item is not None
    queue.claim_next()
    queue.mark_failed(item.item_id, "boom")
    assert queue.get(item.item_id).state == STATE_FAILED
    assert queue.retry(item.item_id) is True
    assert queue.get(item.item_id).state == STATE_QUEUED


def test_retry_rejects_non_failed_item(tmp_path: Path) -> None:
    queue = WatchQueue()
    item = queue.enqueue(tmp_path / "a.txt", "p1", "open")
    assert item is not None
    assert queue.retry(item.item_id) is False


def test_clear_finished_removes_only_terminal(tmp_path: Path) -> None:
    queue = WatchQueue()
    a = queue.enqueue(tmp_path / "a.txt", "p1", "open")
    b = queue.enqueue(tmp_path / "b.txt", "p1", "open")
    assert a is not None and b is not None
    queue.claim_next()
    queue.mark_done(a.item_id)
    removed = queue.clear_finished()
    assert removed == 1
    remaining = {item.item_id for item in queue.items()}
    assert remaining == {b.item_id}


def test_clear_finished_frees_dedup_so_file_can_requeue(tmp_path: Path) -> None:
    queue = WatchQueue()
    source = tmp_path / "a.txt"
    first = queue.enqueue(source, "p1", "open")
    assert first is not None
    queue.claim_next()
    queue.mark_done(first.item_id)
    queue.clear_finished()
    again = queue.enqueue(source, "p1", "open")
    assert again is not None


def test_counts_reports_each_state(tmp_path: Path) -> None:
    queue = WatchQueue()
    a = queue.enqueue(tmp_path / "a.txt", "p1", "open")
    queue.enqueue(tmp_path / "b.txt", "p1", "open")
    assert a is not None
    queue.claim_next()
    queue.mark_done(a.item_id)
    counts = queue.counts()
    assert counts[STATE_DONE] == 1
    assert counts[STATE_QUEUED] == 1


def test_listener_receives_events(tmp_path: Path) -> None:
    events: list[str] = []
    queue = WatchQueue(listener=lambda name, _item: events.append(name))
    item = queue.enqueue(tmp_path / "a.txt", "p1", "open")
    assert item is not None
    queue.claim_next()
    queue.mark_done(item.item_id)
    assert "enqueued" in events
    assert "claimed" in events
    assert STATE_DONE in events


def test_bad_listener_does_not_break_queue(tmp_path: Path) -> None:
    def boom(_name: str, _item: QueueItem | None) -> None:
        raise RuntimeError("listener boom")

    queue = WatchQueue(listener=boom)
    item = queue.enqueue(tmp_path / "a.txt", "p1", "open")
    assert item is not None  # enqueue succeeded despite listener crash


def test_persistence_round_trip(tmp_path: Path) -> None:
    store = tmp_path / "queue.json"
    queue = WatchQueue(storage_path=store)
    a = queue.enqueue(tmp_path / "a.txt", "p1", "open")
    b = queue.enqueue(tmp_path / "b.txt", "p1", "open")
    assert a is not None and b is not None
    queue.claim_next()
    queue.mark_done(a.item_id)

    reloaded = WatchQueue(storage_path=store)
    states = {item.source_path: item.state for item in reloaded.items()}
    assert states[str((tmp_path / "a.txt").resolve())] == STATE_DONE
    assert states[str((tmp_path / "b.txt").resolve())] == STATE_QUEUED


def test_processing_item_is_requeued_on_reload(tmp_path: Path) -> None:
    store = tmp_path / "queue.json"
    queue = WatchQueue(storage_path=store)
    item = queue.enqueue(tmp_path / "a.txt", "p1", "open")
    assert item is not None
    claimed = queue.claim_next()
    assert claimed is not None and claimed.state == STATE_PROCESSING

    reloaded = WatchQueue(storage_path=store)
    recovered = reloaded.items()[0]
    assert recovered.state == STATE_QUEUED


def test_from_dict_coerces_unknown_state_to_queued() -> None:
    item = QueueItem.from_dict({"item_id": "x", "state": "bogus", "source_path": "a"})
    assert item.state == STATE_QUEUED


def test_skipped_is_terminal_and_clearable(tmp_path: Path) -> None:
    queue = WatchQueue()
    item = queue.enqueue(tmp_path / "a.txt", "p1", "open")
    assert item is not None
    queue.claim_next()
    queue.mark_skipped(item.item_id, "feature off")
    assert queue.get(item.item_id).state == STATE_SKIPPED
    assert queue.clear_finished() == 1
