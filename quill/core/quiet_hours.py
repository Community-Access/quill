"""Quiet hours: a window in which the apps stop speaking on their own.

Both apps talk. A feed check ticks, a new episode announces itself by name, a
download finishes and says so, and -- once reminders land (item 7.5) -- an
alarm goes off. All of that is right at two in the afternoon and wrong at two
in the morning, and the only answer available today is turning each feature
off one at a time and remembering to turn it back on (list.md 11.9).

So: one window, shared by Quill Radio and QUILL Cast, in which **unprompted**
speech stays silent.

**Unprompted is the whole distinction.** Quiet hours must never silence the
answer to a keypress. A listener who presses Play at three in the morning is
entitled to hear "Playing WQXR" -- they asked. What quiet hours holds back is
the speech nobody asked for: check ticks, new-episode announcements,
download-finished notices, reminders. Every call site opts *in* by naming its
kind here, which is why this is a small vocabulary rather than a gate around
``_announce``.

**One explicit override.** :data:`Kind.URGENT` is never silenced: a recording
that failed at 3 a.m. is exactly the thing somebody set an alarm-clock radio
for, and an app that swallowed it to be polite would have chosen the wrong
side. The setting that governs the rest is one checkbox, not a matrix.

**Windows wrap.** 22:00 to 07:00 is the ordinary case and crosses midnight,
so the comparison is deliberately not ``start <= now <= end``.

Pure: no clock of its own (callers pass *now*), no store, no wx. The store is
:func:`load_quiet_hours` / :func:`save_quiet_hours`, one shared file, because
a quiet hour is a fact about the listener rather than about an app.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import time as _time
from pathlib import Path
from typing import Any

from quill.core.storage import write_json_atomic

__all__ = [
    "DEFAULT_END",
    "DEFAULT_START",
    "QuietHours",
    "SILENCEABLE_KINDS",
    "Kind",
    "describe",
    "is_quiet_at",
    "load_quiet_hours",
    "parse_clock",
    "save_quiet_hours",
    "silences",
    "store_path",
]


class Kind:
    """What a piece of speech *is*, for the purposes of being held back.

    Deliberately a handful of strings rather than a severity number: "this is
    a check tick" is a fact a call site knows and a level is a judgement it
    would have to make.
    """

    #: The heartbeat of an automatic feed check.
    TICK = "tick"
    #: "Three new episodes of The Daily."
    NEW_EPISODE = "new_episode"
    #: "Saved Episode 412 to Downloads."
    DOWNLOAD = "download"
    #: A reminder firing (item 7.5).
    REMINDER = "reminder"
    #: Anything the listener did not ask for that does not fit above.
    BACKGROUND = "background"
    #: Never silenced: a failure, a recording that stopped, an alarm.
    URGENT = "urgent"


#: The kinds quiet hours can hold back. Everything else speaks.
SILENCEABLE_KINDS: frozenset[str] = frozenset({
    Kind.TICK,
    Kind.NEW_EPISODE,
    Kind.DOWNLOAD,
    Kind.REMINDER,
    Kind.BACKGROUND,
})

DEFAULT_START = "22:00"
DEFAULT_END = "07:00"


def parse_clock(text: str, fallback: str = "00:00") -> _time:
    """``"22:00"`` -> a time. Anything unreadable falls back rather than raising."""
    for candidate in (text, fallback):
        parts = str(candidate or "").strip().split(":")
        if len(parts) != 2:
            continue
        try:
            hour, minute = int(parts[0]), int(parts[1])
        except ValueError:
            continue
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return _time(hour, minute)
    return _time(0, 0)


@dataclass(slots=True)
class QuietHours:
    """The listener's quiet window, and what it holds back."""

    enabled: bool = False
    start: str = DEFAULT_START
    end: str = DEFAULT_END
    #: Reminders are the one silenceable kind somebody may want *through* the
    #: quiet window -- an alarm clock is the reason they set one. Off by
    #: default: quiet means quiet unless you say otherwise.
    allow_reminders: bool = False

    def start_time(self) -> _time:
        return parse_clock(self.start, DEFAULT_START)

    def end_time(self) -> _time:
        return parse_clock(self.end, DEFAULT_END)

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "start": self.start,
            "end": self.end,
            "allow_reminders": self.allow_reminders,
        }

    @classmethod
    def from_dict(cls, data: Any) -> QuietHours:
        if not isinstance(data, dict):
            return cls()
        return cls(
            enabled=bool(data.get("enabled", False)),
            start=str(data.get("start", DEFAULT_START) or DEFAULT_START),
            end=str(data.get("end", DEFAULT_END) or DEFAULT_END),
            allow_reminders=bool(data.get("allow_reminders", False)),
        )


def is_quiet_at(hours: QuietHours, now: _time) -> bool:
    """Whether *now* falls inside the window (which may cross midnight)."""
    if not hours.enabled:
        return False
    start, end = hours.start_time(), hours.end_time()
    if start == end:
        # A zero-length window means nothing rather than everything: somebody
        # who set both ends the same has not asked for permanent silence.
        return False
    if start < end:
        return start <= now < end
    return now >= start or now < end


def silences(hours: QuietHours, kind: str, now: _time) -> bool:
    """Whether *kind* should be held back right now.

    Urgent speech is never held back, and anything not in
    :data:`SILENCEABLE_KINDS` is treated as prompted -- an answer to something
    the listener did.
    """
    if kind not in SILENCEABLE_KINDS:
        return False
    if kind == Kind.REMINDER and hours.allow_reminders:
        return False
    return is_quiet_at(hours, now)


def describe(hours: QuietHours) -> str:
    """What the setting does, said the way this family says settings.

    Says what it does *not* do as well (the rule from section 3): the most
    expensive misreading of "quiet hours" is thinking the app has gone deaf,
    or that it has stopped checking feeds.
    """
    if not hours.enabled:
        return (
            "Quiet hours are off. Check ticks, new-episode announcements and "
            "reminders speak whenever they happen."
        )
    tail = " Reminders still speak." if hours.allow_reminders else " Reminders are held back too."
    return (
        f"Quiet from {hours.start} to {hours.end}. Feeds are still checked and "
        "downloads still run -- only the announcements are held back, and "
        "anything you press a key for still answers." + tail
    )


def toggle_sentence(hours: QuietHours) -> str:
    """What to say when quiet hours are switched on or off."""
    if hours.enabled:
        return f"Quiet hours on, {hours.start} to {hours.end}. Background announcements are held."
    return "Quiet hours off. Background announcements speak again."


# -- the shared store ----------------------------------------------------------


def store_path(data_dir: Path) -> Path:
    return data_dir / "quiet-hours.json"


def load_quiet_hours(data_dir: Path) -> QuietHours:
    """The listener's window (defaults when absent or unreadable)."""
    try:
        raw = json.loads(store_path(data_dir).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return QuietHours()
    return QuietHours.from_dict(raw)


def save_quiet_hours(data_dir: Path, hours: QuietHours) -> None:
    """Persist atomically. Never raises: a settings write must not kill a tick."""
    try:
        write_json_atomic(store_path(data_dir), hours.to_dict())
    except OSError:
        return
