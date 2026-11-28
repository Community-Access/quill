"""My GitHub in the Workbench: the loader over the existing Inbox and Notifications reads."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from quill.core.github.explore import GitHubExploreClient
from quill.core.github.my_github_prefs import MyGitHubPrefs, save
from quill.core.github.notification_triage import NotificationInbox
from quill.core.github.notifications import GitHubNotification
from quill.core.github.workbench_tree import GITHUB_TREE, START_NODE
from quill.core.workbench.filters import Query
from quill.ui.github_workbench_explore import load_explore
from quill.ui.github_workbench_window import start_ref

MY_GITHUB = GITHUB_TREE.node("my_github")


def _hit(repo: str, number: int, title: str, *, pull: bool = False) -> Any:
    kind = "pull" if pull else "issues"
    return SimpleNamespace(
        repository=SimpleNamespace(full_name=repo),
        number=number,
        title=title,
        html_url=f"https://github.com/{repo}/{kind}/{number}",
        pull_request=object() if pull else None,
        state="open",
        updated_at="2026-11-21T10:00:00Z",
    )


class _Provider:
    is_authenticated = True

    def __init__(self, *, notifications_fail: bool = False, search_fails: bool = False) -> None:
        self.notifications_fail = notifications_fail
        self.search_fails = search_fails
        self.queries: list[str] = []
        self.done: list[str] = []
        self.read: list[str] = []
        self._gh = SimpleNamespace(
            get_user=lambda: SimpleNamespace(login="me"), search_issues=self._search
        )

    def _search(self, query: str) -> list[Any]:
        self.queries.append(query)
        if self.search_fails:
            raise RuntimeError("search is rate limited")
        if "assignee:me" in query:
            return [_hit("o/web", 40, "Add search")]
        if "user-review-requested:me" in query:
            return [_hit("o/api", 7, "Retry", pull=True)]
        return []

    def fetch_notification_inbox(
        self, *, include_read: bool, limit: int, if_modified_since: str = ""
    ) -> NotificationInbox:
        if self.notifications_fail:
            raise RuntimeError("GitHub is not answering")
        note = GitHubNotification(
            "n1",
            "o/app",
            "mention",
            "Crash on save",
            "Issue",
            True,
            "2026-11-20T10:00:00Z",
            subject_url="https://api.github.com/repos/o/app/issues/5",
        )
        return NotificationInbox((note,), poll_interval=0)

    def mark_notification_done(self, note_id: str) -> None:
        self.done.append(note_id)

    def mark_notification_read(self, note_id: str) -> None:
        self.read.append(note_id)


def _load(provider: _Provider, notes: list[str]) -> list[Any]:
    client = GitHubExploreClient(provider)  # type: ignore[arg-type]
    return load_explore(client, MY_GITHUB, instance="", query=Query(), notes=notes)


@pytest.fixture(autouse=True)
def _data(quill_data_dir: Any) -> None:
    return None


def test_my_github_is_the_first_node_after_start_here() -> None:
    labels = [spec.key for spec in GITHUB_TREE if spec.parent is None][:2]
    assert labels == [START_NODE, "my_github"]


def test_it_assembles_the_queue_and_says_the_counts() -> None:
    notes: list[str] = []
    rows = _load(_Provider(), notes)
    assert {row.kind for row in rows} == {"notification", "issue", "pr"}
    assert (
        "3 need your attention: 1 unread notification, 1 assigned issue, 1 review request." in notes
    )
    assert not any("could not load" in note for note in notes)


def test_a_failing_source_is_named_and_the_rest_still_load() -> None:
    notes: list[str] = []
    rows = _load(_Provider(notifications_fail=True), notes)
    assert {row.kind for row in rows} == {"issue", "pr"}
    assert any(note.startswith("Notifications could not load") for note in notes)
    notes = []
    rows = _load(_Provider(search_fails=True), notes)
    assert [row.kind for row in rows] == ["notification"]
    assert "1 need your attention" not in " ".join(notes)  # singular verb
    assert any("1 needs your attention" in note for note in notes)


def test_an_empty_queue_says_so_in_one_sentence() -> None:
    class Quiet(_Provider):
        def _search(self, query: str) -> list[Any]:
            return []

        def fetch_notification_inbox(self, **_kw: Any) -> NotificationInbox:
            return NotificationInbox((), poll_interval=0)

    notes: list[str] = []
    assert _load(Quiet(), notes) == []
    assert "Nothing needs your attention." in notes


def test_saved_choices_filter_sort_and_group_the_rows() -> None:
    save("me", MyGitHubPrefs(kinds=("review_request",)))
    notes: list[str] = []
    rows = _load(_Provider(), notes)
    assert [row.repo for row in rows] == ["o/api"]
    assert "2 items hidden" not in " ".join(notes)
    assert any("hidden by your filter" in note for note in notes)
    save("me", MyGitHubPrefs(group="repository", sort="repository"))
    notes = []
    rows = _load(_Provider(), notes)
    assert [row.repo for row in rows] == ["o/api", "o/app", "o/web"]
    assert any(note.startswith("Grouped by repository") for note in notes)


def test_a_filter_that_hides_everything_says_how_many() -> None:
    save("me", MyGitHubPrefs(repository="nobody/nothing"))
    notes: list[str] = []
    assert _load(_Provider(), notes) == []
    assert "Nothing shows with your filters; 3 items are hidden." in notes


def test_a_second_load_says_what_changed_once() -> None:
    provider = _Provider()
    client = GitHubExploreClient(provider)  # type: ignore[arg-type]
    first: list[str] = []
    load_explore(client, MY_GITHUB, instance="", query=Query(), notes=first)
    assert not any("since the last refresh" in note for note in first)
    provider.search_fails = False
    second: list[str] = []
    load_explore(client, MY_GITHUB, instance="", query=Query(), notes=second)
    assert "No changes since the last refresh." in second


def test_rows_keep_the_notification_identity_so_read_and_done_use_the_existing_actions() -> None:
    rows = _load(_Provider(), [])
    note = next(row for row in rows if row.kind == "notification")
    assert note.key == "n1"
    provider = _Provider()
    client = GitHubExploreClient(provider)  # type: ignore[arg-type]
    client.mark_notification_done(note.key)
    client.mark_notification_seen(note.key)
    assert provider.done == ["n1"]
    assert provider.read == ["n1"]


def test_the_window_opens_on_my_github_when_signed_in() -> None:
    assert start_ref("", signed_in=True).key == "my_github"  # type: ignore[union-attr]
    assert start_ref("", signed_in=False).key == START_NODE  # type: ignore[union-attr]
