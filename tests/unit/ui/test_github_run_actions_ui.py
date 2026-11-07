"""Workflow run actions in GitHub Items, What Failed, and pending deployments."""

from __future__ import annotations

from typing import Any

import pytest
import wx

from quill.core.github.items_provider import GitHubItemsError, GitHubWorkflowRun
from quill.core.github.run_actions import CheckOutcome, CombinedCheckStatus, PendingDeployment
from quill.ui.github_items_dialog import GitHubItemsDialog
from quill.ui.github_items_view import VIEW_RUNS
from tests.wx_session import patch_call_after, shared_wx_app


class _SyncThread:
    def __init__(self, target=None, args=(), kwargs=None, daemon=None, **_kw) -> None:
        self._target, self._args, self._kwargs = target, args, kwargs or {}

    def start(self) -> None:
        self._target(*self._args, **self._kwargs)


class _Provider:
    is_authenticated = True
    token = "tok"

    def __init__(self) -> None:
        self.calls: list[tuple[Any, ...]] = []
        self.fail: Exception | None = None

    def _record(self, *call: Any) -> None:
        if self.fail is not None:
            raise self.fail
        self.calls.append(call)

    def rerun_failed_jobs(self, repo: str, run_id: int) -> None:
        self._record("rerun_failed", repo, run_id)

    def cancel_workflow_run(self, repo: str, run_id: int) -> None:
        self._record("cancel", repo, run_id)

    def delete_workflow_run(self, repo: str, run_id: int) -> None:
        self._record("delete", repo, run_id)

    def approve_fork_run(self, repo: str, run_id: int) -> None:
        self._record("approve", repo, run_id)

    def fetch_combined_check_status(self, repo: str, sha: str, *, required=()):
        self._record("status", repo, sha)
        return CombinedCheckStatus(sha, (CheckOutcome("build", "pass"), CheckOutcome("t", "fail")))

    def fetch_pending_deployments(self, repo: str, run_id: int):
        return (PendingDeployment(7, "production", True, ("jeff",)),)

    def review_pending_deployments(self, repo, run_id, ids, *, approve, comment):
        self._record("review", ids, approve, comment)
        return ("production",)


RUN = GitHubWorkflowRun(
    name="CI",
    status="completed",
    conclusion="failure",
    branch="main",
    run_number=12,
    id=900,
    head_sha="abcdef1234",
)


@pytest.fixture
def items(monkeypatch: pytest.MonkeyPatch):
    shared_wx_app()
    monkeypatch.setattr("quill.ui.github_items_dialog_run_actions.threading.Thread", _SyncThread)
    patch_call_after(monkeypatch, lambda fn, *a, **k: fn(*a, **k))
    frame = wx.Frame(None)
    dialog = GitHubItemsDialog(frame, _Provider(), initial_repo="o/r")
    dialog._repo = "o/r"
    dialog._view = VIEW_RUNS
    dialog._rows = [RUN]
    dialog._selected_indices = lambda: [0]
    dialog.statuses = []
    dialog.questions = []
    dialog._set_status = lambda message, **_kw: dialog.statuses.append(message)
    dialog._announce = lambda message: dialog.statuses.append(message)
    dialog._reload = lambda: dialog.statuses.append("reloaded")

    def confirm(message: str, title: str) -> bool:
        dialog.questions.append((title, message))
        return True

    dialog._confirm_action = confirm
    yield dialog
    dialog.dialog.Destroy()
    frame.Destroy()


def test_rerun_failed_cancel_and_approve_confirm_then_report_what_github_did(items) -> None:
    items._rerun_failed_jobs()
    items._cancel_selected_run()
    items._approve_fork_run()
    assert items._provider.calls == [
        ("rerun_failed", "o/r", 900),
        ("cancel", "o/r", 900),
        ("approve", "o/r", 900),
    ]
    assert [title for title, _ in items.questions] == [
        "Re-run Failed Jobs",
        "Cancel Run",
        "Approve Fork Run",
    ]
    assert "GitHub accepted the cancel request and is stopping run #12, CI." in " ".join(
        items.statuses
    )


def test_delete_says_what_will_be_deleted_and_reloads(items) -> None:
    items._delete_selected_run()
    title, question = items.questions[-1]
    assert title == "Delete Workflow Run"
    assert "run #12, CI on branch main (failure) from o/r" in question
    assert "cannot be undone" in question
    assert items._provider.calls == [("delete", "o/r", 900)]
    assert items.statuses[-2:] == ["Deleted run #12, CI.", "reloaded"]


def test_declined_confirmation_sends_nothing(items) -> None:
    items._confirm_action = lambda _m, _t: False
    items._delete_selected_run()
    items._cancel_selected_run()
    assert items._provider.calls == []


def test_failure_is_reported_not_claimed_as_success(items) -> None:
    items._provider.fail = GitHubItemsError("Could not cancel the run. Access denied.")
    items._cancel_selected_run()
    assert items.statuses[-1] == "Could not cancel the run. Access denied."


def test_combined_status_is_one_line(items) -> None:
    items._show_combined_status()
    assert items.statuses[-1] == "Commit abcdef1: 1 of 2 checks pass; failing: t."


def test_run_actions_appear_in_the_actions_menu_builder(items) -> None:
    labels: list[str] = []
    items._add_run_actions(lambda label, _handler: labels.append(label))
    assert labels[0] == "What Failed...\tCtrl+Shift+W"
    assert "Delete Run..." in labels and "Review Pending Deployments..." in labels


def test_what_failed_opens_the_digest_for_the_selected_run(items, monkeypatch) -> None:
    opened: list[dict[str, Any]] = []

    class _Digest:
        def __init__(self, _parent, _provider, **kwargs) -> None:
            opened.append(kwargs)

        def show(self) -> None:
            return None

    monkeypatch.setattr("quill.ui.github_run_digest_dialog.RunFailureDigestDialog", _Digest)
    items._show_failure_digest()
    assert opened[0]["run_id"] == 900 and opened[0]["run_label"] == "run #12, CI"


def test_digest_dialog_shows_text_and_summary(monkeypatch) -> None:
    shared_wx_app()
    from quill.ui import github_run_digest_dialog as module

    monkeypatch.setattr(module.threading, "Thread", _SyncThread)
    patch_call_after(monkeypatch, lambda fn, *a, **k: fn(*a, **k))
    monkeypatch.setattr(
        module,
        "collect_failure_digest",
        lambda *_a, **_k: "What failed in run #12\n1 of 2 jobs failed.\nJob 1 of 1: build",
    )
    frame = wx.Frame(None)
    spoken: list[str] = []
    dialog = module.RunFailureDigestDialog(
        frame, _Provider(), repo="o/r", run_id=900, run_label="run #12", announce_cb=spoken.append
    )
    dialog._load()
    assert dialog._text.GetValue().startswith("What failed in run #12")
    assert spoken == ["What failed is ready. 1 of 2 jobs failed."]
    assert dialog._copy_btn.IsEnabled()
    dialog.dialog.Destroy()
    frame.Destroy()


def test_pending_deployments_approve_with_comment(monkeypatch) -> None:
    shared_wx_app()
    from quill.ui import github_pending_deployments_dialog as module

    monkeypatch.setattr(module.threading, "Thread", _SyncThread)
    monkeypatch.setattr(module, "show_modal_dialog", lambda *_a, **_k: wx.ID_YES)
    patch_call_after(monkeypatch, lambda fn, *a, **k: fn(*a, **k))
    frame = wx.Frame(None)
    provider = _Provider()
    spoken: list[str] = []
    dialog = module.PendingDeploymentsDialog(
        frame, provider, repo="o/r", run_id=900, run_label="run #12", announce_cb=spoken.append
    )
    dialog._load()
    assert dialog._env_boxes[0].GetValue()
    dialog._review(True)
    assert spoken[-1] == "Write a comment first; GitHub requires one."
    dialog._comment.SetValue("Looks good")
    dialog._review(True)
    assert provider.calls == [("review", [7], True, "Looks good")]
    assert "Approved by GitHub: production." in spoken
    dialog.dialog.Destroy()
    frame.Destroy()
