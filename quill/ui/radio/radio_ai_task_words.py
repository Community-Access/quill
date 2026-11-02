"""Find and Record's words and reads (codex.md 6.5): the spec, the rows, the facts.

Kept apart from :mod:`quill.ui.radio.radio_ai_task` (the tools) so neither
module grows past its size budget (GATE-11). Everything here is text: a station
as one numbered line, a scheduled recording in plain words ("WBGO, every Friday
at 7:30 PM, for 30 minutes"), and what is on screen for the first instruction.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from quill.core.ai.app_task import AppTaskSpec

__all__ = [
    "FIND_AND_RECORD",
    "INSTRUCTION_HELP",
    "RadioTaskState",
    "clock_words",
    "radio_task_facts",
    "station_row",
]

APP = "radio"

#: The search rows a find returns at most.
_FIND_LIMIT = 15
#: Songs a recent-songs read lists at most.
_SONG_LIMIT = 20

_WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
_MONTHS = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)

FIND_AND_RECORD = AppTaskSpec(
    app=APP,
    agent_id="radio-find-and-record",
    title="Find and Record",
    instructions=(
        "You help someone who uses a screen reader with Quill Radio, an internet "
        "radio player. Find stations with radio_find_stations or "
        "radio_list_favorites, then play, record or schedule a recording with the "
        "station's id from those lists (such as S1 or F2, or 'playing' for the "
        "station on now). Use radio_list_scheduled before scheduling, so you do "
        "not add a recording that is already there. Times are this computer's "
        "local time. Say station names as the lists give them."
    ),
    done_words={
        f"{APP}.play_station": "Played a station",
        f"{APP}.record_station": "Started a recording",
        f"{APP}.schedule_recording": "Scheduled a recording",
    },
)

INSTRUCTION_HELP = (
    "Type what you want Quill Radio to find, play, record or schedule, then press "
    "Enter. For example: find a jazz station from New Orleans and record it "
    "tonight from 8 for an hour. Playing, recording and scheduling each ask you "
    "first. While a task runs, what you type here goes to it as a follow-up."
)


class RadioTaskState:
    """The stations one task has seen, by the ids the lists gave them."""

    def __init__(self) -> None:
        self.found: dict[str, Any] = {}
        self._next = 1

    def remember(self, station: Any) -> str:
        for key, known in self.found.items():
            if key.startswith("S") and _same(known, station):
                return key
        key = f"S{self._next}"
        self._next += 1
        self.found[key] = station
        return key


def _same(a: Any, b: Any) -> bool:
    url_a = str(getattr(a, "stream_url", "") or "")
    return bool(url_a) and url_a == str(getattr(b, "stream_url", "") or "")


# --------------------------------------------------------------------------- #
# Words
# --------------------------------------------------------------------------- #


def _name(station: Any) -> str:
    return str(getattr(station, "display_name", "") or getattr(station, "name", "") or "")


def station_row(key: str, station: Any, *, folder: str = "") -> str:
    """One station as a line of text: id, name, what it plays, where it is from."""
    bits = [f"{key}. {_name(station)}"]
    tags = [str(t) for t in (getattr(station, "tags", ()) or ())][:4]
    if tags:
        bits.append(", ".join(tags))
    codec = str(getattr(station, "codec", "") or "")
    rate = int(getattr(station, "bitrate_kbps", 0) or 0)
    if codec or rate:
        bits.append(" ".join(p for p in (codec, f"{rate} kbps" if rate else "") if p))
    if folder:
        bits.append(f"in your folder {folder}")
    source = str(getattr(station, "source", "") or "")
    if source and not folder:
        bits.append(f"from {source}")
    if bool(getattr(station, "is_recording", False)):
        bits.append("a finished recording, not a live stream")
    return ". ".join(bits) + "."


def clock_words(hhmm: str) -> str:
    """``"20:00"`` as ``"8:00 PM"``."""
    hour, _sep, minute = hhmm.partition(":")
    h = int(hour)
    suffix = "AM" if h < 12 else "PM"
    shown = h % 12 or 12
    return f"{shown}:{minute} {suffix}"


def _date_words(day: date) -> str:
    return f"{_WEEKDAYS[day.weekday()]} {day.day} {_MONTHS[day.month - 1]} {day.year}"


def _minutes_words(minutes: int) -> str:
    if minutes % 60 == 0:
        hours = minutes // 60
        return "one hour" if hours == 1 else f"{hours} hours"
    return "one minute" if minutes == 1 else f"{minutes} minutes"


def _when_words(recurrence: str, hhmm: str, day_text: str, weekday: int) -> str:
    at = clock_words(hhmm)
    if recurrence == "daily":
        return f"every day at {at}"
    if recurrence == "weekly":
        return f"every {_WEEKDAYS[weekday]} at {at}"
    try:
        day = date.fromisoformat(day_text.strip())
    except ValueError:
        return f"on {day_text} at {at}"
    return f"on {_date_words(day)} at {at}"


def _entry_words(entry: Any, now: datetime | None = None) -> str:
    from quill.core.radio.recording_schedule import next_occurrence

    try:
        hhmm = datetime.fromisoformat(entry.run_at).strftime("%H:%M")
        day_text = entry.run_at[:10]
    except ValueError:
        return f"{entry.station_name}, at {entry.run_at}"
    when = _when_words(entry.recurrence, hhmm, day_text, entry.weekday)
    line = f"{entry.station_name}, {when}, for {_minutes_words(entry.duration_minutes)}"
    if not entry.enabled:
        line += " (turned off)"
    upcoming = next_occurrence(entry, now or datetime.now().astimezone())
    if upcoming is not None and entry.enabled and entry.recurrence != "once":
        local = upcoming.astimezone()
        line += f"; next {_date_words(local.date())} at {clock_words(local.strftime('%H:%M'))}"
    return line + "."


# --------------------------------------------------------------------------- #
# What Radio knows, read on the UI thread
# --------------------------------------------------------------------------- #


def _playing(host: Any) -> Any:
    controller = getattr(host, "_radio_controller", None)
    return controller.state.station if controller is not None else None


def _favorite_stations(host: Any) -> list[tuple[Any, str]]:
    """``(station, folder)`` for each favourite that is a stream, in display order."""
    from quill.core.radio.favorites import is_place

    store = getattr(host, "_radio_favorites", None)
    favorites = list(getattr(store, "favorites", []) or [])
    return [
        (fav.station, str(getattr(fav, "folder", "") or ""))
        for fav in favorites
        if not is_place(fav.station)
    ]


def radio_task_facts(host: Any) -> str:
    """What is on screen, as text, sent with the first instruction."""
    from quill.core.ai.app_ask_context import facts_text, filter_facts, radio_context
    from quill.ui.radio.radio_ai_features import _what_is_on

    station, playing = _what_is_on(host)
    lines = [facts_text(filter_facts(radio_context(station, playing)))]
    chosen = getattr(host, "_selected_favorite", None)
    try:
        favorite = chosen() if callable(chosen) else None
    except Exception:  # noqa: BLE001 - no tree, no selection
        favorite = None
    if favorite is not None:
        label = str(getattr(favorite, "display_label", "") or _name(favorite.station))
        lines.append(f"Selected favourite: {label}")
    return "\n".join(line for line in lines if line.strip())
