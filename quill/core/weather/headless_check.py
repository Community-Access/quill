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

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from quill.core.weather import (
    alert_delivery,
    alert_rules_store,
    feed_health,
    feed_health_store,
    monitor,
    place_watch,
)
from quill.core.weather import locations as loc_store
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
    #: The place (or places, comma-separated) the new alerts are for.
    location_label: str = ""
    #: Set when the alert feed has been failing long enough to warn about, or has
    #: just recovered (see ``feed_health``); the caller shows it as a toast.
    feed_notice: feed_health.Notice | None = None


def run_check(
    data_dir: Path,
    *,
    fetch_alerts: AlertFetcher,
    safe_mode: bool = False,
    now: Callable[[], float] = time.time,
    on_notice: Callable[[feed_health.Notice], None] | None = None,
) -> HeadlessCheckResult:
    """Perform one headless alert check for every watched place.

    The places are the ones the live watch uses: the watch list when there is
    one, else every saved place. Returns the alerts issued since the last check
    (empty on the first run, which just records a baseline). Persists the
    notified-id set so the next run -- and the live in-app watch -- will not
    repeat them. A place whose fetch fails is skipped and the earlier ids are
    kept, so its alerts are not toasted again next time; when every fetch
    fails the first error is raised for the caller (offline / transient).
    """
    if safe_mode:
        return HeadlessCheckResult(checked=False, reason="safe mode")
    store = loc_store.load_locations(data_dir)
    config = monitor.load_config(data_dir)
    if not store.locations:
        return HeadlessCheckResult(checked=False, reason="no location")
    # Every saved place unless switched off; a snoozed or out-of-schedule place is
    # still checked, but quiet (an Extreme alert breaks through, as in the app).
    moment = datetime.fromtimestamp(now()).astimezone()
    muted, watches = set(config.muted_ids), place_watch.load_watches(data_dir)
    states = {
        loc.id: place_watch.state_of(loc.id, muted, watches, moment) for loc in store.locations
    }
    places = [loc for loc in store.locations if states[loc.id].checked]
    if not places:
        return HeadlessCheckResult(checked=False, reason="every place is switched off")
    choices = alert_rules_store.load_choices(data_dir)
    at = moment.time()
    quiet_reason = {
        pid: ("a snooze" if st is place_watch.WatchState.SNOOZED else "its schedule")
        for pid, st in states.items()
        if st.quiet
    }

    alerts: list[WeatherAlert] = []
    where: dict[str, str] = {}  # alert id -> the first place it was seen for
    failures: list[Exception] = []
    held_back: set[str] = set()  # alerts the user's choices keep from a toast
    tracker = feed_health_store.load_tracker(data_dir)
    for place in places:
        try:
            found = list(fetch_alerts(place.latitude, place.longitude))
        except Exception as error:  # noqa: BLE001 - one place offline is not all of them
            failures.append(error)
            # Recorded as a failure, never as an empty answer: the last known
            # alerts and the last good check time are left exactly as they were.
            tracker.record_failure(place.id, place.label, error, now())
            continue
        quiet = quiet_reason.get(place.id, "")
        hidden = alert_delivery.hidden_ids(found, place.id, choices, at, quiet)
        tracker.record_success(place.id, place.label, found, now(), hidden_ids=hidden)
        for alert in found:
            if alert.id and alert.id in where:
                continue  # one alert covering two watched places is said once
            if alert.id:
                where[alert.id] = place.label
                if alert.id in hidden:
                    held_back.add(alert.id)
            alerts.append(alert)
    notice = tracker.end_of_round(now())
    feed_health_store.save_tracker(data_dir, tracker)
    if notice is not None and on_notice is not None:
        on_notice(notice)
    if failures and len(failures) == len(places):
        raise failures[0]
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
        return HeadlessCheckResult(is_baseline=True, checked=True, feed_notice=notice)

    previous = monitor.load_notified_ids(data_dir)
    # An alert the choices hold back is still recorded as seen (it stays in the
    # alert list and in Alert Feed Status) but is not toasted.
    fresh = [a for a in alerts if a.id and a.id not in previous and a.id not in held_back]
    monitor.save_notified_ids(data_dir, current_ids | previous if failures else current_ids)
    fresh.sort(key=lambda a: a.tier_rank)
    labels = list(dict.fromkeys(where[a.id] for a in fresh if a.id in where))
    return HeadlessCheckResult(
        new_alerts=fresh, checked=True, location_label=", ".join(labels), feed_notice=notice
    )


def feed_notice_toast(notices: list[feed_health.Notice]) -> tuple[str, str]:
    """A (title, body) for feed notices that arrive without any new alert."""
    return notices[0].title, " ".join(n.text for n in notices)


def with_feed_notices(title: str, body: str, notices: list[feed_health.Notice]) -> tuple[str, str]:
    """An alert toast with any feed notice riding along (one toast per process)."""
    if not notices:
        return title, body
    return title, f"{body} {' '.join(n.text for n in notices)}"


def final_toast(
    data_dir: Path, result: HeadlessCheckResult | None, notices: list[feed_health.Notice]
) -> tuple[str, str] | None:
    """The one toast this run shows (a throwaway wx.App each, so only one): the
    new alerts with any feed notice riding along, a feed notice alone (the service
    failed for a while, or recovered), or None."""
    if result is not None and result.new_alerts:
        store = loc_store.load_locations(data_dir)
        primary = store.primary()
        label = result.location_label or (primary.label if primary is not None else "your area")
        return with_feed_notices(*toast_content(result.new_alerts, label), notices)
    return feed_notice_toast(notices) if notices else None


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
