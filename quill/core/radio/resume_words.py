"""What Quill Radio says about a recording an unexpected close interrupted (FUX-05).

The resume offer used to read "A recording of WQXR was in progress until
2026-11-24 21:00:00-05:00": a raw timestamp, nothing about what had already
been recorded, and nothing about what Resume or Skip would do to it. A
recording whose time had run out was cleared without a word, and the files
moved home from the temporary folder were only counted.

Everything here names the work the way a listener does -- the station and the
spoken start time (:func:`spoken_start`, the same words a finished recording
uses), how much was recorded and where it is kept -- and says what each choice
does. wx-free and strict-typed; the frame only speaks and keeps the sentences.
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

from quill.core.radio.recording_report import format_length, spoken_start
from quill.core.radio.recording_resume import ActiveRecordingMarker

__all__ = [
    "batch_line",
    "clock",
    "cut_short_sentence",
    "kept_where",
    "moved_sentence",
    "offer_sentence",
    "partial_file",
    "recorded_seconds",
    "resume_failed_sentence",
    "unclaimed",
]


def clock(when: datetime) -> str:
    """``9:00 PM``: an end time as it is said, not as ISO writes it."""
    hour = when.hour % 12 or 12
    return f"{hour}:{when:%M} {'AM' if when.hour < 12 else 'PM'}"


def _same(a: Path, b: Path) -> bool:
    return os.path.normcase(str(a)) == os.path.normcase(str(b))


def _belongs(path: Path, marker: ActiveRecordingMarker) -> bool:
    """Whether *path* is the part *marker* recorded (moved home, perhaps as " (2)")."""
    for named in (marker.temp_path, marker.output_path):
        if named and _same(Path(named), path):
            return True
    if not marker.output_path:
        return False
    home = Path(marker.output_path)
    return _same(path.parent, home.parent) and path.stem.startswith(home.stem)


def partial_file(marker: ActiveRecordingMarker, moved: list[Path]) -> Path | None:
    """The part *marker* recorded before the close, wherever it now is, or None."""
    for path in moved:
        if _belongs(path, marker):
            return path
    for named in (marker.output_path, marker.temp_path):
        if named:
            candidate = Path(named)
            try:
                if candidate.is_file() and candidate.stat().st_size > 0:
                    return candidate
            except OSError:
                continue
    return None


def unclaimed(moved: list[Path], markers: list[ActiveRecordingMarker]) -> list[Path]:
    """Moved files no marker accounts for: only these need a sentence of their own."""
    return [path for path in moved if not any(_belongs(path, m) for m in markers)]


def recorded_seconds(marker: ActiveRecordingMarker, path: Path | None) -> int | None:
    """How much was recorded: from the start to the file's last write, or None."""
    started = marker.started
    if path is None or started is None:
        return None
    try:
        written = path.stat().st_mtime
    except OSError:
        return None
    last = (
        datetime.fromtimestamp(written, started.tzinfo)
        if started.tzinfo
        else datetime.fromtimestamp(written)
    )
    seconds = int((last - started).total_seconds())
    ceiling = max(0, marker.duration_minutes) * 60
    if seconds < 0:
        return None
    return min(seconds, ceiling) if ceiling else seconds


def kept_where(path: Path, destination_root: str, temp_dir: str = "") -> str:
    """Where the part is kept, in words: never a temporary path."""
    if temp_dir and _same(path.parent, Path(temp_dir)):
        return "in the temporary recording folder"
    if destination_root and _same(path.parent, Path(destination_root)):
        return "in your recordings folder"
    return f"in the {path.parent.name or path.parent} folder"


def _what(marker: ActiveRecordingMarker) -> str:
    station = marker.station_name or "the stream"
    started = marker.started
    return f"{station}, started {spoken_start(started)}" if started else station


def _kept(seconds: int | None, where: str) -> str:
    if not where:
        return "Nothing it recorded before then was found."
    if seconds is None:
        return f"What it recorded is kept {where}."
    return f"What it recorded, {format_length(seconds)}, is kept {where}."


def offer_sentence(
    marker: ActiveRecordingMarker, *, left: int, seconds: int | None, where: str
) -> str:
    """The single resume offer: the work, what exists, and what each button does."""
    end = marker.end
    joint = " and" if marker.started else ","
    due = f"{joint} due to end at {clock(end)}" if end else ""
    comma = "," if (marker.started or end) else ""
    return (
        f"Your recording of {_what(marker)}{due}{comma} stopped unexpectedly. "
        f"{_kept(seconds, where)}\n\n"
        f"Resume records the remaining {format_length(max(1, left) * 60)} as a separate "
        "file. Skip records nothing more. Either way, nothing already recorded is deleted."
    )


def batch_line(marker: ActiveRecordingMarker, *, left: int, seconds: int | None) -> str:
    """One row of the several-recordings offer."""
    done = f"{format_length(seconds)} recorded" if seconds is not None else "nothing recorded found"
    return f"{_what(marker)}: {done}, {format_length(max(1, left) * 60)} left"


def cut_short_sentence(marker: ActiveRecordingMarker, *, seconds: int | None, where: str) -> str:
    """A recording whose time ran out while the app was closed: said once, kept."""
    end = marker.end
    due = f" before it was due to end at {clock(end)}" if end else ""
    comma = "," if marker.started else ""
    return (
        f"Your recording of {_what(marker)}{comma} stopped unexpectedly{due}. "
        f"{_kept(seconds, where)}"
    )


def resume_failed_sentence(marker: ActiveRecordingMarker) -> str:
    """A resume that did not start: the station, never exception text."""
    return (
        f"The recording of {marker.station_name or 'the stream'} could not be resumed. "
        "What it recorded before is kept."
    )


def moved_sentence(paths: list[Path], where: str) -> str:
    """Files left in the temporary folder by a crash, moved home, each named."""
    if not paths:
        return ""
    names = "; ".join(path.stem for path in paths)
    noun = "recording" if len(paths) == 1 else "recordings"
    return (
        f"Moved {len(paths)} {noun} left in the temporary folder after an unexpected "
        f"close to {where}: {names}."
    )
