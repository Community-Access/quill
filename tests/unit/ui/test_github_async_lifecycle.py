"""Stale and post-close GitHub responses must not update native dialogs."""

from __future__ import annotations

from quill.core.github.explore import ExploreRow
from quill.core.github.fetch_results import GitHubFetchResult
from quill.ui import github_explore_dialog, github_pr_review_dialog, github_workflow_jobs_dialog


class _Control:
    def __init__(self) -> None:
        self.value = None

    def Set(self, value: object) -> None:
        self.value = value

    def SetValue(self, value: object) -> None:
        self.value = value

    def SetLabel(self, value: str) -> None:
        self.value = value

    def SetSelection(self, value: int) -> None:
        self.value = value

    def Enable(self, value: bool) -> None:
        self.value = value


def test_explore_ignores_an_older_load_result(monkeypatch) -> None:
    dialog = object.__new__(github_explore_dialog.GitHubExploreDialog)
    dialog._load_token = 2
    dialog.dialog = object()
    monkeypatch.setattr(github_explore_dialog, "dialog_alive", lambda _dialog: True)

    dialog._loaded(1, [], "")

    assert not hasattr(dialog, "_rows")


def test_explore_ignores_a_response_after_close(monkeypatch) -> None:
    dialog = object.__new__(github_explore_dialog.GitHubExploreDialog)
    dialog._load_token = 2
    dialog.dialog = object()
    monkeypatch.setattr(github_explore_dialog, "dialog_alive", lambda _dialog: False)

    dialog._loaded(2, [], "")

    assert not hasattr(dialog, "_rows")


def test_explore_announces_partial_results_and_keeps_the_reason(monkeypatch) -> None:
    dialog = object.__new__(github_explore_dialog.GitHubExploreDialog)
    dialog._load_token = 1
    dialog.dialog = object()
    dialog._view_key = lambda: "search"
    dialog._list = _Control()
    dialog._detail = _Control()
    dialog._open_btn = _Control()
    dialog._use_btn = _Control()
    dialog._status = _Control()
    announcements: list[str] = []
    dialog._announce = announcements.append
    dialog._select = lambda _event: None
    monkeypatch.setattr(github_explore_dialog, "dialog_alive", lambda _dialog: True)

    result = GitHubFetchResult(
        (ExploreRow("Issue", "Issue detail", kind="issue"),),
        complete=False,
        warning="Search results stopped after a later-page failure.",
    )
    dialog._loaded(1, result, "")

    assert "incomplete" in dialog._status.value
    assert "later-page failure" in dialog._status.value
    assert "incomplete data" in announcements[-1]


def test_pr_review_ignores_a_response_after_close(monkeypatch) -> None:
    dialog = object.__new__(github_pr_review_dialog.GitHubPullReviewDialog)
    dialog.dialog = object()
    monkeypatch.setattr(github_pr_review_dialog, "dialog_alive", lambda _dialog: False)

    dialog._refresh_ready(None, (), None)  # type: ignore[arg-type]

    assert not hasattr(dialog, "_state")


def test_workflow_jobs_ignores_older_list_and_log_results(monkeypatch) -> None:
    dialog = object.__new__(github_workflow_jobs_dialog.WorkflowJobsDialog)
    dialog._jobs_token = 3
    dialog._log_token = 4
    dialog.dialog = object()
    monkeypatch.setattr(github_workflow_jobs_dialog, "dialog_alive", lambda _dialog: True)

    dialog._loaded(2, [], "")
    dialog._log_loaded(3, "stale log", "")

    assert not hasattr(dialog, "_jobs")
    assert not hasattr(dialog, "_detail")


def test_workflow_jobs_ignores_responses_after_close(monkeypatch) -> None:
    dialog = object.__new__(github_workflow_jobs_dialog.WorkflowJobsDialog)
    dialog._jobs_token = 3
    dialog._log_token = 4
    dialog.dialog = object()
    monkeypatch.setattr(github_workflow_jobs_dialog, "dialog_alive", lambda _dialog: False)

    dialog._loaded(3, [], "")
    dialog._log_loaded(4, "late log", "")

    assert not hasattr(dialog, "_jobs")
    assert not hasattr(dialog, "_detail")
