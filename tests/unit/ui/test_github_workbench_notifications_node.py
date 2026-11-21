"""The Workbench's Notifications and Inbox nodes: Include read, Snooze and GitHub's poll interval.

Each of the three was stored or offered and then ignored by the loader: the
option never reached the request, a snooze was saved and the row stayed, and
Refresh read the inbox again however soon GitHub had asked apps to wait.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any

import pytest

from quill.core.github.attention_queue import GitHubAttentionQueue
from quill.core.github.explore import GitHubExploreClient
from quill.core.github.notification_triage import NotificationInbox
from quill.core.github.notifications import GitHubNotification
from quill.core.github.workbench_prefs import WorkbenchPrefs, save_prefs
from quill.core.github.workbench_tree import GITHUB_TREE
from quill.core.workbench.filters import Query
from quill.ui.github_workbench_explore import load_explore

NOTIFICATIONS = GITHUB_TREE.node("notifications")


def _note(number: int, *, unread: bool = True) -> GitHubNotification:
    return GitHubNotification(
        str(number),
        "o/r",
        "mention",
        f"Thing {number}",
        "Issue",
        unread,
        "2026-11-20T10:00:00Z",
        subject_url=f"https://github.com/o/r/issues/{number}",
    )


class _Provider:
    is_authenticated = True

    def __init__(self) -> None:
        self.reads: list[bool] = []
        self._gh = SimpleNamespace(get_user=lambda: SimpleNamespace(login="me"))

    def fetch_notification_inbox(
        self, *, include_read: bool, limit: int, if_modified_since: str = ""
    ) -> NotificationInbox:
        self.reads.append(include_read)
        notes = (_note(1), _note(2, unread=False)) if include_read else (_note(1),)
        return NotificationInbox(notes, poll_interval=60)


@pytest.fixture
def client(quill_data_dir: Any) -> tuple[GitHubExploreClient, _Provider]:
    provider = _Provider()
    return GitHubExploreClient(provider), provider  # type: ignore[arg-type]


def test_include_read_notifications_reaches_the_request(client: Any) -> None:
    explore, provider = client
    assert len(load_explore(explore, NOTIFICATIONS, instance="", query=Query())) == 1
    save_prefs(WorkbenchPrefs(include_read_notifications=True))
    rows = load_explore(explore, NOTIFICATIONS, instance="", query=Query())
    assert provider.reads == [False, True]
    assert [row.key for row in rows] == ["1", "2"]


def test_a_snoozed_notification_leaves_the_list_until_include_read_shows_it(client: Any) -> None:
    explore, _provider = client
    queue = GitHubAttentionQueue.load("me")
    queue.snooze("https://github.com/o/r/issues/1", datetime.now(UTC) + timedelta(days=1))
    notes: list[str] = []
    assert load_explore(explore, NOTIFICATIONS, instance="", query=Query(), notes=notes) == []
    assert notes == [
        "1 notification snoozed on this computer is hidden; turn on Include read "
        "notifications in Workbench Options to show it."
    ]
    save_prefs(WorkbenchPrefs(include_read_notifications=True))
    rows = load_explore(explore, NOTIFICATIONS, instance="", query=Query())
    assert rows[0].key == "1" and rows[0].detail.startswith("Snoozed here until ")


def test_refresh_inside_github_s_poll_interval_shows_the_last_list(client: Any) -> None:
    explore, provider = client
    load_explore(explore, NOTIFICATIONS, instance="", query=Query())
    notes: list[str] = []
    rows = load_explore(explore, NOTIFICATIONS, instance="", query=Query(), notes=notes)
    assert provider.reads == [False]  # the second Refresh did not ask GitHub again
    assert [row.key for row in rows] == ["1"]
    assert len(notes) == 1 and notes[0].startswith(
        "GitHub asks apps to wait between checks; this is the list from the last check. "
        "Try again in "
    )
