"""Recent documents: the one set of rules both editors keep their list by.

QUILL and QUILL Lite each remember the files you opened -- QUILL in
``recent.json``, QUILL Lite in its own settings -- and the two lists stay
**separate on purpose**: a recent list is a record of one install on one
computer, which is why "Bring My QUILL Lite Settings" and both portable backups
leave it behind (``lite_bridge._NOT_COPIED``, ``lite.settings.LOCAL_SETTINGS``).
What they share is everything *about* the list: how a file goes to the top,
what pinning means, what Clear clears, how a row is worded and numbered, and
which missing files are hidden from the menu. That lives here, wx-free, so the
Open Recent submenu and the Recent Documents window cannot say one thing in one
editor and another in the other.

**Pins are a second list, not a flag on the first.** A pinned document is kept
however many others you open after it, so it cannot live in a list that is cut
to a length. The two lists are shown as one -- pinned first, in the order you
pinned them, then the rest newest first -- and a file is never shown twice.

**Clear leaves pins alone.** Pinning is the way you say "keep this one", and a
Clear that undid it would make pinning worthless the first time you tidied up.

**A missing file is hidden from the menu only when it is certainly gone.**
``quill.core.recent._is_fixed_drive`` is the test (#14): a file missing from an
internal drive has been moved or deleted, but one missing from a USB stick or a
network share usually means the drive is not plugged in, and dropping it would
lose it for good the next time it is. The Recent Documents window shows every
row either way and says which ones are not there.

Strict-typed, no ``wx``.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

__all__ = [
    "DEFAULT_LIMIT",
    "LIMIT_MAX",
    "LIMIT_MIN",
    "NUMBERED",
    "RecentEntry",
    "certainly_gone",
    "clamp_limit",
    "clear_unpinned",
    "describe_cleared",
    "drop_missing",
    "entries",
    "forget",
    "is_pinned",
    "menu_label",
    "menu_paths",
    "ordered",
    "remember",
    "same_file",
    "toggle_pin",
]

#: How many recent files are remembered unless you say otherwise. QUILL's
#: ``recent_files_limit`` default, and QUILL Lite's long-standing ten.
DEFAULT_LIMIT = 10
#: The range the setting is clamped to, in both editors.
LIMIT_MIN = 1
LIMIT_MAX = 50
#: How many rows of the Open Recent submenu get Alt+Shift+1 to Alt+Shift+9.
NUMBERED = 9


def clamp_limit(value: object) -> int:
    """*value* as a usable limit: a number from 1 to 50, ten when unreadable."""
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        return DEFAULT_LIMIT
    try:
        number = int(value)
    except ValueError:
        return DEFAULT_LIMIT
    return max(LIMIT_MIN, min(LIMIT_MAX, number))


def _key(path: str | Path) -> str:
    """The form two spellings of one file agree on: case and slashes folded."""
    return os.path.normcase(os.path.normpath(str(path)))


def same_file(first: str | Path, second: str | Path) -> bool:
    """Whether *first* and *second* name the same file, by text alone."""
    return _key(first) == _key(second)


def remember(paths: Sequence[str], path: str | Path, limit: int) -> list[str]:
    """*paths* with *path* moved to the top, no duplicate, cut to *limit*."""
    text = str(path)
    kept = [entry for entry in paths if not same_file(entry, text)]
    return [text, *kept][: clamp_limit(limit)]


def forget(paths: Sequence[str], path: str | Path) -> list[str]:
    """*paths* without *path*. The file itself is never touched."""
    return [entry for entry in paths if not same_file(entry, path)]


def is_pinned(pinned: Sequence[str], path: str | Path) -> bool:
    return any(same_file(entry, path) for entry in pinned)


def toggle_pin(pinned: Sequence[str], path: str | Path) -> tuple[list[str], bool]:
    """Pin *path*, or unpin it if it was pinned. Returns the list and the new state."""
    if is_pinned(pinned, path):
        return forget(pinned, path), False
    return [*pinned, str(path)], True


def ordered(recent: Sequence[str], pinned: Sequence[str]) -> list[str]:
    """The one list both editors show: pinned first, then the rest, no repeats."""
    shown: list[str] = []
    for entry in [*pinned, *recent]:
        if not any(same_file(entry, seen) for seen in shown):
            shown.append(str(entry))
    return shown


def clear_unpinned(recent: Sequence[str], pinned: Sequence[str]) -> list[str]:
    """What the recent list holds after Clear: nothing that is not pinned."""
    return [entry for entry in recent if is_pinned(pinned, entry)]


def _exists(path: str) -> bool:
    try:
        return Path(path).exists()
    except OSError:
        return True  # keep on any access error rather than risk a wrong answer


def certainly_gone(path: str | Path) -> bool:
    """Missing from a confirmed internal drive -- never true for USB or network."""
    from quill.core.recent import _is_fixed_drive

    candidate = Path(path)
    return _is_fixed_drive(candidate) and not _exists(str(candidate))


def drop_missing(paths: Sequence[str]) -> list[str]:
    """*paths* less the certainly gone: the at-launch tidy both editors offer.

    ``prune_missing_recent_files`` is QUILL's function since #14, used here
    unchanged so a USB or network entry survives in QUILL Lite exactly as in QUILL.
    """
    from quill.core.recent import prune_missing_recent_files

    kept, _removed = prune_missing_recent_files([Path(p) for p in paths], enabled=True)
    return [str(p) for p in kept]


def menu_paths(
    recent: Sequence[str],
    pinned: Sequence[str],
    *,
    gone: Callable[[str], bool] = certainly_gone,
) -> list[str]:
    """What the Open Recent submenu lists: :func:`ordered`, less the certainly gone."""
    return [entry for entry in ordered(recent, pinned) if not gone(entry)]


def menu_label(index: int, path: str | Path, *, pinned: bool = False) -> str:
    """One Open Recent row: the name first, because it is what you listen for.

    The first nine carry a digit and Alt+Shift+digit, in both editors. The
    folder follows in brackets, so two files called ``notes.txt`` can be told
    apart without the whole path being read before the name.
    """
    target = Path(path)
    text = f"{target.name}  ({target.parent})" + (", pinned" if pinned else "")
    if index <= NUMBERED:
        return f"&{index} {text}\tAlt+Shift+{index}"
    return text


@dataclass(frozen=True, slots=True)
class RecentEntry:
    """One row of the Recent Documents window."""

    path: str
    pinned: bool
    exists: bool

    @property
    def name(self) -> str:
        return Path(self.path).name or self.path

    @property
    def folder(self) -> str:
        return str(Path(self.path).parent)

    @property
    def label(self) -> str:
        """The row as it is read: name, folder, then pinned and missing if so."""
        parts = [f"{self.name}, in {self.folder}"]
        if self.pinned:
            parts.append("pinned")
        if not self.exists:
            parts.append("not found")
        return ", ".join(parts)


def entries(
    recent: Sequence[str],
    pinned: Sequence[str],
    *,
    exists: Callable[[str], bool] = _exists,
) -> tuple[RecentEntry, ...]:
    """Every remembered document, pinned first, each told whether it is there."""
    return tuple(
        RecentEntry(path=entry, pinned=is_pinned(pinned, entry), exists=exists(entry))
        for entry in ordered(recent, pinned)
    )


def describe_cleared(removed: int, kept_pinned: int) -> str:
    """The sentence said after Clear, including what it left alone."""
    noun = "document" if removed == 1 else "documents"
    said = f"Cleared {removed} recent {noun}."
    if kept_pinned:
        pins = "pinned document stays" if kept_pinned == 1 else "pinned documents stay"
        said += f" {kept_pinned} {pins}."
    return said
