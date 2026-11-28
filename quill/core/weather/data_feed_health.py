"""Feed health for Quill Weather's *data* feeds: history, records, nowcast,
approaching weather, pollen and marine.

The alert feed's health (``feed_health``) answers "no alerts, or could not
reach the service?". These feeds need the same honesty for a different
question: "no data for this date, or could not reach the service?". Each feed
is registered here once (:data:`FEEDS`), and every fetch reports its outcome,
so a failure is always spoken as a failure, with its reason, and never as an
empty answer.

The bookkeeping is the alert feed's own :class:`FeedHealthTracker` and its
thresholds and failure classifier, keyed by feed id instead of by place; only
the words differ, because these feeds are not the National Weather Service.

wx-free and strict-typed. Persists to ``weather_data_feed_health.json``.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from quill.core.weather.feed_health import (
    FailureKind,
    FeedHealthTracker,
    FeedState,
    classify_failure,
    format_clock,
)

logger = logging.getLogger(__name__)

_STORE_NAME = "weather_data_feed_health.json"


@dataclass(frozen=True, slots=True)
class FeedInfo:
    label: str  # for the status report: "Open-Meteo history"
    service: str  # for sentences: "Open-Meteo's historical weather service"


#: Every data feed Quill Weather uses, by id. Add a row before using a new feed.
FEEDS: dict[str, FeedInfo] = {
    "open_meteo_recent": FeedInfo(
        "Open-Meteo recent days", "Open-Meteo's forecast service, for the last 92 days"
    ),
    "open_meteo_archive": FeedInfo(
        "Open-Meteo history (Copernicus ERA5)", "Open-Meteo's historical weather service"
    ),
    "rcc_acis": FeedInfo(
        "NOAA RCC-ACIS station records and normals",
        "the NOAA Regional Climate Centers' ACIS service",
    ),
    "open_meteo_nowcast": FeedInfo(
        "Open-Meteo next hours, rain soon and daylight", "Open-Meteo's forecast service"
    ),
    "open_meteo_around": FeedInfo("Open-Meteo weather around you", "Open-Meteo's forecast service"),
    "open_meteo_pollen": FeedInfo("Open-Meteo pollen", "Open-Meteo's air quality service"),
    "open_meteo_marine": FeedInfo("Open-Meteo marine", "Open-Meteo's marine service"),
}

_STATE_WORDS = {
    FeedState.NEVER: "Not used yet",
    FeedState.HEALTHY: "Working",
    FeedState.DEGRADED: "Last request failed",
    FeedState.UNREACHABLE: "Cannot be reached",
    FeedState.CHECKS_OFF: "Network requests are off",
}

_KIND_REASON = {
    FailureKind.CONNECT: "could not connect, or the connection timed out",
    FailureKind.SERVICE: "it answered with an error, so it may be busy",
    FailureKind.UNREADABLE: "it sent a reply Quill Weather could not read",
    FailureKind.SAFE_MODE: "network requests are off in Safe Mode",
}


def failure_sentence(feed: str, error: BaseException) -> str:
    """The sentence to show or speak when a fetch failed. Never "no data"."""
    info = FEEDS[feed]
    from quill.core.weather.open_meteo_limits import OpenMeteoBusy

    if isinstance(error, OpenMeteoBusy) and error.args:
        return str(error.args[0])  # the Open-Meteo gate's own plain sentence
    kind, _detail = classify_failure(error)
    if kind is FailureKind.SAFE_MODE:
        return "Weather data is a network service, and network requests are off in Safe Mode."
    return (
        f"Quill Weather could not get this from {info.service}: {_KIND_REASON[kind]}. "
        "This is not the same as no data. Try again in a few minutes."
    )


class DataFeedHealth:
    """Per-feed health, using the alert feed's tracker underneath."""

    def __init__(self, *, safe_mode: bool = False) -> None:
        self.tracker = FeedHealthTracker(safe_mode=safe_mode)
        #: Lookups record from worker threads while the UI thread saves.
        self._lock = threading.Lock()

    def record_success(self, feed: str, now: float) -> None:
        with self._lock:
            self.tracker.record_success(feed, FEEDS[feed].label, (), now)

    def record_failure(self, feed: str, error: BaseException, now: float) -> None:
        with self._lock:
            self.tracker.record_failure(feed, FEEDS[feed].label, error, now)

    def state_of(self, feed: str, now: float) -> FeedState:
        return self.tracker.state_of(feed, now)

    def status_lines(self, now: float) -> list[str]:
        """The "Data feeds" section of the Alert Feed Status report: only feeds
        that have been used, since an unused one has nothing to say."""
        used = [f for f in FEEDS if f in self.tracker.places]
        if not used:
            return []
        lines = ["Data feeds (history, records, next hours, around you, pollen, marine)"]
        for feed in used:
            health = self.tracker.places[feed]
            state = self.state_of(feed, now)
            line = f"  {FEEDS[feed].label}: {_STATE_WORDS[state]}"
            if health.last_success is not None:
                line += f". Last worked at {format_clock(health.last_success, now)}"
            if health.consecutive_failures and health.last_failure_kind is not None:
                line += f". Last failure: {_KIND_REASON[health.last_failure_kind]}"
            lines.append(line + ".")
        return lines

    def to_json(self) -> dict[str, Any]:
        with self._lock:
            return self.tracker.to_json()

    @classmethod
    def from_json(cls, raw: Any, *, safe_mode: bool = False) -> DataFeedHealth:
        health = cls(safe_mode=safe_mode)
        health.tracker = FeedHealthTracker.from_json(raw, safe_mode=safe_mode)
        for feed in [f for f in health.tracker.places if f not in FEEDS]:
            del health.tracker.places[feed]  # a feed retired since it was saved
        return health


def load(data_dir: Path, *, safe_mode: bool = False) -> DataFeedHealth:
    """Missing or damaged reads as "not used yet"; never raises."""
    import json

    path = data_dir / _STORE_NAME
    if not path.exists():
        return DataFeedHealth(safe_mode=safe_mode)
    try:
        return DataFeedHealth.from_json(
            json.loads(path.read_text(encoding="utf-8")), safe_mode=safe_mode
        )
    except (OSError, ValueError, TypeError) as exc:
        logger.warning("weather data feed health is unreadable (%s); starting fresh", exc)
        return DataFeedHealth(safe_mode=safe_mode)


def save(data_dir: Path, health: DataFeedHealth) -> None:
    """Atomic and best effort: bookkeeping never breaks a lookup."""
    from quill.core.storage import write_json_atomic

    try:
        write_json_atomic(data_dir / _STORE_NAME, health.to_json())
    except OSError as exc:
        logger.warning("could not save weather data feed health: %s", exc)


_SHARED: dict[str, DataFeedHealth] = {}
_SHARED_LOCK = threading.Lock()


def shared(data_dir: Path, *, safe_mode: bool = False) -> DataFeedHealth:
    """The one record per data folder for this process, so every window and
    command reports into the same place."""
    key = str(data_dir)
    with _SHARED_LOCK:
        health = _SHARED.get(key)
        if health is None:
            health = load(data_dir, safe_mode=safe_mode)
            _SHARED[key] = health
        return health
