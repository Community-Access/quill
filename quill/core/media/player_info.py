"""The reviewable summary of what is playing right now.

A player's status normally arrives as speech, one line at a time, and then it is
gone. This builds the same facts as a block of text that can be read at whatever
pace the listener wants -- arrow through it by character or word, copy a line
out of it, check the exact remaining time twice without touching playback.

Pure and wx-free: the caller gathers the numbers, this turns them into lines,
and :mod:`quill.ui.media.player_info_dialog` shows them.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class PlayerInfo:
    """Everything worth reporting about the current item."""

    title: str = ""
    #: The podcast, album, station, or book this belongs to.
    collection: str = ""
    position_ms: int = 0
    duration_ms: int = 0
    speed: float = 1.0
    #: True when the audio is coming off the network rather than a local file.
    streaming: bool = False
    #: True when the local copy is kept permanently, False when it is a
    #: temporary copy that retention will clean up. Ignored when streaming.
    saved_permanently: bool = True
    bookmark_count: int = 0
    note_count: int = 0
    #: The saved resume position, if there is one and it is not where we are.
    resume_ms: int = 0
    #: Free-text extras a caller wants included, e.g. ("Chapter 3 of 12",).
    extras: tuple[str, ...] = ()


def format_duration(ms: int) -> str:
    """``1:02:03`` or ``4:11``; negative and nonsense values read as ``0:00``."""
    if ms <= 0:
        return "0:00"
    total_seconds = ms // 1000
    minutes, seconds = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"


def spoken_duration(ms: int) -> str:
    """``1 hour 2 minutes 3 seconds`` -- for speech, where ``1:02:03`` is read
    as a time of day by some screen readers."""
    if ms <= 0:
        return "0 seconds"
    total_seconds = ms // 1000
    minutes, seconds = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    parts: list[str] = []
    if hours:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if minutes:
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
    if seconds or not parts:
        parts.append(f"{seconds} second{'s' if seconds != 1 else ''}")
    return " ".join(parts)


def percent_complete(position_ms: int, duration_ms: int) -> int:
    """How far through, 0-100. Zero when the duration is unknown."""
    if duration_ms <= 0 or position_ms <= 0:
        return 0
    return max(0, min(100, round(position_ms * 100 / duration_ms)))


def format_speed(speed: float) -> str:
    """``1.25x``, or ``Normal`` at 1.0 -- "1.0x" is noise on the common case."""
    if abs(speed - 1.0) < 0.005:
        return "Normal"
    text = f"{speed:.2f}".rstrip("0").rstrip(".")
    return f"{text}x"


def player_info_lines(info: PlayerInfo) -> list[str]:
    """The report, one ``Label: value`` line at a time.

    Lines that have nothing to say are left out entirely rather than printed
    empty -- a report full of "Unknown" is harder to review than a short one.
    """
    lines: list[str] = []
    if info.title:
        lines.append(f"Title: {info.title}")
    if info.collection:
        lines.append(f"From: {info.collection}")

    lines.append(f"Position: {format_duration(info.position_ms)}")
    if info.duration_ms > 0:
        remaining = max(0, info.duration_ms - info.position_ms)
        lines.append(f"Duration: {format_duration(info.duration_ms)}")
        lines.append(f"Remaining: {format_duration(remaining)}")
        lines.append(f"Progress: {percent_complete(info.position_ms, info.duration_ms)} percent")
    else:
        lines.append("Duration: not known for a live stream")

    lines.append(f"Speed: {format_speed(info.speed)}")

    if info.streaming:
        lines.append("Source: streaming")
    else:
        lines.append(
            "Source: a file on this computer"
            if info.saved_permanently
            else "Source: a temporary copy on this computer"
        )

    if info.bookmark_count:
        lines.append(
            f"Bookmarks: {info.bookmark_count}" if info.bookmark_count != 1 else "Bookmarks: 1"
        )
    if info.note_count:
        lines.append(f"Notes: {info.note_count}" if info.note_count != 1 else "Notes: 1")
    if info.resume_ms > 0 and abs(info.resume_ms - info.position_ms) > 1000:
        lines.append(f"Will resume at: {format_duration(info.resume_ms)}")
    lines.extend(extra for extra in info.extras if extra)
    return lines


def player_info_text(info: PlayerInfo) -> str:
    """The whole report as one reviewable block."""
    return "\n".join(player_info_lines(info))


def player_info_summary(info: PlayerInfo) -> str:
    """One spoken sentence, for the status bar or a quick announcement."""
    if not info.title:
        return "Nothing is playing."
    if info.duration_ms > 0:
        remaining = max(0, info.duration_ms - info.position_ms)
        return (
            f"{info.title}, {spoken_duration(info.position_ms)} in, "
            f"{spoken_duration(remaining)} remaining."
        )
    return f"{info.title}, {spoken_duration(info.position_ms)} in."
