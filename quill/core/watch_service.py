"""High-level watch service facade (WATCH-1 through WATCH-7).

Bundles the watch profile store, durable queue, multi-profile manager, action
registry, and worker behind one wx-free entry point so the UI layer constructs a
single object and calls high-level methods (``start``, ``stop``, queue
inspection, profile CRUD). All persistence lives under the app data directory.

No ``wx`` imports: the UI passes in callbacks (open handler, queue listener) and
a feature check; this module owns the wiring and lifecycle.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

from .watch_actions import WatchActionRegistry, default_registry
from .watch_profile_store import WatchProfileStore
from .watch_profiles import WatchManager, WatchProfile
from .watch_queue import QueueItem, WatchQueue
from .watch_worker import WatchWorker

logger = logging.getLogger(__name__)

#: Feature id that gates the entire watch subsystem (FLAG-1).
WATCH_FEATURE_ID = "core.watch_folder"

_PROFILES_FILENAME = "watch-profiles.json"
_QUEUE_FILENAME = "watch-queue.json"


class WatchService:
    """Owns and coordinates the whole watch subsystem for the running app."""

    def __init__(
        self,
        *,
        data_dir: Path,
        feature_enabled: Callable[[str], bool] | None = None,
        on_open: Callable[[Path], None] | None = None,
        on_convert: Callable[[Path, str], Path] | None = None,
        on_run_macro: Callable[[Path, str], None] | None = None,
        on_ai: Callable[[Path, object], object] | None = None,
        queue_listener: Callable[[str, QueueItem | None], None] | None = None,
        registry: WatchActionRegistry | None = None,
    ) -> None:
        self._data_dir = Path(data_dir)
        self._feature_enabled = feature_enabled
        self._watch_dir = self._data_dir / "watch"
        self._watch_dir.mkdir(parents=True, exist_ok=True)

        self.store = WatchProfileStore(storage_path=self._watch_dir / _PROFILES_FILENAME)
        self.queue = WatchQueue(
            storage_path=self._watch_dir / _QUEUE_FILENAME,
            listener=queue_listener,
        )
        self.registry = registry or default_registry(
            feature_enabled=feature_enabled,
            on_open=on_open,
            on_convert=on_convert,
            on_run_macro=on_run_macro,
            on_ai=on_ai,  # type: ignore[arg-type]
        )
        self.manager = WatchManager(self.queue)
        self.worker = WatchWorker(
            queue=self.queue,
            registry=self.registry,
            profile_lookup=self.store.lookup,
        )
        self._running = False

    # -- lifecycle -------------------------------------------------------

    @property
    def is_running(self) -> bool:
        return self._running

    def is_feature_enabled(self) -> bool:
        if self._feature_enabled is None:
            return True
        return bool(self._feature_enabled(WATCH_FEATURE_ID))

    def start(self) -> list[str]:
        """Start the worker and pollers for all enabled profiles.

        Does nothing and returns an empty list when the watch feature is off, so
        the subsystem disappears in lockstep with its flag (FLAG-1).
        """
        if self._running:
            return list(self.manager.active_profile_ids())
        if not self.is_feature_enabled():
            return []
        self.worker.start()
        started = self.manager.start(self.store.enabled_profiles())
        self._running = True
        return started

    def stop(self) -> None:
        if not self._running:
            return
        self.manager.stop()
        self.worker.stop()
        self._running = False

    def restart(self) -> list[str]:
        """Apply profile or feature changes by cleanly cycling the subsystem."""
        self.stop()
        return self.start()

    # -- profile management (delegates to the store, restarts if running) ---

    def add_profile(self, profile: WatchProfile) -> WatchProfile:
        added = self.store.add(profile)
        self._reapply_if_running()
        return added

    def update_profile(self, profile: WatchProfile) -> bool:
        changed = self.store.update(profile)
        if changed:
            self._reapply_if_running()
        return changed

    def delete_profile(self, profile_id: str) -> bool:
        removed = self.store.delete(profile_id)
        if removed:
            self._reapply_if_running()
        return removed

    def set_profile_enabled(self, profile_id: str, enabled: bool) -> bool:
        changed = self.store.set_enabled(profile_id, enabled)
        if changed:
            self._reapply_if_running()
        return changed

    def duplicate_profile(self, profile_id: str) -> WatchProfile | None:
        return self.store.duplicate(profile_id)

    def profiles(self) -> list[WatchProfile]:
        return self.store.profiles()

    def _reapply_if_running(self) -> None:
        if self._running:
            self.manager.start(self.store.enabled_profiles())

    # -- queue passthroughs for the monitor (WATCH-4) -------------------

    def queue_items(self) -> list[QueueItem]:
        return self.queue.items()

    def queue_counts(self) -> dict[str, int]:
        return self.queue.counts()

    def primed_count(self) -> int:
        """Pre-existing files claimed-and-ignored (profiles with process_existing off)."""
        return self.queue.primed_count()

    def pause(self) -> None:
        self.queue.pause()

    def resume(self) -> None:
        self.queue.resume()

    def retry_item(self, item_id: str) -> bool:
        retried = self.queue.retry(item_id)
        if retried:
            self.worker.wake()
        return retried

    def clear_finished(self) -> int:
        return self.queue.clear_finished()


__all__ = ["WATCH_FEATURE_ID", "WatchService"]
