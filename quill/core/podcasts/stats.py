"""Listening statistics (1.1.0): how much you listened, and what you saved.

``history.py`` answers "what did I play recently" in fifteen capped entries.
This answers a different question -- how much time went into podcasts, where
it went, and how much of it you got back by listening faster or by skipping
silence -- and needs a real append-only log to do it.

Three accessibility rules, taken from Earshot and worth keeping verbatim:

- every statistic is readable as plain text;
- durations are spoken naturally ("3 hours, 47 minutes"), never as ``13620``
  or ``03:47:00``;
- any chart is a secondary representation. The text *is* the report, which is
  why :func:`summarize` returns numbers and :func:`format_duration` returns
  English, and why the dialog that shows them is a read-only text field you
  arrow through line by line.

One number is deliberately absent unless it is real: time saved by Smart
Speed is only counted when the silence-trimming path reports what it actually
dropped. A fabricated "time saved" figure is worse than an absent one, so an
unreported saving stays zero rather than being estimated from the filter
settings.

WHAT IS SHARED WITH QUILL RADIO, AND WHAT IS NOT
------------------------------------------------
The engine -- the session record, the periods, the retention window, the
per-key totals, the CSV -- is :mod:`quill.core.media_stats`, and Radio sits on
the same one (``core/radio/stats.py``). What stays here is Cast's own
vocabulary and, deliberately, **Cast's own on-disk shape**.

The store is not migrated onto the shared one, and that is a decision rather
than an omission. This file has been accumulating real listening history in
``{"retention_days": n, "sessions": [...]}`` with ``show_id`` and
``episode_guid`` field names since 1.1.0. Rewriting it to the shared record's
spelling would gain tidiness and risk somebody's history, and there is no
version of that trade worth taking for a file nobody can recompute. The two
readers understand each other's field names (see
``MediaSession.from_dict``), so a future migration stays available and simply
is not urgent.

What genuinely was duplicated -- the period table and the way a duration is
spoken -- now comes from the shared module, so "this week" cannot come to mean
two different weeks in two apps a listener compares.

wx-free, strict-typed.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

from quill.core import media_stats
from quill.core.podcasts.models import now_iso

_FILE_NAME = "podcast_stats.json"
#: A hard ceiling on the log regardless of the retention window: a heavy
#: listener generates a session per play, and an unbounded JSON file that is
#: rewritten on every flush eventually becomes the reason playback stutters.
_MAX_SESSIONS = 5000
#: Matches Earshot's history_retention_days. Prune on write.
DEFAULT_RETENTION_DAYS = 90

#: Period selectors offered by the Statistics dialog: (id, label, days).
#: Shared with Quill Radio, because "this week" has to mean the same seven days
#: in both apps or a listener comparing them is comparing nothing.
PERIODS = media_stats.PERIODS


@dataclass(slots=True)
class ListeningSession:
    """One stretch of listening, flushed at a natural stopping point.

    ``seconds`` is wall-clock time with the audio actually playing --
    the honest denominator. ``speed`` is the rate it played at, which is what
    makes "time saved by speed" arithmetic rather than guesswork:
    ``seconds x (speed - 1)`` is exactly the extra content you got through.
    """

    show_id: str
    episode_guid: str
    seconds: float = 0.0
    speed: float = 1.0
    #: Seconds of silence the Smart Speed pass actually removed, when the
    #: pass can report it. Zero means "not measured", never "none saved".
    smart_speed_saved_seconds: float = 0.0
    #: True only when this session ran to the end of the episode.
    completed: bool = False
    date: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "show_id": self.show_id,
            "episode_guid": self.episode_guid,
            "seconds": round(self.seconds, 2),
            "speed": self.speed,
            "smart_speed_saved_seconds": round(self.smart_speed_saved_seconds, 2),
            "completed": self.completed,
            "date": self.date,
        }

    @classmethod
    def from_dict(cls, data: object) -> ListeningSession | None:
        if not isinstance(data, dict):
            return None
        show_id = str(data.get("show_id", "")).strip()
        episode_guid = str(data.get("episode_guid", "")).strip()
        if not show_id or not episode_guid:
            return None
        return cls(
            show_id=show_id,
            episode_guid=episode_guid,
            seconds=_coerce_float(data.get("seconds"), 0.0),
            speed=_coerce_float(data.get("speed"), 1.0) or 1.0,
            smart_speed_saved_seconds=_coerce_float(data.get("smart_speed_saved_seconds"), 0.0),
            completed=bool(data.get("completed", False)),
            date=str(data.get("date", "")),
        )


@dataclass(slots=True)
class ShowTotal:
    show_id: str
    seconds: float = 0.0
    sessions: int = 0
    completed: int = 0


@dataclass(slots=True)
class StatsSummary:
    """Everything the Statistics dialog reports for one period."""

    period_id: str = "all"
    period_label: str = "All time"
    total_seconds: float = 0.0
    saved_by_speed_seconds: float = 0.0
    saved_by_trim_seconds: float = 0.0
    #: True when at least one session in the period carried a measured Smart
    #: Speed saving -- the dialog omits the line entirely when it is False,
    #: rather than reporting a confident zero.
    trim_measured: bool = False
    episodes_completed: int = 0
    sessions: int = 0
    shows: list[ShowTotal] = field(default_factory=list)

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


#: Spoken-friendly duration ("3 hours, 47 minutes"), shared with Quill Radio.
#: Words rather than colons, because a screen reader reads ``3:47:00`` as
#: "three forty-seven zero zero", which is a time of day and not a length.
format_duration = media_stats.format_duration


def summarize(
    sessions: list[ListeningSession],
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
    totals: dict[str, ShowTotal] = {}
    for session in sessions:
        stamped = _parse(session.date)
        if cutoff is not None and (stamped is None or stamped < cutoff):
            continue
        summary.sessions += 1
        summary.total_seconds += session.seconds
        summary.saved_by_speed_seconds += session.seconds * max(0.0, session.speed - 1.0)
        if session.smart_speed_saved_seconds > 0:
            summary.saved_by_trim_seconds += session.smart_speed_saved_seconds
            summary.trim_measured = True
        if session.completed:
            summary.episodes_completed += 1
        total = totals.setdefault(session.show_id, ShowTotal(show_id=session.show_id))
        total.seconds += session.seconds
        total.sessions += 1
        if session.completed:
            total.completed += 1
    summary.shows = sorted(totals.values(), key=lambda t: t.seconds, reverse=True)
    return summary


def prune(
    sessions: list[ListeningSession],
    *,
    retention_days: int = DEFAULT_RETENTION_DAYS,
    now: datetime | None = None,
) -> list[ListeningSession]:
    """Drop sessions older than the retention window, newest kept.

    A session with no readable date is kept: an unparseable timestamp is a
    bug in whatever wrote it, not permission to throw the listener's history
    away.
    """
    moment = now or datetime.now(UTC)
    if retention_days > 0:
        cutoff = moment - timedelta(days=retention_days)
        kept = [s for s in sessions if (_parse(s.date) or moment) >= cutoff]
    else:
        kept = list(sessions)
    if len(kept) > _MAX_SESSIONS:
        kept = kept[-_MAX_SESSIONS:]
    return kept


def to_csv(sessions: list[ListeningSession], *, show_titles: dict[str, str] | None = None) -> str:
    """The whole log as CSV, newest last, with a header row.

    Plain ``csv`` output rather than a spreadsheet format on purpose: it opens
    in anything, and it reads perfectly well in a text editor with a screen
    reader, which a binary workbook does not.
    """
    import csv
    import io

    titles = show_titles or {}
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow([
        "date",
        "show",
        "show_id",
        "episode_guid",
        "seconds",
        "speed",
        "silence_trimmed_seconds",
        "completed",
    ])
    for session in sessions:
        writer.writerow([
            session.date,
            titles.get(session.show_id, ""),
            session.show_id,
            session.episode_guid,
            round(session.seconds, 2),
            session.speed,
            round(session.smart_speed_saved_seconds, 2),
            "yes" if session.completed else "no",
        ])
    return buffer.getvalue()


def _store_path(data_dir: Path) -> Path:
    return data_dir / _FILE_NAME


def load_sessions(data_dir: Path) -> list[ListeningSession]:
    """Read the log (an absent or broken file reads as empty)."""
    try:
        raw = json.loads(_store_path(data_dir).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    entries = raw.get("sessions") if isinstance(raw, dict) else raw
    sessions: list[ListeningSession] = []
    for entry in entries if isinstance(entries, list) else []:
        session = ListeningSession.from_dict(entry)
        if session is not None:
            sessions.append(session)
    return sessions


def save_sessions(
    data_dir: Path,
    sessions: list[ListeningSession],
    *,
    retention_days: int = DEFAULT_RETENTION_DAYS,
) -> list[ListeningSession]:
    """Prune, then persist atomically; returns what was actually written."""
    from quill.core.storage import write_json_atomic

    kept = prune(sessions, retention_days=retention_days)
    write_json_atomic(
        _store_path(data_dir),
        {"retention_days": retention_days, "sessions": [s.to_dict() for s in kept]},
    )
    return kept


def append_session(
    data_dir: Path,
    session: ListeningSession,
    *,
    retention_days: int = DEFAULT_RETENTION_DAYS,
) -> None:
    """Add one finished session to the log.

    Callers buffer in memory and flush at the points position is already
    saved (pause / stop / episode change / close) -- this must never be
    called from a position poll, which runs once a second on the UI thread.
    """
    if session.seconds <= 0:
        return
    if not session.date:
        session.date = now_iso()
    sessions = load_sessions(data_dir)
    sessions.append(session)
    save_sessions(data_dir, sessions, retention_days=retention_days)


def clear_sessions(data_dir: Path) -> int:
    """Delete the whole log; returns how many sessions were discarded."""
    count = len(load_sessions(data_dir))
    save_sessions(data_dir, [])
    return count


__all__ = [
    "DEFAULT_RETENTION_DAYS",
    "PERIODS",
    "ListeningSession",
    "ShowTotal",
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
