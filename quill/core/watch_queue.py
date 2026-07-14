"""Durable, monitorable watch processing queue (WATCH-3).

Every detected file becomes a :class:`QueueItem` with an explicit lifecycle
(queued, processing, done, failed, skipped), stable ordering, retry with
bounded backoff, and per-profile and global pause/resume. The queue is durable
across restarts: it is schema-validated, persisted atomically, and recoverable.
An atomic *claim* guarantees no item is processed twice even across overlapping
profiles.

This module is UI-framework-agnostic: no ``wx`` imports. The queue emits events
through a caller-supplied listener so the Watch Queue Monitor (WATCH-4) can
render and announce changes without the core knowing about the UI.
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from collections.abc import Callable, Iterable
from dataclasses import dataclass, replace
from pathlib import Path

from .storage import read_json, write_json_atomic

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 1

# Lifecycle states.
STATE_QUEUED = "queued"
STATE_PROCESSING = "processing"
STATE_DONE = "done"
STATE_FAILED = "failed"
STATE_SKIPPED = "skipped"

_TERMINAL_STATES = frozenset({STATE_DONE, STATE_SKIPPED})

_DEFAULT_MAX_ATTEMPTS = 3
_DEFAULT_BASE_BACKOFF = 5.0
_MAX_BACKOFF = 300.0

#: Listener signature: ``(event_name, item)``. ``item`` may be ``None`` for
#: queue-wide events such as ``"cleared"``.
QueueListener = Callable[[str, "QueueItem | None"], None]


@dataclass(frozen=True, slots=True)
class QueueItem:
    """A single file moving through the watch queue."""

    item_id: str
    source_path: str
    profile_id: str
    action_id: str
    state: str = STATE_QUEUED
    attempts: int = 0
    created_at: float = 0.0
    updated_at: float = 0.0
    not_before: float = 0.0
    message: str = ""
    result_path: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "item_id": self.item_id,
            "source_path": self.source_path,
            "profile_id": self.profile_id,
            "action_id": self.action_id,
            "state": self.state,
            "attempts": self.attempts,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "not_before": self.not_before,
            "message": self.message,
            "result_path": self.result_path,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, object]) -> QueueItem:
        state = str(raw.get("state", STATE_QUEUED))
        if state not in _ALL_STATES:
            state = STATE_QUEUED
        # An item caught mid-processing by a crash is re-queued on load so it is
        # retried rather than stuck forever in ``processing``.
        if state == STATE_PROCESSING:
            state = STATE_QUEUED
        return cls(
            item_id=str(raw.get("item_id") or uuid.uuid4().hex),
            source_path=str(raw.get("source_path", "")),
            profile_id=str(raw.get("profile_id", "")),
            action_id=str(raw.get("action_id", "")),
            state=state,
            attempts=_as_int(raw.get("attempts"), 0),
            created_at=_as_float(raw.get("created_at"), 0.0),
            updated_at=_as_float(raw.get("updated_at"), 0.0),
            not_before=_as_float(raw.get("not_before"), 0.0),
            message=str(raw.get("message", "")),
            result_path=str(raw.get("result_path", "")),
        )


_ALL_STATES = frozenset({STATE_QUEUED, STATE_PROCESSING, STATE_DONE, STATE_FAILED, STATE_SKIPPED})


def _as_int(value: object, default: int) -> int:
    if isinstance(value, (int, float, str)):
        try:
            return int(value)
        except (TypeError, ValueError):
            return default
    return default


def _as_float(value: object, default: float) -> float:
    if isinstance(value, (int, float, str)):
        try:
            return float(value)
        except (TypeError, ValueError):
            return default
    return default


class WatchQueue:
    """A thread-safe, durable processing queue for watch items.

    The queue owns a single re-entrant lock guarding all item state and the
    paused sets, so concurrent watchers (one per profile) and the worker can
    enqueue, claim, and complete items without races. Persistence is atomic and
    happens under the lock so the on-disk file is always a consistent snapshot.
    """

    def __init__(
        self,
        *,
        storage_path: Path | None = None,
        max_attempts: int = _DEFAULT_MAX_ATTEMPTS,
        base_backoff_seconds: float = _DEFAULT_BASE_BACKOFF,
        listener: QueueListener | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._storage_path = storage_path
        self._max_attempts = max(1, int(max_attempts))
        self._base_backoff = max(0.0, float(base_backoff_seconds))
        self._listener = listener
        self._clock = clock
        # RLock required: _dequeue_item calls _release_slot which re-enters
        # _try_flush under the same lock. A plain Lock would deadlock.
        self._lock = threading.RLock()
        self._items: dict[str, QueueItem] = {}
        self._order: list[str] = []
        self._known_sources: set[str] = set()
        # Files claimed by prime() — present at start and intentionally ignored
        # because their profile has process_existing off. Surfaced as a monitor
        # hint so an "empty" queue is self-explanatory.
        self._primed_count = 0
        self._paused_profiles: set[str] = set()
        self._globally_paused = False
        if storage_path is not None:
            self._load()

    # -- enqueue ---------------------------------------------------------

    def enqueue(self, source_path: Path, profile_id: str, action_id: str) -> QueueItem | None:
        """Add a new item for ``source_path``; returns ``None`` if already known.

        The de-duplication key is the resolved source path, so a file is claimed
        exactly once even when several overlapping profiles all see it.
        """
        try:
            canonical = str(source_path.resolve())
        except OSError:
            canonical = str(source_path)
        now = self._clock()
        with self._lock:
            if canonical in self._known_sources:
                return None
            item = QueueItem(
                item_id=uuid.uuid4().hex,
                source_path=canonical,
                profile_id=profile_id,
                action_id=action_id,
                state=STATE_QUEUED,
                attempts=0,
                created_at=now,
                updated_at=now,
                not_before=now,
            )
            self._items[item.item_id] = item
            self._order.append(item.item_id)
            self._known_sources.add(canonical)
            self._save_locked()
        self._emit("enqueued", item)
        return item

    def prime(self, source_path: Path) -> None:
        """Reserve ``source_path``'s de-dup slot without enqueuing an item.

        Used when a profile ignores pre-existing files: the slot is claimed so
        the file is never actioned, but no queue item (and no monitor noise) is
        created for it.
        """
        try:
            canonical = str(source_path.resolve())
        except OSError:
            canonical = str(source_path)
        with self._lock:
            if canonical not in self._known_sources:
                self._known_sources.add(canonical)
                self._primed_count += 1

    def primed_count(self) -> int:
        """How many pre-existing files have been primed (claimed and ignored)."""
        with self._lock:
            return self._primed_count

    # -- claim / complete ------------------------------------------------

    def claim_next(self) -> QueueItem | None:
        """Atomically claim the next runnable item, or ``None`` if none ready.

        Skips items whose profile (or the whole queue) is paused and items whose
        backoff window has not elapsed. The claimed item transitions to
        ``processing`` and its attempt count is incremented.
        """
        now = self._clock()
        with self._lock:
            if self._globally_paused:
                return None
            for item_id in self._order:
                item = self._items[item_id]
                if item.state != STATE_QUEUED:
                    continue
                if item.profile_id in self._paused_profiles:
                    continue
                if item.not_before > now:
                    continue
                claimed = replace(
                    item,
                    state=STATE_PROCESSING,
                    attempts=item.attempts + 1,
                    updated_at=now,
                )
                self._items[item_id] = claimed
                self._save_locked()
                self._emit("claimed", claimed)
                return claimed
            return None

    def mark_done(self, item_id: str, message: str = "", result_path: str = "") -> None:
        self._finalize(item_id, STATE_DONE, message, result_path)

    def mark_skipped(self, item_id: str, message: str = "") -> None:
        self._finalize(item_id, STATE_SKIPPED, message, "")

    def mark_failed(self, item_id: str, message: str = "") -> None:
        """Record a failure, retrying with bounded backoff until attempts run out."""
        now = self._clock()
        with self._lock:
            item = self._items.get(item_id)
            if item is None:
                return
            if item.attempts < self._max_attempts:
                backoff = min(self._base_backoff * (2 ** max(0, item.attempts - 1)), _MAX_BACKOFF)
                requeued = replace(
                    item,
                    state=STATE_QUEUED,
                    updated_at=now,
                    not_before=now + backoff,
                    message=message,
                )
                self._items[item_id] = requeued
                self._save_locked()
                self._emit("retry", requeued)
                return
            failed = replace(item, state=STATE_FAILED, updated_at=now, message=message)
            self._items[item_id] = failed
            self._save_locked()
        self._emit("failed", self._items[item_id])

    def retry(self, item_id: str) -> bool:
        """Manually re-queue a failed item, resetting its backoff window."""
        now = self._clock()
        with self._lock:
            item = self._items.get(item_id)
            if item is None or item.state != STATE_FAILED:
                return False
            requeued = replace(item, state=STATE_QUEUED, updated_at=now, not_before=now, message="")
            self._items[item_id] = requeued
            self._save_locked()
        self._emit("retry", self._items[item_id])
        return True

    def _finalize(self, item_id: str, state: str, message: str, result_path: str) -> None:
        now = self._clock()
        with self._lock:
            item = self._items.get(item_id)
            if item is None:
                return
            finished = replace(
                item,
                state=state,
                updated_at=now,
                message=message,
                result_path=result_path,
            )
            self._items[item_id] = finished
            self._save_locked()
        self._emit(state, self._items[item_id])

    # -- pause / resume --------------------------------------------------

    def pause(self) -> None:
        with self._lock:
            self._globally_paused = True
        self._emit("paused", None)

    def resume(self) -> None:
        with self._lock:
            self._globally_paused = False
        self._emit("resumed", None)

    @property
    def is_paused(self) -> bool:
        with self._lock:
            return self._globally_paused

    def pause_profile(self, profile_id: str) -> None:
        with self._lock:
            self._paused_profiles.add(profile_id)
        self._emit("profile_paused", None)

    def resume_profile(self, profile_id: str) -> None:
        with self._lock:
            self._paused_profiles.discard(profile_id)
        self._emit("profile_resumed", None)

    def is_profile_paused(self, profile_id: str) -> bool:
        with self._lock:
            return profile_id in self._paused_profiles

    # -- inspection ------------------------------------------------------

    def items(self) -> list[QueueItem]:
        """All items in stable insertion order."""
        with self._lock:
            return [self._items[item_id] for item_id in self._order]

    def items_by_state(self, state: str) -> list[QueueItem]:
        return [item for item in self.items() if item.state == state]

    def get(self, item_id: str) -> QueueItem | None:
        with self._lock:
            return self._items.get(item_id)

    def counts(self) -> dict[str, int]:
        counts = {state: 0 for state in _ALL_STATES}
        for item in self.items():
            counts[item.state] = counts.get(item.state, 0) + 1
        return counts

    def pending_count(self) -> int:
        with self._lock:
            return sum(1 for item in self._items.values() if item.state == STATE_QUEUED)

    # -- clearing --------------------------------------------------------

    def clear_finished(self) -> int:
        """Drop terminal (done/skipped) items; returns how many were removed."""
        removed = 0
        with self._lock:
            keep_order: list[str] = []
            for item_id in self._order:
                item = self._items[item_id]
                if item.state in _TERMINAL_STATES:
                    del self._items[item_id]
                    self._known_sources.discard(item.source_path)
                    removed += 1
                else:
                    keep_order.append(item_id)
            self._order = keep_order
            if removed:
                self._save_locked()
        if removed:
            self._emit("cleared", None)
        return removed

    def clear_all(self) -> int:
        """Remove every item regardless of state; returns how many were removed."""
        with self._lock:
            removed = len(self._order)
            self._items.clear()
            self._order.clear()
            self._known_sources.clear()
            if removed:
                self._save_locked()
        if removed:
            self._emit("cleared", None)
        return removed

    # -- persistence -----------------------------------------------------

    def _emit(self, event: str, item: QueueItem | None) -> None:
        if self._listener is None:
            return
        try:
            self._listener(event, item)
        except Exception:  # a bad listener must never break the queue
            logger.exception("Watch queue listener failed for event %s", event)

    def _save_locked(self) -> None:
        if self._storage_path is None:
            return
        payload = {
            "schema_version": SCHEMA_VERSION,
            "items": [self._items[item_id].to_dict() for item_id in self._order],
        }
        try:
            write_json_atomic(self._storage_path, payload)
        except OSError:
            logger.exception("Failed to persist watch queue to %s", self._storage_path)

    def _load(self) -> None:
        assert self._storage_path is not None
        try:
            raw = read_json(self._storage_path, default=None)
        except (OSError, ValueError):
            logger.exception("Failed to read watch queue from %s", self._storage_path)
            return
        if not isinstance(raw, dict):
            return
        raw_items = raw.get("items")
        if not isinstance(raw_items, Iterable):
            return
        for entry in raw_items:
            if not isinstance(entry, dict):
                continue
            item = QueueItem.from_dict(entry)
            if item.item_id in self._items:
                continue
            self._items[item.item_id] = item
            self._order.append(item.item_id)
            if item.source_path and item.state not in _TERMINAL_STATES:
                self._known_sources.add(item.source_path)


__all__ = [
    "SCHEMA_VERSION",
    "STATE_DONE",
    "STATE_FAILED",
    "STATE_PROCESSING",
    "STATE_QUEUED",
    "STATE_SKIPPED",
    "QueueItem",
    "QueueListener",
    "WatchQueue",
]
