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

from .monitor_policy import MONITOR_WATCH_FOLDER, MonitorPolicy, resolve_monitor_policy
from .watch_actions import WatchActionRegistry, default_registry
from .watch_default import (
    DEFAULT_WATCH_PROFILE_ID,
    default_watch_profile,
    wants_default_watch,
)
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
        settings: object | None = None,
        policy: MonitorPolicy | None = None,
        on_tick: Callable[[str], None] | None = None,
    ) -> None:
        """``settings`` (or an explicit ``policy``) supplies the shared
        ambient-monitor triple for watched folders: cadence, audible tick, and
        whether a result interrupts speech. ``on_tick`` is the shell's earcon
        player; without one the tick is silently skipped, which is why the
        default construction behaves exactly as it did before.
        """
        self._data_dir = Path(data_dir)
        #: The live settings object: the Watch Folders page's default folder and
        #: its three switches are read from it each time the watch (re)starts.
        self._settings = settings
        #: Whether the enabled profiles run, as chosen by the last start(). The
        #: default folder is decided by settings, not by the caller.
        self._run_profiles = True
        self._policy = policy or resolve_monitor_policy(settings, MONITOR_WATCH_FOLDER)
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
        self.manager = WatchManager(self.queue, policy=self._policy, on_tick=on_tick)
        self.worker = WatchWorker(
            queue=self.queue,
            registry=self.registry,
            profile_lookup=self._lookup_profile,
        )
        self._running = False

    # -- lifecycle -------------------------------------------------------

    @property
    def is_running(self) -> bool:
        return self._running

    def refresh_policy(self, settings: object) -> None:
        """Re-resolve the monitor policy from *settings* and adopt it live.

        The policy was snapshotted at construction, so the watch folder's
        shared monitor controls (cadence, tick sound, interrupt) were
        restart-only — the P0.3 staleness class. Called from the settings-apply
        path; the manager's pollers pick the new values up on their next loop.
        """
        self._policy = resolve_monitor_policy(settings, MONITOR_WATCH_FOLDER)
        self.manager.set_policy(self._policy)
        # The default folder and its switches are live too: a changed folder,
        # subfolder or existing-files choice applies to a running watch now.
        self._settings = settings
        self._reapply_if_running()

    @property
    def policy(self) -> MonitorPolicy:
        """The ambient-monitor policy for watched folders.

        The shell reads ``policy.force_speech`` when it announces what the
        queue found, so "let results interrupt speech" means the same thing
        here as it does for every other monitor.
        """
        return self._policy

    def is_feature_enabled(self) -> bool:
        if self._feature_enabled is None:
            return True
        return bool(self._feature_enabled(WATCH_FEATURE_ID))

    def start(self, *, profiles: bool = True) -> list[str]:
        """Start the worker and pollers for all enabled profiles.

        The Watch Folders page's default folder joins them when *Start watching
        automatically* is on and a folder is chosen (see ``watch_default``).
        ``profiles=False`` runs the default folder alone -- the launch path when
        only that switch is on.

        Does nothing and returns an empty list when the watch feature is off, so
        the subsystem disappears in lockstep with its flag (FLAG-1).
        """
        if self._running:
            return list(self.manager.active_profile_ids())
        if not self.is_feature_enabled():
            return []
        self._run_profiles = profiles
        self.worker.start()
        started = self.manager.start(self._profiles_to_run())
        self._running = True
        return started

    @property
    def default_profile(self) -> WatchProfile | None:
        """The default folder's rule as settings describe it now, or None."""
        return default_watch_profile(self._settings)

    def _profiles_to_run(self) -> list[WatchProfile]:
        running = self.store.enabled_profiles() if self._run_profiles else []
        default = self.default_profile
        if default is not None and wants_default_watch(self._settings):
            running.append(default)
        return running

    def _lookup_profile(self, profile_id: str) -> WatchProfile | None:
        """The worker's lookup: the stored profiles, plus the default folder's rule."""
        if profile_id == DEFAULT_WATCH_PROFILE_ID:
            return self.default_profile
        return self.store.lookup(profile_id)

    def stop(self) -> None:
        if not self._running:
            return
        self.manager.stop()
        self.worker.stop()
        self._running = False

    def restart(self) -> list[str]:
        """Apply profile or feature changes by cleanly cycling the subsystem."""
        self.stop()
        return self.start(profiles=self._run_profiles)

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
            self.manager.start(self._profiles_to_run())

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
