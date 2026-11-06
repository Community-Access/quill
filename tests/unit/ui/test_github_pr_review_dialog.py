"""Tests for the accessible pull-request review reader."""

from __future__ import annotations

from typing import Any

import pytest
import wx

from quill.core.github.items_provider import GitHubPullDiff, GitHubPullFile
from quill.core.github.pr_review import (
    GitHubCheckRun,
    GitHubPullReviewState,
    GitHubReviewComment,
    GitHubReviewThread,
)
from quill.ui.github_pr_review_dialog import GitHubPullReviewDialog
from tests.wx_session import shared_wx_app


class _FakeProvider:
    def __init__(self, *, authenticated: bool = True) -> None:
        self.is_authenticated = authenticated

    def _repo(self, _full_name: str) -> Any:
        raise AssertionError("The dialog tests populate the view without network access")


@pytest.fixture(scope="module")
def wx_app():
    app = shared_wx_app()
    yield app
    app.Destroy()


@pytest.fixture
def review_dialog(wx_app):
    frame = wx.Frame(None)
    dialog = GitHubPullReviewDialog(
        frame,
        _FakeProvider(),
        "owner/repo",
        7,
        announce_cb=lambda _message: None,
    )
    dialog.dialog.Show()
    wx.Yield()
    yield dialog
    dialog.dialog.Destroy()
    frame.Destroy()


def _state(**overrides: Any) -> GitHubPullReviewState:
    values: dict[str, Any] = {
        "number": 7,
        "title": "Add feature",
        "state": "open",
        "draft": False,
        "merged": False,
        "mergeable": True,
        "mergeable_state": "clean",
        "base_ref": "main",
        "head_ref": "feature",
        "head_sha": "a" * 40,
        "author": "author",
        "url": "https://github.com/owner/repo/pull/7",
        "reviews": (),
        "checks": (GitHubCheckRun("CI", "completed", "success", "https://ci", "All green"),),
        "thread_count": 1,
        "outdated_thread_count": 0,
    }
    values.update(overrides)
    return GitHubPullReviewState(**values)


def _thread() -> GitHubReviewThread:
    return GitHubReviewThread(
        comments=(
            GitHubReviewComment(
                id=11,
                author="reviewer",
                body="Please clarify this branch.",
                path="src/example.py",
                line=23,
            ),
            GitHubReviewComment(
                id=12,
                author="author",
                body="Updated in the latest commit.",
                path="src/example.py",
                line=23,
                in_reply_to=11,
            ),
        )
    )


def test_review_reader_shows_header_threads_checks_and_replies(review_dialog) -> None:
    review_dialog._refresh_ready(_state(), (_thread(),))

    assert "Ready to merge" in review_dialog._header.GetLabel()
    assert "approved" not in review_dialog._header.GetLabel()
    root = review_dialog._outline.GetRootItem()
    assert review_dialog._outline.GetItemText(root).startswith("PR #7")
    files, _ = review_dialog._outline.GetFirstChild(root)
    file_node, _ = review_dialog._outline.GetFirstChild(files)
    thread_node, _ = review_dialog._outline.GetFirstChild(file_node)
    assert review_dialog._outline.GetItemText(file_node) == "src/example.py"
    assert "Line 23, reviewer, 1 replies" in review_dialog._outline.GetItemText(thread_node)
    review_dialog._outline.SelectItem(thread_node)
    assert review_dialog._node_kind() == ("thread", 0), (
        review_dialog._outline.GetSelection().IsOk(),
        review_dialog._outline.GetSelection().GetID(),
        thread_node.GetID(),
        review_dialog._nodes,
    )
    review_dialog._select_node(None)
    assert "CI" in review_dialog._check_list.GetString(0)
    detail = review_dialog._thread_detail.GetValue()
    assert "Please clarify this branch." in detail
    assert "Updated in the latest commit." in detail
    assert review_dialog._summary.GetValue().startswith("PR #7: Add feature")


def test_review_actions_are_disabled_for_anonymous_viewer(wx_app) -> None:
    frame = wx.Frame(None)
    dialog = GitHubPullReviewDialog(frame, _FakeProvider(authenticated=False), "owner/repo", 7)
    try:
        assert all(not button.IsEnabled() for button in dialog._write_buttons)
        assert dialog._browser_btn.IsEnabled()
        assert dialog._copy_btn.IsEnabled()
    finally:
        dialog.dialog.Destroy()
        frame.Destroy()


def test_empty_review_threads_are_explained(review_dialog) -> None:
    review_dialog._refresh_ready(_state(thread_count=0, checks=()), ())
    assert "Review threads: 0" in review_dialog._thread_detail.GetValue()
    assert review_dialog._check_list.GetCount() == 0
    assert not review_dialog._reply_btn.IsEnabled()


def test_selected_thread_can_be_replied_to(review_dialog, monkeypatch) -> None:
    review_dialog._refresh_ready(_state(), (_thread(),))
    root = review_dialog._outline.GetRootItem()
    files, _ = review_dialog._outline.GetFirstChild(root)
    file_node, _ = review_dialog._outline.GetFirstChild(files)
    thread_node, _ = review_dialog._outline.GetFirstChild(file_node)
    review_dialog._outline.SelectItem(thread_node)
    review_dialog._select_node(None)
    assert review_dialog._reply_btn.IsEnabled()
    calls: list[tuple[str, int, int, str]] = []
    monkeypatch.setattr(review_dialog, "_text_entry", lambda *_args: "Thanks, updated.")
    monkeypatch.setattr(
        review_dialog._client,
        "reply_to_thread",
        lambda repo, number, comment_id, body: calls.append((repo, number, comment_id, body)),
    )
    monkeypatch.setattr(review_dialog, "_run_action", lambda action, _message: action())

    review_dialog._reply_to_thread(None)

    assert calls == [("owner/repo", 7, 11, "Thanks, updated.")]


def test_closed_pull_request_disables_review_actions(review_dialog) -> None:
    review_dialog._refresh_ready(_state(state="closed"), (_thread(),))
    assert all(not button.IsEnabled() for button in review_dialog._write_buttons)


def test_control_r_replies_to_selected_thread(review_dialog, monkeypatch) -> None:
    review_dialog._refresh_ready(_state(), (_thread(),))
    called: list[None] = []
    monkeypatch.setattr(review_dialog, "_reply_to_thread", lambda _event: called.append(None))

    class _Key:
        def ControlDown(self) -> bool:
            return True

        def GetKeyCode(self) -> int:
            return ord("R")

    review_dialog._on_review_key(_Key())
    assert called == [None]


def test_refresh_keeps_selected_review_thread(review_dialog) -> None:
    first = _thread()
    second = GitHubReviewThread(
        comments=(GitHubReviewComment(id=21, author="other", body="Second thread"),)
    )
    review_dialog._refresh_ready(_state(thread_count=2), (first, second))
    root = review_dialog._outline.GetRootItem()
    general, _ = review_dialog._outline.GetNextChild(
        root, review_dialog._outline.GetFirstChild(root)[1]
    )
    # The second thread has no file path, so it lives under General conversations.
    second_node, _ = review_dialog._outline.GetFirstChild(general)
    review_dialog._outline.SelectItem(second_node)
    review_dialog._select_node(None)

    review_dialog._refresh_ready(_state(thread_count=2), (first, second))

    assert review_dialog._node_kind() == ("thread", 1)
    assert "Second thread" in review_dialog._thread_detail.GetValue()


def test_double_clicking_check_opens_its_link(review_dialog, monkeypatch) -> None:
    review_dialog._refresh_ready(_state(), ())
    review_dialog._check_list.SetSelection(0)
    opened: list[str] = []
    monkeypatch.setattr("quill.ui.github_pr_review_dialog.webbrowser.open", opened.append)

    review_dialog._open_check(None)

    assert opened == ["https://ci"]


def test_changed_file_without_comments_opens_its_own_diff(review_dialog, monkeypatch) -> None:
    diff = GitHubPullDiff(
        number=7,
        title="Add feature",
        base_ref="main",
        base_sha="a" * 40,
        head_ref="feature",
        head_sha="b" * 40,
        files=(GitHubPullFile("src/uncommented.py", "modified", 4, 2, 6),),
    )
    review_dialog._refresh_ready(_state(thread_count=0), (), diff)
    root = review_dialog._outline.GetRootItem()
    files, _ = review_dialog._outline.GetFirstChild(root)
    file_node, _ = review_dialog._outline.GetFirstChild(files)
    review_dialog._outline.SelectItem(file_node)
    review_dialog._select_node(None)
    assert "+4 -2 lines" in review_dialog._thread_detail.GetValue()

    opened: list[str] = []

    class _FakeDiffDialog:
        def __init__(self, *_args, initial_file: str = "", **_kwargs) -> None:
            opened.append(initial_file)

        def show(self) -> None:
            pass

    monkeypatch.setattr("quill.ui.github_pr_diff_dialog.GitHubPullDiffDialog", _FakeDiffDialog)
    review_dialog._open_file_diff(None)
    assert opened == ["src/uncommented.py"]


def test_review_context_menu_offers_node_actions(review_dialog) -> None:
    review_dialog._refresh_ready(_state(), (_thread(),))
    root = review_dialog._outline.GetRootItem()
    files, _ = review_dialog._outline.GetFirstChild(root)
    file_node, _ = review_dialog._outline.GetFirstChild(files)
    thread_node, _ = review_dialog._outline.GetFirstChild(file_node)
    review_dialog._outline.SelectItem(thread_node)
    review_dialog._select_node(None)
    menu, refs = review_dialog._build_node_menu()
    labels = [item.GetItemLabelText() for item in menu.GetMenuItems()]
    assert "Reply to Thread..." in labels
    assert "Copy Conversation" in labels
    menu.Destroy()
    del refs

    review_dialog._outline.SelectItem(root)
    review_dialog._select_node(None)
    menu, refs = review_dialog._build_node_menu()
    labels = [item.GetItemLabelText() for item in menu.GetMenuItems()]
    assert "Submit Review..." in labels
    assert "Request Reviewers..." in labels
    assert "Copy Pull Request Link" in labels
    menu.Destroy()
    del refs
