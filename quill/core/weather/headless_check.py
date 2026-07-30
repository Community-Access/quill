"""One-shot, headless US-alert check -- the engine behind the OS-scheduled
background watch (QUILL Weather PRD 5.2, "runs with no window open").

A Windows Scheduled Task launches ``quill-weather --check-once`` on a cadence.
Each run is a short-lived process with no window and no in-memory history, so
"what have I already told the user about" is read from and written back to disk
(``monitor.load_notified_ids`` / ``save_notified_ids``). This module holds the
pure decision -- load the watched location, diff the current alerts against the
persisted set, and report the newly-issued ones -- with the network fetch
injected so it is fully unit-testable with no HTTP. The caller (the app's
``--check-once`` path) does the actual NWS fetch and shows the toast.

wx-free, no clock, no randomness.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from quill.core.weather import locations as loc_store
from quill.core.weather import monitor
from quill.core.weather.models import WeatherAlert

#: A fetcher takes (latitude, longitude) and returns the active alerts. The real
#: one is ``nws.active_alerts``; tests pass a stub.
AlertFetcher = Callable[[float, float], list[WeatherAlert]]


@dataclass(slots=True)
class HeadlessCheckResult:
    new_alerts: list[WeatherAlert] = field(default_factory=list)
    #: True on the very first check (records the baseline, notifies nothing).
    is_baseline: bool = False
    #: False when the check was skipped (Safe Mode, no saved location).
    checked: bool = False
    reason: str = ""


def run_check(
    data_dir: Path, *, fetch_alerts: AlertFetcher, safe_mode: bool = False
) -> HeadlessCheckResult:
    """Perform one headless alert check for the watched (or primary) location.

    Returns the alerts issued since the last check (empty on the first run,
    which just records a baseline). Persists the notified-id set so the next
    run -- and the live in-app watch -- will not repeat them. The caller must
    handle a fetch that raises (offline / transient); this function assumes a
    successful fetch and never invents notifications on error.
    """
    if safe_mode:
        return HeadlessCheckResult(checked=False, reason="safe mode")
    store = loc_store.load_locations(data_dir)
    config = monitor.load_config(data_dir)
    location = store.find(config.location_id) or store.primary()
    if location is None:
        return HeadlessCheckResult(checked=False, reason="no location")

    alerts = list(fetch_alerts(location.latitude, location.longitude))
    # Fold in any alerts contributed by enabled Quillin ``weather.alerts`` sources
    # (a QuillinAppHost populates the registry; empty when none / in Safe Mode).
    # The sources make no network call of their own, so this adds no egress.
    from quill.core.weather import alert_source_registry

    alerts.extend(alert_source_registry.alerts_from_sources())
    current_ids = {a.id for a in alerts if a.id}

    if not monitor.notified_ids_exist(data_dir):
        # First ever background check: record what's active without alerting, so
        # the user is not toasted for every alert already in effect.
        monitor.save_notified_ids(data_dir, current_ids)
        return HeadlessCheckResult(is_baseline=True, checked=True)

    previous = monitor.load_notified_ids(data_dir)
    fresh = [a for a in alerts if a.id and a.id not in previous]
    monitor.save_notified_ids(data_dir, current_ids)
    fresh.sort(key=lambda a: a.tier_rank)
    return HeadlessCheckResult(new_alerts=fresh, checked=True)


def toast_content(new_alerts: list[WeatherAlert], location_label: str) -> tuple[str, str]:
    """A (title, body) pair for the Windows toast, most-severe first. Empty
    inputs are the caller's responsibility to avoid (no alerts -> no toast)."""
    if len(new_alerts) == 1:
        alert = new_alerts[0]
        title = f"Weather alert: {alert.event}"
        body = alert.headline or f"A {alert.event} is in effect for {location_label}."
        return title, body
    events = ", ".join(a.event for a in new_alerts)
    title = f"{len(new_alerts)} new weather alerts"
    return title, f"{location_label}: {events}. Most urgent: {new_alerts[0].event}."
