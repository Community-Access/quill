"""A new download folder takes the downloads still waiting with it (Chris Nova, 2026-11-20).

Each download's file path was fixed when the episode was queued, so changing
the download folder in Preferences only reached episodes queued afterwards:
everything already waiting still saved to the old folder. The person changed
the folder to put their episodes somewhere; the ones they had just asked for
are the ones they expect to find there.

Only downloads that have not written anything yet move. One that has started
(or was paused part way) keeps its partial file where it is and resumes there,
because moving a half-written file is a copy that can fail on another drive,
and the person would lose what had already arrived. The sentence says how many
moved and how many finish in the old folder, once (FUX-04).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

__all__ = ["follow_new_folder"]


def _relative(path: Path, root: Path) -> Path | None:
    try:
        return path.relative_to(root)
    except ValueError:
        return None


def _downloads(count: int) -> str:
    return "1 download" if count == 1 else f"{count} downloads"


def follow_new_folder(queue: Any, old_root: Path | None, new_root: Path | None) -> str:
    """Move the waiting downloads under *old_root* to *new_root*; say what happened.

    Returns "" when the folder did not change or nothing was waiting, so the
    caller's own "saved" sentence is all the person hears.
    """
    if queue is None or old_root is None or new_root is None:
        return ""
    if Path(old_root) == Path(new_root):
        return ""
    old_root, new_root = Path(old_root), Path(new_root)

    def move(item: Any) -> Path | None:
        relative = _relative(Path(item.destination), old_root)
        if relative is None or Path(item.destination).exists():
            return None  # another folder, or already part-written: resume in place
        return new_root / relative

    moved = queue.move_waiting(move)
    staying = sum(
        1
        for item in queue.snapshot()
        if item.status in ("queued", "paused", "downloading")
        and _relative(Path(item.destination), old_root) is not None
    )
    parts = []
    if moved:
        parts.append(f"{_downloads(moved)} waiting will now save to {new_root}.")
    if staying:
        verb = "finishes" if staying == 1 else "finish"
        parts.append(f"{_downloads(staying)} already started {verb} in the old folder.")
    return " ".join(parts)
