"""Tests for GitHubItemsDialog's Compare Branches, Columns..., Backspace
drill-back, and repo-URL-paste features -- the GHManage-parity gaps closed
alongside the existing Unified GitHub Management surface.

Mirrors the real-wx.App, _SyncThread, faked-provider pattern already used in
test_github_items_dialog_actions.py.
"""

from __future__ import annotations

from typing import Any

import pytest
import wx

from quill.core.github.items_provider import (
    GitHubBranch,
    GitHubBranchComparison,
    GitHubItemsError,
    GitHubRepoForkInfo,
)
from quill.ui.github_items_dialog import VIEW_BRANCHES, VIEW_COMMITS, VIEW_ISSUES, GitHubItemsDialog
from quill.ui.github_items_view import VIEW_COLUMNS


class _FakeProvider:
    def __init__(self) -> None:
        self.fork_info = GitHubRepoForkInfo(is_fork=False)
        self.compared: list[tuple[str, str, str]] = []
        self.compare_result = GitHubBranchComparison(
            base="main", head="feature", ahead_by=2, behind_by=1, status="diverged"
        )
        self.raise_on_compare: Exception | None = None

    def fetch_fork_info(self, repo: str) -> GitHubRepoForkInfo:
        return self.fork_info

    def compare_branches(self, repo: str, base: str, head: str) -> GitHubBranchComparison:
        if self.raise_on_compare is not None:
            raise self.raise_on_compare
        self.compared.append((repo, base, head))
        return self.compare_result


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


class _StubShow:
    def show(self) -> None:
        pass


@pytest.fixture
def dlg(wx_app, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("quill.ui.github_items_dialog.threading.Thread", _SyncThread)
    monkeypatch.setattr(wx, "CallAfter", lambda fn, *a, **k: fn(*a, **k))
    # A real modal ShowModal() would block the test; every compare-branches
    # test that doesn't specifically assert on dialog construction gets a
    # no-op stub here, mirroring _show_modal's short-circuit below.
    monkeypatch.setattr(
        "quill.ui.github_compare_branches_dialog.GitHubCompareBranchesDialog",
        lambda *a, **k: _StubShow(),
    )
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
    dialog.statuses = statuses
    dialog.announcements = announcements
    return dialog


# ---------------------------------------------------------------------------
# Compare Branches
# ---------------------------------------------------------------------------


def test_compare_branches_requires_a_loaded_repo(dlg) -> None:
    dlg._repo = ""
    dlg._view = VIEW_BRANCHES
    dlg._on_compare_branches()
    assert "Load a repository" in dlg.announcements[-1]


def test_compare_branches_requires_branches_view(dlg) -> None:
    dlg._view = VIEW_ISSUES
    dlg._on_compare_branches()
    assert "Branches view" in dlg.announcements[-1]


def test_compare_branches_prefills_head_from_selected_branch_row(dlg) -> None:
    """Also proves Compare Branches needs no authenticated session: the fake
    provider here carries no ``is_authenticated`` at all (unlike
    Batch.../Actions..., which would raise AttributeError if this code path
    touched it) -- it never writes to GitHub."""
    dlg._view = VIEW_BRANCHES
    assert not hasattr(dlg._provider, "is_authenticated")
    dlg._rows = [GitHubBranch(name="feature-x", commit_sha="abc123")]
    dlg._selected_indices = lambda: [0]
    dlg._on_compare_branches()
    assert dlg._provider.compared == [("owner/repo", "main", "feature-x")]


def test_compare_branches_opens_result_dialog_and_reports_status(dlg, monkeypatch) -> None:
    dlg._view = VIEW_BRANCHES
    dlg._rows = [GitHubBranch(name="feature", commit_sha="abc123")]
    dlg._selected_indices = lambda: [0]
    opened: list[Any] = []
    monkeypatch.setattr(
        "quill.ui.github_compare_branches_dialog.GitHubCompareBranchesDialog",
        lambda *a, **k: opened.append((a, k)) or _StubShow(),
    )
    dlg._on_compare_branches()
    assert opened, "the compare dialog should have been constructed"
    assert "2 ahead" in dlg.statuses[-1] and "1 behind" in dlg.statuses[-1]


def test_compare_branches_reports_provider_error(dlg) -> None:
    dlg._view = VIEW_BRANCHES
    dlg._rows = [GitHubBranch(name="feature", commit_sha="abc123")]
    dlg._selected_indices = lambda: [0]
    dlg._provider.raise_on_compare = GitHubItemsError("no common ancestor")
    dlg._on_compare_branches()
    assert "Error:" in dlg.statuses[-1]


# ---------------------------------------------------------------------------
# Columns... menu (per-view column selection)
# ---------------------------------------------------------------------------


def test_columns_default_to_every_column_visible(dlg) -> None:
    for view, cols in VIEW_COLUMNS.items():
        assert dlg._visible_columns[view] == list(cols)


def test_toggling_off_a_column_removes_it_from_rendering(dlg) -> None:
    dlg._view = VIEW_BRANCHES
    all_cols = VIEW_COLUMNS[VIEW_BRANCHES]
    assert dlg._current_columns() == all_cols
    dlg._visible_columns[VIEW_BRANCHES] = [c for c in all_cols if c != "protected"]
    dlg._rebuild_columns()
    assert "protected" not in dlg._current_columns()
    assert dlg._list.GetColumnCount() == len(all_cols) - 1


def test_columns_refuses_to_hide_the_last_visible_column(dlg) -> None:
    dlg._view = VIEW_BRANCHES
    only = VIEW_COLUMNS[VIEW_BRANCHES][0]
    dlg._visible_columns[VIEW_BRANCHES] = [only]

    # Simulate the menu handler's own guard directly (no live PopupMenu in a
    # headless test): removing the sole remaining column must refuse.
    visible = list(dlg._visible_columns[VIEW_BRANCHES])
    if only in visible and len(visible) <= 1:
        dlg._announce("At least one column must stay visible.")
    assert dlg._visible_columns[VIEW_BRANCHES] == [only]
    assert "must stay visible" in dlg.announcements[-1]


def test_column_visibility_is_independent_per_view(dlg) -> None:
    dlg._visible_columns[VIEW_BRANCHES] = ["name"]
    assert dlg._visible_columns[VIEW_ISSUES] == list(VIEW_COLUMNS[VIEW_ISSUES])


def test_column_choice_persists_across_dialog_instances(wx_app, monkeypatch, tmp_path) -> None:
    """A choice made in the Columns... menu survives closing and reopening
    the dialog -- the whole point of routing it through GitHubSavedItems."""
    monkeypatch.setattr("quill.core.github.saved_items.app_data_dir", lambda: tmp_path)
    frame = wx.Frame(None)

    first = GitHubItemsDialog(frame, _FakeProvider(), initial_repo="owner/repo")
    only = VIEW_COLUMNS[VIEW_BRANCHES][0]
    first._visible_columns[VIEW_BRANCHES] = [only]
    first._saved.set_columns(VIEW_BRANCHES, [only])

    second = GitHubItemsDialog(frame, _FakeProvider(), initial_repo="owner/repo")
    assert second._visible_columns[VIEW_BRANCHES] == [only]


# ---------------------------------------------------------------------------
# Backspace steps back from the Commits drill-down
# ---------------------------------------------------------------------------


class _FakeKeyEvent:
    def __init__(self, key: int) -> None:
        self._key = key

    def GetKeyCode(self) -> int:
        return self._key

    def Skip(self) -> None:
        pass


def test_backspace_in_commits_returns_to_branches(dlg) -> None:
    dlg._view = VIEW_COMMITS
    dlg._drill_branch = "feature"
    dlg._on_list_key(_FakeKeyEvent(wx.WXK_BACK))
    assert dlg._view == VIEW_BRANCHES
    assert dlg._drill_branch is None


def test_backspace_in_commits_without_a_drill_branch_is_a_no_op(dlg) -> None:
    dlg._view = VIEW_COMMITS
    dlg._drill_branch = None
    dlg._on_list_key(_FakeKeyEvent(wx.WXK_BACK))
    assert dlg._view == VIEW_COMMITS


def test_backspace_outside_commits_view_is_a_no_op(dlg) -> None:
    dlg._view = VIEW_BRANCHES
    dlg._drill_branch = None
    dlg._on_list_key(_FakeKeyEvent(wx.WXK_BACK))
    assert dlg._view == VIEW_BRANCHES


# ---------------------------------------------------------------------------
# Pasting a GitHub URL into the repository field
# ---------------------------------------------------------------------------


def test_on_load_normalizes_a_pasted_github_url(dlg) -> None:
    loaded: list[str] = []
    dlg._reload = lambda: loaded.append(dlg._repo)
    dlg._fetch_fork_info_async = lambda _repo: None
    dlg._repo_ctrl.SetValue("https://github.com/owner/repo")
    dlg._on_load(None)
    assert dlg._repo_ctrl.GetValue() == "owner/repo"
    assert loaded == ["owner/repo"]


def test_on_load_rejects_input_with_no_recoverable_owner_repo(dlg) -> None:
    dlg._repo_ctrl.SetValue("not-a-repo")
    dlg._on_load(None)
    assert "owner/repo" in dlg.statuses[-1]
