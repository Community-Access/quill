"""Weather monitoring -- the decision logic behind Weather Guardian's US alert
watch (QUILL Weather PRD 5.2). Leasey's "Automatic Weather Reporting" announces
when the weather changes for a monitored place; this is QUILL's alert-focused
first slice: poll one US location's active watches/warnings/advisories on a
timer and speak the ones that are newly issued (and note when they all clear).
A "severe-weather mode" tightens the poll (down to the NWS 30-second courtesy
floor) while an alert is active, then relaxes back -- the free-API way to
approach push latency without a NWWS credential or an XMPP feed.

Everything here is pure and wx-free: the *scheduling* (a wx.Timer) and the
*fetch* (``nws.active_alerts`` off the task manager) live in the UI mixin, but
every decision -- what counts as new, what to say, whether to force speech --
is a testable function of the inputs. Config persists atomically like the rest
of the weather package.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from quill.core.weather.models import ALERT_TIERS, WeatherAlert

_STORE_NAME = "weather_monitor.json"
#: Background monitoring is gentle on the NWS: never poll more often than this
#: (well above the 30-second alert-poll floor). The UI clamps to it.
MONITOR_MIN_MINUTES = 5
MONITOR_MAX_MINUTES = 120
#: Severe-weather mode: when an alert is active the watch tightens its poll to
#: this many seconds for near-real-time updates, then relaxes back to the normal
#: interval when it clears. Floored at the NWS 30-second courtesy limit -- this
#: is the free-API alternative to a NWWS push feed.
MONITOR_FAST_FLOOR_SECONDS = 30
MONITOR_FAST_DEFAULT_SECONDS = 60
#: A newly-issued alert at or above this tier forces speech (interrupts), so a
#: tornado/flash-flood warning is never merely queued behind other output.
_FORCE_TIER_RANK = ALERT_TIERS.index("Urgent")


@dataclass(slots=True)
class MonitorConfig:
    """Persisted Weather Guardian settings."""

    enabled: bool = False
    #: Location to watch; "" means "whatever is the primary location".
    location_id: str = ""
    interval_minutes: int = 10
    #: Severe-weather mode: tighten the poll while an alert is active.
    fast_when_active: bool = True
    fast_interval_seconds: int = MONITOR_FAST_DEFAULT_SECONDS

    def normalized(self) -> MonitorConfig:
        self.interval_minutes = max(
            MONITOR_MIN_MINUTES, min(MONITOR_MAX_MINUTES, int(self.interval_minutes))
        )
        # The fast poll floors at the NWS courtesy limit and never exceeds the
        # normal interval (a "fast" cadence slower than normal is meaningless).
        self.fast_interval_seconds = max(
            MONITOR_FAST_FLOOR_SECONDS,
            min(self.interval_minutes * 60, int(self.fast_interval_seconds)),
        )
        return self

    def poll_seconds(self, has_active_alerts: bool) -> int:
        """The number of seconds until the next poll, given whether an alert is
        currently active. Severe-weather mode tightens the cadence when it is."""
        if self.fast_when_active and has_active_alerts:
            return self.fast_interval_seconds
        return self.interval_minutes * 60

    def cadence_phrase(self) -> str:
        """A spoken description of the polling cadence for the start summary."""
        normal = self.interval_minutes
        base = f"every {normal} minutes" if normal != 1 else "every minute"
        if not self.fast_when_active:
            return f"Checking {base}"
        secs = self.fast_interval_seconds
        fast = f"every {secs} seconds" if secs % 60 else f"every {secs // 60} minute(s)"
        return f"Checking {base}, or {fast} while an alert is active"


@dataclass(slots=True)
class MonitorState:
    """In-memory watch state for one session (not persisted -- a fresh start
    re-announces the current situation once, then only changes thereafter)."""

    #: Alert ids seen on the previous poll.
    known_alert_ids: set[str] = field(default_factory=set)
    #: Whether at least one poll has completed (so the first poll is a baseline,
    #: not a burst of "new" announcements for already-active alerts).
    primed: bool = False


@dataclass(slots=True)
class MonitorUpdate:
    """What one poll changed, relative to the prior state."""

    new_alerts: list[WeatherAlert] = field(default_factory=list)
    all_cleared: bool = False  # there were alerts, now there are none
    is_baseline: bool = False  # the first poll of the session


def apply_poll(state: MonitorState, current: list[WeatherAlert]) -> MonitorUpdate:
    """Fold a fresh alert list into the watch state and report what changed.

    The first poll of a session is a *baseline*: it records the current alerts
    without flagging them all as "new" (that would spam every active alert on
    startup). Subsequent polls flag only alerts whose id was not seen before,
    and note when a previously-alerting location has gone quiet.
    """
    current_ids = {a.id for a in current if a.id}
    if not state.primed:
        state.known_alert_ids = current_ids
        state.primed = True
        return MonitorUpdate(is_baseline=True)
    fresh = [a for a in current if a.id and a.id not in state.known_alert_ids]
    all_cleared = bool(state.known_alert_ids) and not current_ids
    state.known_alert_ids = current_ids
    fresh.sort(key=lambda a: a.tier_rank)
    return MonitorUpdate(new_alerts=fresh, all_cleared=all_cleared)


def should_force_speech(update: MonitorUpdate) -> bool:
    """Whether an update is urgent enough to interrupt (force speech). Any newly
    issued alert at or above the Urgent tier qualifies."""
    return any(a.tier_rank <= _FORCE_TIER_RANK for a in update.new_alerts)


def start_summary(location_label: str, current: list[WeatherAlert], config: MonitorConfig) -> str:
    """The one-time spoken line when monitoring starts."""
    cadence = config.cadence_phrase()
    if not current:
        return f"Weather monitoring on for {location_label}. No active alerts right now. {cadence}."
    n = len(current)
    plural = "" if n == 1 else "s"
    top = current[0].event
    return (
        f"Weather monitoring on for {location_label}. {n} active alert{plural} right now; "
        f"the most urgent is a {top}. {cadence}."
    )


def update_announcement(update: MonitorUpdate, location_label: str) -> str | None:
    """The spoken line for a poll's changes, or None when nothing changed.

    A baseline poll is silent (the start summary already spoke). Newly issued
    alerts are announced most-severe first; an all-clear is announced once."""
    if update.is_baseline:
        return None
    if update.new_alerts:
        if len(update.new_alerts) == 1:
            a = update.new_alerts[0]
            where = f" for {a.area_description.split(';')[0].strip()}" if a.area_description else ""
            return f"New weather alert for {location_label}: {a.event}{where}. {a.headline}".strip()
        events = ", ".join(a.event for a in update.new_alerts)
        return (
            f"{len(update.new_alerts)} new weather alerts for {location_label}: {events}. "
            f"The most urgent is a {update.new_alerts[0].event}."
        )
    if update.all_cleared:
        return f"Weather alerts for {location_label} have cleared. No active alerts now."
    return None


# -- persistence --------------------------------------------------------------


def _store_path(data_dir: Path) -> Path:
    return data_dir / _STORE_NAME


def config_exists(data_dir: Path) -> bool:
    """Whether a monitor config has ever been written. Lets a caller tell a
    first run (no file -> sensible default) from a user who deliberately turned
    monitoring off (file present, enabled False)."""
    return _store_path(data_dir).exists()


_NOTIFIED_STORE = "weather_notified.json"


def _notified_path(data_dir: Path) -> Path:
    return data_dir / _NOTIFIED_STORE


def notified_ids_exist(data_dir: Path) -> bool:
    """Whether the notified-alerts record has ever been written (first-run flag
    for the headless background check, which has no in-memory session state)."""
    return _notified_path(data_dir).exists()


def load_notified_ids(data_dir: Path) -> set[str]:
    """The set of alert ids already surfaced to the user, persisted so a
    short-lived background check (and the live in-app watch) never re-announce
    the same alert across process boundaries."""
    import json

    try:
        raw = json.loads(_notified_path(data_dir).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return set()
    if isinstance(raw, list):
        return {str(x) for x in raw}
    return set()


def save_notified_ids(data_dir: Path, ids: set[str]) -> None:
    """Persist the notified-alerts record atomically."""
    from quill.core.storage import write_json_atomic

    write_json_atomic(_notified_path(data_dir), sorted(ids))


def load_config(data_dir: Path) -> MonitorConfig:
    """Read the monitor config (absent or broken reads as disabled defaults)."""
    import json

    try:
        raw = json.loads(_store_path(data_dir).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return MonitorConfig()
    if not isinstance(raw, dict):
        return MonitorConfig()
    config = MonitorConfig()
    if isinstance(raw.get("enabled"), bool):
        config.enabled = raw["enabled"]
    if isinstance(raw.get("location_id"), str):
        config.location_id = raw["location_id"]
    if isinstance(raw.get("interval_minutes"), (int, float)):
        config.interval_minutes = int(raw["interval_minutes"])
    if isinstance(raw.get("fast_when_active"), bool):
        config.fast_when_active = raw["fast_when_active"]
    if isinstance(raw.get("fast_interval_seconds"), (int, float)):
        config.fast_interval_seconds = int(raw["fast_interval_seconds"])
    return config.normalized()


def save_config(data_dir: Path, config: MonitorConfig) -> None:
    """Persist the monitor config atomically."""
    from quill.core.storage import write_json_atomic

    config.normalized()
    write_json_atomic(
        _store_path(data_dir),
        {
            "enabled": config.enabled,
            "location_id": config.location_id,
            "interval_minutes": config.interval_minutes,
            "fast_when_active": config.fast_when_active,
            "fast_interval_seconds": config.fast_interval_seconds,
        },
    )
