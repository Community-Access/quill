"""Things the apps want to tell you about, kept where you can go back to them.

A desktop notification is a good way to be told something and a terrible way to
*remember* it: it appears over whatever you were reading, it disappears on its
own schedule, and if a screen reader was mid-sentence when it arrived it may
never have been read at all. Every listener has lost one that way.

So the toast is not the record -- this is. Every alert an app raises lands here
first, and the desktop notification (and the sound) are the optional, louder
half on top. That is what makes the **quiet** alert mode a real choice rather
than a euphemism for "off": quiet still records, it just does not interrupt.
And it is what makes a missed toast recoverable, which is the accessibility
point of the whole thing.

### Shape

A :class:`Notice` is deliberately small: who raised it, one line of title, one
of body, when, whether it has been read, and an optional *target* the app knows
how to open (a show id, say). No severity, no icons, no actions list -- a
notification centre that grows a taxonomy is one nobody can skim.

The store is **bounded** (:data:`MAX_NOTICES`) and drops the oldest first. An
unbounded list of "you have new episodes" from two years ago is not a feature.

wx-free, strict-typed, pure I/O through :mod:`quill.core.storage`, so both apps
and the tests can use it without a display.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from quill.core.storage import read_json, write_json_atomic

__all__ = [
    "MAX_NOTICES",
    "Notice",
    "add_notice",
    "clear_notices",
    "load_notices",
    "mark_all_read",
    "mark_read",
    "notices_path",
    "save_notices",
    "unread_count",
]

#: The newest this many are kept; older ones fall off the end. Two years of
#: "new episodes" is not a record anybody reads, and an unbounded file is a
#: file that eventually costs a launch.
MAX_NOTICES = 200

#: The file, under the shared app data dir so Quill Radio and QUILL Cast see
#: one list rather than two: the same reason their check settings were merged.
_FILENAME = "notifications.json"


@dataclass(slots=True)
class Notice:
    """One thing an app wanted to tell you."""

    #: Which app raised it, in words a person would recognise ("Quill Radio").
    app: str = ""
    title: str = ""
    body: str = ""
    #: ISO-8601 UTC. Stored as a string so the file stays readable and a
    #: clock-format change can never make an old file unloadable.
    created_at: str = ""
    read: bool = False
    #: What the app should open if somebody activates this row -- a show id,
    #: typically. Opaque here on purpose: this module has no opinion about what
    #: an app's ids mean.
    target: str = ""
    id: str = field(default_factory=lambda: uuid4().hex)

    @classmethod
    def create(cls, *, app: str, title: str, body: str = "", target: str = "") -> Notice:
        return cls(
            app=str(app),
            title=str(title),
            body=str(body),
            target=str(target),
            created_at=datetime.now(UTC).isoformat(timespec="seconds"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "app": self.app,
            "title": self.title,
            "body": self.body,
            "created_at": self.created_at,
            "read": self.read,
            "target": self.target,
        }

    @classmethod
    def from_dict(cls, raw: Any) -> Notice | None:
        """One stored notice, or None when the row is not usable.

        A row with no title is dropped rather than shown as a blank line: a
        list with an empty entry in it reads as a bug to somebody arrowing
        through it, and there is nothing to say about it.
        """
        if not isinstance(raw, dict):
            return None
        title = str(raw.get("title", "") or "").strip()
        if not title:
            return None
        notice = cls(
            app=str(raw.get("app", "") or ""),
            title=title,
            body=str(raw.get("body", "") or ""),
            created_at=str(raw.get("created_at", "") or ""),
            read=bool(raw.get("read", False)),
            target=str(raw.get("target", "") or ""),
        )
        stored_id = str(raw.get("id", "") or "").strip()
        if stored_id:
            notice.id = stored_id
        return notice


def notices_path(data_dir: Path) -> Path:
    return data_dir / _FILENAME


def load_notices(data_dir: Path) -> list[Notice]:
    """Every stored notice, newest first. ``[]`` when there is no file.

    Never raises: an unreadable or half-written file means an empty list, which
    is the state every install starts in. Losing this costs the history of what
    you were told, never anything you made.
    """
    try:
        raw = read_json(notices_path(data_dir), [])
    except Exception:  # noqa: BLE001 - an unreadable list is an empty one
        return []
    if not isinstance(raw, list):
        return []
    notices = [n for n in (Notice.from_dict(row) for row in raw) if n is not None]
    return notices[:MAX_NOTICES]


def save_notices(data_dir: Path, notices: list[Notice]) -> None:
    """Write the list out, newest first and bounded. Best effort."""
    try:
        payload = [n.to_dict() for n in notices[:MAX_NOTICES]]
        write_json_atomic(notices_path(data_dir), payload)
    except Exception:  # noqa: BLE001 - losing the record beats crashing an app
        return


def add_notice(data_dir: Path, notice: Notice) -> list[Notice]:
    """Record *notice* at the top and return the whole list."""
    notices = [notice, *load_notices(data_dir)][:MAX_NOTICES]
    save_notices(data_dir, notices)
    return notices


def unread_count(notices: list[Notice]) -> int:
    return sum(1 for n in notices if not n.read)


def mark_read(data_dir: Path, notice_id: str) -> list[Notice]:
    """Mark one notice read. Returns the whole list."""
    notices = load_notices(data_dir)
    for notice in notices:
        if notice.id == notice_id:
            notice.read = True
            break
    save_notices(data_dir, notices)
    return notices


def mark_all_read(data_dir: Path) -> list[Notice]:
    notices = load_notices(data_dir)
    for notice in notices:
        notice.read = True
    save_notices(data_dir, notices)
    return notices


def clear_notices(data_dir: Path) -> list[Notice]:
    """Empty the list. The only destructive thing here, and it destroys only
    the record of being told, never the episodes it was telling you about."""
    save_notices(data_dir, [])
    return []
