"""The lines of a player's "Now playing" field, built once for every player.

QUILL Cast's Now Playing window and Quill Radio's player panel both show a
read-only, multi-line field named "Now playing" (plan Phase 2, 2026-11-27).
Both build it here, beside :mod:`quill.core.media.player_info`, so the two cannot
drift apart. The order is fixed and every line is optional: a fact nobody
knows is a line left out, never "unknown".

* Episode title, then podcast
* Chapter: title, time, "3 of 12"
* Position: 18:30 of 58:00, 39:30 left, 32 percent
* Speed, volume, sleep timer
* Published date, season and episode number, file or stream
* Chapter source and transcript status

Pure and wx-free.
"""

from __future__ import annotations

from dataclasses import dataclass

from quill.core.media.progress_words import percent_phrase
from quill.core.podcasts.listening_words import clock

__all__ = ["NowPlayingFacts", "now_playing_lines", "position_line"]


@dataclass(slots=True)
class NowPlayingFacts:
    """What the caller knows; anything left at its default is not said."""

    title: str = ""
    collection: str = ""
    paused: bool = False
    chapter_title: str = ""
    chapter_start_ms: int = 0
    chapter_index: int = -1
    chapter_count: int = 0
    position_ms: int = 0
    #: A length worth trusting (``progress_words.trusted_length_ms``), or 0.
    length_ms: int = 0
    live: bool = False
    speed: float = 1.0
    volume_percent: int | None = None
    muted: bool = False
    sleep: str = ""
    published: str = ""
    season: int = 0
    episode_number: int = 0
    #: "file" or "stream"; "" says neither.
    where: str = ""
    chapter_source: str = ""
    transcript: str = ""


def position_line(position_ms: int, length_ms: int, *, live: bool = False) -> str:
    """ "18:30 of 58:00, 39:30 left, 32 percent"; live says time since tuning in."""
    if live:
        return f"Live, {clock(position_ms)} since you tuned in"
    if length_ms <= 0:
        return f"{clock(position_ms)} in"
    left = max(0, length_ms - position_ms)
    words = f"{clock(position_ms)} of {clock(length_ms)}, {clock(left)} left"
    percent = percent_phrase(position_ms, length_ms)
    return f"{words}, {percent}" if percent else words


def _levels(facts: NowPlayingFacts) -> str:
    parts: list[str] = []
    if abs(facts.speed - 1.0) > 1e-6:
        parts.append(f"Speed {facts.speed:g} times normal")
    if facts.muted:
        parts.append("muted")
    elif facts.volume_percent is not None:
        parts.append(f"volume {facts.volume_percent} percent")
    if facts.sleep:
        parts.append(facts.sleep)
    if not parts:
        return ""
    line = ", ".join(parts)
    return line[0].upper() + line[1:]


def _date_words(value: str) -> str:
    """27 November 2026 from 2026-11-27; anything else as given."""
    from datetime import date

    try:
        day = date.fromisoformat(value[:10])
    except ValueError:
        return value
    return f"{day.day} {day:%B} {day.year}"


def _about(facts: NowPlayingFacts) -> str:
    parts: list[str] = []
    if facts.published:
        parts.append(f"Published {_date_words(facts.published)}")
    if facts.season and facts.episode_number:
        parts.append(f"season {facts.season}, episode {facts.episode_number}")
    elif facts.episode_number:
        parts.append(f"episode {facts.episode_number}")
    if facts.where == "file":
        parts.append("playing from the file")
    elif facts.where == "stream":
        parts.append("streaming")
    if not parts:
        return ""
    line = ", ".join(parts)
    return line[0].upper() + line[1:]


def now_playing_lines(facts: NowPlayingFacts) -> list[str]:
    """The field's lines, in order; ``["Nothing is playing."]`` with no title."""
    if not facts.title:
        return ["Nothing is playing."]
    title = f"{facts.title} (paused)" if facts.paused else facts.title
    lines = [f"{title}, from {facts.collection}" if facts.collection else title]
    if facts.chapter_index >= 0 and facts.chapter_count:
        name = " ".join(facts.chapter_title.split()) or "Untitled"
        lines.append(
            f"Chapter: {name}, {clock(facts.chapter_start_ms)}, "
            f"{facts.chapter_index + 1} of {facts.chapter_count}"
        )
    lines.append("Position: " + position_line(facts.position_ms, facts.length_ms, live=facts.live))
    for line in (_levels(facts), _about(facts)):
        if line:
            lines.append(line)
    sources = [part for part in (facts.chapter_source, facts.transcript) if part]
    if sources:
        lines.append("; ".join(sources))
    return lines
