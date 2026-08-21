"""How much you listened, to what, and when -- for any app that plays audio.

QUILL Cast has reported this since 1.1.0 and Quill Radio has not, so a listener
who spends an hour on a podcast and an hour on a station could see one of those
and not the other. The whole shape was already right and already reusable: pure,
wx-free, a session log with a retention window, periods, per-key totals and CSV
export. What it was not was app-independent -- the store filename, the retention
default and the key were all "podcast".

So this is that engine with those three things passed in, and each app supplies
its own vocabulary on top:

* **Cast** keys a session by show, and cares about speed and silence trimming,
  because "you got through nine hours of content in seven" is the interesting
  number for a podcast.
* **Radio** keys a session by station, and those two fields mean nothing at all
  for a live stream -- so Radio's summary omits them rather than reporting a
  confident zero.

**A session is wall-clock time with the audio actually playing.** It is the
honest denominator, and it is what makes everything derived from it arithmetic
rather than guesswork.

**The log is capped twice.** A retention window in days, because a listening
history is personal and keeping it forever is a decision nobody asked for; and a
hard ceiling on the number of records, because a heavy listener generates a
session per play and an unbounded JSON file rewritten on every flush eventually
becomes the reason playback stutters.

wx-free, strict-typed, pure apart from the store.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

__all__ = [
    "DEFAULT_RETENTION_DAYS",
    "MAX_SESSIONS",
    "PERIODS",
    "KeyTotal",
    "MediaSession",
    "StatsSummary",
    "append_session",
    "clear_sessions",
    "format_duration",
    "load_sessions",
    "prune",
    "save_sessions",
    "summarize",
    "to_csv",
]

#: A hard ceiling on the log regardless of the retention window.
MAX_SESSIONS = 5000

#: Ninety days. Long enough to answer "what did I listen to last month", short
#: enough that nobody is quietly accumulating a year of their own habits.
DEFAULT_RETENTION_DAYS = 90

#: Period selectors offered by a statistics dialog: (id, label, days).
#: ``0`` days means "everything the log still holds".
PERIODS: tuple[tuple[str, str, int], ...] = (
    ("week", "This week", 7),
    ("month", "This month", 30),
    ("year", "This year", 365),
    ("all", "All time", 0),
)


@dataclass(slots=True)
class MediaSession:
    """One stretch of listening, flushed at a natural stopping point.

    *key* is whatever the app counts by: a show id in Cast, a station key in
    Radio. *item* is the thing inside it, where there is one -- an episode
    GUID; a live stream has none, and an empty item is not an error.
    """

    key: str
    item: str = ""
    seconds: float = 0.0
    #: The rate it played at. ``seconds x (speed - 1)`` is exactly the extra
    #: content speed bought, which is why this is stored rather than derived.
    #: Always 1.0 for a live stream.
    speed: float = 1.0
    #: Seconds of silence a trimming pass actually removed, when the pass can
    #: report it. Zero means "not measured", never "none saved".
    trimmed_seconds: float = 0.0
    #: True only when this session ran to the end of the thing being played.
    completed: bool = False
    date: str = ""
    #: A second dimension the app may group by -- Radio's network, say. Free
    #: text, never part of the identity.
    group: str = ""

    def to_dict(self) -> dict[str, object]:
        row: dict[str, object] = {
            "key": self.key,
            "seconds": round(self.seconds, 2),
            "completed": self.completed,
            "date": self.date,
        }
        # Only what is actually set: a Radio log full of ``"speed": 1.0`` and
        # ``"trimmed_seconds": 0`` would be two thirds noise.
        if self.item:
            row["item"] = self.item
        if self.speed != 1.0:
            row["speed"] = self.speed
        if self.trimmed_seconds:
            row["trimmed_seconds"] = round(self.trimmed_seconds, 2)
        if self.group:
            row["group"] = self.group
        return row

    @classmethod
    def from_dict(cls, data: object) -> MediaSession | None:
        if not isinstance(data, dict):
            return None
        key = str(data.get("key", "") or data.get("show_id", "")).strip()
        if not key:
            return None
        return cls(
            key=key,
            item=str(data.get("item", "") or data.get("episode_guid", "")).strip(),
            seconds=_coerce_float(data.get("seconds"), 0.0),
            speed=_coerce_float(data.get("speed"), 1.0) or 1.0,
            trimmed_seconds=_coerce_float(
                data.get("trimmed_seconds", data.get("smart_speed_saved_seconds")), 0.0
            ),
            completed=bool(data.get("completed", False)),
            date=str(data.get("date", "")),
            group=str(data.get("group", "")),
        )


@dataclass(slots=True)
class KeyTotal:
    """One show's, or one station's, share of a period."""

    key: str
    seconds: float = 0.0
    sessions: int = 0
    completed: int = 0


@dataclass(slots=True)
class StatsSummary:
    """Everything a statistics dialog reports for one period."""

    period_id: str = "all"
    period_label: str = "All time"
    total_seconds: float = 0.0
    saved_by_speed_seconds: float = 0.0
    saved_by_trim_seconds: float = 0.0
    #: True when at least one session carried a *measured* trim saving. The
    #: dialog omits the line entirely when this is False, rather than reporting
    #: a confident zero for something nobody measured.
    trim_measured: bool = False
    items_completed: int = 0
    sessions: int = 0
    keys: list[KeyTotal] = field(default_factory=list)
    groups: list[KeyTotal] = field(default_factory=list)

    @property
    def total_with_savings_seconds(self) -> float:
        """The content you got through: real time plus what speed bought."""
        return self.total_seconds + self.saved_by_speed_seconds + self.saved_by_trim_seconds


def _coerce_float(value: object, default: float) -> float:
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value) if value.strip() else default
        except ValueError:
            return default
    return default


def _parse(timestamp: str) -> datetime | None:
    text = (timestamp or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


def format_duration(seconds: float) -> str:
    """Spoken-friendly duration: "3 hours, 47 minutes".

    Words, not colons: a screen reader reads ``3:47:00`` as "three forty-seven
    zero zero", which is a time of day, not a length. Under a minute reports
    seconds so a fresh install does not read "0 minutes" and look broken.
    """
    total = int(max(0.0, seconds))
    if total < 60:
        return f"{total} second{'s' if total != 1 else ''}"
    hours, remainder = divmod(total, 3600)
    minutes = remainder // 60
    parts: list[str] = []
    if hours:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if minutes or not hours:
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
    return ", ".join(parts)


def summarize(
    sessions: list[MediaSession],
    *,
    period: str = "all",
    now: datetime | None = None,
) -> StatsSummary:
    """Total the sessions falling inside *period* (one of :data:`PERIODS`)."""
    moment = now or datetime.now(UTC)
    label, days = "All time", 0
    for period_id, period_label, period_days in PERIODS:
        if period_id == period:
            label, days = period_label, period_days
            break
    cutoff = moment - timedelta(days=days) if days else None
    summary = StatsSummary(period_id=period, period_label=label)
    totals: dict[str, KeyTotal] = {}
    groups: dict[str, KeyTotal] = {}
    for session in sessions:
        stamped = _parse(session.date)
        if cutoff is not None and (stamped is None or stamped < cutoff):
            continue
        summary.sessions += 1
        summary.total_seconds += session.seconds
        summary.saved_by_speed_seconds += session.seconds * max(0.0, session.speed - 1.0)
        if session.trimmed_seconds > 0:
            summary.saved_by_trim_seconds += session.trimmed_seconds
            summary.trim_measured = True
        if session.completed:
            summary.items_completed += 1
        total = totals.setdefault(session.key, KeyTotal(key=session.key))
        total.seconds += session.seconds
        total.sessions += 1
        if session.completed:
            total.completed += 1
        if session.group:
            grouped = groups.setdefault(session.group, KeyTotal(key=session.group))
            grouped.seconds += session.seconds
            grouped.sessions += 1
    summary.keys = sorted(totals.values(), key=lambda t: t.seconds, reverse=True)
    summary.groups = sorted(groups.values(), key=lambda t: t.seconds, reverse=True)
    return summary


def prune(
    sessions: list[MediaSession],
    *,
    retention_days: int = DEFAULT_RETENTION_DAYS,
    now: datetime | None = None,
) -> list[MediaSession]:
    """Drop sessions older than the retention window, newest kept.

    A session with no readable date is kept: an unparseable timestamp is a bug
    in whatever wrote it, not permission to throw the listener's history away.
    """
    moment = now or datetime.now(UTC)
    if retention_days > 0:
        cutoff = moment - timedelta(days=retention_days)
        kept = [s for s in sessions if (_parse(s.date) or moment) >= cutoff]
    else:
        kept = list(sessions)
    if len(kept) > MAX_SESSIONS:
        kept = kept[-MAX_SESSIONS:]
    return kept


def to_csv(
    sessions: list[MediaSession],
    *,
    titles: dict[str, str] | None = None,
    key_header: str = "Key",
    item_header: str = "Item",
) -> str:
    """The whole log as CSV, newest last, with a header row.

    Plain ``csv`` rather than a spreadsheet format on purpose: it opens in
    anything, and it reads perfectly well in a text editor with a screen
    reader, which a binary workbook does not.
    """
    import csv
    import io

    names = titles or {}
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow([
        "Date",
        key_header,
        item_header,
        "Minutes",
        "Speed",
        "Trimmed minutes",
        "Completed",
    ])
    for session in sessions:
        writer.writerow([
            session.date,
            names.get(session.key, session.key),
            session.item,
            f"{session.seconds / 60:.1f}",
            f"{session.speed:g}",
            f"{session.trimmed_seconds / 60:.1f}",
            "yes" if session.completed else "no",
        ])
    return buffer.getvalue()


# -- the store ---------------------------------------------------------------


def load_sessions(data_dir: Path, *, file_name: str) -> list[MediaSession]:
    """The log, or [] when there is none or it cannot be read."""
    import json

    try:
        raw = json.loads((data_dir / file_name).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    if not isinstance(raw, list):
        return []
    rows = [MediaSession.from_dict(entry) for entry in raw]
    return [row for row in rows if row is not None]


def save_sessions(
    data_dir: Path,
    sessions: list[MediaSession],
    *,
    file_name: str,
    retention_days: int = DEFAULT_RETENTION_DAYS,
    now: datetime | None = None,
) -> None:
    """Persist the log atomically, pruned on the way out."""
    from quill.core.storage import write_json_atomic

    kept = prune(sessions, retention_days=retention_days, now=now)
    write_json_atomic(data_dir / file_name, [session.to_dict() for session in kept])


def append_session(
    data_dir: Path,
    session: MediaSession,
    *,
    file_name: str,
    retention_days: int = DEFAULT_RETENTION_DAYS,
    now: datetime | None = None,
) -> None:
    """Add one session and save. A session of no length is not recorded.

    Never raises: statistics are a courtesy, and one that failed must not cost
    somebody their playback.
    """
    if session.seconds <= 0:
        return
    try:
        if not session.date:
            session.date = (now or datetime.now(UTC)).isoformat()
        sessions = load_sessions(data_dir, file_name=file_name)
        sessions.append(session)
        save_sessions(
            data_dir,
            sessions,
            file_name=file_name,
            retention_days=retention_days,
            now=now,
        )
    except Exception:  # noqa: BLE001 - statistics must never break playback
        return


def clear_sessions(data_dir: Path, *, file_name: str) -> int:
    """Delete the whole log. Returns how many sessions were removed."""
    sessions = load_sessions(data_dir, file_name=file_name)
    try:
        (data_dir / file_name).unlink(missing_ok=True)
    except OSError:
        return 0
    return len(sessions)
