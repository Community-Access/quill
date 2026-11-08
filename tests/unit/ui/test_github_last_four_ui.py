"""The last four GitHub features in the shared dialogs: Request Copilot Review,
Assign to Copilot, Commit Comments, gist editing in Explore, and the attention
queue's summaries in the status line."""

from __future__ import annotations

from typing import Any

import pytest
import wx

from quill.core.github.commit_comments import CommitComment
from quill.core.github.copilot import CopilotAssignment
from quill.core.github.explore_models import ExploreRow
from quill.core.github.fetch_results import GitHubFetchResult
from quill.core.github.gists import Gist, GistDraft, GistFile
from quill.core.github.items_errors import GitHubItemsError
from quill.core.github.items_provider import GitHubCommit, GitHubItem
from quill.ui import github_commit_comments_dialog, github_gist_editor_dialog
from quill.ui.github_commit_comments_dialog import GitHubCommitCommentsDialog
from quill.ui.github_explore_dialog import GitHubExploreDialog
from quill.ui.github_gist_editor_dialog import GitHubGistEditorDialog
from quill.ui.github_items_dialog import GitHubItemsDialog
from quill.ui.github_items_view import VIEW_COMMITS, VIEW_ISSUES
from quill.ui.github_pr_review_copilot import GitHubPullReviewCopilotMixin
from quill.ui.github_pr_review_dialog import GitHubPullReviewDialog
from tests.wx_session import patch_call_after, shared_wx_app


class _SyncThread:
    def __init__(self, target=None, args=(), kwargs=None, daemon=None, **_kw) -> None:
        self._target, self._args, self._kwargs = target, args, kwargs or {}

    def start(self) -> None:
        self._target(*self._args, **self._kwargs)


class _Provider:
    """A signed-in provider whose answers a test sets; records every call."""

    is_authenticated = True
    token = "tok"
    _gh = None

    def __init__(self) -> None:
        self.calls: list[tuple[Any, ...]] = []
        self.answers: dict[str, Any] = {}

    def __getattr__(self, name: str) -> Any:
        if name.startswith("__"):
            raise AttributeError(name)

        def call(*args: Any, **kwargs: Any) -> Any:
            self.calls.append((name, *args))
            answer = self.answers.get(name)
            if isinstance(answer, BaseException):
                raise answer
            return answer(*args, **kwargs) if callable(answer) else answer

        return call


ISSUE = GitHubItem(3, "Broken", "open", "https://github.com/o/r/issues/3", False)
PULL = GitHubItem(4, "Fix", "open", "https://github.com/o/r/pull/4", True)
COMMIT = GitHubCommit("abcdef1234567890", "abcdef1", "Fix it")


# -- Request Copilot Review ------------------------------------------------------------


class _ReviewHost(GitHubPullReviewCopilotMixin):
    def __init__(self, provider: _Provider, can_write: bool = True) -> None:
        self._client = type("C", (), {"can_write": can_write, "_provider": provider})()
        self._repo, self._number = "o/r", 4
        self._reviewers_btn = type("B", (), {"IsEnabled": lambda _self: can_write})()
        self.spoken: list[str] = []
        self._announce = self.spoken.append

    def _run_action(self, action, success: str) -> None:
        try:
            self.spoken.append(success + (action() or ""))
        except GitHubItemsError as exc:
            self.spoken.append(f"Review action failed: {exc}")


def test_review_window_carries_the_copilot_mixin() -> None:
    assert GitHubPullReviewCopilotMixin in GitHubPullReviewDialog.__mro__


def test_request_copilot_review_says_what_github_confirmed() -> None:
    provider = _Provider()
    provider.answers["request_copilot_review"] = "Copilot review requested on pull request #4."
    host = _ReviewHost(provider)
    labels: list[tuple[str, bool]] = []
    host._append_copilot_entries(lambda label, _h, *, enabled: labels.append((label, enabled)))
    assert labels == [("Request Copilot Review", True)]
    host._request_copilot_review(None)
    assert provider.calls == [("request_copilot_review", "o/r", 4)]
    assert host.spoken == ["Copilot review requested on pull request #4."]


def test_request_copilot_review_refusal_is_said() -> None:
    provider = _Provider()
    provider.answers["request_copilot_review"] = GitHubItemsError("not available to your account")
    host = _ReviewHost(provider)
    host._request_copilot_review(None)
    assert "not available to your account" in host.spoken[-1]


def test_request_copilot_review_needs_an_account() -> None:
    provider = _Provider()
    host = _ReviewHost(provider, can_write=False)
    host._request_copilot_review(None)
    assert provider.calls == [] and "Sign in" in host.spoken[-1]


# -- GitHub Items: Assign to Copilot and Commit Comments -------------------------------


@pytest.fixture
def items(monkeypatch: pytest.MonkeyPatch):
    shared_wx_app()
    monkeypatch.setattr("quill.ui.github_items_dialog_housekeeping.threading.Thread", _SyncThread)
    patch_call_after(monkeypatch, lambda fn, *a, **k: fn(*a, **k))
    frame = wx.Frame(None)
    provider = _Provider()
    dialog = GitHubItemsDialog(frame, provider, initial_repo="o/r")
    dialog._repo = "o/r"
    dialog._view = VIEW_ISSUES
    dialog.statuses = []
    dialog.modals = []
    dialog._set_status = lambda message, **_kw: dialog.statuses.append(message)
    dialog._announce = lambda message: dialog.statuses.append(message)
    dialog._reload = lambda: dialog.statuses.append("reloaded")
    dialog.answer = wx.ID_YES

    def show_modal(modal: Any, title: str) -> int:
        dialog.modals.append((title, modal.GetMessage()))
        return dialog.answer

    dialog._show_modal = show_modal
    yield dialog, provider
    dialog.dialog.Destroy()
    frame.Destroy()


def _menu_labels(dialog: GitHubItemsDialog, model: object) -> list[str]:
    labels: list[str] = []
    dialog._add_copilot_and_commit_actions(lambda label, _action: labels.append(label), model)
    return labels


def test_assign_to_copilot_is_offered_on_issues_only(items) -> None:
    dialog, _provider = items
    assert _menu_labels(dialog, ISSUE) == ["Assign #3 to Copilot..."]
    assert _menu_labels(dialog, PULL) == []
    assert _menu_labels(dialog, COMMIT) == ["Commit Comments..."]


def _ready() -> CopilotAssignment:
    return CopilotAssignment("o/r", 3, True, "BOT", "I_3", "OPEN", ("U_bob",), ("bob",))


def test_assign_to_copilot_checks_asks_then_assigns(items) -> None:
    dialog, provider = items
    provider.answers["check_copilot_assignment"] = _ready()
    provider.answers["assign_issue_to_copilot"] = "Issue #3 assigned to Copilot."
    dialog._assign_to_copilot(ISSUE)
    assert dialog.modals[0][0] == "Assign to Copilot"
    assert "bob stay assigned too" in dialog.modals[0][1]
    assert [call[0] for call in provider.calls] == [
        "check_copilot_assignment",
        "assign_issue_to_copilot",
    ]
    assert dialog.statuses[-2:] == ["Issue #3 assigned to Copilot.", "reloaded"]


def test_assign_to_copilot_cancelled_sends_nothing(items) -> None:
    dialog, provider = items
    provider.answers["check_copilot_assignment"] = _ready()
    dialog.answer = wx.ID_NO
    dialog._assign_to_copilot(ISSUE)
    assert [call[0] for call in provider.calls] == ["check_copilot_assignment"]
    assert dialog.statuses[-1] == "Cancelled; nothing was sent to GitHub."


def test_assign_to_copilot_unavailable_explains_and_sends_nothing(items) -> None:
    dialog, provider = items
    provider.answers["check_copilot_assignment"] = CopilotAssignment("o/r", 3, False)
    dialog.answer = wx.ID_OK
    dialog._assign_to_copilot(ISSUE)
    assert "not available for o/r" in dialog.modals[0][1]
    assert [call[0] for call in provider.calls] == ["check_copilot_assignment"]


def test_assign_to_copilot_check_failure_is_said(items) -> None:
    dialog, provider = items
    provider.answers["check_copilot_assignment"] = GitHubItemsError("Could not check. Denied.")
    dialog._assign_to_copilot(ISSUE)
    assert dialog.statuses[-1] == "Could not check. Denied."
    assert dialog.modals == []


def test_commit_comments_open_from_a_commit_row(items, monkeypatch) -> None:
    dialog, provider = items
    dialog._view = VIEW_COMMITS
    opened: list[tuple[str, str]] = []

    class Fake:
        def __init__(self, _parent, _provider, repo, sha, **_kw) -> None:
            opened.append((repo, sha))

        def show(self) -> None:
            pass

    monkeypatch.setattr(github_commit_comments_dialog, "GitHubCommitCommentsDialog", Fake)
    dialog._open_commit_comments(COMMIT)
    assert opened == [("o/r", "abcdef1234567890")]


# -- The Commit Comments window --------------------------------------------------------


@pytest.fixture
def comments(monkeypatch: pytest.MonkeyPatch):
    shared_wx_app()
    monkeypatch.setattr(github_commit_comments_dialog.threading, "Thread", _SyncThread)
    patch_call_after(monkeypatch, lambda fn, *a, **k: fn(*a, **k))
    frame = wx.Frame(None)
    provider = _Provider()
    spoken: list[str] = []
    provider.answers["fetch_commit_comments"] = GitHubFetchResult((
        CommitComment(1, "octocat", "2026-11-07T10:00:00Z", "Nice"),
    ))
    window = GitHubCommitCommentsDialog(
        frame, provider, "o/r", "abcdef1234567890", announce_cb=spoken.append
    )
    yield window, provider, spoken
    window.dialog.Destroy()
    frame.Destroy()


def test_comments_list_reads_author_date_and_text(comments) -> None:
    window, _provider, spoken = comments
    window._load()
    assert window._list.GetStrings() == ["octocat, 2026-11-07: Nice"]
    assert "Author: octocat" in window._detail.GetValue()
    assert spoken[-1] == "1 comment on this commit."


def test_post_on_a_line_then_reloads(comments) -> None:
    window, provider, spoken = comments
    provider.answers["add_commit_comment"] = CommitComment(
        2, "me", "2026-11-07", "Why?", path="a.py", line=3
    )
    window._body.SetValue("Why?")
    window._path.SetValue("a.py")
    window._line.SetValue("3")
    window._post(None)
    assert ("add_commit_comment", "o/r", "abcdef1234567890", "Why?") in provider.calls
    assert "Comment posted on a.py line 3." in spoken
    assert window._body.GetValue() == ""


def test_post_refuses_a_line_without_a_file(comments) -> None:
    window, provider, spoken = comments
    window._body.SetValue("x")
    window._line.SetValue("3")
    window._post(None)
    assert spoken[-1] == "Name the file the line is in, or clear the line."
    assert not any(call[0] == "add_commit_comment" for call in provider.calls)


def test_post_failure_is_said_not_claimed(comments) -> None:
    window, provider, spoken = comments
    provider.answers["add_commit_comment"] = GitHubItemsError("Could not comment. Denied.")
    window._body.SetValue("x")
    window._post(None)
    assert spoken[-1] == "Could not comment. Denied."
    assert window._body.GetValue() == "x"


def test_a_stale_comment_list_is_dropped(comments) -> None:
    window, _provider, _spoken = comments
    window._generation = 5
    window._loaded(4, GitHubFetchResult(()))
    assert window._list.GetStrings() == []


# -- Gists in Explore ------------------------------------------------------------------


GIST_ROW = ExploreRow(
    "Notes (secret)", "Gist: Notes", "https://gist.github.com/g1", kind="gist", key="g1"
)


@pytest.fixture
def explore(monkeypatch: pytest.MonkeyPatch):
    shared_wx_app()
    for module in ("github_explore_dialog", "github_explore_gists"):
        monkeypatch.setattr(f"quill.ui.{module}.threading.Thread", _SyncThread)
    patch_call_after(monkeypatch, lambda fn, *a, **k: fn(*a, **k))
    frame = wx.Frame(None)
    provider = _Provider()
    dialog = GitHubExploreDialog(
        frame, provider, initial_view="gists", gist_source_cb=lambda: ("doc.md", "# Hi")
    )
    dialog.spoken = []
    dialog.questions = []
    dialog._announce = dialog.spoken.append
    dialog._load = lambda _event: dialog.spoken.append("reloaded")
    dialog.answer = True

    def confirm(message: str, title: str) -> bool:
        dialog.questions.append((title, message))
        return dialog.answer

    dialog._confirm = confirm
    yield dialog
    dialog.dialog.Destroy()
    frame.Destroy()


class _Editor:
    """Stands in for the gist editor: records its draft and applies an edit."""

    seen: list[tuple[GistDraft, bool]] = []
    edit: Any = None
    accept = True

    def __init__(self, _parent, draft: GistDraft, *, creating: bool, **_kw) -> None:
        self.draft, self.public = draft, False
        _Editor.seen.append((draft, creating))

    def show(self) -> bool:
        if _Editor.edit is not None:
            _Editor.edit(self)
        return _Editor.accept


@pytest.fixture
def editor(monkeypatch: pytest.MonkeyPatch):
    _Editor.seen, _Editor.edit, _Editor.accept = [], None, True
    monkeypatch.setattr(github_gist_editor_dialog, "GitHubGistEditorDialog", _Editor)
    return _Editor


def _gist_labels(dialog: GitHubExploreDialog, row: ExploreRow | None) -> list[str]:
    labels: list[str] = []
    dialog._add_gist_actions(lambda label, _action: labels.append(label), row)
    return labels


def test_gist_actions_are_offered_on_gist_rows_and_the_view(explore) -> None:
    assert _gist_labels(explore, GIST_ROW) == [
        "Edit Gist...",
        "Star Gist",
        "Unstar Gist",
        "Delete Gist...",
        "New Gist...",
    ]


def test_new_gist_starts_from_the_document_and_creates_it(explore, editor) -> None:
    explore._client.create_gist = lambda draft, *, public: explore.spoken.append(
        f"create {sorted(draft.files)} public={public}"
    )

    def make_public(window: _Editor) -> None:
        window.public = True

    editor.edit = make_public
    explore._new_gist()
    draft, creating = editor.seen[0]
    assert creating and draft.files == {"doc.md": "# Hi"}
    assert "create ['doc.md'] public=True" in explore.spoken
    assert "Created the public gist with 1 file." in explore.spoken


def test_edit_gist_reads_edits_and_says_what_saved(explore, editor) -> None:
    gist = Gist("g1", "Notes", False, "", (GistFile("a.md", "A"), GistFile("b.md", "B")))
    explore._client.fetch_gist = lambda gist_id: gist
    sent: list[dict[str, object]] = []
    explore._client.update_gist = lambda gist_id, draft: sent.append(draft.changes())
    editor.edit = lambda window: window.draft.delete_file("b.md")
    explore._edit_gist(GIST_ROW)
    assert sent == [{"files": {"b.md": None}}]
    assert explore.spoken[-2:] == ["Gist saved. GitHub confirmed: delete b.md.", "reloaded"]


def test_edit_gist_with_no_changes_sends_nothing(explore, editor) -> None:
    explore._client.fetch_gist = lambda gist_id: Gist("g1", "", False, "", (GistFile("a", "A"),))
    explore._client.update_gist = lambda *_a: pytest.fail("nothing should be sent")
    explore._edit_gist(GIST_ROW)
    assert explore.spoken[-1] == "No changes to save; nothing was sent to GitHub."


def test_a_stale_gist_read_opens_no_editor(explore, editor) -> None:
    explore._gist_read_token = 3
    explore._gist_read(2, "g1", Gist("g1"))
    assert editor.seen == []


def test_delete_gist_asks_first(explore) -> None:
    deleted: list[str] = []
    explore._client.delete_gist = deleted.append
    explore.answer = False
    explore._delete_gist(GIST_ROW)
    assert deleted == [] and explore.questions[0][0] == "Delete Gist"
    explore.answer = True
    explore._delete_gist(GIST_ROW)
    assert deleted == ["g1"]
    assert "Deleted the gist Notes (secret)." in explore.spoken


def test_star_failure_is_said_and_not_claimed(explore) -> None:
    def refuse(_gist_id: str, _starred: bool) -> None:
        raise GitHubItemsError("Could not star the gist. Denied.")

    explore._client.set_gist_starred = refuse
    explore._star_gist(GIST_ROW, True)
    assert explore.spoken[-1].startswith("Action failed:")
    assert explore.spoken[-1].endswith("Could not star the gist. Denied.")


# -- The gist editor window ------------------------------------------------------------


@pytest.fixture
def gist_window(monkeypatch: pytest.MonkeyPatch):
    shared_wx_app()
    frame = wx.Frame(None)
    said: list[str] = []
    gist = Gist("g1", "Notes", False, "", (GistFile("a.md", "A"), GistFile("b.md", "B")))
    window = GitHubGistEditorDialog(frame, GistDraft.from_gist(gist), creating=False)
    window._say = said.append
    yield window, said, monkeypatch
    window.dialog.Destroy()
    frame.Destroy()


def test_editor_keeps_text_edits_and_renames(gist_window) -> None:
    window, _said, _mp = gist_window
    assert window._files.GetStrings() == ["a.md", "b.md"]
    window._text.SetValue("A changed")
    window._prompt = lambda *_a, **_k: "intro.md"
    window._rename_file(None)
    assert window.draft.names() == ["intro.md", "b.md"]
    assert window.draft.files["intro.md"] == "A changed"


def test_editor_delete_asks_and_refuses_the_last_file(gist_window) -> None:
    window, said, monkeypatch = gist_window
    answers = iter([wx.ID_YES, wx.ID_YES])
    monkeypatch.setattr(
        github_gist_editor_dialog, "show_modal_dialog", lambda *_a, **_k: next(answers)
    )
    window._delete_file(None)
    assert window.draft.names() == ["b.md"]
    assert not window._delete_btn.IsEnabled()
    window._delete_file(None)
    assert "at least one file" in said[-1]


def test_editor_refuses_an_empty_file_on_save(gist_window) -> None:
    window, said, _mp = gist_window
    window._text.SetValue("   ")
    window._on_ok(None)
    assert "is empty" in said[-1]


# -- Attention queue status --------------------------------------------------------------


def test_queue_status_says_the_summary_note(explore) -> None:
    explore._view.SetSelection(0)
    result = GitHubFetchResult(
        (ExploreRow("o/r #1: T (PR). Approved, no checks, no open threads", "Review requested"),),
        warning="GitHub did not summarise 1 pull request",
    )
    explore._loaded(explore._load_token, result, "", None, "search")
    assert explore._status.GetLabel().endswith("GitHub did not summarise 1 pull request.")
