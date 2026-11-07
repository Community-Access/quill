"""Tests for GitHubItemsDialog's write actions: new issue/PR, merge, delete
branch, re-run workflow, and comment reply/edit/delete.

Constructed with a real wx.App/Frame (matching test_status_dialog.py's
precedent — this dialog builds real wx controls in __init__ and there is no
wx-free seam to fake around that). Per-test, ``_show_modal`` is monkeypatched
to short-circuit dialog confirmation, ``_selected_indices`` is monkeypatched
to avoid driving real wx.ListCtrl selection state, and ``_provider`` is a
lightweight fake recording calls -- mirroring the level of faking already
used for the batch-operations code path this mirrors.
"""

from __future__ import annotations

from typing import Any

import pytest
import wx

from quill.core.github.issue_templates import GitHubIssueTemplate
from quill.core.github.items_provider import (
    GitHubItem,
    GitHubItemsError,
    GitHubRelease,
    GitHubReleaseAsset,
    GitHubRepoForkInfo,
)
from quill.ui.github_items_dialog import GitHubItemsDialog
from quill.ui.github_items_view import RELEASE_ASSET_COLUMNS, VIEW_RELEASES
from tests.wx_session import patch_call_after, shared_wx_app


class _FakeProvider:
    def __init__(self, *, authenticated: bool = True, token: str = "tok") -> None:
        self._authenticated = authenticated
        self._token = token
        self.created_issues: list[tuple[str, str, str]] = []
        self.created_issue_options: list[tuple[tuple[str, ...], tuple[str, ...]]] = []
        self.created_pulls: list[tuple[str, str, str, str, str]] = []
        self.merged: list[tuple[str, int]] = []
        self.reran: list[tuple[str, int]] = []
        self.posted_comments: list[tuple[str, int, str]] = []
        self.edited_comments: list[tuple[str, int, str]] = []
        self.deleted_comments: list[tuple[str, int]] = []
        self.merge_result = "merged-sha-1234567"
        self.raise_on_merge: Exception | None = None
        self.fork_info = GitHubRepoForkInfo(is_fork=False)

    @property
    def is_authenticated(self) -> bool:
        return self._authenticated

    @property
    def token(self) -> str:
        return self._token

    def fetch_issue_templates(self, _repo: str) -> tuple[GitHubIssueTemplate, ...]:
        return ()

    def create_issue(
        self,
        repo: str,
        title: str,
        body: str,
        *,
        labels: tuple[str, ...] = (),
        assignees: tuple[str, ...] = (),
    ) -> GitHubItem:
        self.created_issues.append((repo, title, body))
        self.created_issue_options.append((labels, assignees))
        return GitHubItem(number=101, title=title, state="open", url="", is_pr=False)

    def create_pull_request(
        self, repo: str, title: str, body: str, head: str, base: str
    ) -> GitHubItem:
        self.created_pulls.append((repo, title, body, head, base))
        return GitHubItem(number=102, title=title, state="open", url="", is_pr=True)

    def search_items(self, _repo: str, _query: str, *, limit: int) -> list[GitHubItem]:
        return []

    def merge_pull_request(self, repo: str, number: int, **_kw: Any) -> str:
        if self.raise_on_merge:
            raise self.raise_on_merge
        self.merged.append((repo, number))
        return self.merge_result

    def rerun_workflow_run(self, repo: str, run_id: int) -> None:
        self.reran.append((repo, run_id))

    def create_comment(self, repo: str, number: int, body: str) -> dict:
        self.posted_comments.append((repo, number, body))
        return {"id": "1", "author": "me", "created_at": "", "body": body}

    def edit_comment(self, repo: str, comment_id: int, body: str) -> dict:
        self.edited_comments.append((repo, comment_id, body))
        return {"id": str(comment_id), "author": "me", "created_at": "", "body": body}

    def delete_comment(self, repo: str, comment_id: int) -> None:
        self.deleted_comments.append((repo, comment_id))

    def fetch_issue_comments(self, repo: str, number: int) -> list[dict]:
        return []

    def fetch_fork_info(self, repo: str) -> GitHubRepoForkInfo:
        return self.fork_info


@pytest.fixture(scope="module")
def wx_app():
    app = shared_wx_app()
    yield app
    app.Destroy()


class _SyncThread:
    """Stands in for threading.Thread: runs target(*args, **kwargs) immediately
    on .start(), so the write actions' worker/CallAfter round trip is
    deterministic in a test with no real wx event loop pumping CallAfter's
    queue. Every prior caller here happened to use a zero-arg target, so a
    version that silently dropped args/kwargs went unnoticed until a target
    that actually takes arguments (_fork_info_worker) exposed it."""

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
def dlg(wx_app, monkeypatch: pytest.MonkeyPatch, tmp_path):
    monkeypatch.setattr("quill.ui.github_items_dialog.threading.Thread", _SyncThread)
    monkeypatch.setattr("quill.core.github.local_drafts.app_data_dir", lambda: tmp_path)
    patch_call_after(monkeypatch, lambda fn, *a, **k: fn(*a, **k))
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
# Actions menu gating
# ---------------------------------------------------------------------------


def test_actions_menu_requires_a_loaded_repo(dlg) -> None:
    dlg._repo = ""
    dlg._on_actions_menu(None)
    assert "Load a repository" in dlg.announcements[-1]


def test_back_forward_navigation_controls_are_named_and_stateful(dlg) -> None:
    from quill.core.github.navigation_state import GitHubItemsContext

    assert dlg._back_btn.GetName() == "Return to the previous GitHub repository or item"
    assert dlg._forward_btn.GetName() == "Move forward to the next GitHub repository or item"
    assert not dlg._back_btn.IsEnabled()
    assert not dlg._forward_btn.IsEnabled()
    dlg._navigation_state.record(
        GitHubItemsContext(repository="owner/repo", selected_key="issue:1")
    )
    dlg._navigation_state.record(
        GitHubItemsContext(repository="owner/repo", selected_key="issue:2")
    )
    dlg._update_navigation_buttons()
    assert dlg._back_btn.IsEnabled()
    assert not dlg._forward_btn.IsEnabled()
    dlg._navigation_state.back()
    dlg._update_navigation_buttons()
    assert not dlg._back_btn.IsEnabled()
    assert dlg._forward_btn.IsEnabled()


def test_actions_menu_requires_authentication(dlg) -> None:
    dlg._provider = _FakeProvider(authenticated=False)
    dlg._on_actions_menu(None)
    assert "signed-in" in dlg.announcements[-1]


def test_review_selected_pr_opens_review_reader(dlg, monkeypatch: pytest.MonkeyPatch) -> None:
    pr = GitHubItem(number=5, title="Fix it", state="open", url="", is_pr=True)
    dlg._rows = [pr]
    dlg._list.InsertItem(0, "Fix it")
    dlg._list.Select(0)
    opened: list[tuple[str, int]] = []

    class _ReviewDialog:
        def __init__(self, _parent, _provider, repo: str, number: int, **_kwargs) -> None:
            opened.append((repo, number))

        def show(self) -> None:
            return None

    monkeypatch.setattr("quill.ui.github_pr_review_dialog.GitHubPullReviewDialog", _ReviewDialog)

    dlg._on_review()

    assert opened == [("owner/repo", 5)]


def test_pr_context_menu_exposes_review_and_copy_actions(dlg, monkeypatch) -> None:
    pr = GitHubItem(
        number=5,
        title="Fix it",
        state="open",
        url="https://github.com/owner/repo/pull/5",
        is_pr=True,
    )
    dlg._rows = [pr]
    dlg._list.InsertItem(0, "Fix it")
    dlg._list.Select(0)
    labels: list[str] = []
    monkeypatch.setattr(
        wx.ListCtrl,
        "PopupMenu",
        lambda _self, menu: labels.extend(item.GetItemLabelText() for item in menu.GetMenuItems()),
    )

    dlg._on_item_context_menu(None)

    assert "Open Review..." in labels
    assert "Open File Differences..." in labels
    assert "Copy Link" in labels
    assert "Copy Details" in labels


def test_codespaces_handoff_discloses_billing_and_preserves_selected_branch(
    dlg, monkeypatch
) -> None:
    from quill.core.github.items_provider import GitHubBranch

    class _ConfirmDialog:
        def __init__(self, _parent, message: str, *_args, **_kwargs) -> None:
            self.message = message

        def Destroy(self) -> None:
            return None

    monkeypatch.setattr(wx, "MessageDialog", _ConfirmDialog)
    urls: list[str] = []
    monkeypatch.setattr(
        "quill.ui.github_items_dialog_menus.webbrowser.open",
        lambda url, **_kwargs: urls.append(url) or True,
    )
    confirmed = []

    def _confirm(dialog, title):
        confirmed.append((dialog.message, title))
        return wx.ID_YES

    dlg._show_modal = _confirm
    dlg._open_in_codespaces(GitHubBranch(name="feature/demo", commit_sha="abc"))

    assert urls == ["https://codespaces.new/owner/repo/tree/feature%2Fdemo"]
    assert "can incur charges" in confirmed[0][0]
    assert "will not create a Codespace" in confirmed[0][0]
    assert "attach your GitHub token" in confirmed[0][0]


# ---------------------------------------------------------------------------
# New issue / new pull request
# ---------------------------------------------------------------------------


def test_new_issue_creates_via_provider(dlg, monkeypatch: pytest.MonkeyPatch) -> None:
    from quill.ui.github_issue_draft_dialog import GitHubIssueDraft

    class _FakeIssueDraftDialog:
        def __init__(self, *_args, **_kwargs) -> None:
            return None

        def show(self):
            return GitHubIssueDraft("Bug title", "steps to repro", (), ())

    monkeypatch.setattr(
        "quill.ui.github_issue_draft_dialog.GitHubIssueDraftDialog",
        _FakeIssueDraftDialog,
    )
    monkeypatch.setattr(
        "quill.ui.github_items_dialog_issue_templates.threading.Thread", _SyncThread
    )
    dlg._new_issue()
    assert dlg._provider.created_issues == [("owner/repo", "Bug title", "steps to repro")]
    assert "Created ISSUE #101" in dlg.statuses[-1]


def test_new_issue_uses_the_selected_repository_template(dlg, monkeypatch) -> None:
    template = GitHubIssueTemplate(
        name="Bug report",
        filename="bug.md",
        about="Report a bug",
        title="[Bug] ",
        body="## Steps\nDescribe the steps.",
        labels=("bug",),
        assignees=("alice",),
    )
    monkeypatch.setattr(dlg._provider, "fetch_issue_templates", lambda _repo: (template,))

    class _ChoiceDialog:
        def __init__(self, *_args, **_kwargs) -> None:
            return None

        def SetName(self, _name: str) -> None:
            return None

        def GetSelection(self) -> int:
            return 1

        def Destroy(self) -> None:
            return None

    monkeypatch.setattr(wx, "SingleChoiceDialog", _ChoiceDialog)
    selected: list[dict[str, object]] = []
    monkeypatch.setattr(dlg, "_prompt_and_create", lambda **kwargs: selected.append(kwargs))

    dlg._new_issue()

    assert selected == [{"kind": "issue", "template": template}]


def test_new_issue_form_hands_off_to_browser_with_explanation(dlg, monkeypatch) -> None:
    template = GitHubIssueTemplate(
        name="Feature request",
        filename="feature.yml",
        about="Structured request",
        url="https://github.com/owner/repo/blob/main/.github/ISSUE_TEMPLATE/feature.yml",
        supported=False,
    )
    monkeypatch.setattr(dlg._provider, "fetch_issue_templates", lambda _repo: (template,))

    class _ChoiceDialog:
        def __init__(self, *_args, **_kwargs) -> None:
            return None

        def SetName(self, _name: str) -> None:
            return None

        def GetSelection(self) -> int:
            return 1

        def Destroy(self) -> None:
            return None

    monkeypatch.setattr(wx, "SingleChoiceDialog", _ChoiceDialog)
    opened: list[tuple[GitHubIssueTemplate, str]] = []
    monkeypatch.setattr(
        dlg,
        "_open_template_in_browser",
        lambda selected, reason: opened.append((selected, reason)),
    )

    dlg._new_issue()

    assert opened == [(template, "This structured issue form is completed on GitHub.")]


def test_new_issue_warns_about_similar_issues_before_creating(dlg, monkeypatch) -> None:
    from quill.ui.github_issue_draft_dialog import GitHubIssueDraft

    class _FakeIssueDraftDialog:
        def __init__(self, *_args, **_kwargs) -> None:
            return None

        def show(self):
            return GitHubIssueDraft("Existing bug title", "Reproduction steps", (), ())

    monkeypatch.setattr(
        "quill.ui.github_issue_draft_dialog.GitHubIssueDraftDialog",
        _FakeIssueDraftDialog,
    )
    dlg._provider.search_items = lambda *_args, **_kwargs: [
        GitHubItem(
            number=77,
            title="Existing bug title",
            state="open",
            url="https://github.com/owner/repo/issues/77",
            is_pr=False,
        )
    ]

    class _FakeMessageDialog:
        def __init__(self, _parent, message: str, *_args, **_kwargs) -> None:
            self.message = message

        def Destroy(self) -> None:
            return None

    monkeypatch.setattr(wx, "MessageDialog", _FakeMessageDialog)
    monkeypatch.setattr(
        "quill.ui.github_items_dialog_issue_templates.threading.Thread", _SyncThread
    )

    def _confirm(dialog, _title):
        if isinstance(dialog, _FakeMessageDialog):
            assert "#77: Existing bug title" in dialog.message
            return wx.ID_NO
        return wx.ID_OK

    dlg._show_modal = _confirm
    dlg._new_issue()

    assert dlg._provider.created_issues == []
    assert "cancelled after duplicate suggestions" in dlg.announcements[-1]


def test_new_issue_cancelled_at_title_does_nothing(dlg, monkeypatch: pytest.MonkeyPatch) -> None:
    class _CancelledIssueDraftDialog:
        def __init__(self, *_args, **_kwargs) -> None:
            return None

        def show(self):
            return None

    monkeypatch.setattr(
        "quill.ui.github_issue_draft_dialog.GitHubIssueDraftDialog",
        _CancelledIssueDraftDialog,
    )
    dlg._new_issue()
    assert dlg._provider.created_issues == []


def test_new_issue_submits_edited_template_metadata(dlg, monkeypatch) -> None:
    from quill.ui.github_issue_draft_dialog import GitHubIssueDraft

    template = GitHubIssueTemplate(
        name="Bug report",
        filename="bug.md",
        title="[Bug] ",
        body="Template body",
        labels=("bug",),
        assignees=("alice",),
    )
    monkeypatch.setattr(dlg._provider, "fetch_issue_templates", lambda _repo: (template,))

    class _FakeDraftDialog:
        def __init__(self, _parent, selected_template, **_kwargs) -> None:
            assert selected_template is template

        def show(self):
            return GitHubIssueDraft("[Bug] edited", "Edited body", ("bug",), ("alice",))

    class _ChoiceDialog:
        def __init__(self, *_args, **_kwargs) -> None:
            return None

        def SetName(self, _name: str) -> None:
            return None

        def GetSelection(self) -> int:
            return 1

        def Destroy(self) -> None:
            return None

    monkeypatch.setattr(wx, "SingleChoiceDialog", _ChoiceDialog)
    monkeypatch.setattr(
        "quill.ui.github_issue_draft_dialog.GitHubIssueDraftDialog", _FakeDraftDialog
    )
    monkeypatch.setattr(
        "quill.ui.github_items_dialog_issue_templates.threading.Thread", _SyncThread
    )

    dlg._new_issue()

    assert dlg._provider.created_issues == [("owner/repo", "[Bug] edited", "Edited body")]
    assert dlg._provider.created_issue_options == [(("bug",), ("alice",))]


def test_new_pull_request_requires_head_and_base(dlg, monkeypatch: pytest.MonkeyPatch) -> None:
    # title, body, head="", base -> head blank should abort before creating.
    values = iter(["PR title", "body", ""])
    monkeypatch.setattr(wx, "TextEntryDialog", lambda *a, **k: _FakeTextEntry(next(values, "main")))
    dlg._new_pull_request()
    assert dlg._provider.created_pulls == []


def test_new_pull_request_creates_via_provider(dlg, monkeypatch: pytest.MonkeyPatch) -> None:
    values = iter(["PR title", "body", "feature", "main"])
    monkeypatch.setattr(wx, "TextEntryDialog", lambda *a, **k: _FakeTextEntry(next(values, "")))
    dlg._new_pull_request()
    assert dlg._provider.created_pulls == [("owner/repo", "PR title", "body", "feature", "main")]


# ---------------------------------------------------------------------------
# Merge
# ---------------------------------------------------------------------------


def test_merge_selected_pr_confirms_and_merges(dlg, monkeypatch: pytest.MonkeyPatch) -> None:
    pr = GitHubItem(number=5, title="Fix it", state="open", url="", is_pr=True, base_branch="main")
    dlg._rows = [pr]
    dlg._selected_indices = lambda: [0]
    monkeypatch.setattr(
        "quill.ui.github_repo_admin_dialogs.TypedConfirmDialog",
        lambda *a, **k: _FakeTypedConfirm(True),
    )
    dlg._merge_selected_pr()
    assert dlg._provider.merged == [("owner/repo", 5)]
    assert "Merged #5" in dlg.statuses[-1]


def test_merge_selected_pr_declined_confirmation(dlg, monkeypatch: pytest.MonkeyPatch) -> None:
    pr = GitHubItem(number=5, title="Fix it", state="open", url="", is_pr=True)
    dlg._rows = [pr]
    dlg._selected_indices = lambda: [0]
    monkeypatch.setattr(
        "quill.ui.github_repo_admin_dialogs.TypedConfirmDialog",
        lambda *a, **k: _FakeTypedConfirm(False),
    )
    dlg._merge_selected_pr()
    assert dlg._provider.merged == []


def test_merge_surfaces_provider_error(dlg, monkeypatch: pytest.MonkeyPatch) -> None:
    pr = GitHubItem(number=5, title="Fix it", state="open", url="", is_pr=True)
    dlg._rows = [pr]
    dlg._selected_indices = lambda: [0]
    dlg._provider.raise_on_merge = GitHubItemsError("not mergeable")
    monkeypatch.setattr(
        "quill.ui.github_repo_admin_dialogs.TypedConfirmDialog",
        lambda *a, **k: _FakeTypedConfirm(True),
    )
    dlg._merge_selected_pr()
    assert any("not mergeable" in s for s in dlg.statuses)


# ---------------------------------------------------------------------------
# Delete branch
# ---------------------------------------------------------------------------


def test_delete_selected_branch(dlg, monkeypatch: pytest.MonkeyPatch) -> None:
    from quill.core.github.items_provider import GitHubBranch

    branch = GitHubBranch(name="stale", commit_sha="abc")
    dlg._rows = [branch]
    dlg._selected_indices = lambda: [0]
    monkeypatch.setattr(
        "quill.ui.github_repo_admin_dialogs.TypedConfirmDialog",
        lambda *a, **k: _FakeTypedConfirm(True),
    )
    deleted: list[tuple[str, str]] = []
    monkeypatch.setattr(
        "quill.core.github.repo_admin.GitHubRepoAdminProvider",
        lambda token: _FakeRepoAdmin(deleted),
    )
    dlg._delete_selected_branch()
    assert deleted == [("owner/repo", "stale")]
    assert "Deleted branch stale" in dlg.statuses[-1]


# ---------------------------------------------------------------------------
# Re-run workflow
# ---------------------------------------------------------------------------


def test_rerun_selected_workflow(dlg) -> None:
    from quill.core.github.items_provider import GitHubWorkflowRun

    run = GitHubWorkflowRun(name="CI", status="completed", run_number=7, id=700)
    dlg._rows = [run]
    dlg._selected_indices = lambda: [0]
    dlg._confirm_action = lambda message, title: True
    dlg._rerun_selected_workflow()
    assert dlg._provider.reran == [("owner/repo", 700)]


def test_rerun_declined(dlg) -> None:
    from quill.core.github.items_provider import GitHubWorkflowRun

    run = GitHubWorkflowRun(name="CI", status="completed", run_number=7, id=700)
    dlg._rows = [run]
    dlg._selected_indices = lambda: [0]
    dlg._confirm_action = lambda message, title: False
    dlg._rerun_selected_workflow()
    assert dlg._provider.reran == []


# ---------------------------------------------------------------------------
# View Artifacts
# ---------------------------------------------------------------------------


def test_view_artifacts_opens_the_dialog_for_the_selected_run(
    dlg, monkeypatch: pytest.MonkeyPatch
) -> None:
    from quill.core.github.items_provider import GitHubWorkflowRun

    run = GitHubWorkflowRun(
        name="CI",
        status="completed",
        run_number=7,
        id=700,
        url="https://github.com/owner/repo/actions/runs/7",
    )
    dlg._rows = [run]
    dlg._selected_indices = lambda: [0]

    opened: list[dict] = []

    class _FakeArtifactsDialog:
        def __init__(self, parent, provider, **kwargs) -> None:
            opened.append(kwargs)

        def show(self) -> None:
            pass

    monkeypatch.setattr("quill.ui.github_artifacts_dialog.ArtifactsDialog", _FakeArtifactsDialog)
    dlg._view_artifacts_for_selected()

    assert opened == [
        {
            "repo": "owner/repo",
            "run_id": 700,
            "run_label": "#7 - CI",
            "run_url": "https://github.com/owner/repo/actions/runs/7",
            "announce_cb": dlg._announce,
        }
    ]


def test_view_artifacts_requires_a_selected_run(dlg, monkeypatch: pytest.MonkeyPatch) -> None:
    dlg._rows = []
    dlg._selected_indices = lambda: []

    opened: list[object] = []
    monkeypatch.setattr(
        "quill.ui.github_artifacts_dialog.ArtifactsDialog",
        lambda *a, **k: opened.append((a, k)),
    )
    dlg._view_artifacts_for_selected()
    assert opened == []


# ---------------------------------------------------------------------------
# Comment reply / edit / delete
# ---------------------------------------------------------------------------


def test_reply_to_thread(dlg, monkeypatch: pytest.MonkeyPatch) -> None:
    dlg._comment_target = ("owner/repo", 9)
    monkeypatch.setattr(wx, "TextEntryDialog", lambda *a, **k: _FakeTextEntry("thanks!"))
    dlg._reply_to_thread()
    assert dlg._provider.posted_comments == [("owner/repo", 9, "thanks!")]


def test_reply_without_a_loaded_thread(dlg) -> None:
    dlg._comment_target = None
    dlg._reply_to_thread()
    assert dlg._provider.posted_comments == []
    assert "Select an issue" in dlg.announcements[-1]


def test_edit_current_comment(dlg, monkeypatch: pytest.MonkeyPatch) -> None:
    dlg._comments = [{"id": "42", "author": "me", "body": "typo hree"}]
    dlg._current_comment = 0
    monkeypatch.setattr(wx, "TextEntryDialog", lambda *a, **k: _FakeTextEntry("typo here"))
    dlg._edit_current_comment()
    assert dlg._provider.edited_comments == [("owner/repo", 42, "typo here")]


def test_edit_without_a_navigated_comment(dlg) -> None:
    dlg._comments = []
    dlg._current_comment = -1
    dlg._edit_current_comment()
    assert dlg._provider.edited_comments == []
    assert "Navigate to a comment" in dlg.announcements[-1]


def test_delete_current_comment(dlg, monkeypatch: pytest.MonkeyPatch) -> None:
    dlg._comments = [{"id": "42", "author": "me", "body": "oops"}]
    dlg._current_comment = 0
    monkeypatch.setattr(
        "quill.ui.github_repo_admin_dialogs.TypedConfirmDialog",
        lambda *a, **k: _FakeTypedConfirm(True),
    )
    dlg._delete_current_comment()
    assert dlg._provider.deleted_comments == [("owner/repo", 42)]


def test_delete_current_comment_declined(dlg, monkeypatch: pytest.MonkeyPatch) -> None:
    dlg._comments = [{"id": "42", "author": "me", "body": "oops"}]
    dlg._current_comment = 0
    monkeypatch.setattr(
        "quill.ui.github_repo_admin_dialogs.TypedConfirmDialog",
        lambda *a, **k: _FakeTypedConfirm(False),
    )
    dlg._delete_current_comment()
    assert dlg._provider.deleted_comments == []


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class _FakeTextEntry:
    def __init__(self, value: str, *, ok: bool = True) -> None:
        self._value = value
        self._ok = ok

    def GetValue(self) -> str:
        return self._value

    def __enter__(self) -> _FakeTextEntry:
        return self

    def __exit__(self, *exc: object) -> None:
        return None


class _FakeTypedConfirm:
    def __init__(self, result: bool) -> None:
        self._result = result

    def show(self) -> bool:
        return self._result


class _FakeRepoAdmin:
    def __init__(self, sink: list[tuple[str, str]]) -> None:
        self._sink = sink

    def delete_branch(self, repo: str, branch: str) -> None:
        self._sink.append((repo, branch))

    def close(self) -> None:
        pass


# ---------------------------------------------------------------------------
# View Upstream (fork navigation)
# ---------------------------------------------------------------------------


def test_upstream_button_disabled_for_a_non_fork(dlg) -> None:
    dlg._provider.fork_info = GitHubRepoForkInfo(is_fork=False)
    dlg._fetch_fork_info_async("owner/repo")
    assert dlg._upstream_btn.IsEnabled() is False
    assert dlg._fork_info == GitHubRepoForkInfo(is_fork=False)


def test_upstream_button_enabled_for_a_fork_and_announces(dlg) -> None:
    dlg._provider.fork_info = GitHubRepoForkInfo(is_fork=True, parent_full_name="upstream/repo")
    dlg._fetch_fork_info_async("owner/repo")
    assert dlg._upstream_btn.IsEnabled() is True
    assert "fork of upstream/repo" in dlg.announcements[-1]


def test_upstream_button_stays_disabled_when_parent_unresolvable(dlg) -> None:
    dlg._provider.fork_info = GitHubRepoForkInfo(is_fork=True, parent_full_name="")
    dlg._fetch_fork_info_async("owner/repo")
    assert dlg._upstream_btn.IsEnabled() is False


def test_stale_fork_info_response_is_discarded_if_repo_changed(dlg) -> None:
    """The user can switch repos before an in-flight fork-info fetch returns
    -- its result must not clobber state for the repo now actually loaded."""
    dlg._provider.fork_info = GitHubRepoForkInfo(is_fork=True, parent_full_name="upstream/repo")
    dlg._on_fork_info_loaded("some-other/repo", dlg._provider.fork_info)
    assert dlg._upstream_btn.IsEnabled() is False
    assert dlg._fork_info is None


def test_view_upstream_click_reloads_with_parent_repo(dlg) -> None:
    dlg._fork_info = GitHubRepoForkInfo(is_fork=True, parent_full_name="upstream/repo")
    dlg._upstream_btn.Enable(True)
    loaded: list[str] = []
    dlg._on_load = lambda _e: loaded.append(dlg._repo_ctrl.GetValue())
    dlg._on_view_upstream(None)
    assert dlg._repo_ctrl.GetValue() == "upstream/repo"
    assert loaded == ["upstream/repo"]


def test_view_upstream_click_does_nothing_when_no_fork_info(dlg) -> None:
    dlg._fork_info = None
    loaded: list[str] = []
    dlg._on_load = lambda _e: loaded.append("called")
    dlg._on_view_upstream(None)
    assert loaded == []


# ---------------------------------------------------------------------------
# Release download counts: asset drill-down (Enter in, Backspace out)
# ---------------------------------------------------------------------------


def _release_with_assets() -> GitHubRelease:
    return GitHubRelease(
        tag="v2.0",
        name="Release 2.0",
        url="https://github.com/owner/repo/releases/tag/v2.0",
        assets=(
            GitHubReleaseAsset(
                name="big.exe",
                download_count=900,
                size_bytes=2 * 1024 * 1024,
                browser_download_url="https://example.com/big.exe",
            ),
            GitHubReleaseAsset(
                name="small.zip",
                download_count=100,
                size_bytes=1024,
                browser_download_url="https://example.com/small.zip",
            ),
        ),
    )


def _load_releases_into_list(dlg, releases: list[GitHubRelease]) -> None:
    dlg._view = VIEW_RELEASES
    dlg._drill_release = None
    dlg._rebuild_columns()
    dlg._rows = list(releases)
    dlg._unfiltered_rows = list(releases)
    dlg._populate_list()
    if releases:
        dlg._list.Select(0)
        dlg._list.Focus(0)


def test_enter_on_release_drills_into_assets_most_downloaded_first(dlg) -> None:
    release = _release_with_assets()
    _load_releases_into_list(dlg, [release])
    dlg._on_activate(None)  # Enter on the release row
    assert dlg._drill_release is release
    assert [a.name for a in dlg._rows] == ["big.exe", "small.zip"]
    assert dlg._current_columns() == RELEASE_ASSET_COLUMNS
    # Status line totals the release's downloads with the correctness caveat.
    assert "1000 total downloads" in dlg.statuses[-1]
    assert "unique people" in dlg.statuses[-1]


def test_enter_on_asset_opens_browser_download_url(dlg, monkeypatch: pytest.MonkeyPatch) -> None:
    opened: list[str] = []
    monkeypatch.setattr(
        "quill.ui.github_items_dialog.webbrowser.open", lambda url: opened.append(url)
    )
    release = _release_with_assets()
    _load_releases_into_list(dlg, [release])
    dlg._on_activate(None)  # drill in; row 0 (big.exe) is selected
    dlg._on_activate(None)  # Enter on the most-downloaded asset
    assert opened == ["https://example.com/big.exe"]


def test_backspace_in_asset_drill_returns_to_releases(dlg) -> None:
    reloaded: list[bool] = []
    dlg._reload = lambda: reloaded.append(True)
    release = _release_with_assets()
    _load_releases_into_list(dlg, [release])
    dlg._on_activate(None)  # drill in
    assert dlg._drill_release is release

    class _Key:
        def GetKeyCode(self) -> int:
            return wx.WXK_BACK

        def Skip(self) -> None:
            pass

    dlg._on_list_key(_Key())
    assert reloaded == [True]  # stepped back out via a reload of the releases list


def test_clear_list_resets_asset_drill(dlg) -> None:
    release = _release_with_assets()
    _load_releases_into_list(dlg, [release])
    dlg._on_activate(None)
    assert dlg._drill_release is release
    dlg._clear_list()
    assert dlg._drill_release is None


def test_release_with_no_assets_announces_and_does_not_drill_open(dlg) -> None:
    release = GitHubRelease(tag="v1.0", name="Release 1.0")
    _load_releases_into_list(dlg, [release])
    dlg._on_activate(None)
    assert dlg._drill_release is release
    assert dlg._rows == []
    assert "no downloadable assets" in dlg.announcements[-1]
