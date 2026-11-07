"""Explore's notifications view: unread count, Done keeps your place, Enter opens in QUILL."""

from __future__ import annotations

from typing import Any

import pytest
import wx

from quill.core.github.notification_triage import NotificationInbox, parse_notification
from quill.ui.github_explore_dialog import GitHubExploreDialog
from tests.wx_session import patch_call_after, shared_wx_app


def _note(thread_id: str, kind: str = "pulls", *, unread: bool = True) -> Any:
    return parse_notification({
        "id": thread_id,
        "unread": unread,
        "reason": "review_requested" if kind == "pulls" else "mention",
        "updated_at": "2026-11-07T10:00:00Z",
        "repository": {"full_name": "o/r"},
        "subject": {
            "title": f"Thread {thread_id}",
            "type": "PullRequest" if kind == "pulls" else "Issue",
            "url": f"https://api.github.com/repos/o/r/{kind}/{thread_id}",
        },
    })


class _Provider:
    is_authenticated = True
    token = "tok"
    _gh = None

    def __init__(self) -> None:
        self.notes = [_note("1"), _note("2"), _note("3", "issues")]
        self.done: list[str] = []
        self.unsubscribed: list[str] = []
        self.read: list[str] = []
        self.read_all: list[str] = []

    def fetch_notification_inbox(self, *, include_read, limit, if_modified_since=""):
        return NotificationInbox(tuple(self.notes), poll_interval=60, last_modified="Sat")

    def mark_notification_done(self, notification_id: str) -> None:
        self.done.append(notification_id)

    def unsubscribe_notification(self, notification_id: str) -> None:
        self.unsubscribed.append(notification_id)

    def mark_notification_read(self, notification_id: str) -> None:
        self.read.append(notification_id)

    def mark_all_notifications_read(self, last_read_at: str = "") -> bool:
        self.read_all.append(last_read_at)
        return True


class _SyncThread:
    def __init__(self, target=None, args=(), kwargs=None, daemon=None, **_kw) -> None:
        self._target, self._args, self._kwargs = target, args, kwargs or {}

    def start(self) -> None:
        self._target(*self._args, **self._kwargs)


@pytest.fixture
def explore(monkeypatch: pytest.MonkeyPatch):
    shared_wx_app()
    for module in ("github_explore_dialog", "github_explore_notifications"):
        monkeypatch.setattr(f"quill.ui.{module}.threading.Thread", _SyncThread)
    patch_call_after(monkeypatch, lambda fn, *a, **k: fn(*a, **k))
    frame = wx.Frame(None)
    provider = _Provider()
    opened: list[object] = []
    dialog = GitHubExploreDialog(
        frame, provider, initial_view="notifications", on_open_reference=opened.append
    )
    spoken: list[str] = []
    dialog._announce = spoken.append
    dialog.spoken = spoken
    dialog.opened = opened
    dialog.provider = provider
    dialog._load(None)
    yield dialog
    dialog.dialog.Destroy()
    frame.Destroy()


def test_load_says_the_unread_count_once_and_rows_carry_reasons(explore) -> None:
    assert explore.spoken == ["3 unread."]
    assert explore._list.GetString(0) == "Unread, review requested: o/r — Thread 1"
    assert explore._done_btn.IsEnabled() and explore._unsubscribe_btn.IsEnabled()


def test_done_removes_the_row_and_lands_on_the_next_one(explore) -> None:
    explore._list.SetSelection(1)
    explore._select(None)
    explore._triage_notification(False)
    assert explore.provider.done == ["2"]
    assert [row.key for row in explore._rows] == ["1", "3"]
    assert explore._list.GetSelection() == 1
    assert explore.spoken[-1] == "Marked done."


def test_delete_key_marks_done_and_unsubscribe_on_the_last_row(explore) -> None:
    explore._list.SetSelection(2)
    explore._select(None)
    event = type(
        "E",
        (),
        {"GetKeyCode": lambda self: wx.WXK_DELETE, "HasAnyModifiers": lambda self: False},
    )()
    explore._on_notification_key(event)
    assert explore.provider.done == ["3"]
    assert explore._list.GetSelection() == 1
    explore._triage_notification(True)
    assert explore.provider.unsubscribed == ["2"]
    assert explore._list.GetSelection() == 0


def test_refresh_inside_the_poll_interval_keeps_the_last_list(explore) -> None:
    explore.provider.notes = []
    explore._load(None)
    assert len(explore._rows) == 3
    assert "Try again in" in explore._status.GetLabel()


def test_enter_on_a_pull_request_marks_it_read_and_opens_review(explore, monkeypatch) -> None:
    reviewed: list[tuple[str, int]] = []

    class _Review:
        def __init__(self, _parent, _provider, repo, number, **_kw) -> None:
            reviewed.append((repo, number))

        def show(self) -> None:
            return None

    monkeypatch.setattr("quill.ui.github_pr_review_dialog.GitHubPullReviewDialog", _Review)
    explore._list.SetSelection(0)
    explore._select(None)
    explore._activate(None)
    assert explore.provider.read == ["1"]
    assert reviewed == [("o/r", 1)]
    assert explore._list.GetString(0).startswith("Read, review requested")


def test_enter_on_an_issue_opens_it_in_the_items_viewer(explore, monkeypatch) -> None:
    ended: list[int] = []
    monkeypatch.setattr(explore.dialog, "EndModal", ended.append, raising=False)
    explore._list.SetSelection(2)
    explore._select(None)
    explore._activate(None)
    assert explore.opened and explore.opened[0].kind == "issue"
    assert explore.opened[0].number == 3
    assert ended == [wx.ID_OK]


def test_mark_all_read_asks_first_then_clears_the_unread_list(explore) -> None:
    explore._confirm = lambda _message, _title: False
    explore._mark_all_read()
    assert explore.provider.read_all == []
    explore._confirm = lambda _message, _title: True
    explore._mark_all_read()
    assert len(explore.provider.read_all) == 1
    assert explore._rows == []
    assert explore.spoken[-1] == "Marked all notifications read."


def test_triage_controls_hide_outside_the_notifications_view(explore) -> None:
    explore._view.SetSelection(0)
    explore._on_view_changed(None)
    assert not explore._done_btn.IsShown()
