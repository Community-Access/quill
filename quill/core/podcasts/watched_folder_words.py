"""Watched folders, in words: the list row and what an arrival says (qc.md 5d).

Split from :mod:`quill.core.podcasts.watched_folders` under GATE-11. wx-free.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from quill.core.podcasts.watched_folders import (
    NETWORK_POLL_MINUTES,
    WatchedFolder,
    is_network_path,
)

# -- what is said ------------------------------------------------------------------


def _minutes(seconds: float) -> str:
    minutes = round((seconds or 0) / 60)
    if minutes <= 0:
        return ""
    return "1 minute" if minutes == 1 else f"{minutes} minutes"


def arrival_sentence(folder: WatchedFolder, added: list[tuple[Any, Any]]) -> str:
    """What is spoken for *added*, by the folder's Tell me setting ("" = nothing)."""
    if not added or folder.tell == "quiet":
        return ""
    name = folder.display_name()
    if folder.tell == "batch" or len(added) > 3:
        noun = "recording" if len(added) == 1 else "recordings"
        return f"{len(added)} new {noun} in {name}."
    parts = []
    for _show, episode in added:
        length = _minutes(getattr(episode, "duration_seconds", 0) or 0)
        parts.append(f"{episode.title}, {length}" if length else str(episode.title))
    return f"New in {name}: " + "; ".join(parts) + "."


def _when(iso: str, now: datetime) -> str:
    if not iso:
        return "nothing new yet"
    try:
        then = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return "nothing new yet"
    hours = (now - then).total_seconds() / 3600
    if hours < 1:
        return "last new: just now"
    if hours < 24:
        whole = int(hours)
        return f"last new: {whole} hour{'s' if whole != 1 else ''} ago"
    return f"last new: {then.astimezone().strftime('%A %d %B')}"


def state_of(folder: WatchedFolder) -> str:
    if folder.paused:
        return "paused"
    if not Path(folder.path).is_dir():
        return "unavailable"
    if is_network_path(folder.path):
        return f"checked every {NETWORK_POLL_MINUTES} minutes"
    return "watching"


def file_count(library: Any, folder: WatchedFolder) -> int:
    total = 0
    for show_id in [folder.show_id, *folder.group_shows.values()]:
        show = library.find_show(show_id) if show_id else None
        total += len(show.episodes) if show is not None else 0
    return total


def row_text(library: Any, folder: WatchedFolder, *, now: datetime | None = None) -> str:
    """One row of the Watched Folders list, as a sentence."""
    count = file_count(library, folder)
    files = "1 file" if count == 1 else f"{count} files"
    moment = now or datetime.now(UTC)
    return (
        f"{folder.display_name()}, {state_of(folder)}, {files}, "
        f"{_when(folder.last_arrival, moment)}, {folder.path}"
    )
