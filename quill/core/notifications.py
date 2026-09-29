"""Things the apps have told you, kept where you can go back to them.

QUILL has written to this list for a long time -- one line, a category, a
timestamp -- and 3.1.0 gave it a second job: the record behind a desktop
notification.

That matters because a toast is a good way to be told something and a poor way
to *remember* it. It appears over whatever you were reading, it leaves on its
own schedule, and if a screen reader was mid-sentence when it arrived it may
never have been read at all. So the toast is not the record; this is, and the
notification and the sound are the optional louder half on top. It is what
makes the **quiet** alert mode a real choice rather than a euphemism for "off",
and what makes a missed notification recoverable.

### One store, two shapes

Every existing caller keeps working unchanged: :func:`add_notification` takes a
message and a category, and :func:`load_notifications` hands the list back.
:func:`add_notice` is the richer door -- who said it, a title, a body, whether
it has been read, and an optional *target* the app knows how to open -- and the
extra fields default so an entry written by either route reads correctly
through both. A file written by an older build loads with the new fields empty
rather than failing.

The list is **bounded** (:data:`MAX_NOTICES`) and oldest-first on disk, which is
the order it has always been stored in; the reader shows it newest-first
because that is the order it is asked about.

wx-free, strict-typed, pure I/O through :mod:`quill.core.storage`.
"""

from __future__ import annotations

import dataclasses
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from quill.core.paths import app_data_dir
from quill.core.storage import read_json, write_json_atomic

__all__ = [
    "MAX_NOTICES",
    "Notification",
    "add_notice",
    "add_notification",
    "clear_notifications",
    "load_notifications",
    "mark_all_read",
    "mark_read",
    "newest_first",
    "notifications_path",
    "save_notifications",
    "unread_count",
]

#: The newest this many are kept; older ones fall off. Two years of "new
#: episodes" is not a record anybody reads, and an unbounded file eventually
#: costs a launch.
MAX_NOTICES = 200


@dataclass(frozen=True, slots=True)
class Notification:
    """One thing an app wanted to tell you.

    Frozen, as it has always been. Marking one read rebuilds it through
    :func:`dataclasses.replace` rather than mutating in place, which keeps the
    old contract (and anything relying on it) intact.
    """

    timestamp: str
    category: str
    message: str
    #: Added in 3.1.0, all optional so an older file still loads and an older
    #: caller still writes a valid entry.
    app: str = ""
    title: str = ""
    body: str = ""
    read: bool = False
    #: What the app should open if somebody activates this row -- a show id,
    #: typically. Opaque here: this module has no opinion about an app's ids.
    target: str = ""
    id: str = field(default_factory=lambda: uuid4().hex)

    @classmethod
    def create(cls, message: str, category: str = "info") -> Notification:
        return cls(
            timestamp=datetime.now(UTC).isoformat(),
            category=category,
            message=message.strip(),
        )

    @classmethod
    def notice(
        cls, *, app: str, title: str, body: str = "", target: str = "", category: str = "info"
    ) -> Notification:
        """The richer shape: who said it, what it said, and a way back.

        ``message`` is filled in as well, so an entry written this way still
        reads correctly to every caller that only knows about messages.
        """
        title = str(title).strip()
        body = str(body).strip()
        return cls(
            timestamp=datetime.now(UTC).isoformat(),
            category=category,
            message=f"{title} -- {body}" if body else title,
            app=str(app).strip(),
            title=title,
            body=body,
            target=str(target).strip(),
        )

    @property
    def is_unread(self) -> bool:
        return not self.read


def notifications_path() -> Path:
    return app_data_dir() / "notifications.json"


def load_notifications() -> list[Notification]:
    """Every stored entry, oldest first. ``[]`` when there is none.

    A row with no message *and* no title is dropped rather than shown as a
    blank line: an empty entry reads as a bug to somebody arrowing through it,
    and there is nothing to say about it.
    """
    raw = read_json(notifications_path(), default=[])
    if not isinstance(raw, list):
        return []
    entries: list[Notification] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        timestamp = str(item.get("timestamp", "")).strip()
        category = str(item.get("category", "info")).strip() or "info"
        message = str(item.get("message", "")).strip()
        title = str(item.get("title", "")).strip()
        if not timestamp or not (message or title):
            continue
        entries.append(
            Notification(
                timestamp=timestamp,
                category=category,
                message=message or title,
                app=str(item.get("app", "")).strip(),
                title=title,
                body=str(item.get("body", "")).strip(),
                read=bool(item.get("read", False)),
                target=str(item.get("target", "")).strip(),
                id=str(item.get("id", "")).strip() or uuid4().hex,
            )
        )
    return entries


def save_notifications(entries: list[Notification], limit: int = MAX_NOTICES) -> None:
    trimmed = entries[-limit:]
    write_json_atomic(notifications_path(), [asdict(entry) for entry in trimmed])


def add_notification(
    message: str, category: str = "info", limit: int = MAX_NOTICES
) -> list[Notification]:
    entries = load_notifications()
    entries.append(Notification.create(message, category))
    save_notifications(entries, limit=limit)
    return entries[-limit:]


def add_notice(
    *, app: str, title: str, body: str = "", target: str = "", category: str = "info"
) -> list[Notification]:
    """Record the richer shape. Returns the whole list, oldest first."""
    entries = load_notifications()
    entries.append(
        Notification.notice(app=app, title=title, body=body, target=target, category=category)
    )
    save_notifications(entries)
    return entries[-MAX_NOTICES:]


def clear_notifications() -> None:
    """Empty the list. It removes the record of being told, never the thing it
    was telling you about."""
    write_json_atomic(notifications_path(), [])


def newest_first(entries: list[Notification]) -> list[Notification]:
    """The stored order reversed, which is how a reader asks about it."""
    return list(reversed(entries))


def unread_count(entries: list[Notification]) -> int:
    return sum(1 for entry in entries if not entry.read)


def mark_read(notice_id: str) -> list[Notification]:
    """Mark one entry read. Returns the whole list, oldest first."""
    entries = load_notifications()
    updated = [
        dataclasses.replace(entry, read=True) if entry.id == notice_id else entry
        for entry in entries
    ]
    save_notifications(updated)
    return updated


def mark_all_read() -> list[Notification]:
    entries = [dataclasses.replace(entry, read=True) for entry in load_notifications()]
    save_notifications(entries)
    return entries
