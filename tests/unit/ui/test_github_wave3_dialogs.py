"""Wave 3 surfaces: repository files, blame and history runs, milestones, batch
milestone and assignees, discussion threads, and alert triage in Explore."""

from __future__ import annotations

from typing import Any

import pytest
import wx

from quill.core.github.alert_triage import alert_row
from quill.core.github.discussion_actions import parse_discussion_thread
from quill.core.github.explore import ExploreRow
from quill.core.github.items_errors import GitHubItemsError
from quill.core.github.items_provider import GitHubItem
from quill.core.github.milestones import GitHubMilestone
from quill.core.github.notifications import GitHubSecurityAlert
from quill.core.github.repo_files import BlameRun, RepoEntry
from tests.wx_session import patch_call_after, shared_wx_app


class _SyncThread:
    def __init__(self, target=None, args=(), kwargs=None, daemon=None, **_kw) -> None:
        self._target, self._args, self._kwargs = target, args, kwargs or {}

    def start(self) -> None:
        self._target(*self._args, **self._kwargs)


_MODULES = (
    "quill.ui.github_repo_files_dialog",
    "quill.ui.github_file_runs_dialog",
    "quill.ui.github_milestones_dialog",
    "quill.ui.github_items_dialog_repository",
    "quill.ui.github_discussion_dialog",
    "quill.ui.github_explore_community",
    "quill.ui.github_explore_dialog",
)


@pytest.fixture
def frame(monkeypatch: pytest.MonkeyPatch):
    shared_wx_app()
    for module in _MODULES:
        monkeypatch.setattr(f"{module}.threading.Thread", _SyncThread)
    patch_call_after(monkeypatch)
    window = wx.Frame(None)
    yield window
    window.Destroy()


class _Provider:
    is_authenticated = True
    token = "tok"

    def __init__(self) -> None:
        self.calls: list[tuple[Any, ...]] = []
        self.fail: str = ""

    def _check(self) -> None:
        if self.fail:
            raise GitHubItemsError(self.fail)

    # files
    def fetch_default_branch(self, repo: str) -> str:
        return "main"

    def fetch_ref_names(self, repo: str) -> list[str]:
        return ["main", "v1.0"]

    def fetch_repo_folder(self, repo: str, ref: str, path: str = "") -> list[RepoEntry]:
        self.calls.append(("folder", ref, path))
        if path == "":
            return [RepoEntry("docs", "docs", "dir"), RepoEntry("a.py", "a.py", "file", 12)]
        return [RepoEntry("guide.md", "docs/guide.md", "file", 3)]

    def fetch_repo_file_text(self, repo: str, path: str, ref: str) -> str:
        self._check()
        self.calls.append(("file", path, ref))
        return "one\ntwo\n"

    def fetch_readme(self, repo: str, ref: str, folder: str = "") -> tuple[str, str]:
        self.calls.append(("readme", folder))
        return f"{folder}/README.md".lstrip("/"), "# Hello"

    def fetch_blame(self, repo: str, ref: str, path: str) -> list[BlameRun]:
        return [
            BlameRun(1, 4, "a" * 40, "First", "Jeff", "2026-11-01", "https://x/a"),
            BlameRun(5, 9, "b" * 40, "Second", "Kelly", "2026-11-02", "https://x/b"),
        ]

    # milestones
    def fetch_milestones(self, repo: str, *, state: str = "open") -> list[GitHubMilestone]:
        self.calls.append(("milestones", state))
        return [GitHubMilestone(3, "Release 2.0", open_issues=5, closed_issues=8)]

    def update_milestone(self, repo: str, number: int, **kwargs: Any) -> GitHubMilestone:
        self._check()
        self.calls.append(("update", number, kwargs))
        return GitHubMilestone(3, "Release 2.0", state=kwargs.get("state") or "open")

    def assign_milestone(self, repo: str, numbers: list[int], milestone: int | None) -> list[str]:
        self.calls.append(("assign_milestone", list(numbers), milestone))
        return []

    def add_assignees(self, repo: str, numbers: list[int], logins: list[str]) -> list[str]:
        self.calls.append(("add_assignees", list(numbers), list(logins)))
        return ["#2: GitHub did not assign kelly"]

    # discussions and alerts
    def fetch_discussion_thread(self, repo: str, number: int):
        from tests.unit.core.test_github_discussion_actions import THREAD

        return parse_discussion_thread(THREAD, number)

    def reply_to_discussion(self, discussion_id: str, body: str, *, reply_to: str = "") -> str:
        self._check()
        self.calls.append(("reply", discussion_id, body, reply_to))
        return "u"

    def set_discussion_answer(self, comment_id: str, *, answer: bool) -> None:
        self.calls.append(("answer", comment_id, answer))

    def set_security_alert_state(self, repo, kind, number, **kwargs) -> str:
        self._check()
        self.calls.append(("alert", repo, kind, number, kwargs))
        return "dismissed"


def _modal(monkeypatch: pytest.MonkeyPatch, module: str, answers: list[int]) -> list[str]:
    titles: list[str] = []

    def fake(dialog: object, title: str, **_kw: object) -> int:
        titles.append(title)
        return answers.pop(0) if answers else wx.ID_CANCEL

    monkeypatch.setattr(f"{module}.show_modal_dialog", fake)
    return titles


# -- repository files --------------------------------------------------------


def _files_dialog(frame: wx.Frame, provider: _Provider, opened: list[str]):
    from quill.ui.github_repo_files_dialog import GitHubRepoFilesDialog

    dialog = GitHubRepoFilesDialog(frame, provider, repo="o/r", open_in_editor_cb=opened.append)
    dialog.spoken = []
    dialog._announce = dialog.spoken.append
    dialog._start()
    return dialog


def _child(dialog, label_start: str):
    tree = dialog._tree
    item, cookie = tree.GetFirstChild(tree.GetRootItem())
    while item.IsOk():
        if tree.GetItemText(item).startswith(label_start):
            return item
        item, cookie = tree.GetNextChild(tree.GetRootItem(), cookie)
    raise AssertionError(label_start)


def test_files_load_the_default_branch_and_expand_folders_on_demand(frame) -> None:
    provider = _Provider()
    dialog = _files_dialog(frame, provider, [])
    try:
        assert dialog._ref_ctrl.GetValue() == "main"
        folder = _child(dialog, "docs")
        assert dialog._tree.GetItemText(dialog._tree.GetFirstChild(folder)[0]) == "Loading..."
        dialog._tree.Expand(folder)
        dialog._load_folder(folder, "docs", dialog._token)
        assert ("folder", "main", "docs") in provider.calls
        assert dialog._tree.GetItemText(dialog._tree.GetFirstChild(folder)[0]) == (
            "guide.md, 3 bytes"
        )
        assert "2 items in main." in dialog.spoken
    finally:
        dialog.dialog.Destroy()


def test_a_folder_that_lands_after_a_reload_is_dropped(frame) -> None:
    provider = _Provider()
    dialog = _files_dialog(frame, provider, [])
    try:
        folder = _child(dialog, "docs")
        stale = dialog._token
        dialog._token += 1
        dialog._load_folder(folder, "docs", stale)
        assert dialog._tree.GetItemText(dialog._tree.GetFirstChild(folder)[0]) == "Loading..."
    finally:
        dialog.dialog.Destroy()


def test_view_file_readme_and_open_in_editor(frame) -> None:
    provider = _Provider()
    opened: list[str] = []
    dialog = _files_dialog(frame, provider, opened)
    try:
        dialog._tree.SelectItem(_child(dialog, "a.py"))
        dialog._view_file()
        assert dialog._contents.GetValue() == "one\ntwo\n"
        assert "a.py: 2 lines in Contents." in dialog.spoken
        dialog._show_readme()
        assert ("readme", "") in provider.calls
        assert dialog._contents.GetValue() == "# Hello"
        dialog._open_file_in_editor()
        assert opened == ["https://github.com/o/r/blob/main/a.py"]
    finally:
        dialog.dialog.Destroy()


def test_a_file_that_cannot_be_read_says_why(frame) -> None:
    provider = _Provider()
    dialog = _files_dialog(frame, provider, [])
    try:
        provider.fail = "a.py is a binary file, so there is no text to show."
        dialog._tree.SelectItem(_child(dialog, "a.py"))
        dialog._view_file()
        assert dialog.spoken[-1].endswith("no text to show.")
        assert dialog._edit_btn.IsEnabled()
    finally:
        dialog.dialog.Destroy()


def test_open_in_editor_is_off_without_a_callback(frame) -> None:
    from quill.ui.github_repo_files_dialog import GitHubRepoFilesDialog

    dialog = GitHubRepoFilesDialog(frame, _Provider(), repo="o/r")
    try:
        dialog._start()
        dialog._tree.SelectItem(_child(dialog, "a.py"))
        dialog._update_buttons()
        assert not dialog._edit_btn.IsEnabled()
        assert dialog._view_btn.IsEnabled()
    finally:
        dialog.dialog.Destroy()


# -- blame and history runs --------------------------------------------------


def test_runs_move_with_alt_n_and_alt_p_and_enter_opens_the_commit(
    frame, monkeypatch: pytest.MonkeyPatch
) -> None:
    from quill.ui.github_file_runs_dialog import FileRun, GitHubFileRunsDialog

    opened: list[str] = []
    monkeypatch.setattr("quill.ui.github_file_runs_dialog.webbrowser.open", opened.append)
    rows = [FileRun("Lines 1 to 4: Jeff", "d1", "u1"), FileRun("Lines 5 to 9: Kelly", "d2", "u2")]
    dialog = GitHubFileRunsDialog(frame, title="Blame for a.py", noun="runs", load=lambda: rows)
    spoken: list[str] = []
    dialog._announce = spoken.append
    try:
        dialog._load()
        assert dialog._list.GetSelection() == 0
        assert spoken == ["2 runs."]
        dialog.move(1)
        assert dialog._detail.GetValue() == "d2"
        dialog.move(1)
        assert spoken[-1] == "Last one."
        dialog.move(-1)
        assert dialog._list.GetSelection() == 0
        dialog._open_commit()
        assert opened == ["u1"]
    finally:
        dialog.dialog.Destroy()


def test_runs_load_failure_is_spoken(frame) -> None:
    from quill.ui.github_file_runs_dialog import GitHubFileRunsDialog

    def fail() -> list[object]:
        raise GitHubItemsError("To read the blame you need a signed-in GitHub account")

    dialog = GitHubFileRunsDialog(frame, title="Blame", noun="runs", load=fail)
    spoken: list[str] = []
    dialog._announce = spoken.append
    try:
        dialog._load()
        assert spoken[0].startswith("Could not load the runs:")
    finally:
        dialog.dialog.Destroy()


def test_blame_rows_from_the_files_dialog(frame, monkeypatch: pytest.MonkeyPatch) -> None:
    provider = _Provider()
    dialog = _files_dialog(frame, provider, [])
    captured: dict[str, Any] = {}

    class _Runs:
        def __init__(self, parent, *, title, noun, load, announce_cb=None) -> None:
            captured.update(title=title, rows=list(load()))

        def show(self) -> None:
            pass

    monkeypatch.setattr("quill.ui.github_repo_files_dialog.GitHubFileRunsDialog", _Runs)
    try:
        dialog._tree.SelectItem(_child(dialog, "a.py"))
        dialog._show_blame()
        assert captured["title"] == "Blame for a.py"
        assert captured["rows"][1].label.startswith("Lines 5 to 9: Kelly, ")
        assert captured["rows"][1].url == "https://x/b"
    finally:
        dialog.dialog.Destroy()


# -- milestones ---------------------------------------------------------------


def test_milestones_list_in_words_and_close_asks_first(
    frame, monkeypatch: pytest.MonkeyPatch
) -> None:
    from quill.ui.github_milestones_dialog import GitHubMilestonesDialog

    provider = _Provider()
    titles = _modal(monkeypatch, "quill.ui.github_milestones_dialog", [wx.ID_YES])
    dialog = GitHubMilestonesDialog(frame, provider, repo="o/r")
    spoken: list[str] = []
    dialog._announce = spoken.append
    try:
        dialog._load()
        assert dialog._list.GetString(0).startswith(
            "Release 2.0: 61 percent done, 5 open, 8 closed, no due date"
        )
        dialog._toggle_state()
        assert titles == ["Close Milestone"]
        assert ("update", 3, {"state": "closed"}) in provider.calls
        assert spoken[-1] == "Closed milestone Release 2.0. 1 milestone."
    finally:
        dialog.dialog.Destroy()


def test_milestone_close_cancelled_sends_nothing(frame, monkeypatch: pytest.MonkeyPatch) -> None:
    from quill.ui.github_milestones_dialog import GitHubMilestonesDialog

    provider = _Provider()
    _modal(monkeypatch, "quill.ui.github_milestones_dialog", [wx.ID_NO])
    dialog = GitHubMilestonesDialog(frame, provider, repo="o/r")
    dialog._announce = lambda _m: None
    try:
        dialog._load()
        dialog._toggle_state()
        assert not [call for call in provider.calls if call[0] == "update"]
    finally:
        dialog.dialog.Destroy()


def test_milestone_write_failure_is_shown(frame, monkeypatch: pytest.MonkeyPatch) -> None:
    from quill.ui.github_milestones_dialog import GitHubMilestonesDialog

    provider = _Provider()
    _modal(monkeypatch, "quill.ui.github_milestones_dialog", [wx.ID_YES])
    dialog = GitHubMilestonesDialog(frame, provider, repo="o/r")
    spoken: list[str] = []
    dialog._announce = spoken.append
    try:
        dialog._load()
        provider.fail = "Could not close the milestone. Access denied."
        dialog._toggle_state()
        assert spoken[-1].endswith("Access denied.")
        assert dialog._status.GetLabel().endswith("Access denied.")
    finally:
        dialog.dialog.Destroy()


# -- batch milestone and assignees in GitHub Items ---------------------------


@pytest.fixture
def items(frame, monkeypatch: pytest.MonkeyPatch):
    from quill.ui.github_items_dialog import GitHubItemsDialog
    from quill.ui.github_items_view import VIEW_ISSUES

    dialog = GitHubItemsDialog(frame, _Provider(), initial_repo="o/r")
    dialog._repo = "o/r"
    dialog._view = VIEW_ISSUES
    dialog._rows = [
        GitHubItem(number=n, title=t, state="open", url="", is_pr=False)
        for n, t in ((1, "a"), (2, "b"))
    ]
    dialog.statuses = []
    dialog.questions = []
    dialog._set_status = lambda message, **_kw: dialog.statuses.append(message)
    dialog._announce = lambda message: dialog.statuses.append(message)
    dialog._reload = lambda: dialog.statuses.append("reloaded")
    dialog._show_modal = lambda _dlg, _title: wx.ID_OK

    def confirm(message: str, title: str) -> bool:
        dialog.questions.append(message)
        return True

    dialog._confirm_action = confirm
    yield dialog
    dialog.dialog.Destroy()


def test_batch_set_milestone_confirms_the_items_then_counts(items) -> None:
    items._batch_set_milestone([1, 2])
    assert ("assign_milestone", [1, 2], 3) in items._provider.calls
    assert "Set milestone 'Release 2.0' on 2 item(s) in o/r?" in items.questions[0]
    assert "#1, #2" in items.questions[0]
    assert "Batch change applied to 2 of 2 item(s)." in items.statuses


def test_batch_assignees_report_what_github_skipped(items, monkeypatch) -> None:
    monkeypatch.setattr(wx.TextEntryDialog, "GetValue", lambda self: "jeff, kelly")
    items._batch_add_assignees([1, 2])
    assert ("add_assignees", [1, 2], ["jeff", "kelly"]) in items._provider.calls
    assert any("1 of 2" in status and "did not assign kelly" in status for status in items.statuses)


def test_batch_cancel_sends_nothing(items) -> None:
    items._confirm_action = lambda *_a: False
    items._batch_set_milestone([1])
    assert not [call for call in items._provider.calls if call[0] == "assign_milestone"]
    assert "Batch change cancelled." in items.statuses


# -- discussions ---------------------------------------------------------------


def test_discussion_thread_reply_and_answer(frame, monkeypatch: pytest.MonkeyPatch) -> None:
    from quill.ui import github_discussion_dialog
    from quill.ui.github_discussion_dialog import GitHubDiscussionDialog

    provider = _Provider()
    monkeypatch.setattr(github_discussion_dialog, "ask_text", lambda *_a: "Thanks!")
    _modal(monkeypatch, "quill.ui.github_discussion_dialog", [wx.ID_YES])
    dialog = GitHubDiscussionDialog(frame, provider, repo="o/r", number=4)
    spoken: list[str] = []
    dialog._announce = spoken.append
    try:
        dialog._load()
        assert dialog._list.GetString(0) == "Discussion: Which theme?, Answered by kelly."
        assert "Option A: 12 votes, 40 percent" in dialog._detail.GetValue()
        dialog._list.SetSelection(2)  # bo's reply under ann's comment
        dialog._on_select()
        assert not dialog._answer_btn.IsEnabled()
        dialog._reply()
        assert ("reply", "D_1", "Thanks!", "C_1") in provider.calls
        dialog._list.SetSelection(1)
        dialog._on_select()
        dialog._toggle_answer()
        assert ("answer", "C_1", True) in provider.calls
        assert spoken[-1].startswith("Marked ann's comment as the answer.")
    finally:
        dialog.dialog.Destroy()


def test_discussion_reply_failure_is_spoken(frame, monkeypatch: pytest.MonkeyPatch) -> None:
    from quill.ui import github_discussion_dialog
    from quill.ui.github_discussion_dialog import GitHubDiscussionDialog

    provider = _Provider()
    monkeypatch.setattr(github_discussion_dialog, "ask_text", lambda *_a: "Hi")
    dialog = GitHubDiscussionDialog(frame, provider, repo="o/r", number=4)
    spoken: list[str] = []
    dialog._announce = spoken.append
    try:
        dialog._load()
        provider.fail = "Could not reply to the discussion. GitHub said: locked"
        dialog._reply()
        assert spoken[-1].endswith("GitHub said: locked")
    finally:
        dialog.dialog.Destroy()


# -- alert triage in Explore -------------------------------------------------


def _explore(frame, provider: _Provider):
    from quill.ui.github_explore_dialog import GitHubExploreDialog

    dialog = GitHubExploreDialog(frame, provider, initial_repo="o/r", initial_view="security")
    dialog.spoken = []
    dialog._announce = dialog.spoken.append
    dialog._load = lambda _event=None: dialog.spoken.append("reloaded")
    return dialog


def test_dismiss_alert_uses_githubs_reason_and_confirms(
    frame, monkeypatch: pytest.MonkeyPatch
) -> None:
    provider = _Provider()
    dialog = _explore(frame, provider)
    titles = _modal(monkeypatch, "quill.ui.dialog_contract", [wx.ID_OK])
    dialog._prompt = lambda *_a, **_k: "not reachable"
    asked: list[str] = []
    dialog._confirm = lambda message, title: asked.append(message) or True
    alert = GitHubSecurityAlert(7, "open", "high", "lodash", "Bad", alert_type="Dependabot")
    try:
        dialog._dismiss_alert(alert_row(alert, "o/r"))
        assert titles == ["Dismiss Alert"]
        assert "as a fix has already been started" in asked[0]
        assert provider.calls == [
            (
                "alert",
                "o/r",
                "dependabot",
                7,
                {"dismiss": True, "reason": "fix_started", "comment": "not reachable"},
            )
        ]
        assert "Dismissed Dependabot alert #7." in dialog.spoken
    finally:
        dialog.dialog.Destroy()


def test_dismiss_declined_sends_nothing_and_failures_are_reported(
    frame, monkeypatch: pytest.MonkeyPatch
) -> None:
    provider = _Provider()
    dialog = _explore(frame, provider)
    row = alert_row(GitHubSecurityAlert(7, "dismissed", "high", "x", "y"), "o/r")
    dialog._confirm = lambda *_a: False
    try:
        dialog._reopen_alert(row)
        assert provider.calls == []
        dialog._confirm = lambda *_a: True
        provider.fail = "Could not reopen Dependabot alert #7. Access denied."
        dialog._reopen_alert(row)
        assert any("Access denied" in message for message in dialog.spoken)
    finally:
        dialog.dialog.Destroy()


def test_community_actions_follow_the_row_and_view(frame) -> None:
    provider = _Provider()
    dialog = _explore(frame, provider)
    labels: list[str] = []
    try:
        dialog._rows = [alert_row(GitHubSecurityAlert(7, "open", "high", "x", "y"), "o/r")]
        dialog._list.Set([dialog._rows[0].label])
        dialog._list.SetSelection(0)
        dialog._add_community_actions(lambda label, _action: labels.append(label))
        assert labels == ["Dismiss Alert..."]
        labels.clear()
        dialog._rows = [ExploreRow("#4 x", "d", "u", "o/r", "discussion", "4")]
        dialog._add_community_actions(lambda label, _action: labels.append(label))
        assert labels == ["Open Discussion Thread..."]
    finally:
        dialog.dialog.Destroy()
