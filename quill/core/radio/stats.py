"""How much you listened to the radio, and to what.

Quill Radio kept a *recently played* list (``core/radio/history.py``) and a song
log (``song_history.py``), and neither of them was time. So the app could tell
you what you had on and never how long -- which is the one question somebody
asks at the end of a week.

The engine is shared with QUILL Cast (:mod:`quill.core.media_stats`); this
module is Radio's vocabulary on top of it.

**A station, not an episode.** Sessions are keyed the way
``core/radio/favorites.py`` keys a station, so the totals here and the favorites
list are talking about the same thing and a renamed favorite does not fork into
two rows. The network is carried alongside as the group, because "four hours of
ACB Media" is a fact about a *network* that no per-station row can add up for
you.

**No speed, and no trimming.** Both are real numbers for a podcast and mean
nothing for a live stream: you cannot listen to a broadcast at 1.4x, and there
is no silence to remove from something that has not been recorded. Radio's
summary omits those lines entirely rather than reporting a confident zero --
which is the same rule Cast follows for a trim it did not measure.

wx-free, strict-typed.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from quill.core import media_stats
from quill.core.media_stats import MediaSession, StatsSummary

__all__ = [
    "FILE_NAME",
    "clear_sessions",
    "load_sessions",
    "record_listen",
    "station_key",
    "summarize",
]

#: Radio's own log, beside Cast's. The two count different things by different
#: keys, and one file would mean each app's summary silently including the
#: other's rows.
FILE_NAME = "radio_stats.json"


def station_key(station: Any) -> str:
    """A station's identity, spelled the way Favorites spells it.

    Delegates to ``favorites.FavoriteStation.key``'s own rule rather than
    reimplementing it, so a station counted here and the same station saved in
    Favorites can never disagree about being the same station.
    """
    from quill.core.radio.favorites import FavoriteStation

    try:
        return FavoriteStation(station=station).key
    except Exception:  # noqa: BLE001 - a station that cannot be keyed is not counted
        return ""


def record_listen(
    data_dir: Path,
    station: Any,
    seconds: float,
    *,
    network: str = "",
    now: datetime | None = None,
) -> None:
    """Note a stretch of listening. Never raises; a zero-length stretch is not one."""
    key = station_key(station)
    if not key or seconds <= 0:
        return
    media_stats.append_session(
        data_dir,
        MediaSession(
            key=key,
            item="",
            seconds=float(seconds),
            speed=1.0,
            completed=False,
            group=(network or "").strip(),
        ),
        file_name=FILE_NAME,
        now=now,
    )


def load_sessions(data_dir: Path) -> list[MediaSession]:
    """Radio's whole session log."""
    return media_stats.load_sessions(data_dir, file_name=FILE_NAME)


def summarize(data_dir: Path, *, period: str = "all", now: datetime | None = None) -> StatsSummary:
    """What Radio listened to in one period, totalled by station and network."""
    return media_stats.summarize(load_sessions(data_dir), period=period, now=now)


def clear_sessions(data_dir: Path) -> int:
    """Delete Radio's listening history. Returns how many sessions went."""
    return media_stats.clear_sessions(data_dir, file_name=FILE_NAME)


def describe(summary: StatsSummary, names: dict[str, str] | None = None) -> list[str]:
    """The summary as lines a screen reader reads straight through.

    A list of sentences rather than a table: a table of two columns read aloud
    is two columns to arrow across for information that fits in a sentence.
    """
    titles = names or {}
    duration = media_stats.format_duration
    lines = [
        f"{summary.period_label}.",
        f"Listened for {duration(summary.total_seconds)}.",
        f"{summary.sessions} listening session{'' if summary.sessions == 1 else 's'}.",
    ]
    if summary.keys:
        lines.append("")
        lines.append("By station:")
        lines.extend(
            f"{titles.get(total.key, total.key)}: {duration(total.seconds)}"
            for total in summary.keys[:20]
        )
    if summary.groups:
        lines.append("")
        lines.append("By network:")
        lines.extend(f"{total.key}: {duration(total.seconds)}" for total in summary.groups[:20])
    if not summary.sessions:
        lines = [f"{summary.period_label}.", "Nothing listened to yet in this period."]
    return lines
