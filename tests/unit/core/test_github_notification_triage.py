"""Notifications triage: reasons in words, poll interval, Done, Unsubscribe, read-all."""

from __future__ import annotations

from typing import Any

import pytest

from quill.core.github import notification_triage as triage
from quill.core.github.explore import GitHubExploreClient
from quill.core.github.items_errors import GitHubItemsError
from quill.core.github.notification_triage import (
    GitHubNotificationTriageMixin,
    NotificationInbox,
    NotificationPollGate,
    fetch_notification_inbox,
    notification_row,
    parse_notification,
    reason_in_words,
    selection_after_removal,
    unread_summary,
)
from quill.core.github.notifications import GitHubNotification
from quill.core.github.rest_transport import GitHubRestError, RestResponse


def _raw(thread_id: str, *, unread: bool = True, reason: str = "mention") -> dict[str, Any]:
    return {
        "id": thread_id,
        "unread": unread,
        "reason": reason,
        "updated_at": "2026-11-07T10:00:00Z",
        "url": f"https://api.github.com/notifications/threads/{thread_id}",
        "repository": {"full_name": "o/r"},
        "subject": {
            "title": f"Thread {thread_id}",
            "type": "PullRequest",
            "url": f"https://api.github.com/repos/o/r/pulls/{thread_id}",
        },
    }


def _note(thread_id: str, *, unread: bool = True) -> GitHubNotification:
    return parse_notification(_raw(thread_id, unread=unread))


def test_reasons_are_spoken_in_words() -> None:
    assert reason_in_words("review_requested") == "review requested"
    assert reason_in_words("mention") == "you were mentioned"
    assert reason_in_words("team_mention") == "your team was mentioned"
    assert reason_in_words("brand_new_reason") == "brand new reason"


def test_row_leads_with_read_state_and_reason() -> None:
    row = notification_row(parse_notification(_raw("12", reason="review_requested")))
    assert row.label == "Unread, review requested: o/r — Thread 12"
    assert row.url == "https://github.com/o/r/pull/12"
    assert row.kind == "notification" and row.key == "12"
    assert "Why you got it: review requested" in row.detail


def test_unread_summary_is_one_sentence() -> None:
    assert unread_summary([_note(str(i)) for i in range(12)]) == "12 unread."
    assert unread_summary([_note("1"), _note("2", unread=False)]) == "1 unread of 2."
    assert unread_summary([_note("1", unread=False)]) == "No unread notifications; 1 read."
    assert unread_summary([]) == "No notifications."


@pytest.mark.parametrize(
    ("count", "removed", "expected"),
    [(3, 0, 0), (3, 1, 1), (3, 2, 1), (1, 0, -1)],
)
def test_cursor_lands_on_the_next_row(count: int, removed: int, expected: int) -> None:
    assert selection_after_removal(count, removed) == expected


def test_poll_gate_waits_per_query() -> None:
    now = [100.0]
    gate = NotificationPollGate(clock=lambda: now[0])
    assert gate.wait_seconds("unread") == 0
    gate.record("unread", 60)
    now[0] = 130.0
    assert gate.wait_seconds("unread") == 30
    assert gate.wait_seconds("all") == 0
    now[0] = 160.5
    assert gate.wait_seconds("unread") == 0


class _Pages:
    def __init__(self, pages: list[RestResponse]) -> None:
        self.pages = pages
        self.calls: list[dict[str, Any]] = []

    def __call__(self, token, method, path, *, query=None, extra_headers=None, **_kw):
        self.calls.append({
            "method": method,
            "path": path,
            "query": query,
            "headers": extra_headers,
        })
        return self.pages.pop(0)


def test_inbox_reads_pages_poll_interval_and_dedupes() -> None:
    request = _Pages([
        RestResponse(
            200,
            {"x-poll-interval": "90", "last-modified": "Sat", "link": '<x>; rel="next"'},
            [_raw("1"), _raw("2")],
        ),
        RestResponse(200, {}, [_raw("2"), _raw("3")]),
    ])
    inbox = fetch_notification_inbox("t", include_read=True, limit=10, request=request)
    assert [note.id for note in inbox.items] == ["1", "2", "3"]
    assert inbox.poll_interval == 90
    assert inbox.last_modified == "Sat"
    assert request.calls[0]["query"]["all"] == "true"
    assert request.calls[1]["query"]["page"] == "2"


def test_inbox_conditional_request_returns_not_modified() -> None:
    request = _Pages([RestResponse(304, {"x-poll-interval": "60"}, None)])
    inbox = fetch_notification_inbox(
        "t", include_read=False, limit=10, if_modified_since="Sat", request=request
    )
    assert inbox.not_modified is True
    assert request.calls[0]["headers"] == {"If-Modified-Since": "Sat"}
    assert request.calls[0]["query"]["all"] == "false"


class _Provider(GitHubNotificationTriageMixin):
    def __init__(self, token: str | None = "tok") -> None:
        self._token = token

    def _require_write_access(self, action: str) -> None:
        if not self._token:
            raise GitHubItemsError(f"To {action} you need a signed-in GitHub account.")


@pytest.fixture
def sent(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str, Any]]:
    calls: list[tuple[str, str, Any]] = []
    statuses = {"PUT": 205, "DELETE": 204}

    def fake(token, method, path, *, body=None, **_kw):
        calls.append((method, path, body))
        return RestResponse(statuses.get(method, 200), {}, None)

    monkeypatch.setattr(triage, "request_json", fake)
    return calls


def test_done_unsubscribe_and_read_all_use_the_documented_endpoints(sent) -> None:
    provider = _Provider()
    provider.mark_notification_done("42")
    provider.unsubscribe_notification("42")
    assert provider.mark_all_notifications_read("2026-11-07T10:00:00Z") is True
    assert sent == [
        ("DELETE", "/notifications/threads/42", None),
        ("DELETE", "/notifications/threads/42/subscription", None),
        ("PUT", "/notifications", {"read": True, "last_read_at": "2026-11-07T10:00:00Z"}),
    ]


def test_read_all_accepted_in_background_is_not_claimed_as_done(monkeypatch) -> None:
    monkeypatch.setattr(triage, "request_json", lambda *a, **k: RestResponse(202, {}, None))
    assert _Provider().mark_all_notifications_read() is False


def test_thread_ids_are_validated_and_signed_out_is_refused(sent) -> None:
    with pytest.raises(GitHubItemsError, match="valid GitHub thread ID"):
        _Provider().mark_notification_done("../1")
    with pytest.raises(GitHubItemsError, match="signed-in"):
        _Provider(token=None).unsubscribe_notification("1")
    assert sent == []


def test_failures_become_actionable_messages(monkeypatch) -> None:
    def refuse(*_a, **_k):
        raise GitHubRestError("Not Found", status=404)

    monkeypatch.setattr(triage, "request_json", refuse)
    with pytest.raises(
        GitHubItemsError, match="Could not mark the notification done. GitHub could not find"
    ):
        _Provider().mark_notification_done("7")


class _InboxProvider:
    is_authenticated = True
    token = "tok"
    _gh = None

    def __init__(self) -> None:
        self.inboxes = [
            NotificationInbox((_note("1"), _note("2")), poll_interval=60, last_modified="Sat"),
            NotificationInbox((), poll_interval=60, last_modified="Sat", not_modified=True),
        ]
        self.since: list[str] = []
        self.done: list[str] = []

    def fetch_notification_inbox(self, *, include_read, limit, if_modified_since=""):
        self.since.append(if_modified_since)
        return self.inboxes.pop(0)

    def mark_notification_done(self, notification_id: str) -> None:
        self.done.append(notification_id)


def test_client_reuses_rows_on_304_and_forgets_done_rows() -> None:
    provider = _InboxProvider()
    client = GitHubExploreClient(provider)  # type: ignore[arg-type]
    first = client.fetch("notifications")
    assert [row.key for row in first] == ["1", "2"]
    assert client.notification_wait_seconds(False) > 0
    assert client.notification_summary(False) == "2 unread."
    client.mark_notification_done("1")
    assert provider.done == ["1"]
    again = client.fetch("notifications")
    assert provider.since == ["", "Sat"]
    assert [row.key for row in again] == ["2"]
