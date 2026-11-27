"""Which saved places Weather Guardian watches, and when (Quill Weather 2.3.0).

The default is "watch every saved place", exactly as before. On top of that a
place can be:

* **switched off** (kept saved, not watched), in ``MonitorConfig.muted_ids``;
* **watched until** a date and time while otherwise off (a trip, a relative's area
  during a storm); it ends by itself and says so once;
* **snoozed** for a while (1, 4 or 12 hours, or until tomorrow morning); a plain
  reminder is spoken once when the snooze ends;
* **scheduled** (for example Work only on weekdays from 8 to 6);
* in one or more **groups** (Family, Work, Travel) that can be watched or
  unwatched together.

A snoozed place, and a place outside its schedule, is still *checked*: it is
quiet exactly as quiet hours are quiet, and an Extreme alert breaks through under
the same rule (``QuietHours.extreme_breaks_through``). A place that is off, or whose
watch has ended, is not checked at all.

Pure and wx-free; the clock is always passed in.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_STORE_NAME = "weather_place_watch.json"
SNOOZE_CHOICES = ("1 hour", "4 hours", "12 hours", "Until tomorrow morning")
_TOMORROW_MORNING = time(7, 0)
DAY_NAMES = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


class WatchState(StrEnum):
    WATCHING = "watching"
    OFF = "off"
    SNOOZED = "snoozed"
    OUTSIDE_SCHEDULE = "outside_schedule"
    ENDED = "ended"  # a temporary watch that has run out

    @property
    def checked(self) -> bool:
        """Whether the place is polled at all (so Extreme can still break through)."""
        return self in (WatchState.WATCHING, WatchState.SNOOZED, WatchState.OUTSIDE_SCHEDULE)

    @property
    def quiet(self) -> bool:
        """Polled, but held back from speech like quiet hours."""
        return self in (WatchState.SNOOZED, WatchState.OUTSIDE_SCHEDULE)


@dataclass(slots=True)
class Schedule:
    days: list[int] = field(default_factory=lambda: [0, 1, 2, 3, 4])  # Monday = 0
    start: str = "08:00"
    end: str = "18:00"

    def active_at(self, moment: datetime) -> bool:
        if moment.weekday() not in self.days:
            return False
        start, end = _clock(self.start), _clock(self.end)
        now = moment.time().replace(second=0, microsecond=0)
        if start == end:
            return True  # a whole day
        if start < end:
            return start <= now < end
        return now >= start or now < end

    def as_text(self) -> str:
        """The form the schedule is typed in: 'Mon-Fri 08:00-18:00'."""
        days = _describe_days(self.days)
        days = {"weekdays": "Mon-Fri", "weekends": "Sat,Sun", "every day": "Mon-Sun"}.get(
            days, days.replace(" ", "")
        )
        return f"{days} {self.start}-{self.end}"

    def describe(self) -> str:
        days = _describe_days(self.days)
        return f"{days} from {_say_time(_clock(self.start))} to {_say_time(_clock(self.end))}"


@dataclass(slots=True)
class PlaceRule:
    groups: list[str] = field(default_factory=list)
    #: Epoch seconds. While in the future the place is watched even if switched off.
    until: float | None = None
    snooze_until: float | None = None
    schedule: Schedule | None = None
    #: A finished temporary watch or snooze has been said once.
    until_said: bool = False
    snooze_said: bool = True


@dataclass(slots=True)
class PlaceWatches:
    rules: dict[str, PlaceRule] = field(default_factory=dict)

    def rule(self, place_id: str) -> PlaceRule:
        return self.rules.setdefault(place_id, PlaceRule())

    def groups(self) -> list[str]:
        return sorted({g for r in self.rules.values() for g in r.groups}, key=str.lower)

    def members(self, group: str) -> list[str]:
        return [
            pid for pid, r in self.rules.items() if group.lower() in (g.lower() for g in r.groups)
        ]


def _clock(text: str) -> time:
    hours, _, minutes = text.partition(":")
    return time(max(0, min(23, int(hours))), max(0, min(59, int(minutes or 0))))


def _say_time(moment: time) -> str:
    return datetime(2000, 1, 1, moment.hour, moment.minute).strftime("%I:%M %p").lstrip("0")


def _describe_days(days: list[int]) -> str:
    ordered = sorted(set(days))
    if ordered == [0, 1, 2, 3, 4]:
        return "weekdays"
    if ordered == [5, 6]:
        return "weekends"
    if ordered == list(range(7)):
        return "every day"
    return ", ".join(DAY_NAMES[d] for d in ordered)


def parse_schedule(text: str) -> Schedule | None:
    """'Mon-Fri 08:00-18:00', 'weekdays 8:00-18:00', 'Sat,Sun 10:00-14:00'; ''
    clears. Raises ValueError for anything else."""
    text = text.strip()
    if not text:
        return None
    days_part, _, hours_part = text.rpartition(" ")
    if not days_part or "-" not in hours_part:
        raise ValueError("Use days and hours, like Mon-Fri 08:00-18:00.")
    start, _, end = hours_part.partition("-")
    for part in (start, end):
        h, sep, m = part.partition(":")
        if not (h.isdigit() and 0 <= int(h) <= 23 and (not sep or (m.isdigit() and int(m) <= 59))):
            raise ValueError("Hours must look like 08:00.")
    days = _parse_days(days_part)
    s_h, _, s_m = start.partition(":")
    e_h, _, e_m = end.partition(":")
    return Schedule(
        days, f"{int(s_h):02d}:{int(s_m or 0):02d}", f"{int(e_h):02d}:{int(e_m or 0):02d}"
    )


def _parse_days(text: str) -> list[int]:
    low = text.strip().lower()
    names = [d.lower() for d in DAY_NAMES]
    fixed = {
        "weekdays": [0, 1, 2, 3, 4],
        "weekends": [5, 6],
        "daily": list(range(7)),
        "every day": list(range(7)),
    }
    if low in fixed:
        return fixed[low]
    days: set[int] = set()
    for chunk in low.replace(" ", "").split(","):
        if "-" in chunk:
            a, _, b = chunk.partition("-")
            if a[:3] not in names or b[:3] not in names:
                raise ValueError("Days are like Mon-Fri or Sat,Sun.")
            i, j = names.index(a[:3]), names.index(b[:3])
            days.update(range(i, j + 1) if i <= j else [*range(i, 7), *range(0, j + 1)])
        elif chunk[:3] in names:
            days.add(names.index(chunk[:3]))
        else:
            raise ValueError("Days are like Mon-Fri or Sat,Sun.")
    return sorted(days)


# -- state ---------------------------------------------------------------------


def state_of(place_id: str, muted: set[str], watches: PlaceWatches, now: datetime) -> WatchState:
    rule = watches.rules.get(place_id)
    stamp = now.timestamp()
    if place_id in muted:
        if rule is not None and rule.until is not None:
            return WatchState.WATCHING if stamp < rule.until else WatchState.ENDED
        return WatchState.OFF
    if rule is None:
        return WatchState.WATCHING
    if rule.snooze_until is not None and stamp < rule.snooze_until:
        return WatchState.SNOOZED
    if rule.schedule is not None and not rule.schedule.active_at(now):
        return WatchState.OUTSIDE_SCHEDULE
    return WatchState.WATCHING


def snooze(rule: PlaceRule, choice: str, now: datetime) -> datetime:
    """Snooze for one of ``SNOOZE_CHOICES``; returns when it ends."""
    if choice == "Until tomorrow morning":
        end = datetime.combine(now.date() + timedelta(days=1), _TOMORROW_MORNING, now.tzinfo)
    else:
        hours = {"1 hour": 1, "4 hours": 4, "12 hours": 12}[choice]
        end = now + timedelta(hours=hours)
    rule.snooze_until = end.timestamp()
    rule.snooze_said = False
    return end


def end_snooze(rule: PlaceRule) -> None:
    rule.snooze_until = None
    rule.snooze_said = True


def set_watch_until(rule: PlaceRule, when: datetime | None) -> None:
    rule.until = when.timestamp() if when else None
    rule.until_said = False


def parse_until(text: str, now: datetime) -> datetime | None:
    """'2026-12-03 18:00', or '' to clear. Must be in the future."""
    text = text.strip()
    if not text:
        return None
    try:
        when = datetime.strptime(text, "%Y-%m-%d %H:%M").replace(tzinfo=now.tzinfo)
    except ValueError as error:
        raise ValueError("Use a date and time like 2026-12-03 18:00.") from error
    if when <= now:
        raise ValueError("That time has already passed.")
    return when


def due_notices(
    muted: set[str], watches: PlaceWatches, labels: dict[str, str], now: datetime
) -> list[str]:
    """Things that ended since the last look, each said once (and marked said)."""
    said: list[str] = []
    stamp = now.timestamp()
    for pid, rule in watches.rules.items():
        label = labels.get(pid, "")
        if not label:
            continue
        if rule.snooze_until is not None and stamp >= rule.snooze_until:
            rule.snooze_until = None
            if not rule.snooze_said:
                rule.snooze_said = True
                said.append(f"The snooze for {label} has ended. It is being watched again.")
        if pid in muted and rule.until is not None and stamp >= rule.until and not rule.until_said:
            rule.until_said = True
            said.append(f"The temporary watch for {label} has ended. It is no longer watched.")
    return said


# -- describing ------------------------------------------------------------------


def _say_moment(stamp: float, now: datetime) -> str:
    when = datetime.fromtimestamp(stamp, now.tzinfo)
    clock = when.strftime("%I:%M %p").lstrip("0")
    return clock if when.date() == now.date() else f"{when.strftime('%b')} {when.day} at {clock}"


def describe_state(place_id: str, muted: set[str], watches: PlaceWatches, now: datetime) -> str:
    """'watched', 'not watched', 'snoozed until 6 PM', ... for one place."""
    state = state_of(place_id, muted, watches, now)
    rule = watches.rules.get(place_id)
    if state is WatchState.WATCHING:
        if place_id in muted and rule and rule.until:
            return f"watched until {_say_moment(rule.until, now)}"
        return "watched"
    if state is WatchState.SNOOZED and rule and rule.snooze_until:
        return f"snoozed until {_say_moment(rule.snooze_until, now)}"
    if state is WatchState.OUTSIDE_SCHEDULE and rule and rule.schedule:
        return f"outside its schedule, {rule.schedule.describe()}"
    if state is WatchState.ENDED:
        return "not watched, the temporary watch ended"
    return "not watched, switched off"


def row_text(
    place_id: str, label: str, muted: set[str], watches: PlaceWatches, now: datetime
) -> str:
    """'Home, watched' / 'Cabin, not watched, switched off' (plus its groups)."""
    text = f"{label}, {describe_state(place_id, muted, watches, now)}"
    rule = watches.rules.get(place_id)
    if rule and rule.groups:
        text += f" ({', '.join(rule.groups)})"
    return text


def summary_sentence(
    places: list[tuple[str, str]], muted: set[str], watches: PlaceWatches, now: datetime
) -> str:
    """'Watching 3 of 5 places. Cabin is snoozed until 6 PM.'"""
    states = {pid: state_of(pid, muted, watches, now) for pid, _l in places}
    watching = sum(1 for s in states.values() if s is WatchState.WATCHING)
    total = len(places)
    head = f"Watching {watching} of {total} {'place' if total == 1 else 'places'}."
    notes = []
    for pid, label in places:
        if states[pid] is not WatchState.WATCHING:
            notes.append(f"{label} is {describe_state(pid, muted, watches, now)}.")
    return " ".join([head, *notes])


def not_watched_lines(
    places: list[tuple[str, str]], muted: set[str], watches: PlaceWatches, now: datetime
) -> list[str]:
    """For Alert Feed Status and the start summary: who is not watched, and why."""
    return [
        f"{label}: {describe_state(pid, muted, watches, now)}"
        for pid, label in places
        if state_of(pid, muted, watches, now) is not WatchState.WATCHING
    ]


# -- bulk and group changes -------------------------------------------------------


def watch_all(muted: set[str]) -> set[str]:
    return set()


def watch_none(all_ids: list[str]) -> set[str]:
    return set(all_ids)


def invert(all_ids: list[str], muted: set[str]) -> set[str]:
    return {i for i in all_ids if i not in muted}


def set_group(muted: set[str], watches: PlaceWatches, group: str, watched: bool) -> set[str]:
    members = set(watches.members(group))
    return muted - members if watched else muted | members


# -- persistence -------------------------------------------------------------------


def to_json(watches: PlaceWatches) -> dict[str, Any]:
    return {
        "version": 1,
        "places": {
            pid: {
                "groups": r.groups,
                "until": r.until,
                "snooze_until": r.snooze_until,
                "snooze_said": r.snooze_said,
                "until_said": r.until_said,
                "schedule": (
                    {"days": r.schedule.days, "start": r.schedule.start, "end": r.schedule.end}
                    if r.schedule
                    else None
                ),
            }
            for pid, r in list(watches.rules.items())[:100]
        },
    }


def from_json(raw: Any) -> PlaceWatches:
    if not isinstance(raw, dict) or not isinstance(raw.get("places"), dict):
        raise ValueError("place watch file has no places")
    out = PlaceWatches()
    for pid, item in list(raw["places"].items())[:100]:
        if not isinstance(pid, str) or not isinstance(item, dict):
            continue
        rule = PlaceRule()
        groups = item.get("groups")
        if isinstance(groups, list):
            rule.groups = [str(g)[:40] for g in groups if isinstance(g, str) and g.strip()][:10]
        for key in ("until", "snooze_until"):
            value = item.get(key)
            if isinstance(value, int | float) and not isinstance(value, bool):
                setattr(rule, key, float(value))
        rule.snooze_said = item.get("snooze_said") is not False
        rule.until_said = item.get("until_said") is True
        sched = item.get("schedule")
        if isinstance(sched, dict):
            try:
                days = [int(d) for d in sched.get("days", []) if 0 <= int(d) <= 6]
                start, end = str(sched.get("start", "08:00")), str(sched.get("end", "18:00"))
                _clock(start), _clock(end)
                rule.schedule = Schedule(days, start, end)
            except (ValueError, TypeError):
                rule.schedule = None
        out.rules[pid] = rule
    return out


def load_watches(data_dir: Path) -> PlaceWatches:
    import json

    path = data_dir / _STORE_NAME
    if not path.exists():
        return PlaceWatches()
    try:
        return from_json(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, ValueError, TypeError) as exc:
        logger.warning("weather place watch file is unreadable (%s); using the defaults", exc)
        try:
            from quill.core.migration_backup import backup_corrupt_file

            backup_corrupt_file("weather_place_watch", path)
        except Exception:  # noqa: BLE001 - keeping a copy is best effort
            pass
        return PlaceWatches()


def save_watches(data_dir: Path, watches: PlaceWatches) -> None:
    from quill.core.storage import write_json_atomic

    write_json_atomic(data_dir / _STORE_NAME, to_json(watches))
