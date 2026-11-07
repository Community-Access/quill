"""Wave 4 in the shared dialogs: Explore's repository actions, rate limit and quiet refresh,
the Items viewer's housekeeping and release actions, and the two new small dialogs."""

from __future__ import annotations

from typing import Any

import pytest
import wx

from quill.core.github.explore_models import ExploreRow
from quill.core.github.explore_views import VIEWS
from quill.core.github.issue_housekeeping import SubIssue
from quill.core.github.items_errors import GitHubItemsError
from quill.core.github.items_provider import GitHubItem, GitHubRelease, GitHubReleaseAsset
from quill.core.github.rate_limits import RateLimitBucket, RateLimitReport
from quill.core.github.release_admin import ReleaseAssetRecord, ReleaseRecord
from quill.ui import (
    github_explore_repo_actions,
    github_items_dialog_housekeeping,
    github_items_dialog_releases,
    github_sub_issue_order_dialog,
)
from quill.ui.github_explore_dialog import GitHubExploreDialog
from quill.ui.github_items_dialog import GitHubItemsDialog
from quill.ui.github_items_view import VIEW_ISSUES, VIEW_RELEASES
from tests.wx_session import patch_call_after, shared_wx_app


class _SyncThread:
    def __init__(self, target=None, args=(), kwargs=None, daemon=None, **_kw) -> None:
        self._target, self._args, self._kwargs = target, args, kwargs or {}

    def start(self) -> None:
        self._target(*self._args, **self._kwargs)


class _Provider:
    is_authenticated = True
    token = "tok"
    _gh = None


class _Recorder:
    """Stands in for a core action class; records calls, returns canned answers."""

    def __init__(self, answers: dict[str, Any] | None = None) -> None:
        self.calls: list[tuple[Any, ...]] = []
        self.answers = answers or {}

    def __getattr__(self, name: str) -> Any:
        def call(*args: Any, **kwargs: Any) -> Any:
            self.calls.append((name, *args))
            answer = self.answers.get(name)
            if isinstance(answer, BaseException):
                raise answer
            return answer(*args, **kwargs) if callable(answer) else answer

        return call


@pytest.fixture
def explore(monkeypatch: pytest.MonkeyPatch):
    shared_wx_app()
    for module in ("github_explore_dialog", "github_explore_repo_actions"):
        monkeypatch.setattr(f"quill.ui.{module}.threading.Thread", _SyncThread)
    patch_call_after(monkeypatch, lambda fn, *a, **k: fn(*a, **k))
    frame = wx.Frame(None)
    dialog = GitHubExploreDialog(frame, _Provider(), initial_view="repo_overview")
    dialog.spoken = []
    dialog.questions = []
    dialog._announce = dialog.spoken.append
    dialog._load = lambda _event: dialog.spoken.append("reloaded")

    def confirm(message: str, title: str) -> bool:
        dialog.questions.append((title, message))
        return True

    dialog._confirm = confirm
    dialog.actions = _Recorder()
    dialog._actions = lambda: dialog.actions
    yield dialog
    dialog.dialog.Destroy()
    frame.Destroy()


def test_sync_fork_asks_then_says_githubs_answer(explore) -> None:
    explore.actions.answers["sync_fork"] = "Merged 3 commits from up:main."
    explore._sync_fork("me/r")
    assert explore.questions[0][0] == "Sync Fork"
    assert explore.actions.calls == [("sync_fork", "me/r")]
    assert explore.spoken[-1] == "Merged 3 commits from up:main."


def test_a_refused_write_says_why_and_claims_nothing(explore) -> None:
    explore.actions.answers["set_archived"] = GitHubItemsError("Could not archive o/r. Denied.")
    explore._set_archived("o/r", True)
    assert explore.spoken[-1] == "Could not archive o/r. Denied."
    assert "reloaded" not in explore.spoken


def test_delete_repository_needs_the_typed_name(explore, monkeypatch) -> None:
    answers = iter([False, True])

    class Typed:
        def __init__(self, *_a, **kwargs) -> None:
            assert kwargs["expected"] == "o/r"

        def show(self) -> bool:
            return next(answers)

    monkeypatch.setattr("quill.ui.github_repo_admin_dialogs.TypedConfirmDialog", Typed)
    explore._delete_repository("o/r")
    assert explore.actions.calls == []
    assert "not deleted" in explore.spoken[-1]
    explore._delete_repository("o/r")
    assert explore.actions.calls == [("delete_repository", "o/r")]
    assert explore.spoken[-2:] == ["Deleted o/r.", "reloaded"]


def test_topics_are_read_then_offered_then_set(explore, monkeypatch) -> None:
    explore.actions.answers["get_topics"] = ("python",)
    explore.actions.answers["set_topics"] = ("python", "accessibility")
    prompts: list[str] = []

    def prompt(message: str, title: str, default: str = "") -> str:
        prompts.append(default)
        return "python accessibility"

    explore._prompt = prompt
    explore._set_topics("o/r")
    assert prompts == ["python"]
    assert explore.spoken[-1] == "Topics for o/r are now: python, accessibility."


def test_releases_only_opens_the_page_because_the_api_cannot_set_it(explore, monkeypatch):
    explore.actions.answers["get_watch_level"] = "watching"
    opened: list[str] = []
    monkeypatch.setattr(github_explore_repo_actions.webbrowser, "open", opened.append)

    class Choice:
        def __init__(self, *_a, **_k) -> None:
            pass

        def __enter__(self) -> Choice:
            return self

        def __exit__(self, *_a) -> None:
            return None

        def SetSelection(self, _index: int) -> None:  # noqa: N802 - wx API
            pass

        def GetSelection(self) -> int:  # noqa: N802 - wx API
            return 1

    monkeypatch.setattr(wx, "SingleChoiceDialog", Choice)
    explore._show_choice = lambda _dialog, _title: wx.ID_OK
    explore._choose_watch_level("o/r")
    assert opened == ["https://github.com/o/r"]
    assert ("set_watch_level", "o/r", "releases") not in explore.actions.calls
    assert "cannot set Releases only" in explore.spoken[-1]


def test_follow_and_delete_cache(explore) -> None:
    explore._set_following("alice", True)
    assert explore.spoken[-1] == "You now follow @alice."
    row = ExploreRow("pip-linux, 2 KB, branch main", "", "", "o/r", "cache", "7")
    explore._delete_cache(row)
    assert ("delete_cache", "o/r", "7") in explore.actions.calls
    assert explore.questions[-1][0] == "Delete Cache"


def test_rate_limit_readout_is_said_once(explore, monkeypatch) -> None:
    report = RateLimitReport((RateLimitBucket("core", 5000, 4212, 0.0),))
    monkeypatch.setattr(github_explore_repo_actions, "fetch_rate_limit_report", lambda _t: report)
    explore._show_rate_limit()
    assert explore.spoken == ["GitHub API: 4,212 of 5,000 left."]
    assert explore._status.GetLabel() == "GitHub API: 4,212 of 5,000 left."


def test_a_refresh_that_changed_nothing_says_so(explore) -> None:
    explore._repo.SetValue("o/r")
    explore._rows = [ExploreRow("a", "detail")]
    assert explore._note_if_unchanged("labels", "1 results loaded.") == "1 results loaded."
    assert explore._note_if_unchanged("labels", "1 results loaded.") == (
        "No changes since the last load; 1 results."
    )
    explore._rows = [ExploreRow("b", "detail")]
    assert explore._note_if_unchanged("labels", "1 results loaded.") == "1 results loaded."
    assert explore._note_if_unchanged("notifications", "x") == "x"


def test_repository_actions_submenu_is_offered_for_a_repository(explore) -> None:
    menu = wx.Menu()
    added: list[str] = []
    row = ExploreRow("o/r", "", "https://github.com/o/r", "o/r", "repo")
    explore._add_wave4_actions(menu, lambda label, *_a, **_k: added.append(label), row)
    labels = [item.GetItemLabelText() for item in menu.GetMenuItems()]
    assert labels == ["Repository Actions for o/r"]
    submenu = menu.GetMenuItems()[0].GetSubMenu()
    assert [item.GetItemLabelText() for item in submenu.GetMenuItems()][-1] == (
        "Delete Repository..."
    )
    assert added == ["GitHub API Rate Limit\tCtrl+Shift+L"]
    menu.Destroy()


def test_new_search_views_need_a_query(explore) -> None:
    keys = [key for key, _ in VIEWS]
    explore._view.SetSelection(keys.index("code_search"))
    explore._query.SetValue("")
    GitHubExploreDialog._load(explore, None)
    assert explore._status.GetLabel() == "Enter a search query first."


# -- Items viewer -------------------------------------------------------------------


ISSUE = GitHubItem(number=3, title="Crash", state="open", url="u", is_pr=False)


@pytest.fixture
def items(monkeypatch: pytest.MonkeyPatch):
    shared_wx_app()
    for module in ("github_items_dialog_housekeeping", "github_sub_issue_order_dialog"):
        monkeypatch.setattr(f"quill.ui.{module}.threading.Thread", _SyncThread)
    patch_call_after(monkeypatch, lambda fn, *a, **k: fn(*a, **k))
    frame = wx.Frame(None)
    dialog = GitHubItemsDialog(frame, _Provider(), initial_repo="o/r")
    dialog._repo = "o/r"
    dialog._view = VIEW_ISSUES
    dialog._rows = [ISSUE]
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
    dialog.housekeeper = _Recorder()
    dialog._housekeeping = lambda: dialog.housekeeper
    dialog.admin = _Recorder()
    dialog._release_admin = lambda: dialog.admin
    yield dialog
    dialog.dialog.Destroy()
    frame.Destroy()


class _Choice:
    picked = 0

    def __init__(self, *_a, **_k) -> None:
        pass

    def __enter__(self) -> _Choice:
        return self

    def __exit__(self, *_a) -> None:
        return None

    def GetSelection(self) -> int:  # noqa: N802 - wx API
        return self.picked

    def GetValue(self) -> str:  # noqa: N802 - wx API
        return "o/other"

    def GetPath(self) -> str:  # noqa: N802 - wx API
        return self.path


def test_lock_with_a_reason(items, monkeypatch) -> None:
    _Choice.picked = 2
    monkeypatch.setattr(wx, "SingleChoiceDialog", _Choice)
    items._show_modal = lambda _d, _t: wx.ID_OK
    items._lock_item(ISSUE)
    assert items.housekeeper.calls == [("lock", "o/r", 3, "too heated")]
    assert items.statuses[-1] == "Locked #3 as too heated. Only collaborators can comment now."


def test_transfer_asks_first_and_reloads(items, monkeypatch) -> None:
    monkeypatch.setattr(wx, "TextEntryDialog", _Choice)
    items._show_modal = lambda _d, _t: wx.ID_OK
    items.housekeeper.answers["transfer"] = "Moved to o/other as #40: url"
    items._transfer_item(ISSUE)
    assert items.questions[0][0] == "Transfer Issue"
    assert items.statuses[-2:] == ["Moved to o/other as #40: url", "reloaded"]
    items._confirm_action = lambda _m, _t: False
    items.housekeeper.calls.clear()
    items._transfer_item(ISSUE)
    assert items.housekeeper.calls == []


def test_issue_type_says_when_the_repository_has_none(items) -> None:
    items.housekeeper.answers["issue_types"] = ()
    items._set_item_type(ISSUE)
    assert "has no issue types" in items.statuses[-1]


def test_sub_issues_open_the_order_dialog(items, monkeypatch) -> None:
    order = [SubIssue(1, 10, "a"), SubIssue(2, 11, "b")]
    items.housekeeper.answers["sub_issues"] = order
    opened: list[Any] = []

    class Dialog:
        def __init__(self, _parent, _hk, **kwargs) -> None:
            opened.append(kwargs)

        def show(self) -> None:
            pass

    monkeypatch.setattr(github_sub_issue_order_dialog, "SubIssueOrderDialog", Dialog)
    items._reorder_sub_issues(ISSUE)
    assert opened[0]["parent_number"] == 3 and len(opened[0]["order"]) == 2


def test_housekeeping_submenu_is_issue_aware(items) -> None:
    menu = wx.Menu()
    items._add_issue_housekeeping(menu, ISSUE)
    sub = menu.GetMenuItems()[0].GetSubMenu()
    assert "Transfer Issue..." in [item.GetItemLabelText() for item in sub.GetMenuItems()]
    pr_menu = wx.Menu()
    items._add_issue_housekeeping(pr_menu, GitHubItem(4, "PR", "open", "u", True))
    pr_labels = [
        i.GetItemLabelText() for i in pr_menu.GetMenuItems()[0].GetSubMenu().GetMenuItems()
    ]
    assert pr_labels == ["Lock Conversation...", "Unlock Conversation"]
    menu.Destroy()
    pr_menu.Destroy()


def test_rate_limit_key_in_the_items_viewer(items, monkeypatch) -> None:
    report = RateLimitReport((RateLimitBucket("core", 60, 59, 0.0),))
    monkeypatch.setattr(
        "quill.core.github.rate_limits.fetch_rate_limit_report", lambda _token: report
    )
    items._show_api_rate_limit()
    assert items.statuses[-1] == "GitHub API: 59 of 60 left."


RELEASE = GitHubRelease(tag="v1.0", name="One", draft=True)
RECORD = ReleaseRecord(
    id=5, tag="v1.0", name="One", draft=True, assets=(ReleaseAssetRecord(9, "app.zip"),)
)


def test_edit_release_confirms_publishing_a_draft(items, monkeypatch) -> None:
    from quill.ui import github_release_edit_dialog
    from quill.ui.github_release_edit_dialog import EditReleaseValues

    items._view = VIEW_RELEASES
    items._rows = [RELEASE]
    items.admin.answers["find_release"] = RECORD
    items.admin.answers["edit_release"] = (RECORD, "Release One: published.")

    class Editor:
        def __init__(self, *_a, **_k) -> None:
            pass

        def show(self) -> EditReleaseValues:
            return EditReleaseValues("One", "Notes", False, False)

    monkeypatch.setattr(github_release_edit_dialog, "EditReleaseDialog", Editor)
    items._edit_selected_release()
    assert items.questions[0][0] == "Publish Release"
    assert items.statuses[-2:] == ["Release One: published.", "reloaded"]


def test_upload_and_delete_asset(items, monkeypatch, tmp_path) -> None:
    source = tmp_path / "notes.txt"
    source.write_text("x")
    _Choice.path = str(source)
    monkeypatch.setattr(wx, "FileDialog", _Choice)
    items._show_modal = lambda _d, _t: wx.ID_OK
    items._view = VIEW_RELEASES
    items._rows = [RELEASE]
    items.admin.answers["find_release"] = RECORD

    def upload(repo, record, path, *, progress):
        progress(50)
        return ReleaseAssetRecord(77, "notes.txt", 1)

    items.admin.answers["upload_release_asset"] = upload
    items._upload_release_asset()
    assert "Uploading notes.txt: 50 percent." in items.statuses
    assert items.statuses[-2] == "Uploaded notes.txt (1 bytes) to release v1.0."
    items._drill_release = RELEASE
    items._rows = [GitHubReleaseAsset("app.zip", 3, 10)]
    items._delete_selected_asset()
    assert items.questions[-1][0] == "Delete Release Asset"
    assert ("delete_asset", "o/r", RECORD.assets[0]) in items.admin.calls
    assert items.statuses[-2] == "Deleted app.zip from release v1.0."


def test_release_actions_list_delete_only_inside_a_release(items) -> None:
    labels: list[str] = []
    items._view = VIEW_RELEASES
    items._rows = [RELEASE]
    items._add_release_actions(lambda label, _handler: labels.append(label))
    assert labels == ["Draft Release Notes...", "Edit Release...", "Upload Asset..."]


# -- The two small dialogs ----------------------------------------------------------


def test_sub_issue_dialog_moves_and_says_where_it_landed(monkeypatch) -> None:
    shared_wx_app()
    monkeypatch.setattr(github_sub_issue_order_dialog.threading, "Thread", _SyncThread)
    patch_call_after(monkeypatch, lambda fn, *a, **k: fn(*a, **k))
    order = [SubIssue(1, 10, "a"), SubIssue(2, 11, "b")]
    moved = [SubIssue(2, 11, "b"), SubIssue(1, 10, "a")]
    housekeeper = _Recorder({"move_sub_issue": moved})
    frame = wx.Frame(None)
    spoken: list[str] = []
    dialog = github_sub_issue_order_dialog.SubIssueOrderDialog(
        frame, housekeeper, repo="o/r", parent_number=5, order=order, announce_cb=spoken.append
    )
    dialog._list.SetSelection(1)
    dialog._move(-1)
    assert spoken[-1] == "#11 is now 1 of 2."
    assert dialog._list.GetSelection() == 0
    dialog._move(-1)
    dialog.dialog.Destroy()
    frame.Destroy()


def test_edit_release_dialog_starts_from_githubs_copy() -> None:
    shared_wx_app()
    from quill.ui.github_release_edit_dialog import EditReleaseDialog

    frame = wx.Frame(None)
    dialog = EditReleaseDialog(frame, ReleaseRecord(5, "v1", "One", "Notes", True, True))
    values = dialog.values()
    assert (values.name, values.body, values.draft, values.prerelease) == (
        "One",
        "Notes",
        True,
        True,
    )
    dialog.dialog.Destroy()
    frame.Destroy()


def test_housekeeping_modules_are_imported_by_the_dialog() -> None:
    assert (
        github_items_dialog_housekeeping.GitHubItemsHousekeepingMixin in GitHubItemsDialog.__mro__
    )
    assert github_items_dialog_releases.GitHubItemsReleaseMixin in GitHubItemsDialog.__mro__
