"""Streaks, and the year in review -- as sentences, because the text is the artefact.

Cast has counted hours since 1.1.0 and never said anything about them. Two
things are missing and they are different in kind:

* **Streaks** are a running fact -- "you have listened on eleven days in a row"
  -- and they are **off by default**. A streak is a nudge, and a nudge nobody
  asked for is pressure. Somebody who wants it turns it on; nobody is told
  about their own habits by an app they opened to hear a podcast.
* **A year in review** is a thing you go and read once, so it is a paragraph,
  not a dashboard. No charts, no tiles, no percentages that mean nothing said
  aloud: a few sentences somebody can read, copy, or send to a friend.

**Every number here is one the log actually contains.** Where the log cannot
support a line -- time saved by trimming, which is only measured when the trim
pass reports it -- the line is *omitted entirely* rather than printed as a
confident zero.

wx-free, strict-typed, pure. A list of sessions and a date in; text out.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

__all__ = ["Streaks", "streaks", "year_in_review"]


@dataclass(frozen=True, slots=True)
class Streaks:
    """How many days in a row, at best and right now."""

    current_days: int = 0
    longest_days: int = 0
    active_days_this_year: int = 0

    def describe(self) -> str:
        """One or two sentences, or "" when there is nothing to say yet."""
        if not self.longest_days:
            return ""
        lines = []
        if self.current_days > 1:
            lines.append(f"You have listened on {self.current_days} days in a row.")
        elif self.current_days == 1:
            lines.append("You have listened today.")
        if self.longest_days > self.current_days:
            lines.append(f"Your longest run is {self.longest_days} days.")
        return " ".join(lines)


def _local_day(stamp: str) -> date | None:
    """The **local** day a session started on.

    Local, not UTC, and that is the whole subtlety: somebody listening at half
    past eleven at night in London is listening on that day, and a UTC bucket
    would put half their evenings on the following morning and break every
    streak they have.
    """
    text = (stamp or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone().date()


def _days(sessions: Sequence[object]) -> set[date]:
    found: set[date] = set()
    for session in sessions:
        day = _local_day(str(getattr(session, "date", "") or ""))
        if day is not None:
            found.add(day)
    return found


def streaks(sessions: Sequence[object], *, today: date | None = None) -> Streaks:
    """Consecutive listening days: the run now, and the best one.

    A day counts when at least one session started in it, however short --
    "did you listen" is the question, not "how much".

    **Today not having happened yet does not break a streak.** A run ending
    yesterday is still current at nine in the morning; it stops being current
    only once a whole day has passed with nothing in it. Anything else would
    tell somebody their streak was broken before they had had a chance to
    listen, which is the cruellest possible version of this feature.
    """
    now = today or datetime.now().astimezone().date()
    days = _days(sessions)
    if not days:
        return Streaks()

    longest = run = 0
    previous: date | None = None
    for day in sorted(days):
        run = run + 1 if previous is not None and day - previous == timedelta(days=1) else 1
        longest = max(longest, run)
        previous = day

    current = 0
    cursor = now if now in days else now - timedelta(days=1)
    while cursor in days:
        current += 1
        cursor -= timedelta(days=1)

    return Streaks(
        current_days=current,
        longest_days=longest,
        active_days_this_year=len([day for day in days if day.year == now.year]),
    )


def year_in_review(
    sessions: Sequence[object],
    year: int,
    show_titles: dict[str, str] | None = None,
    *,
    today: date | None = None,
) -> str:
    """The year, in plain English. "" when there is nothing to report.

    The text *is* the artefact: it is meant to be read, copied, or sent to
    somebody. That is why it is sentences and not a table -- a table read aloud
    is a list of numbers with their meanings three columns away.
    """
    from quill.core import media_stats

    titles = show_titles or {}
    scoped = [
        session
        for session in sessions
        if (_local_day(str(getattr(session, "date", "") or "")) or date.min).year == year
    ]
    if not scoped:
        return ""

    total = sum(float(getattr(session, "seconds", 0.0) or 0.0) for session in scoped)
    by_speed = sum(
        float(getattr(session, "seconds", 0.0) or 0.0)
        * max(0.0, float(getattr(session, "speed", 1.0) or 1.0) - 1.0)
        for session in scoped
    )
    trimmed = sum(
        float(
            getattr(session, "trimmed_seconds", 0.0)
            or getattr(session, "smart_speed_saved_seconds", 0.0)
            or 0.0
        )
        for session in scoped
    )
    finished = sum(1 for session in scoped if getattr(session, "completed", False))

    per_show: dict[str, float] = {}
    per_month: dict[int, float] = {}
    for session in scoped:
        seconds = float(getattr(session, "seconds", 0.0) or 0.0)
        key = str(getattr(session, "key", "") or getattr(session, "show_id", ""))
        per_show[key] = per_show.get(key, 0.0) + seconds
        day = _local_day(str(getattr(session, "date", "") or ""))
        if day is not None:
            per_month[day.month] = per_month.get(day.month, 0.0) + seconds

    spoken = media_stats.format_duration
    lines = [
        f"Your {year} in listening.",
        "",
        f"You listened for {spoken(total)}.",
    ]
    days_equivalent = total / 86400
    if days_equivalent >= 1:
        lines.append(f"That is {days_equivalent:.1f} days of audio.")
    if finished:
        lines.append(f"You finished {finished} episode{'' if finished == 1 else 's'}.")

    if per_month:
        busiest = max(per_month.items(), key=lambda row: row[1])
        month_name = date(year, busiest[0], 1).strftime("%B")
        lines.append(f"Your busiest month was {month_name}, at {spoken(busiest[1])}.")

    top = sorted(per_show.items(), key=lambda row: row[1], reverse=True)[:5]
    if top:
        lines.append("")
        lines.append("What you listened to most:")
        for key, seconds in top:
            share = (seconds / total * 100) if total else 0
            # A show id read aloud is noise. If the library no longer holds
            # the show, say that rather than reading out its id.
            name = titles.get(key) or "A podcast no longer in your library"
            lines.append(f"{name}: {spoken(seconds)}, {share:.0f} percent of your year.")

    if by_speed >= 60:
        lines.append("")
        lines.append(f"Playing faster than normal saved you {spoken(by_speed)}.")
    # Omitted entirely when nothing measured it: a confident zero here would be
    # a claim the log cannot support.
    if trimmed >= 60:
        lines.append(f"Trimming silence saved you another {spoken(trimmed)}.")

    run = streaks(scoped, today=today)
    if run.active_days_this_year:
        lines.append("")
        lines.append(f"You listened on {run.active_days_this_year} days this year.")
        described = run.describe()
        if described:
            lines.append(described)
    return "\n".join(lines)
