"""Tests for the accessible pull-request review reader."""

from __future__ import annotations

from typing import Any

import pytest
import wx

from quill.core.github import local_drafts
from quill.core.github.items_provider import GitHubPullDiff, GitHubPullFile
from quill.core.github.merge_policy import GitHubMergePolicy, GitHubPullQueueState
from quill.core.github.pr_review import (
    GitHubCheckRun,
    GitHubPullReviewState,
    GitHubReviewComment,
    GitHubReviewError,
    GitHubReviewThread,
)
from quill.ui.github_pr_review_dialog import GitHubPullReviewDialog
from quill.ui.github_review_draft_dialog import GitHubReviewDraft
from tests.wx_session import patch_call_after, shared_wx_app


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
def review_dialog(wx_app, tmp_path, monkeypatch):
    monkeypatch.setattr(local_drafts, "app_data_dir", lambda: tmp_path)
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

    assert (
        "required reviews and branch protection rules are not verified"
        in review_dialog._header.GetLabel()
    )
    assert "Ready to merge" not in review_dialog._header.GetLabel()
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


def test_review_actions_are_disabled_for_anonymous_viewer(wx_app, tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(local_drafts, "app_data_dir", lambda: tmp_path)
    frame = wx.Frame(None)
    dialog = GitHubPullReviewDialog(frame, _FakeProvider(authenticated=False), "owner/repo", 7)
    try:
        assert all(not button.IsEnabled() for button in dialog._write_buttons)
        assert dialog._browser_btn.IsEnabled()
        assert dialog._copy_btn.IsEnabled()
    finally:
        dialog.dialog.Destroy()
        frame.Destroy()


def test_merge_policy_button_loads_policy_for_the_current_head(review_dialog, monkeypatch) -> None:
    policy = GitHubMergePolicy(
        base_branch="main",
        branch_protection_available=True,
        branch_protection_enabled=True,
        required_checks=("CI",),
    )
    queue = GitHubPullQueueState(
        merge_queue_enabled=False,
        in_merge_queue=False,
        auto_merge_enabled=False,
        head_sha="a" * 40,
    )
    review_dialog._refresh_ready(_state(), (_thread(),))
    calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def _fetch(*args, **kwargs):
        calls.append((args, kwargs))
        return policy, queue

    monkeypatch.setattr(review_dialog._client, "fetch_merge_policy_context", _fetch)
    patch_call_after(monkeypatch)

    class _SyncThread:
        def __init__(self, *, target, daemon):
            self._target = target

        def start(self):
            self._target()

    monkeypatch.setattr("quill.ui.github_pr_review_dialog.threading.Thread", _SyncThread)
    review_dialog._load_merge_policy(None)

    assert calls[0][0] == ("owner/repo", 7, "main")
    assert calls[0][1] == {"expected_head_sha": "a" * 40}
    assert review_dialog._state.merge_policy is policy
    assert review_dialog._state.merge_queue_state is queue
    assert "Head revision: " + "a" * 40 in review_dialog._summary.GetValue()
    assert "Required checks observed: CI" in review_dialog._summary.GetValue()
    assert "refresh the review to recheck" in review_dialog._status.GetLabel()


def test_review_submission_clears_the_local_draft_only_after_submit(
    review_dialog, monkeypatch
) -> None:
    store = review_dialog._review_draft_store
    assert store.save_review(
        "owner/repo",
        7,
        event="comment",
        body="Review body",
        head_sha="a" * 40,
    )
    submitted: list[tuple[str, int, str, str]] = []

    class _Composer:
        def __init__(
            self, _parent, *, draft_store, repository, number, current_head_sha, announce_cb
        ) -> None:
            assert callable(announce_cb)
            assert draft_store is store
            assert repository == "owner/repo" and number == 7
            assert current_head_sha == "a" * 40

        def show(self):
            return GitHubReviewDraft("comment", "Review body", "a" * 40)

    monkeypatch.setattr("quill.ui.github_review_draft_dialog.GitHubReviewDraftDialog", _Composer)
    monkeypatch.setattr(
        review_dialog._client,
        "fetch_head_sha",
        lambda _repo, _number: "a" * 40,
    )
    monkeypatch.setattr(
        review_dialog._client,
        "submit_review",
        lambda repo, number, event, body: submitted.append((repo, number, event, body)),
    )
    monkeypatch.setattr(review_dialog, "_run_action", lambda action, _message: action())
    review_dialog._refresh_ready(_state(), ())

    review_dialog._submit_review(None)

    assert submitted == [("owner/repo", 7, "comment", "Review body")]
    assert store.get_review("owner/repo", 7) is None


def test_review_submission_stops_if_head_changes_after_composing(
    review_dialog, monkeypatch
) -> None:
    store = review_dialog._review_draft_store
    assert store.save_review(
        "owner/repo",
        7,
        event="comment",
        body="Draft text",
        head_sha="a" * 40,
    )

    class _Composer:
        def __init__(self, *_args, **_kwargs) -> None:
            pass

        def show(self):
            return GitHubReviewDraft("comment", "Draft text", "a" * 40)

    monkeypatch.setattr("quill.ui.github_review_draft_dialog.GitHubReviewDraftDialog", _Composer)
    monkeypatch.setattr(
        review_dialog._client,
        "fetch_head_sha",
        lambda _repo, _number: "b" * 40,
    )
    monkeypatch.setattr(review_dialog, "_run_action", lambda action, _message: action())
    review_dialog._refresh_ready(_state(), ())
    submitted: list[object] = []
    monkeypatch.setattr(
        review_dialog._client,
        "submit_review",
        lambda *_args: submitted.append("submitted"),
    )

    with pytest.raises(GitHubReviewError, match="head changed"):
        review_dialog._submit_review(None)

    assert submitted == []
    assert store.get_review("owner/repo", 7).head_sha == "a" * 40


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


def test_resolved_thread_can_be_reopened_from_context_menu(review_dialog, monkeypatch) -> None:
    from dataclasses import replace

    thread = replace(_thread(), node_id="THREAD_11", resolved=True, can_unresolve=True)
    review_dialog._refresh_ready(_state(), (thread,))
    root = review_dialog._outline.GetRootItem()
    files, _ = review_dialog._outline.GetFirstChild(root)
    file_node, _ = review_dialog._outline.GetFirstChild(files)
    thread_node, _ = review_dialog._outline.GetFirstChild(file_node)
    review_dialog._outline.SelectItem(thread_node)
    review_dialog._select_node(None)
    menu, refs = review_dialog._build_node_menu()
    labels = [item.GetItemLabelText() for item in menu.GetMenuItems()]
    assert "Reopen Thread..." in labels
    menu.Destroy()
    del refs
    calls: list[tuple[str, bool]] = []
    monkeypatch.setattr(review_dialog, "_confirm", lambda *_args: True)
    monkeypatch.setattr(review_dialog, "_run_action", lambda action, _message: action())
    monkeypatch.setattr(
        review_dialog._client,
        "change_thread_resolution",
        lambda node_id, *, resolved: calls.append((node_id, resolved)),
    )
    review_dialog._change_thread_resolution(None)
    assert calls == [("THREAD_11", False)]

    review_dialog._outline.SelectItem(root)
    review_dialog._select_node(None)
    menu, refs = review_dialog._build_node_menu()
    labels = [item.GetItemLabelText() for item in menu.GetMenuItems()]
    assert "Compose Review..." in labels
    assert "Request Reviewers..." in labels
    assert "Copy Pull Request Link" in labels
    menu.Destroy()
    del refs
