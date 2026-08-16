"""Wiring the station catalog into the running app (host-taking functions).

Everything decided lives in ``quill/core/radio/catalog``; this is the layer
that knows about the app: where the profile is, when the minute tick fires,
which preference gates which layer, and what gets spoken. Same shape as
``schedule_wake_ui`` and ``settings_commands``.

The gating rules, stated once:

- ``catalog_enabled`` off means **off**: no store opened, no reads, no
  refresh of any layer, live browsing exactly as the 2.x releases did it.
- Safe Mode refreshes nothing, ever. Reading the local catalog is permitted -
  it is local data, exactly like favorites.
- A branch hidden in Choose Browse Sources is neither served nor refreshed.
- Every automatic announcement only speaks when something changed; a manual
  refresh always answers, because the listener asked.
"""

from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

#: Startup refresh is skipped when the catalog is younger than this.
_STARTUP_FLOOR_SECONDS = 6 * 3600


def catalog_for(host: Any) -> Any:
    """The host's CatalogStore, made on first use; None when disabled.

    Import of the seed happens lazily here too, off the UI thread's critical
    path (callers reach this from task-manager work), so first launch pays
    the 1.2 s decompress exactly once and never blocks the window.
    """
    if not bool(getattr(host._radio_history, "catalog_enabled", True)):
        return None
    store = getattr(host, "_radio_catalog", None)
    if store is not None:
        return store
    try:
        from quill.core.paths import app_data_dir
        from quill.core.radio.catalog.store import CatalogStore

        store = CatalogStore(app_data_dir())
        _ensure_seeded(store)
        host._radio_catalog = store
        return store
    except Exception:  # noqa: BLE001 - no catalog means live browsing, not a crash
        logger.debug("Catalog unavailable; browsing live.", exc_info=True)
        return None


def _ensure_seeded(store: Any) -> None:
    """Import the packaged seed when the profile has no catalog (or an older
    lineage). A missing seed is fine: the first refresh builds from live."""
    from quill.core.radio.catalog import SeedMissingError
    from quill.core.radio.catalog.seed import import_seed

    try:
        import_seed(store)
    except SeedMissingError:
        pass  # dev checkout / seedless build: refresh will populate
    except Exception:  # noqa: BLE001
        logger.warning("Catalog seed import failed; continuing live.", exc_info=True)


def shutdown(host: Any) -> None:
    store = getattr(host, "_radio_catalog", None)
    if store is not None:
        try:
            store.close()
        except Exception:  # noqa: BLE001
            pass


# -- refresh scheduling --------------------------------------------------------


def _visible_source_ids(host: Any) -> set[str]:
    from quill.core.radio import browse_sources

    enabled = getattr(host._radio_history, "browse_sources_enabled", None)
    return {node_id for node_id, _label in browse_sources.visible_roots(enabled)}


def _enabled_spec_ids(host: Any) -> set[str]:
    from quill.core.radio.catalog.sources import enabled_spec_ids

    return enabled_spec_ids(_visible_source_ids(host))


def maybe_refresh_on_tick(host: Any) -> None:
    """Called from the radio minute tick: refresh the single most overdue
    source when the cadence says so. A trickle, never a burst."""
    if getattr(host, "_safe_mode", False):
        return
    history = host._radio_history
    if not bool(getattr(history, "catalog_enabled", True)):
        return
    hours = int(getattr(history, "catalog_refresh_hours", 24) or 0)
    if hours <= 0:
        return
    _refresh_async(host, only_most_overdue=True, interval_hours=hours, announce_quietly=True)


def refresh_on_startup(host: Any) -> None:
    """Layer 1: shortly after launch, if enabled and the catalog is stale."""
    if getattr(host, "_safe_mode", False):
        return
    history = host._radio_history
    if not bool(getattr(history, "catalog_enabled", True)):
        return
    if not bool(getattr(history, "catalog_refresh_on_startup", True)):
        return

    def _work(**_kwargs: Any) -> None:
        store = catalog_for(host)
        if store is None:
            return
        try:
            age = store.age_seconds()
        except Exception:  # noqa: BLE001
            age = None
        if age is not None and age < _STARTUP_FLOOR_SECONDS:
            return
        _refresh_now(host, only_most_overdue=True, interval_hours=1, announce_quietly=True)

    task_manager = getattr(host, "_task_manager", None)
    if task_manager is not None:
        task_manager.submit("radio-catalog-startup", _work, on_success=None, on_failure=None)


def update_catalog_command(host: Any) -> None:
    """Station > Update Station Catalog... - every due source, spoken summary."""
    if getattr(host, "_safe_mode", False):
        host._announce("The station catalog does not update in Safe Mode.")
        return
    if not bool(getattr(host._radio_history, "catalog_enabled", True)):
        host._announce(
            "The station catalog is turned off in Preferences, so there is nothing to update."
        )
        return
    host._announce("Updating the station catalog...")
    _refresh_async(host, only_most_overdue=False, interval_hours=0, announce_quietly=False)


def _refresh_async(
    host: Any, *, only_most_overdue: bool, interval_hours: int, announce_quietly: bool
) -> None:
    task_manager = getattr(host, "_task_manager", None)
    if task_manager is None:
        return
    if getattr(host, "_catalog_refresh_running", False):
        if not announce_quietly:
            host._announce("A catalog update is already running.")
        return
    host._catalog_refresh_running = True

    def _work(**_kwargs: Any) -> object:
        return _refresh_now(
            host,
            only_most_overdue=only_most_overdue,
            interval_hours=interval_hours,
            announce_quietly=announce_quietly,
        )

    def _done(_op: str, summary: object) -> None:
        host._catalog_refresh_running = False
        _speak_summary(host, summary, announce_quietly=announce_quietly)

    def _failed(_op: str, _error: BaseException) -> None:
        host._catalog_refresh_running = False
        if not announce_quietly:
            host._announce("The catalog update could not finish; keeping what you have.")

    task_manager.submit("radio-catalog-refresh", _work, on_success=_done, on_failure=_failed)


def _refresh_now(
    host: Any, *, only_most_overdue: bool, interval_hours: int, announce_quietly: bool
) -> object:
    from quill.core.radio.catalog.refresh import due_sources, refresh
    from quill.core.radio.catalog.sources import station_specs

    store = catalog_for(host)
    if store is None:
        return None
    specs = station_specs()
    now = time.time()
    due = due_sources(
        specs,
        store,
        now=now,
        interval_hours=max(1, interval_hours) if interval_hours else 1,
        enabled_ids=_enabled_spec_ids(host),
    )
    if interval_hours == 0:  # manual: everything visible is due
        due = [s for s in specs if s.id in _enabled_spec_ids(host)]
    if only_most_overdue and due:
        due = due[:1]
    if not due:
        return None
    summary = refresh(due, store, now=now)
    store.reopen_if_stale()
    return summary


def _speak_summary(host: Any, summary: object, *, announce_quietly: bool) -> None:
    if summary is None:
        if not announce_quietly:
            host._announce("The station catalog is already up to date.")
        return
    spoken = getattr(summary, "spoken", None)
    changed = bool(getattr(summary, "changed_anything", False))
    if spoken is None:
        return
    if changed or not announce_quietly:
        host._announce(str(spoken()))
    host._last_catalog_summary = summary


# -- the offline moment (6.5) ---------------------------------------------------


def note_offline_serving(host: Any) -> None:
    """Say, once per session, that browsing is running from the catalog.

    The app quietly being fine when the internet is not is the whole feature;
    one sentence is how it takes credit without bragging.
    """
    if getattr(host, "_catalog_offline_noted", False):
        return
    store = getattr(host, "_radio_catalog", None)
    if store is None:
        return
    try:
        from quill.core.radio.catalog.summary import spoken_age

        age = spoken_age(store.age_seconds())
    except Exception:  # noqa: BLE001
        return
    host._catalog_offline_noted = True
    host._announce(f"You are offline. Browsing from your catalog, updated {age}.")
