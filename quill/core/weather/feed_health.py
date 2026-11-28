"""Alert-feed health: telling "no current alerts" apart from "could not reach
the service" (Quill Weather 2.3.0).

Weather Guardian watches National Weather Service alerts. A watcher that says
nothing when the service is down sounds exactly like a watcher that has nothing
to report, and for a safety app that silence is the worst possible answer. This
module is the memory behind the difference: per watched place it records the
last successful check, the last attempt, how many attempts in a row have failed
and why, and the last alerts the service actually provided.

Three rules the rest of the app leans on:

* A failed check is **never** an empty answer. Recording a failure does not
  touch the last known alerts, and nothing here ever produces an all-clear.
* The user is told once, plainly, when checks have been failing long enough to
  matter, reminded only after a long gap, and told once when it recovers.
* In Safe Mode the network checks are off by choice; that is reported as such,
  never as "unreachable".

Everything is pure and wx-free. The clock is always passed in (epoch seconds), so
every threshold is testable with a fake clock. The tracker persists atomically to
``weather_feed_health.json`` in the data directory; a damaged file is kept aside
and reads as "never checked".
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime, tzinfo
from enum import StrEnum
from typing import Any

from quill.core.weather.models import WeatherAlert

_SCHEMA = 1

#: Checks must have failed for about this long, and at least this many times in
#: a row, before the service is called unreachable.
UNREACHABLE_AFTER_SECONDS = 10 * 60
UNREACHABLE_MIN_ATTEMPTS = 3
#: Sooner while an alert was active at the last good check: that is when a
#: silent failure is most dangerous.
UNREACHABLE_ACTIVE_AFTER_SECONDS = 2 * 60
UNREACHABLE_ACTIVE_MIN_ATTEMPTS = 2
#: While still failing, repeat the warning no more often than this.
REPEAT_AFTER_SECONDS = 30 * 60
#: Data older than this is spoken with an "as of" time.
STALE_AFTER_SECONDS = 15 * 60

#: Bounds on what is kept on disk.
MAX_PLACES = 50
MAX_ALERTS_PER_PLACE = 25
_MAX_TEXT = 400


class FailureKind(StrEnum):
    CONNECT = "connect"  # cannot connect, or timed out
    SERVICE = "service"  # the service answered with an error (HTTP 5xx, 429...)
    UNREADABLE = "unreadable"  # the service answered with something unusable
    SAFE_MODE = "safe_mode"  # network checks are off in Safe Mode


class FeedState(StrEnum):
    NEVER = "never"  # no check has completed yet
    HEALTHY = "healthy"
    DEGRADED = "degraded"  # a recent failure, within the grace window
    UNREACHABLE = "unreachable"
    CHECKS_OFF = "checks_off"  # Safe Mode


_STATE_RANK = {
    FeedState.HEALTHY: 0,
    FeedState.NEVER: 1,
    FeedState.CHECKS_OFF: 2,
    FeedState.DEGRADED: 3,
    FeedState.UNREACHABLE: 4,
}

_STATE_WORDS = {
    FeedState.NEVER: "Not checked yet",
    FeedState.HEALTHY: "Working",
    FeedState.DEGRADED: "Having trouble",
    FeedState.UNREACHABLE: "Cannot be reached",
    FeedState.CHECKS_OFF: "Network checks are off",
}

_KIND_WORDS = {
    FailureKind.CONNECT: "Quill Weather could not connect to the National Weather Service, "
    "or the connection timed out.",
    FailureKind.SERVICE: "The National Weather Service answered with an error, so it may be "
    "busy or having problems.",
    FailureKind.UNREADABLE: "The National Weather Service sent a reply Quill Weather could not "
    "read.",
    FailureKind.SAFE_MODE: "Network checks are turned off in Safe Mode, so no alert checks are "
    "being made.",
}


def classify_failure(error: BaseException) -> tuple[FailureKind, str]:
    """Sort an exception from an alert fetch into a kind and a short detail.

    Looks through the ``__cause__`` chain, because ``nws.active_alerts`` wraps
    the transport error in a ``WeatherError``.
    """
    import http.client
    import ssl
    import urllib.error

    seen: BaseException | None = error
    depth = 0
    while seen is not None and depth < 6:
        if isinstance(seen, urllib.error.HTTPError):
            return FailureKind.SERVICE, f"HTTP {seen.code}"
        if isinstance(seen, TimeoutError):
            return FailureKind.CONNECT, "timed out"
        if isinstance(seen, ssl.SSLError):
            return FailureKind.CONNECT, "secure connection failed"
        if isinstance(seen, urllib.error.URLError | ConnectionError):
            return FailureKind.CONNECT, "could not connect"
        if isinstance(seen, ValueError | http.client.HTTPException | KeyError | TypeError):
            return FailureKind.UNREADABLE, "unreadable reply"
        seen = seen.__cause__ or seen.__context__
        depth += 1
    if "safe mode" in str(error).lower():
        return FailureKind.SAFE_MODE, "Safe Mode"
    if isinstance(error, OSError):
        return FailureKind.CONNECT, "could not connect"
    return FailureKind.CONNECT, "could not connect"


@dataclass(slots=True)
class KnownAlert:
    """One alert the service returned, kept for "last alerts the service gave"."""

    id: str = ""
    event: str = ""
    headline: str = ""
    severity: str = ""
    issued: str = ""
    expires: str = ""
    area: str = ""
    #: True when a rule of the user's hid this one from speech (see alert_rules).
    hidden: bool = False

    @classmethod
    def from_alert(cls, alert: WeatherAlert, *, hidden: bool = False) -> KnownAlert:
        return cls(
            id=alert.id[:_MAX_TEXT],
            event=alert.event[:_MAX_TEXT],
            headline=alert.headline[:_MAX_TEXT],
            severity=alert.severity[:40],
            issued=(alert.effective or alert.onset)[:60],
            expires=(alert.expires or alert.ends)[:60],
            area=alert.area_description[:_MAX_TEXT],
            hidden=hidden,
        )


@dataclass(slots=True)
class PlaceHealth:
    """The health of the alert feed for one watched place."""

    place_id: str
    label: str = ""
    last_success: float | None = None
    last_attempt: float | None = None
    consecutive_failures: int = 0
    first_failure: float | None = None
    last_failure_kind: FailureKind | None = None
    last_failure_detail: str = ""
    #: Alerts from the last *successful* check, with the time they were fetched
    #: (``last_success``). Never cleared by a failure.
    last_alerts: list[KnownAlert] = field(default_factory=list)

    def state(self, now: float, *, checks_off: bool = False) -> FeedState:
        if checks_off:
            return FeedState.CHECKS_OFF
        if self.last_attempt is None and self.last_success is None:
            return FeedState.NEVER
        if self.consecutive_failures == 0:
            return FeedState.HEALTHY if self.last_success is not None else FeedState.NEVER
        had_alerts = bool(self.last_alerts)
        needed = UNREACHABLE_ACTIVE_MIN_ATTEMPTS if had_alerts else UNREACHABLE_MIN_ATTEMPTS
        window = UNREACHABLE_ACTIVE_AFTER_SECONDS if had_alerts else UNREACHABLE_AFTER_SECONDS
        since = self.last_success if self.last_success is not None else self.first_failure
        if self.consecutive_failures >= needed and since is not None and now - since >= window:
            return FeedState.UNREACHABLE
        return FeedState.DEGRADED

    def is_stale(self, now: float) -> bool:
        return self.last_success is None or now - self.last_success >= STALE_AFTER_SECONDS


@dataclass(slots=True)
class Notice:
    """Something to say or toast about the feed. ``kind`` is one of
    ``unreachable``, ``still_unreachable`` or ``recovered``."""

    kind: str
    title: str
    text: str


def format_clock(moment: float, now: float, tz: tzinfo | None = None) -> str:
    """'3:12 PM', or 'Nov 26 at 3:12 PM' when it was not today."""
    when = datetime.fromtimestamp(moment, tz)
    today = datetime.fromtimestamp(now, tz)
    clock = when.strftime("%I:%M %p").lstrip("0")
    if when.date() == today.date():
        return clock
    return f"{when.strftime('%b')} {when.day} at {clock}"


def _plural(count: int, word: str) -> str:
    return f"{count} {word}" if count == 1 else f"{count} {word}s"


def _join(items: list[str]) -> str:
    if len(items) <= 1:
        return "".join(items)
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return f"{', '.join(items[:-1])}, and {items[-1]}"


class FeedHealthTracker:
    """Per-place feed health plus the once-only announcement bookkeeping."""

    def __init__(self, *, safe_mode: bool = False, tz: tzinfo | None = None) -> None:
        self.places: dict[str, PlaceHealth] = {}
        self.safe_mode = safe_mode
        self.tz = tz
        #: When the "cannot reach" warning was last given; None when not in one.
        self.warned_at: float | None = None

    # -- recording --------------------------------------------------------

    def _place(self, place_id: str, label: str) -> PlaceHealth:
        health = self.places.get(place_id)
        if health is None:
            health = PlaceHealth(place_id=place_id)
            self.places[place_id] = health
        if label:
            health.label = label
        return health

    def record_success(
        self,
        place_id: str,
        label: str,
        alerts: Iterable[WeatherAlert],
        now: float,
        *,
        hidden_ids: Iterable[str] = (),
    ) -> None:
        """A check completed. An empty list here means the service said "no
        alerts" -- the only way last_alerts is ever replaced."""
        health = self._place(place_id, label)
        hidden = set(hidden_ids)
        health.last_alerts = [
            KnownAlert.from_alert(a, hidden=a.id in hidden)
            for a in list(alerts)[:MAX_ALERTS_PER_PLACE]
        ]
        health.last_success = now
        health.last_attempt = now
        health.consecutive_failures = 0
        health.first_failure = None
        health.last_failure_kind = None
        health.last_failure_detail = ""

    def record_failure(
        self,
        place_id: str,
        label: str,
        error: BaseException | FailureKind,
        now: float,
    ) -> None:
        """A check failed. Last known alerts and last success are untouched."""
        health = self._place(place_id, label)
        if isinstance(error, FailureKind):
            kind, detail = error, ""
        else:
            kind, detail = classify_failure(error)
        health.last_attempt = now
        health.consecutive_failures += 1
        if health.first_failure is None:
            health.first_failure = now
        health.last_failure_kind = kind
        health.last_failure_detail = detail

    # -- reading ----------------------------------------------------------

    def state_of(self, place_id: str, now: float) -> FeedState:
        health = self.places.get(place_id)
        if health is None:
            return FeedState.CHECKS_OFF if self.safe_mode else FeedState.NEVER
        return health.state(now, checks_off=self.safe_mode)

    def overall_state(self, now: float, place_ids: Iterable[str] | None = None) -> FeedState:
        ids = list(place_ids) if place_ids is not None else list(self.places)
        if self.safe_mode:
            return FeedState.CHECKS_OFF
        if not ids:
            return FeedState.NEVER
        return max((self.state_of(i, now) for i in ids), key=lambda s: _STATE_RANK[s])

    def unreachable_places(self, now: float) -> list[PlaceHealth]:
        if self.safe_mode:
            return []
        return [h for h in self.places.values() if h.state(now) is FeedState.UNREACHABLE]

    def latest_check_succeeded(self, place_id: str) -> bool:
        health = self.places.get(place_id)
        return (
            health is not None
            and health.consecutive_failures == 0
            and (health.last_success is not None)
        )

    # -- announcements ----------------------------------------------------

    def end_of_round(self, now: float) -> Notice | None:
        """Call after every poll round. Returns the one thing worth saying, if any."""
        if self.safe_mode:
            return None
        down = self.unreachable_places(now)
        if down:
            if self.warned_at is None:
                self.warned_at = now
                return self._unreachable_notice(down, now, "unreachable")
            if now - self.warned_at >= REPEAT_AFTER_SECONDS:
                self.warned_at = now
                return self._unreachable_notice(down, now, "still_unreachable")
            return None
        if self.warned_at is not None:
            self.warned_at = None
            return Notice(
                "recovered",
                "Weather alerts are back",
                "Quill Weather can reach the National Weather Service again. "
                "Alert checks are working.",
            )
        return None

    def _unreachable_notice(self, down: list[PlaceHealth], now: float, kind: str) -> Notice:
        lead = (
            "Quill Weather still cannot reach the National Weather Service."
            if kind == "still_unreachable"
            else "Quill Weather cannot reach the National Weather Service."
        )
        return Notice(
            kind,
            "Weather alerts may be missing",
            f"{lead} Alerts may be missing. {self.last_check_sentence(down, now)}",
        )

    def last_check_sentence(self, places: list[PlaceHealth], now: float) -> str:
        """'The last successful check was at 3:12 PM, and it found no alerts.'"""
        done = [p for p in places if p.last_success is not None]
        if not done:
            return "There has not been a successful check yet."
        latest = max(done, key=lambda p: p.last_success or 0.0)
        at = format_clock(latest.last_success or 0.0, now, self.tz)
        count = sum(len(p.last_alerts) for p in done)
        found = "it found no alerts" if count == 0 else f"it found {_plural(count, 'alert')}"
        return f"The last successful check was at {at}, and {found}."

    def as_of_phrase(self, place_ids: Iterable[str], now: float) -> str:
        """' As of 3:12 PM.' when any of the places has old data, else ''."""
        stale = [
            self.places[i]
            for i in place_ids
            if i in self.places
            and self.places[i].is_stale(now)
            and self.places[i].last_success is not None
        ]
        if not stale:
            return ""
        oldest = min(stale, key=lambda p: p.last_success or 0.0)
        return f" As of {format_clock(oldest.last_success or 0.0, now, self.tz)}."

    # -- status text ------------------------------------------------------

    def status_text(self, place_ids: list[str], labels: dict[str, str], now: float) -> str:
        """The plain-text Alert Feed Status report."""
        lines: list[str] = []
        overall = self.overall_state(now, place_ids)
        lines.append("Alert feed status")
        if self.safe_mode:
            lines.append(
                "Network checks are off. Quill Weather is in Safe Mode, so it is not checking "
                "for alerts. This is not a service problem. Restart without Safe Mode to "
                "check for alerts."
            )
            return "\n".join(lines)
        lines.append(f"Overall: {_STATE_WORDS[overall]}.")
        if not place_ids:
            lines.append("No places are being watched yet.")
            return "\n".join(lines)
        for pid in place_ids:
            health = self.places.get(pid)
            name = labels.get(pid) or (health.label if health else pid)
            lines.append("")
            lines.append(name)
            state = self.state_of(pid, now)
            lines.append(f"  State: {_STATE_WORDS[state]}")
            if health is None or health.last_attempt is None and health.last_success is None:
                lines.append("  No check has completed yet.")
                continue
            ok = health.last_success
            lines.append(
                "  Last successful check: "
                + (format_clock(ok, now, self.tz) if ok is not None else "none yet")
            )
            if health.last_attempt is not None:
                lines.append(f"  Last attempt: {format_clock(health.last_attempt, now, self.tz)}")
            if health.consecutive_failures and health.last_failure_kind is not None:
                lines.append(
                    f"  What went wrong: {_KIND_WORDS[health.last_failure_kind]} "
                    f"({_plural(health.consecutive_failures, 'failed attempt')} in a row.)"
                )
            lines.extend(self._alert_lines(health, now))
        return "\n".join(lines)

    def _alert_lines(self, health: PlaceHealth, now: float) -> list[str]:
        if health.last_success is None:
            return ["  Alerts: none known, because no check has succeeded."]
        stale = health.is_stale(now) or health.consecutive_failures > 0
        when = format_clock(health.last_success, now, self.tz)
        tag = f"last known, from {when}" if stale else f"from {when}"
        if not health.last_alerts:
            return [f"  Alerts: the service reported no alerts ({tag})."]
        lines = [f"  Alerts the service provided ({tag}):"]
        for a in health.last_alerts:
            bits = [a.event or "Alert"]
            if a.severity:
                bits.append(a.severity)
            if a.area:
                bits.append(a.area.split(";")[0].strip())
            if a.expires:
                bits.append(f"until {a.expires}")
            entry = ", ".join(bits)
            if a.headline:
                entry += f". {a.headline}"
            lines.append(f"    - {entry}")
        hidden = sum(1 for a in health.last_alerts if a.hidden)
        if hidden:
            lines.append(
                f"  {_plural(hidden, 'alert')} hidden by your settings. They are listed above, "
                "and in Active Alerts."
            )
        return lines

    def summary(self, now: float, place_ids: Iterable[str] | None = None) -> str:
        """One spoken sentence for the status command, before the full report."""
        ids = list(place_ids) if place_ids is not None else list(self.places)
        state = self.overall_state(now, ids)
        if state is FeedState.CHECKS_OFF:
            return "Network checks are off in Safe Mode, so Quill Weather is not checking alerts."
        if state is FeedState.NEVER:
            return "Quill Weather has not checked for alerts yet."
        if state is FeedState.HEALTHY:
            return "The alert feed is working. " + self.last_check_sentence(
                [self.places[i] for i in ids if i in self.places], now
            )
        if state is FeedState.DEGRADED:
            return "The last alert check failed. Quill Weather is trying again."
        return "Quill Weather cannot reach the National Weather Service. Alerts may be missing."

    def tooltip(self, now: float, place_ids: Iterable[str] | None = None) -> str:
        """A short tray tooltip: app name plus the feed state."""
        state = self.overall_state(now, place_ids)
        if state is FeedState.HEALTHY:
            return "Quill Weather: alert checks working"
        if state is FeedState.UNREACHABLE:
            return "Quill Weather: cannot reach the National Weather Service. Alerts may be missing"
        if state is FeedState.DEGRADED:
            return "Quill Weather: last alert check failed, trying again"
        if state is FeedState.CHECKS_OFF:
            return "Quill Weather: network checks are off (Safe Mode)"
        return "Quill Weather: no alert check yet"

    # -- persistence ------------------------------------------------------

    def to_json(self) -> dict[str, Any]:
        places = list(self.places.values())[-MAX_PLACES:]
        return {
            "version": _SCHEMA,
            "warned_at": self.warned_at,
            "places": [
                {
                    "place_id": p.place_id,
                    "label": p.label[:_MAX_TEXT],
                    "last_success": p.last_success,
                    "last_attempt": p.last_attempt,
                    "consecutive_failures": p.consecutive_failures,
                    "first_failure": p.first_failure,
                    "last_failure_kind": p.last_failure_kind.value if p.last_failure_kind else "",
                    "last_failure_detail": p.last_failure_detail[:80],
                    "last_alerts": [
                        {
                            "id": a.id,
                            "event": a.event,
                            "headline": a.headline,
                            "severity": a.severity,
                            "issued": a.issued,
                            "expires": a.expires,
                            "area": a.area,
                            "hidden": a.hidden,
                        }
                        for a in p.last_alerts[:MAX_ALERTS_PER_PLACE]
                    ],
                }
                for p in places
            ],
        }

    @classmethod
    def from_json(
        cls, raw: Any, *, safe_mode: bool = False, tz: tzinfo | None = None
    ) -> FeedHealthTracker:
        tracker = cls(safe_mode=safe_mode, tz=tz)
        if not isinstance(raw, dict):
            raise ValueError("feed health file is not an object")
        warned = raw.get("warned_at")
        tracker.warned_at = _opt_float(warned)
        entries = raw.get("places")
        if not isinstance(entries, list):
            raise ValueError("feed health file has no places list")
        for item in entries[:MAX_PLACES]:
            if not isinstance(item, dict) or not isinstance(item.get("place_id"), str):
                continue
            health = PlaceHealth(place_id=item["place_id"], label=str(item.get("label", "")))
            health.last_success = _opt_float(item.get("last_success"))
            health.last_attempt = _opt_float(item.get("last_attempt"))
            health.first_failure = _opt_float(item.get("first_failure"))
            failures = _opt_float(item.get("consecutive_failures"))
            health.consecutive_failures = max(0, int(failures)) if failures is not None else 0
            try:
                health.last_failure_kind = (
                    FailureKind(item["last_failure_kind"])
                    if item.get("last_failure_kind")
                    else None
                )
            except ValueError:
                health.last_failure_kind = None
            health.last_failure_detail = str(item.get("last_failure_detail", ""))[:80]
            for a in (item.get("last_alerts") or [])[:MAX_ALERTS_PER_PLACE]:
                if isinstance(a, dict):
                    health.last_alerts.append(
                        KnownAlert(
                            id=str(a.get("id", ""))[:_MAX_TEXT],
                            event=str(a.get("event", ""))[:_MAX_TEXT],
                            headline=str(a.get("headline", ""))[:_MAX_TEXT],
                            severity=str(a.get("severity", ""))[:40],
                            issued=str(a.get("issued", ""))[:60],
                            expires=str(a.get("expires", ""))[:60],
                            area=str(a.get("area", ""))[:_MAX_TEXT],
                            hidden=bool(a.get("hidden", False)),
                        )
                    )
            tracker.places[health.place_id] = health
        return tracker


def _opt_float(value: Any) -> float | None:
    """A finite number, or None (so 1e309 or NaN in the file reads as unknown)."""
    import math

    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    return float(value) if math.isfinite(value) else None
