"""The shared Items dialog resumes its local selected row and saved view."""

from __future__ import annotations

from types import SimpleNamespace

from quill.core.github import navigation_state
from quill.core.github.items_provider import GitHubItem
from quill.core.github.navigation_state import GitHubItemsContext, GitHubNavigationState
from quill.ui.github_items_dialog_navigation import GitHubNavigationMixin


class _ListStub:
    selected: int | None = None

    def SetFocus(self) -> None:
        pass

    def Select(self, index: int) -> None:
        self.selected = index

    def Focus(self, index: int) -> None:
        self.selected = index


def test_restore_navigation_uses_the_same_account_and_repository(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(navigation_state, "app_data_dir", lambda: tmp_path)
    token = "account-token"
    GitHubNavigationState.load(token).save(
        GitHubItemsContext(
            repository="owner/repo",
            view="runs",
            show="prs",
            state="all",
            sort="updated_desc",
            search_query="is:failure",
            quick_filter_query="windows",
            selected_key="run:123",
        )
    )
    dialog = SimpleNamespace(
        _repo="",
        _view="issues",
        _show="both",
        _state="open",
        _sort="number_desc",
        _search_query="",
        _quick_filter_query="",
    )

    GitHubNavigationMixin._restore_navigation(
        dialog,
        SimpleNamespace(token=token),
        None,
    )

    assert dialog._repo == "owner/repo"
    assert dialog._view == "runs"
    assert dialog._show == "prs"
    assert dialog._state == "all"
    assert dialog._sort == "updated_desc"
    assert dialog._search_query == "is:failure"
    assert dialog._quick_filter_query == "windows"
    assert dialog._restore_selection_key == "run:123"


def test_direct_reference_takes_precedence_over_saved_resume(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(navigation_state, "app_data_dir", lambda: tmp_path)
    GitHubNavigationState.load("token").save(
        GitHubItemsContext(repository="owner/repo", view="runs", selected_key="run:123")
    )
    reference = SimpleNamespace(repository="other/repo", kind="issue")
    dialog = SimpleNamespace(
        _repo="other/repo",
        _view="issues",
        _show="issues",
        _state="all",
        _sort="number_desc",
        _search_query="",
        _quick_filter_query="",
    )

    GitHubNavigationMixin._restore_navigation(
        dialog,
        SimpleNamespace(token="token"),
        reference,
    )

    assert dialog._view == "issues"
    assert dialog._restore_selection_key == ""


def test_saved_selection_is_restored_after_results_load() -> None:
    row = GitHubItem(
        number=42,
        title="Resume me",
        state="open",
        url="https://github.com/owner/repo/issues/42",
        is_pr=False,
    )
    list_stub = _ListStub()
    details: list[int] = []
    announcements: list[str] = []
    dialog = SimpleNamespace(
        _initial_reference=None,
        _restore_selection_key="issue:42",
        _rows=[row],
        _navigation_key=GitHubNavigationMixin._navigation_key,
        _list=list_stub,
        _show_detail=details.append,
        _announce=announcements.append,
    )

    GitHubNavigationMixin._restore_saved_selection(dialog)

    assert list_stub.selected == 0
    assert details == [0]
    assert announcements == ["Restored the last selected GitHub item."]


def test_back_and_forward_restore_repository_view_and_filters(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(navigation_state, "app_data_dir", lambda: tmp_path)
    state = GitHubNavigationState.load("history-token")
    first = GitHubItemsContext(repository="owner/one", selected_key="issue:1")
    second = GitHubItemsContext(
        repository="owner/one",
        view="branches",
        search_query="main",
        selected_key="branch:main",
    )
    third = GitHubItemsContext(
        repository="owner/two",
        view="runs",
        quick_filter_query="failed",
        selected_key="run:12",
    )
    state.record(first)
    state.record(second)
    state.record(third)

    class _Choice:
        def __init__(self) -> None:
            self.selection = -1

        def SetSelection(self, value: int) -> None:
            self.selection = value

    class _Text:
        def __init__(self) -> None:
            self.value = ""

        def SetValue(self, value: str) -> None:
            self.value = value

        def ChangeValue(self, value: str) -> None:
            self.value = value

    class _Button:
        def __init__(self) -> None:
            self.enabled = False

        def Enable(self, value: bool) -> None:
            self.enabled = value

    loads: list[object] = []
    announcements: list[str] = []
    dialog = SimpleNamespace(
        _navigation_state=state,
        _back_btn=_Button(),
        _forward_btn=_Button(),
        _view_choice=_Choice(),
        _show_choice=_Choice(),
        _state_choice=_Choice(),
        _sort_choice=_Choice(),
        _repo_ctrl=_Text(),
        _search_ctrl=_Text(),
        _quick_filter_ctrl=_Text(),
        _view="issues",
        _show="both",
        _state="open",
        _sort="number_desc",
        _repo="",
        _search_query="",
        _quick_filter_query="",
        _drill_branch=None,
        _drill_release=None,
        _page=1,
        _restore_selection_key="",
        _resume_selection_missing=False,
        _initial_reference=None,
        _announce=announcements.append,
        _rebuild_columns=lambda: None,
        _apply_filter_enablement=lambda: None,
        _on_load=loads.append,
    )
    dialog._update_navigation_buttons = lambda: GitHubNavigationMixin._update_navigation_buttons(
        dialog
    )
    dialog._apply_navigation_context = lambda context: (
        GitHubNavigationMixin._apply_navigation_context(dialog, context)
    )

    GitHubNavigationMixin._go_back(dialog)

    assert dialog._repo == "owner/one"
    assert dialog._view == "branches"
    assert dialog._search_query == "main"
    assert dialog._restore_selection_key == "branch:main"
    assert dialog._back_btn.enabled
    assert dialog._forward_btn.enabled

    GitHubNavigationMixin._go_forward(dialog)

    assert dialog._repo == "owner/two"
    assert dialog._view == "runs"
    assert dialog._quick_filter_query == "failed"
    assert dialog._restore_selection_key == "run:12"
    assert len(loads) == 2
