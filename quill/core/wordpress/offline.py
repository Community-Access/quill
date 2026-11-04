"""Sends waiting for a site to come back (wordpress.md 5.10, 15 item 9 "Working offline").

When a site cannot be reached, a send is not lost and not retried blindly: the
working copy is already on this computer, so all the queue keeps is *which*
copy, on *which* site, and whether it was a publish. Retrying reads the copy
afresh, so what goes out is what the person last saved, and every retry runs
the same conflict check as a send from the menu -- a publish is never re-sent
over somebody else's newer change.

No wx, no network: :func:`is_unreachable` reads an exception, and
:class:`OfflineQueue` is one JSON file beside the working copies.
"""

from __future__ import annotations

import ssl
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.error import URLError

from quill.core.storage import read_json, write_json_atomic
from quill.core.wordpress.api import WordPressApiError
from quill.core.wordpress.local import now_stamp

QUEUE_FILE = "send-queue.json"


def is_unreachable(exc: BaseException) -> bool:
    """True when a request failed on the way, not because the site refused it.

    A time-out, a lost connection or a site that could not be found. A refused
    certificate is *not* one: waiting will not fix it, and QUILL must not keep
    knocking on a site it does not trust.
    """
    if not isinstance(exc, WordPressApiError) or exc.status:
        return False
    cause = exc.__cause__
    if not isinstance(cause, (URLError, TimeoutError, OSError)):
        return False
    reason = getattr(cause, "reason", cause)
    if isinstance(cause, ssl.SSLError) or isinstance(reason, ssl.SSLError):
        return False
    return "certificate" not in str(reason).lower()


@dataclass(frozen=True)
class QueuedSend:
    key: str  # the working copy's key (LocalStore)
    site_id: str
    title: str
    publish: bool
    queued_at: str
    #: When the send that failed began, for the "did it land after all" check.
    since_gmt: str = ""


class OfflineQueue:
    """``<data>/wordpress/send-queue.json``: oldest first, one entry per document."""

    def __init__(self, root: Path) -> None:
        self.path = Path(root) / QUEUE_FILE

    def entries(self) -> list[QueuedSend]:
        raw = read_json(self.path, default=[])
        if not isinstance(raw, list):
            return []
        known = set(QueuedSend.__dataclass_fields__)
        return [
            QueuedSend(**{k: v for k, v in r.items() if k in known})
            for r in raw
            if isinstance(r, dict) and "key" in r and "site_id" in r
        ]

    def add(
        self, *, key: str, site_id: str, title: str, publish: bool, since_gmt: str = ""
    ) -> QueuedSend:
        """Queue a document; queued twice, it keeps its place and a publish wins."""
        entries = self.entries()
        old = next((e for e in entries if e.key == key), None)
        entry = QueuedSend(
            key=key,
            site_id=site_id,
            title=title,
            publish=publish or bool(old and old.publish),
            queued_at=old.queued_at if old else now_stamp(),
            since_gmt=(old.since_gmt if old and old.since_gmt else since_gmt),
        )
        if old is None:
            entries.append(entry)
        else:
            entries[entries.index(old)] = entry
        self._write(entries)
        return entry

    def drop(self, key: str) -> None:
        entries = self.entries()
        kept = [e for e in entries if e.key != key]
        if len(kept) != len(entries):
            self._write(kept)

    def _write(self, entries: list[QueuedSend]) -> None:
        write_json_atomic(self.path, [asdict(e) for e in entries])


def back_online_sentence(site_name: str, drafts: int, published: int) -> str:
    """``Back online: 2 drafts sent to Community Radio.``"""
    parts: list[str] = []
    if drafts:
        parts.append(f"{drafts} draft{'s' if drafts != 1 else ''} sent")
    if published:
        parts.append(f"{published} {'item' if published == 1 else 'items'} published")
    preposition = "to" if drafts else "on"
    return "Back online: " + " and ".join(parts) + f" {preposition} {site_name}."
