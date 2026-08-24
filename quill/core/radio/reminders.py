"""Reminders: "tell me before this starts" (list.md 6.4, and section 7's floor).

A calendar that can only play what is on *now* is a calendar for somebody who
was already looking at it. The useful verb on a programme three days away is
**remind me**, and it is useful enough that the ACB calendar cannot ship
without it -- so the store, the firing and the Upcoming window land here rather
than waiting for section 7, which then becomes surfacing rather than plumbing.

What a reminder is, and what it deliberately is not:

* **It is a time and a thing to say.** Not a scheduled action: a reminder that
  silently started playing something would be a recording, and recordings are
  a separate feature with a separate confirmation.
* **Its target is a handle, not a callback.** ``kind`` plus ``target`` -- the
  same shape Recent Problems uses for Retry -- so a reminder survives a restart
  and still knows what it was about. A stored closure would not.
* **Lead time is per reminder.** "Five minutes before" suits a programme;
  "when it starts" suits an alarm; a day suits a weekly show you have to be
  home for. One global setting would be wrong for two of those three.
* **A missed reminder still fires.** An app that was closed at 6:55 should say
  "this started ten minutes ago" when it opens, not stay silent -- but only
  within :data:`GRACE_SECONDS`, because being told at breakfast about a
  programme that ended at midnight is noise wearing a reminder's clothes.

Quiet hours already carry a ``reminder`` kind and an explicit "let reminders
through anyway" switch, so the holding-back half of 7.5 is done; what this adds
is a reminder for it to hold.

wx-free, strict-typed. The caller supplies *now* and does the announcing.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

_FILENAME = "radio-reminders.json"

#: What a reminder can be about. Strings rather than an enum for the same
#: reason ``problem_log`` uses strings: the store is JSON, and a kind from a
#: newer build must read as "something this version does not surface" rather
#: than as corruption.
KIND_EVENT = "event"
KIND_STATION = "station"
KIND_EPISODE = "episode"
KIND_OTHER = "other"

KINDS: tuple[str, ...] = (KIND_EVENT, KIND_STATION, KIND_EPISODE, KIND_OTHER)

#: How late a reminder may fire and still be worth firing. Two hours: an app
#: closed over lunch should still say what it missed, and an app opened the
#: next morning should not recite yesterday.
GRACE_SECONDS = 7200

#: Lead times offered in the UI, as ``(seconds, label)``. Zero is "when it
#: starts", which is an answer rather than the absence of one.
LEAD_CHOICES: tuple[tuple[int, str], ...] = (
    (0, "When it starts"),
    (300, "5 minutes before"),
    (600, "10 minutes before"),
    (900, "15 minutes before"),
    (1800, "30 minutes before"),
    (3600, "1 hour before"),
    (86400, "1 day before"),
)

#: Priorities. Only ``high`` overrides quiet hours, and only when the listener
#: has also said reminders may come through -- one switch is a preference, two
#: agreeing is a decision.
PRIORITY_NORMAL = "normal"
PRIORITY_HIGH = "high"
PRIORITIES: tuple[str, ...] = (PRIORITY_NORMAL, PRIORITY_HIGH)


@dataclass(slots=True)
class Reminder:
    """One thing to be told about, once."""

    reminder_id: str
    title: str
    due: datetime
    kind: str = KIND_OTHER
    #: The handle that finds the thing again: an event uid, a stream URL, an
    #: episode's ``show|guid``. Opaque here; only the surface that registered
    #: the kind knows how to read it.
    target: str = ""
    #: Free text -- a link, or a message to yourself (7.2).
    note: str = ""
    lead_seconds: int = 0
    priority: str = PRIORITY_NORMAL
    #: Set when it has been delivered, so it fires once and no more.
    fired_at: str = ""
    #: Set while snoozed, and read in place of ``due`` when it is.
    snoozed_until: str = ""
    created_at: str = ""

    @property
    def fires_at(self) -> datetime:
        """When this should actually go off -- snooze first, then lead time."""
        snoozed = _moment(self.snoozed_until)
        if snoozed is not None:
            return snoozed
        return self.due - timedelta(seconds=max(0, int(self.lead_seconds)))

    @property
    def is_done(self) -> bool:
        return bool(self.fired_at.strip())

    def to_dict(self) -> dict[str, Any]:
        return {
            "reminder_id": self.reminder_id,
            "title": self.title,
            "due": self.due.isoformat(),
            "kind": self.kind,
            "target": self.target,
            "note": self.note,
            "lead_seconds": int(self.lead_seconds),
            "priority": self.priority,
            "fired_at": self.fired_at,
            "snoozed_until": self.snoozed_until,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: object) -> Reminder | None:
        """One stored row, or None when it cannot be read.

        A reminder with no time is not a reminder; a reminder with no id could
        never be dismissed. Everything else is optional, because a row written
        by a newer build must degrade rather than take the list down.
        """
        if not isinstance(data, dict):
            return None
        due = _moment(data.get("due"))
        reminder_id = str(data.get("reminder_id", "") or "").strip()
        if due is None or not reminder_id:
            return None
        kind = str(data.get("kind", "") or KIND_OTHER)
        return cls(
            reminder_id=reminder_id,
            title=str(data.get("title", "") or "Reminder"),
            due=due,
            kind=kind if kind in KINDS else KIND_OTHER,
            target=str(data.get("target", "") or ""),
            note=str(data.get("note", "") or ""),
            lead_seconds=_int(data.get("lead_seconds")),
            priority=(
                PRIORITY_HIGH if str(data.get("priority", "")) == PRIORITY_HIGH else PRIORITY_NORMAL
            ),
            fired_at=str(data.get("fired_at", "") or ""),
            snoozed_until=str(data.get("snoozed_until", "") or ""),
            created_at=str(data.get("created_at", "") or ""),
        )


# -- the store --------------------------------------------------------------------


def store_path(data_dir: Path) -> Path:
    return data_dir / _FILENAME


def load_reminders(data_dir: Path) -> list[Reminder]:
    """Everything set, soonest first. An absent or broken file reads as none."""
    from quill.core.storage import read_json

    raw = read_json(store_path(data_dir), default=[])
    if not isinstance(raw, list):
        return []
    found = [Reminder.from_dict(row) for row in raw]
    return sorted((r for r in found if r is not None), key=lambda r: r.fires_at)


def save_reminders(data_dir: Path, reminders: list[Reminder]) -> None:
    from quill.core.storage import write_json_atomic

    write_json_atomic(store_path(data_dir), [r.to_dict() for r in reminders])


def add_reminder(
    data_dir: Path,
    title: str,
    due: datetime,
    *,
    kind: str = KIND_OTHER,
    target: str = "",
    note: str = "",
    lead_seconds: int = 0,
    priority: str = PRIORITY_NORMAL,
    now: datetime | None = None,
) -> Reminder:
    """Set one reminder and return it.

    Setting a second reminder on the same target *replaces* the first: two
    reminders about one programme is a mistake somebody made twice, not a
    thing they asked for.
    """
    moment = now or datetime.now(UTC)
    reminders = load_reminders(data_dir)
    if target:
        reminders = [r for r in reminders if not (r.kind == kind and r.target == target)]
    reminder = Reminder(
        reminder_id=uuid.uuid4().hex,
        title=str(title or "Reminder"),
        due=due,
        kind=kind if kind in KINDS else KIND_OTHER,
        target=target,
        note=note,
        lead_seconds=max(0, int(lead_seconds)),
        priority=priority if priority in PRIORITIES else PRIORITY_NORMAL,
        created_at=moment.isoformat(),
    )
    reminders.append(reminder)
    save_reminders(data_dir, reminders)
    return reminder


def remove_reminder(data_dir: Path, reminder_id: str) -> bool:
    reminders = load_reminders(data_dir)
    kept = [r for r in reminders if r.reminder_id != reminder_id]
    if len(kept) == len(reminders):
        return False
    save_reminders(data_dir, kept)
    return True


def find_for_target(data_dir: Path, kind: str, target: str) -> Reminder | None:
    """The reminder on this thing, if there is one.

    So a row can offer *Remove reminder* rather than a second *Set reminder* --
    a menu that cannot tell you whether you already did something is a menu you
    have to remember for.
    """
    if not target:
        return None
    for reminder in load_reminders(data_dir):
        if reminder.kind == kind and reminder.target == target and not reminder.is_done:
            return reminder
    return None


# -- firing (pure) ----------------------------------------------------------------


def due_now(reminders: list[Reminder], now: datetime) -> list[Reminder]:
    """Everything that should be announced at *now*, soonest first.

    Includes reminders whose moment passed while the app was closed, up to
    :data:`GRACE_SECONDS` -- an app shut at 6:55 should say what it missed. Past
    that, silence: being told at breakfast about a programme that ended at
    midnight is noise wearing a reminder's clothes.
    """
    ready = []
    for reminder in reminders:
        if reminder.is_done:
            continue
        fires = reminder.fires_at
        if fires > now:
            continue
        if (now - fires).total_seconds() > GRACE_SECONDS:
            continue
        ready.append(reminder)
    return sorted(ready, key=lambda r: r.fires_at)


def expired(reminders: list[Reminder], now: datetime) -> list[Reminder]:
    """Reminders whose moment went past unheard and unfireable.

    Named rather than silently dropped: they are what the Upcoming window shows
    as missed, and deleting them behind somebody's back is how "I set a
    reminder and heard nothing" becomes unanswerable.
    """
    return [
        r for r in reminders if not r.is_done and (now - r.fires_at).total_seconds() > GRACE_SECONDS
    ]


def upcoming(reminders: list[Reminder], now: datetime) -> list[Reminder]:
    """Everything still ahead, soonest first."""
    return sorted(
        (r for r in reminders if not r.is_done and r.fires_at > now), key=lambda r: r.fires_at
    )


def mark_fired(data_dir: Path, reminder_id: str, *, now: datetime | None = None) -> bool:
    """Note that a reminder was delivered, so it never fires twice."""
    moment = now or datetime.now(UTC)
    reminders = load_reminders(data_dir)
    changed = False
    for reminder in reminders:
        if reminder.reminder_id == reminder_id and not reminder.is_done:
            reminder.fired_at = moment.isoformat()
            reminder.snoozed_until = ""
            changed = True
    if changed:
        save_reminders(data_dir, reminders)
    return changed


def snooze(data_dir: Path, reminder_id: str, seconds: int, *, now: datetime | None = None) -> bool:
    """Push a reminder out by *seconds* from now.

    From *now* rather than from when it was due: somebody who snoozes at 7:04 a
    reminder that fired at 6:55 means nine minutes from now, not nine minutes
    ago plus nine.
    """
    moment = now or datetime.now(UTC)
    reminders = load_reminders(data_dir)
    changed = False
    for reminder in reminders:
        if reminder.reminder_id == reminder_id:
            reminder.snoozed_until = (moment + timedelta(seconds=max(60, int(seconds)))).isoformat()
            reminder.fired_at = ""
            changed = True
    if changed:
        save_reminders(data_dir, reminders)
    return changed


# -- what it says -----------------------------------------------------------------


def lead_label(seconds: object) -> str:
    """The chosen lead time, in the words the control offers."""
    wanted = _int(seconds)
    for offered, label in LEAD_CHOICES:
        if offered == wanted:
            return label
    return f"{wanted // 60} minutes before"


def announcement(reminder: Reminder, now: datetime) -> str:
    """What to say when one fires.

    Says *when the thing is*, not when the reminder was set for: "starts in ten
    minutes" is what somebody needs, and "your 6:50 reminder" is a fact about
    the reminder rather than about the programme.
    """
    ahead = (reminder.due - now).total_seconds()
    if ahead > 30:
        when = f"starts in {_spoken(ahead)}"
    elif ahead > -60:
        when = "is starting now"
    else:
        when = f"started {_spoken(-ahead)} ago"
    note = f" {reminder.note.strip()}" if reminder.note.strip() else ""
    return f"Reminder: {reminder.title} {when}.{note}"


def row_label(reminder: Reminder, now: datetime) -> str:
    """One line in the Upcoming window."""
    when = spoken_when(reminder.due)
    parts = [reminder.title, when]
    if reminder.lead_seconds:
        parts.append(lead_label(reminder.lead_seconds).lower())
    if reminder.priority == PRIORITY_HIGH:
        parts.append("high priority")
    if reminder.is_done:
        parts.append("done")
    elif (now - reminder.fires_at).total_seconds() > GRACE_SECONDS:
        parts.append("missed")
    return ", ".join(parts)


def spoken_when(moment: datetime) -> str:
    """``Wed 26 Aug, 7:00 PM`` in the reader's own timezone.

    Built by hand rather than with ``%-d``/``%-I``: those are glibc extensions
    and ``strftime`` raises on them on Windows, which is the platform this
    ships on. Zero-padded hours read as "oh seven" to some screen readers, so
    the padding is stripped rather than tolerated.
    """
    local = moment.astimezone()
    hour = local.hour % 12 or 12
    meridiem = "AM" if local.hour < 12 else "PM"
    return (
        f"{local.strftime('%a')} {local.day} {local.strftime('%b')}, "
        f"{hour}:{local.minute:02d} {meridiem}"
    )


def _spoken(seconds: float) -> str:
    total = int(max(0, seconds))
    minutes, _sec = divmod(total, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    if days:
        return f"{days} day{'' if days == 1 else 's'}"
    if hours:
        return f"{hours} hour{'' if hours == 1 else 's'}"
    return f"{max(1, minutes)} minute{'' if minutes == 1 else 's'}"


def _moment(value: object) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        moment = datetime.fromisoformat(text)
    except ValueError:
        return None
    return moment if moment.tzinfo is not None else moment.replace(tzinfo=UTC)


def _int(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return 0
    return max(0, int(value))


__all__ = [
    "GRACE_SECONDS",
    "KINDS",
    "KIND_EPISODE",
    "KIND_EVENT",
    "KIND_OTHER",
    "KIND_STATION",
    "LEAD_CHOICES",
    "PRIORITIES",
    "PRIORITY_HIGH",
    "PRIORITY_NORMAL",
    "Reminder",
    "add_reminder",
    "announcement",
    "due_now",
    "expired",
    "find_for_target",
    "lead_label",
    "load_reminders",
    "mark_fired",
    "remove_reminder",
    "row_label",
    "save_reminders",
    "snooze",
    "spoken_when",
    "store_path",
    "upcoming",
]
