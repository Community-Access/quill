"""Tests for GitHubCompareBranchesDialog: summary text, commit/file list
population, and the per-file diff fetch -- mirroring the real-wx.App,
_SyncThread pattern already used for ArtifactsDialog and GitHubPullDiffDialog.
"""

from __future__ import annotations

from typing import Any

import pytest
import wx

from quill.core.github.items_provider import (
    GitHubBranchComparison,
    GitHubCommit,
    GitHubItemsError,
    GitHubPullFile,
)
from quill.ui.github_compare_branches_dialog import GitHubCompareBranchesDialog
from tests.wx_session import patch_call_after, shared_wx_app


class _FakeProvider:
    def __init__(self) -> None:
        self.file_text: dict[tuple[str, str], str] = {}
        self.raise_on_fetch: Exception | None = None

    def fetch_file_text(self, repo: str, path: str, ref: str) -> str:
        if self.raise_on_fetch is not None:
            raise self.raise_on_fetch
        return self.file_text.get((path, ref), "")


@pytest.fixture(scope="module")
def wx_app():
    app = shared_wx_app()
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


@pytest.fixture(autouse=True)
def _sync_threading(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("quill.ui.github_compare_branches_dialog.threading.Thread", _SyncThread)
    patch_call_after(monkeypatch, lambda fn, *a, **k: fn(*a, **k))


def _comparison(**overrides: Any) -> GitHubBranchComparison:
    defaults: dict[str, Any] = dict(
        base="main",
        head="feature",
        ahead_by=2,
        behind_by=1,
        status="diverged",
        total_commits=2,
        commits=(
            GitHubCommit(sha="a" * 40, short_sha="aaaaaaa", message="Fix thing", author="Alice"),
        ),
        files=(GitHubPullFile(filename="a.py", status="modified", additions=3, deletions=1),),
        permalink_url="https://github.com/owner/repo/compare/main...feature",
    )
    defaults.update(overrides)
    return GitHubBranchComparison(**defaults)


def test_summary_line_reports_ahead_behind_and_counts(wx_app) -> None:
    frame = wx.Frame(None)
    provider = _FakeProvider()
    dlg = GitHubCompareBranchesDialog(frame, provider, "owner/repo", _comparison())
    assert dlg._summary_line().startswith(
        "feature and main have diverged: feature is 2 commits ahead and 1 behind."
    )
    dlg.dialog.Destroy()


def test_summary_line_identical(wx_app) -> None:
    frame = wx.Frame(None)
    provider = _FakeProvider()
    comparison = _comparison(status="identical", ahead_by=0, behind_by=0, total_commits=0, files=())
    dlg = GitHubCompareBranchesDialog(frame, provider, "owner/repo", comparison)
    assert dlg._summary_line() == "feature and main are identical."
    dlg.dialog.Destroy()


def test_commits_and_files_lists_are_populated(wx_app) -> None:
    frame = wx.Frame(None)
    provider = _FakeProvider()
    dlg = GitHubCompareBranchesDialog(frame, provider, "owner/repo", _comparison())
    assert dlg._commits_list.GetItemCount() == 1
    assert dlg._commits_list.GetItemText(0, 0) == "aaaaaaa"
    assert dlg._files.GetCount() == 1
    dlg.dialog.Destroy()


def test_selecting_a_file_fetches_both_refs_and_renders_diff(wx_app) -> None:
    frame = wx.Frame(None)
    provider = _FakeProvider()
    provider.file_text[("a.py", "main")] = "old\n"
    provider.file_text[("a.py", "feature")] = "new\n"
    dlg = GitHubCompareBranchesDialog(frame, provider, "owner/repo", _comparison())
    dlg._files.SetSelection(0)
    dlg._on_select_file(None)
    text = dlg._detail.GetValue()
    assert "a.py" in text
    assert "old" in text or "new" in text
    dlg.dialog.Destroy()


def test_selecting_a_file_falls_back_to_patch_on_fetch_error(wx_app) -> None:
    frame = wx.Frame(None)
    provider = _FakeProvider()
    provider.raise_on_fetch = GitHubItemsError("binary content")
    comparison = _comparison(
        files=(
            GitHubPullFile(
                filename="img.png", status="modified", additions=0, deletions=0, patch=""
            ),
        )
    )
    dlg = GitHubCompareBranchesDialog(frame, provider, "owner/repo", comparison)
    dlg._files.SetSelection(0)
    dlg._on_select_file(None)
    assert "img.png" in dlg._detail.GetValue()
    dlg.dialog.Destroy()


def test_open_browser_button_disabled_without_permalink(wx_app) -> None:
    frame = wx.Frame(None)
    provider = _FakeProvider()
    comparison = _comparison(permalink_url="")
    dlg = GitHubCompareBranchesDialog(frame, provider, "owner/repo", comparison)
    assert dlg._browser_btn.IsEnabled() is False
    dlg.dialog.Destroy()


def test_behind_page_lists_what_the_base_has_and_the_pull_line_shows(
    wx_app, monkeypatch: pytest.MonkeyPatch
) -> None:
    frame = wx.Frame(None)
    said: list[str] = []
    opened: list[str] = []
    monkeypatch.setattr("quill.ui.github_compare_branches_dialog.webbrowser.open", opened.append)
    comparison = _comparison(
        behind_commits=(
            GitHubCommit(sha="b" * 40, short_sha="bbbbbbb", message="On main only\nbody"),
        ),
        pull_number=9,
        pull_title="Feature",
        pull_url="https://github.com/owner/repo/pull/9",
    )
    dlg = GitHubCompareBranchesDialog(
        frame, _FakeProvider(), "owner/repo", comparison, announce_cb=said.append
    )
    assert dlg._behind_list.GetItemCount() == 1
    assert dlg._behind_list.GetItemText(0, 3) == "On main only"
    assert "Pull request #9 is open: Feature." in dlg._summary_line()
    assert dlg._pull_btn.IsEnabled()
    dlg._on_open_pull(None)
    assert opened == ["https://github.com/owner/repo/pull/9"]
    assert said == ["Opened pull request #9 in browser"]
    dlg.dialog.Destroy()


def test_pull_button_greyed_without_a_pull_request(wx_app) -> None:
    dlg = GitHubCompareBranchesDialog(wx.Frame(None), _FakeProvider(), "owner/repo", _comparison())
    assert not dlg._pull_btn.IsEnabled()
    assert dlg._behind_list.GetItemCount() == 0
    dlg.dialog.Destroy()
