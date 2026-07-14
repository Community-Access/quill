"""Model lifecycle policy — idle-unload, single-flight loading, low-resource mode.

The AI footprint & optimization work (QUILL-PRD.md §5.25f) calls for an explicit
runtime-memory policy that ties together the ``warm()`` / ``unload()`` primitives
the speech and Kokoro providers already expose. This module is that policy, kept
**wx-free and headless-testable**: the UI (and the background task pool) drive it,
but it holds no widgets and imports no ``wx``.

Three behaviours, all opt-in / behaviour-preserving:

- **Idle-unload.** A resource untouched for ``idle_timeout`` seconds is a candidate
  for :meth:`ModelLifecycleManager.sweep_idle`, which calls the resource's own
  ``unload()``. A later use simply reloads (the warm cost). Unload is already
  no-op-safe on every provider, so an over-eager sweep can never corrupt state.
- **Single-flight loading.** :meth:`ModelLifecycleManager.loading` hands out one
  lock per resource key, so two rapid triggers can't double-load the same model.
- **Low-resource mode.** When enabled (a Settings value; may auto-enable on very
  low RAM), :meth:`ModelLifecycleManager.reserve` caps the number of *concurrently
  loaded* engines and evicts the least-recently-used one to make room — trading
  concurrency for fit. It **never disables** a feature; it serialises engines.

The manager never loads anything itself — callers own load/unload and simply tell
the manager what happened (:meth:`note_loaded`, :meth:`touch`, :meth:`note_unloaded`)
so it can make eviction/idle decisions. This keeps every provider's tested download
and warm path untouched.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

#: Sentinel meaning "no concurrency cap" (low-resource mode off).
UNLIMITED = 0

#: Below this much RAM, low-resource mode auto-enables (with a one-time notice) even
#: when the user has not turned it on. Above it, the setting is honoured as-is.
LOW_RAM_AUTO_THRESHOLD_GB = 4.0


def should_auto_low_resource(total_ram_gb: float) -> bool:
    """True when the machine is small enough to auto-enable low-resource mode.

    ``total_ram_gb <= 0`` means "unknown" — we do not auto-enable on unknown RAM,
    since guessing wrong would needlessly serialise a capable machine.
    """
    return 0 < total_ram_gb < LOW_RAM_AUTO_THRESHOLD_GB


def build_manager(
    *,
    low_resource_mode: bool,
    idle_unload_minutes: int,
    total_ram_gb: float,
) -> ModelLifecycleManager:
    """Construct a manager from the two Settings values and the machine's RAM.

    ``max_concurrent`` becomes 1 when the user enabled low-resource mode *or* the
    machine is below :data:`LOW_RAM_AUTO_THRESHOLD_GB`; otherwise it is
    :data:`UNLIMITED`. ``idle_unload_minutes`` (0 = never) becomes the idle timeout
    in seconds.
    """
    effective_low_resource = low_resource_mode or should_auto_low_resource(total_ram_gb)
    return ModelLifecycleManager(
        idle_timeout=max(0, idle_unload_minutes) * 60.0,
        max_concurrent=1 if effective_low_resource else UNLIMITED,
    )


@runtime_checkable
class Unloadable(Protocol):
    """Anything with a no-arg, no-op-safe ``unload()`` (every speech provider is)."""

    def unload(self) -> None: ...


@dataclass(slots=True)
class _Entry:
    key: str
    handle: Unloadable
    loaded_at: float
    last_used: float


@dataclass(slots=True)
class ModelLifecycleManager:
    """Track loaded model resources and apply the idle/eviction/single-flight policy.

    ``clock`` is injectable so tests can drive time deterministically; it defaults
    to a monotonic clock. ``idle_timeout`` is in seconds; ``max_concurrent`` is the
    low-resource cap (:data:`UNLIMITED` = off). All public methods are thread-safe.
    """

    idle_timeout: float = 600.0
    max_concurrent: int = UNLIMITED
    clock: Callable[[], float] = time.monotonic
    _entries: dict[str, _Entry] = field(default_factory=dict, init=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False)
    _load_locks: dict[str, threading.Lock] = field(default_factory=dict, init=False)

    # --- registration / usage tracking ------------------------------------

    def note_loaded(self, key: str, handle: Unloadable) -> None:
        """Record that ``key`` is now loaded (or re-touched if already tracked)."""
        now = self.clock()
        with self._lock:
            existing = self._entries.get(key)
            if existing is not None:
                existing.handle = handle
                existing.last_used = now
            else:
                self._entries[key] = _Entry(key, handle, loaded_at=now, last_used=now)

    def touch(self, key: str) -> None:
        """Mark ``key`` as just-used so it resists idle-unload and LRU eviction."""
        now = self.clock()
        with self._lock:
            entry = self._entries.get(key)
            if entry is not None:
                entry.last_used = now

    def note_unloaded(self, key: str) -> None:
        """Drop ``key`` from tracking (its handle was unloaded elsewhere)."""
        with self._lock:
            self._entries.pop(key, None)

    def loaded_keys(self) -> list[str]:
        """Currently-tracked (loaded) keys, most-recently-used last."""
        with self._lock:
            return [e.key for e in sorted(self._entries.values(), key=lambda e: e.last_used)]

    # --- single-flight -----------------------------------------------------

    def loading(self, key: str) -> threading.Lock:
        """Return the per-key load lock; hold it around a load to dedupe concurrent loads.

        Callers should ``with manager.loading(key):`` then re-check whether the model
        is already loaded before doing the expensive load, so a second waiter that
        wakes after the first finished does not reload.
        """
        with self._lock:
            lock = self._load_locks.get(key)
            if lock is None:
                lock = threading.Lock()
                self._load_locks[key] = lock
            return lock

    # --- idle sweep --------------------------------------------------------

    def sweep_idle(self, now: float | None = None) -> list[str]:
        """Unload every resource idle longer than ``idle_timeout``; return their keys.

        Safe to call on a timer from a background thread. ``unload()`` is invoked
        outside the manager lock so a slow unload never blocks usage tracking, and a
        failing ``unload()`` is swallowed (best-effort) but the entry is still dropped.
        """
        if self.idle_timeout <= 0:
            return []
        moment = self.clock() if now is None else now
        with self._lock:
            stale = [
                e for e in self._entries.values() if (moment - e.last_used) >= self.idle_timeout
            ]
            for entry in stale:
                self._entries.pop(entry.key, None)
        return self._unload_all(stale)

    # --- low-resource eviction --------------------------------------------

    def reserve(self, key: str) -> list[str]:
        """Make room for loading ``key`` under the concurrency cap; return evicted keys.

        Call **before** loading ``key``. With low-resource mode off
        (``max_concurrent == UNLIMITED``) this is a no-op. Otherwise, if loading
        ``key`` would exceed the cap, the least-recently-used *other* resources are
        unloaded until there is room. ``key`` itself is never evicted.
        """
        if self.max_concurrent <= UNLIMITED:
            return []
        with self._lock:
            if key in self._entries:
                return []  # already loaded — reserving it needs no new slot
            others = sorted(
                (e for e in self._entries.values() if e.key != key),
                key=lambda e: e.last_used,
            )
            # After loading key there will be len(others)+1 loaded; evict down to cap-1.
            surplus = (len(others) + 1) - self.max_concurrent
            victims = others[:surplus] if surplus > 0 else []
            for entry in victims:
                self._entries.pop(entry.key, None)
        return self._unload_all(victims)

    # --- helpers -----------------------------------------------------------

    def _unload_all(self, entries: list[_Entry]) -> list[str]:
        unloaded: list[str] = []
        for entry in entries:
            try:
                entry.handle.unload()
            except Exception:  # noqa: BLE001 - best-effort; a failed unload must not raise
                pass
            unloaded.append(entry.key)
        return unloaded
