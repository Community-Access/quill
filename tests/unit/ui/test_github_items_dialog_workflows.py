"""Tests for GitHubItemsDialog's Workflows view: Enter (and Actions... > Run
on Branch...) prompts for a branch and dispatches the workflow -- mirrors
the real-wx.App, _SyncThread, faked-provider pattern already used in
test_github_items_dialog_actions.py.
"""

from __future__ import annotations

from typing import Any

import pytest
import wx

from quill.core.github.items_provider import GitHubItemsError, GitHubWorkflow
from quill.ui.github_items_dialog import GitHubItemsDialog


class _FakeProvider:
    def __init__(self, *, authenticated: bool = True) -> None:
        self._authenticated = authenticated
        self.dispatched: list[tuple[str, str, str]] = []
        self.raise_on_dispatch: Exception | None = None

    @property
    def is_authenticated(self) -> bool:
        return self._authenticated

    def dispatch_workflow(self, repo: str, workflow_id: str, ref: str) -> None:
        if self.raise_on_dispatch is not None:
            raise self.raise_on_dispatch
        self.dispatched.append((repo, workflow_id, ref))


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


class _SyncThread:
    def __init__(
        self, target=None, args: tuple = (), kwargs: dict | None = None, daemon=None, **_kw: Any
    ) -> None:
        self._target = target
        self._args = args
        self._kwargs = kwargs or {}

    def start(self) -> None:
        if self._target is not None:
            self._target(*self._args, **self._kwargs)


@pytest.fixture
def dlg(wx_app, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("quill.ui.github_items_dialog_workflows.threading.Thread", _SyncThread)
    monkeypatch.setattr(wx, "CallAfter", lambda fn, *a, **k: fn(*a, **k))
    frame = wx.Frame(None)
    provider = _FakeProvider()
    dialog = GitHubItemsDialog(frame, provider, initial_repo="owner/repo")
    dialog._repo = "owner/repo"
    statuses: list[str] = []
    announcements: list[str] = []
    dialog._set_status = lambda message, **_kw: (
        statuses.append(message) or announcements.append(message)
    )
    dialog._announce = lambda message: announcements.append(message)
    dialog._reload = lambda: None
    dialog._show_modal = lambda _dlg, _title: wx.ID_OK
    dialog._confirm_action = lambda _message, _title: True
    dialog.statuses = statuses
    dialog.announcements = announcements
    return dialog


_WORKFLOW = GitHubWorkflow(id=999, name="CI", path=".github/workflows/ci.yml", state="active")


def test_run_workflow_requires_authentication(dlg) -> None:
    dlg._provider = _FakeProvider(authenticated=False)
    dlg._run_selected_workflow(_WORKFLOW)
    assert "signed-in" in dlg.announcements[-1]
    assert dlg._provider.dispatched == []


def test_run_workflow_dispatches_on_confirmed_branch(dlg) -> None:
    dlg._run_selected_workflow(_WORKFLOW)
    assert dlg._provider.dispatched == [("owner/repo", "999", "main")]
    assert "Dispatched CI on main" in dlg.statuses[-1]


def test_run_workflow_cancelled_confirmation_does_not_dispatch(dlg) -> None:
    dlg._confirm_action = lambda _message, _title: False
    dlg._run_selected_workflow(_WORKFLOW)
    assert dlg._provider.dispatched == []
    assert "cancelled" in dlg.announcements[-1].lower()


def test_run_workflow_reports_dispatch_error(dlg) -> None:
    dlg._provider.raise_on_dispatch = GitHubItemsError("workflow does not accept manual runs")
    dlg._run_selected_workflow(_WORKFLOW)
    assert "Error:" in dlg.statuses[-1]


def test_on_activate_in_workflows_view_runs_the_selected_workflow(dlg) -> None:
    from quill.ui.github_items_view import VIEW_WORKFLOWS

    dlg._view = VIEW_WORKFLOWS
    dlg._rows = [_WORKFLOW]
    dlg._list.InsertItem(0, "CI")
    dlg._list.Select(0)
    dlg._on_activate(None)
    assert dlg._provider.dispatched == [("owner/repo", "999", "main")]
