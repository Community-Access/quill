"""Triage the GitHub notifications inbox: read it, say why, mark it done.

The inbox read goes through :func:`~quill.core.github.rest_transport.request_json`
rather than PyGithub because GitHub's ``X-Poll-Interval`` and ``Last-Modified``
headers are part of the contract -- a client is asked not to check more often
than the interval says, and a conditional request that comes back 304 costs no
rate limit. PyGithub drops both on the floor.

Everything here is wx-free: :class:`NotificationPollGate` decides whether a
refresh may go out yet, :func:`reason_in_words` turns GitHub's reason codes into
words a listener understands, and :func:`notification_row` builds the Explore
row so the dialog only has to show it.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import Any, Protocol

from quill.core.github.explore_models import ExploreRow
from quill.core.github.items_errors import GitHubItemsError
from quill.core.github.notifications import GitHubNotification, _subject_web_url
from quill.core.github.rest_transport import (
    GitHubRestError,
    RestResponse,
    request_json,
    rest_failure_message,
)

#: GitHub's notification reason codes, as a sentence fragment a person says.
REASON_WORDS: dict[str, str] = {
    "approval_requested": "your approval was requested for a deployment",
    "assign": "you were assigned",
    "author": "you opened it",
    "ci_activity": "a workflow run you started finished",
    "comment": "you commented",
    "invitation": "you were invited to the repository",
    "manual": "you subscribed",
    "member_feature_requested": "a member requested a feature",
    "mention": "you were mentioned",
    "review_requested": "review requested",
    "security_advisory_credit": "you were credited on a security advisory",
    "security_alert": "security alert",
    "state_change": "you changed its state",
    "subscribed": "you are watching the repository",
    "team_mention": "your team was mentioned",
}

_SUBJECT_WORDS: dict[str, str] = {
    "Issue": "issue",
    "PullRequest": "pull request",
    "Release": "release",
    "Discussion": "discussion",
    "Commit": "commit",
    "CheckSuite": "workflow run",
    "RepositoryVulnerabilityAlert": "security alert",
    "RepositoryDependabotAlertsThread": "Dependabot alerts",
    "RepositoryInvitation": "repository invitation",
}

DEFAULT_POLL_INTERVAL = 60
_MAX_PAGES = 5


def reason_in_words(reason: str) -> str:
    """The reason a notification arrived, in words (unknown codes are de-underscored)."""
    return REASON_WORDS.get(reason, reason.replace("_", " ") or "no reason given")


def subject_in_words(subject_type: str) -> str:
    return _SUBJECT_WORDS.get(subject_type, subject_type or "item")


def _text(value: object) -> str:
    return str(value) if value is not None else ""


def parse_notification(raw: dict[str, Any]) -> GitHubNotification:
    """Map one REST ``/notifications`` thread onto the shared model."""
    raw_subject = raw.get("subject")
    raw_repository = raw.get("repository")
    subject: dict[str, Any] = raw_subject if isinstance(raw_subject, dict) else {}
    repository: dict[str, Any] = raw_repository if isinstance(raw_repository, dict) else {}
    return GitHubNotification(
        id=_text(raw.get("id")),
        repository=_text(repository.get("full_name")),
        reason=_text(raw.get("reason")),
        subject_title=_text(subject.get("title")),
        subject_type=_text(subject.get("type")),
        unread=bool(raw.get("unread")),
        updated_at=_text(raw.get("updated_at")),
        url=_text(raw.get("url")),
        subject_url=_subject_web_url(subject.get("url")),
    )


def notification_row(note: GitHubNotification) -> ExploreRow:
    """The Explore row: read state and reason first, because that is what triage needs."""
    state = "Unread" if note.unread else "Read"
    reason = reason_in_words(note.reason)
    label = f"{state}, {reason}: {note.repository} — {note.subject_title}"
    detail = (
        f"{subject_in_words(note.subject_type).capitalize()}: {note.subject_title}\n"
        f"Repository: {note.repository}\nWhy you got it: {reason}\n"
        f"{state}. Updated: {note.updated_at}\n{note.subject_url}"
    ).rstrip()
    return ExploreRow(
        label,
        detail,
        note.subject_url,
        note.repository,
        "notification",
        note.id,
        note.updated_at,
        note.subject_title,
    )


def unread_summary(notes: list[GitHubNotification] | tuple[GitHubNotification, ...]) -> str:
    """The one sentence said after a load: "12 unread", or "12 unread of 40"."""
    unread = sum(1 for note in notes if note.unread)
    if not notes:
        return "No notifications."
    if unread == len(notes):
        return f"{unread} unread."
    if unread == 0:
        return f"No unread notifications; {len(notes)} read."
    return f"{unread} unread of {len(notes)}."


def selection_after_removal(count_before: int, removed_index: int) -> int:
    """Where the cursor goes once a row leaves: the next row, else the new last row."""
    remaining = count_before - 1
    if remaining <= 0:
        return -1
    return min(max(removed_index, 0), remaining - 1)


@dataclass(frozen=True, slots=True)
class NotificationInbox:
    """One inbox read: the threads, GitHub's poll interval, and caching evidence."""

    items: tuple[GitHubNotification, ...]
    poll_interval: int = DEFAULT_POLL_INTERVAL
    last_modified: str = ""
    not_modified: bool = False
    more: bool = False


class NotificationPollGate:
    """Honour ``X-Poll-Interval``: no second inbox read until the interval passes.

    Keyed by the query (unread only, or including read) so changing the toggle
    is a new question rather than a repeat of the last one.
    """

    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._lock = threading.Lock()
        self._next_allowed: dict[str, float] = {}

    def record(self, key: str, interval_seconds: int) -> None:
        with self._lock:
            self._next_allowed[key] = self._clock() + max(0, interval_seconds)

    def wait_seconds(self, key: str) -> int:
        with self._lock:
            remaining = self._next_allowed.get(key, 0.0) - self._clock()
        return max(0, int(remaining + 0.999))


def _poll_interval(response: RestResponse) -> int:
    try:
        return max(1, int(response.header("X-Poll-Interval")))
    except ValueError:
        return DEFAULT_POLL_INTERVAL


def _thread_path(notification_id: str) -> str:
    if not notification_id.isdecimal():
        raise GitHubItemsError("This notification has no valid GitHub thread ID.")
    return f"/notifications/threads/{notification_id}"


def fetch_notification_inbox(
    token: str,
    *,
    include_read: bool,
    limit: int,
    if_modified_since: str = "",
    request: Callable[..., RestResponse] = request_json,
) -> NotificationInbox:
    """Read up to *limit* threads, newest first, honouring a conditional request."""
    per_page = max(1, min(limit, 50))
    seen: set[str] = set()
    items: list[GitHubNotification] = []
    poll = DEFAULT_POLL_INTERVAL
    last_modified = ""
    more = False
    for page in range(1, _MAX_PAGES + 1):
        headers = (
            {"If-Modified-Since": if_modified_since} if page == 1 and if_modified_since else {}
        )
        response = request(
            token,
            "GET",
            "/notifications",
            query={
                "all": "true" if include_read else "false",
                "per_page": str(per_page),
                "page": str(page),
            },
            extra_headers=headers,
        )
        if page == 1:
            poll = _poll_interval(response)
            last_modified = response.header("Last-Modified")
            if response.status == 304:
                return NotificationInbox((), poll, if_modified_since, not_modified=True)
        rows = response.data if isinstance(response.data, list) else []
        for raw in rows:
            if not isinstance(raw, dict):
                continue
            note = parse_notification(raw)
            if note.id and note.id not in seen:
                seen.add(note.id)
                items.append(note)
        more = 'rel="next"' in response.header("Link")
        if not more or len(items) >= limit:
            break
    if len(items) > limit:
        items, more = items[:limit], True
    return NotificationInbox(tuple(items), poll, last_modified, more=more)


class _TriageAccess(Protocol):
    _token: str | None

    def _require_write_access(self, action: str) -> None: ...


def _rest(action: str, call: Callable[[], RestResponse]) -> RestResponse:
    try:
        return call()
    except GitHubRestError as exc:
        raise GitHubItemsError(rest_failure_message(action, exc)) from exc


class GitHubNotificationTriageMixin:
    """Inbox read, Done, Unsubscribe and Mark All Read for ``GitHubItemsProvider``."""

    def fetch_notification_inbox(
        self: _TriageAccess,
        *,
        include_read: bool = False,
        limit: int = 50,
        if_modified_since: str = "",
    ) -> NotificationInbox:
        self._require_write_access("read notifications")
        token = self._token or ""
        try:
            return fetch_notification_inbox(
                token, include_read=include_read, limit=limit, if_modified_since=if_modified_since
            )
        except GitHubRestError as exc:
            raise GitHubItemsError(rest_failure_message("load your notifications", exc)) from exc

    def mark_notification_done(self: _TriageAccess, notification_id: str) -> None:
        """Done: off the inbox until something new happens on the thread."""
        self._require_write_access("mark a notification done")
        path = _thread_path(notification_id)
        _rest("mark the notification done", lambda: request_json(self._token, "DELETE", path))

    def unsubscribe_notification(self: _TriageAccess, notification_id: str) -> None:
        """Stop notifications for the thread until you comment or are mentioned."""
        self._require_write_access("unsubscribe from a notification")
        path = _thread_path(notification_id) + "/subscription"
        _rest("unsubscribe from the thread", lambda: request_json(self._token, "DELETE", path))

    def mark_all_notifications_read(self: _TriageAccess, last_read_at: str = "") -> bool:
        """Mark everything up to *last_read_at* read; True when GitHub finished it now.

        GitHub answers 205 when it is done and 202 when it accepted the work and
        will finish it in the background; the caller must say which.
        """
        self._require_write_access("mark all notifications read")
        body: dict[str, object] = {"read": True}
        if last_read_at:
            body["last_read_at"] = last_read_at
        response = _rest(
            "mark all notifications read",
            lambda: request_json(self._token, "PUT", "/notifications", body=body),
        )
        return response.status != 202


def mark_read_locally(note: GitHubNotification) -> GitHubNotification:
    return replace(note, unread=False)


__all__ = [
    "DEFAULT_POLL_INTERVAL",
    "REASON_WORDS",
    "GitHubNotificationTriageMixin",
    "NotificationInbox",
    "NotificationPollGate",
    "fetch_notification_inbox",
    "mark_read_locally",
    "notification_row",
    "parse_notification",
    "reason_in_words",
    "selection_after_removal",
    "subject_in_words",
    "unread_summary",
]
