"""The notifications half of :class:`~quill.core.github.explore.GitHubExploreClient`.

Kept apart from ``explore.py`` (GATE-11). The client remembers the last inbox
it read for each query so a conditional request answered 304 can show the same
rows again, and so a row marked done here leaves that memory too -- otherwise
the next 304 would bring it back.
"""

from __future__ import annotations

import threading
from dataclasses import replace
from datetime import UTC, datetime
from typing import Any

from quill.core.github.explore_models import ExploreRow, GitHubExploreError
from quill.core.github.notification_triage import (
    NotificationPollGate,
    notification_row,
    unread_summary,
)
from quill.core.github.notifications import GitHubNotification


def _query_key(include_read: bool) -> str:
    return "all" if include_read else "unread"


class ExploreNotificationsMixin:
    """Inbox reads that honour the poll interval, plus Done, Unsubscribe and read-all."""

    _provider: Any

    def _notification_init(self) -> None:
        self.notification_poll = NotificationPollGate()
        self._notification_lock = threading.Lock()
        self._inbox: dict[str, list[GitHubNotification]] = {}
        self._last_modified: dict[str, str] = {}
        self.notifications_loaded_at = ""

    def notification_wait_seconds(self, include_read: bool) -> int:
        """Seconds until GitHub's poll interval allows another check of this query."""
        return self.notification_poll.wait_seconds(_query_key(include_read))

    def _fetch_notification_rows(self, *, include_read: bool, limit: int) -> list[ExploreRow]:
        key = _query_key(include_read)
        with self._notification_lock:
            since = self._last_modified.get(key, "") if key in self._inbox else ""
        inbox = self._provider.fetch_notification_inbox(
            include_read=include_read, limit=limit, if_modified_since=since
        )
        self.notification_poll.record(key, inbox.poll_interval)
        with self._notification_lock:
            if not inbox.not_modified:
                self._inbox[key] = list(inbox.items)
                self._last_modified[key] = inbox.last_modified
            notes = list(self._inbox.get(key, []))
        self.notifications_loaded_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        return [notification_row(note) for note in notes]

    def cached_notification_rows(self, include_read: bool) -> list[ExploreRow]:
        """The last inbox read for this query, with local Done and read changes applied."""
        with self._notification_lock:
            notes = list(self._inbox.get(_query_key(include_read), []))
        return [notification_row(note) for note in notes]

    def notification(self, include_read: bool, notification_id: str) -> GitHubNotification | None:
        with self._notification_lock:
            return next(
                (
                    n
                    for n in self._inbox.get(_query_key(include_read), [])
                    if n.id == notification_id
                ),
                None,
            )

    def notification_summary(self, include_read: bool) -> str:
        with self._notification_lock:
            return unread_summary(self._inbox.get(_query_key(include_read), []))

    def _forget(self, notification_id: str) -> None:
        with self._notification_lock:
            for key, notes in self._inbox.items():
                self._inbox[key] = [note for note in notes if note.id != notification_id]

    def _mark_cached_read(self, notification_id: str | None) -> None:
        with self._notification_lock:
            for key, notes in self._inbox.items():
                self._inbox[key] = [
                    replace(note, unread=False)
                    if notification_id is None or note.id == notification_id
                    else note
                    for note in notes
                ]
                if notification_id is None and key == "unread":
                    self._inbox[key] = []

    def _triage(self, call: Any) -> Any:
        if not self._provider.is_authenticated:
            raise GitHubExploreError("Sign in to GitHub to triage notifications.")
        try:
            return call()
        except Exception as exc:  # noqa: BLE001 - provider errors carry the next step
            raise GitHubExploreError(str(exc.args[0]) if exc.args else str(exc)) from exc

    def mark_notification_done(self, notification_id: str) -> None:
        self._triage(lambda: self._provider.mark_notification_done(notification_id))
        self._forget(notification_id)

    def unsubscribe_notification(self, notification_id: str) -> None:
        self._triage(lambda: self._provider.unsubscribe_notification(notification_id))
        self._forget(notification_id)

    def mark_notification_seen(self, notification_id: str) -> None:
        """Mark one thread read (Enter on a row) and keep the cached copy in step."""
        self._triage(lambda: self._provider.mark_notification_read(notification_id))
        self._mark_cached_read(notification_id)

    def mark_all_notifications_read(self) -> bool:
        """Read everything up to the moment the list was loaded; True when GitHub finished."""
        finished = bool(
            self._triage(
                lambda: self._provider.mark_all_notifications_read(self.notifications_loaded_at),
            )
        )
        self._mark_cached_read(None)
        return finished


__all__ = ["ExploreNotificationsMixin"]
