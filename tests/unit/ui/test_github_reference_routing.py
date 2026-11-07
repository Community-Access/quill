"""Direct GitHub references enter the shared workbench at their target."""

from __future__ import annotations

from types import SimpleNamespace

from quill.core.github.items_provider import (
    GitHubBranch,
    GitHubCommit,
    GitHubItem,
    GitHubRelease,
)
from quill.core.github.references import parse_github_reference
from quill.core.github.workflow_models import GitHubWorkflowRun
from quill.core.github.workflows import GitHubWorkflow
from quill.ui.github_items_dialog import GitHubItemsDialog
from quill.ui.github_items_dialog_references import GitHubReferenceMixin
from quill.ui.github_items_view import (
    VIEW_COMMITS,
    VIEW_RELEASES,
    VIEW_RUNS,
    VIEW_WORKFLOWS,
    VIEWS,
)


class _ListStub:
    def __init__(self) -> None:
        self.selected: int | None = None
        self.focused: int | None = None

    def SetFocus(self) -> None:
        pass

    def Select(self, index: int) -> None:
        self.selected = index

    def Focus(self, index: int) -> None:
        self.focused = index


def _issue(number: int, *, is_pr: bool = False) -> GitHubItem:
    return GitHubItem(
        number=number,
        title="Direct item",
        state="open",
        url=f"https://github.com/owner/repo/issues/{number}",
        is_pr=is_pr,
    )


def _attach_reference_loader(dialog: SimpleNamespace) -> SimpleNamespace:
    dialog._load_reference_rows = lambda repo, view, rows: (
        GitHubReferenceMixin._load_reference_rows(dialog, repo, view, rows)
    )
    return dialog


def test_direct_issue_reference_is_fetched_even_when_outside_first_page() -> None:
    reference = parse_github_reference("https://github.com/owner/repo/issues/42")
    direct_item = _issue(42)
    loaded: list[tuple[list[object], str]] = []
    dialog = SimpleNamespace(
        _wx=SimpleNamespace(CallAfter=lambda callback, *args: callback(*args)),
        _initial_reference=reference,
        _provider=SimpleNamespace(fetch_item=lambda repo, number: direct_item),
        _fetch=lambda *_args: [_issue(8)],
        _on_rows_loaded=lambda rows, view: loaded.append((rows, view)),
        _on_load_error=lambda message: (_ for _ in ()).throw(AssertionError(message)),
    )
    _attach_reference_loader(dialog)

    GitHubItemsDialog._load_worker(dialog, "owner/repo", "issues", "both", "open", 30)

    assert loaded == [([direct_item, _issue(8)], "issues")]


def test_direct_pull_request_reference_selects_and_opens_review_reader() -> None:
    reference = parse_github_reference("https://github.com/owner/repo/pull/7")
    item = _issue(7, is_pr=True)
    list_stub = _ListStub()
    details: list[int] = []
    reviews: list[str] = []
    announcements: list[str] = []
    dialog = SimpleNamespace(
        _initial_reference=reference,
        _repo="owner/repo",
        _rows=[item],
        _list=list_stub,
        _show_detail=details.append,
        _announce=announcements.append,
        _on_review=lambda: reviews.append("opened"),
        _wx=SimpleNamespace(CallAfter=lambda callback: callback()),
    )

    GitHubItemsDialog._select_initial_reference(dialog)

    assert list_stub.selected == 0
    assert list_stub.focused == 0
    assert details == [0]
    assert reviews == ["opened"]


def test_issue_url_that_resolves_to_pull_request_opens_review_reader() -> None:
    reference = parse_github_reference("https://github.com/owner/repo/issues/7")
    item = _issue(7, is_pr=True)
    list_stub = _ListStub()
    reviews: list[str] = []
    dialog = SimpleNamespace(
        _initial_reference=reference,
        _repo="owner/repo",
        _rows=[item],
        _list=list_stub,
        _show_detail=lambda _index: None,
        _announce=lambda _message: None,
        _on_review=lambda: reviews.append("opened"),
        _wx=SimpleNamespace(CallAfter=lambda callback: callback()),
    )

    GitHubItemsDialog._select_initial_reference(dialog)

    assert list_stub.selected == 0
    assert reviews == ["opened"]


def test_direct_branch_reference_selects_the_matching_branch() -> None:
    reference = parse_github_reference("https://github.com/owner/repo/tree/feature%2Fbranch")
    branch = GitHubBranch(name="feature/branch", commit_sha="abc123")
    list_stub = _ListStub()
    details: list[int] = []
    announcements: list[str] = []
    dialog = SimpleNamespace(
        _initial_reference=reference,
        _repo="owner/repo",
        _rows=[branch],
        _list=list_stub,
        _show_detail=details.append,
        _announce=announcements.append,
        _wx=SimpleNamespace(),
    )

    GitHubItemsDialog._select_initial_reference(dialog)

    assert list_stub.selected == 0
    assert details == [0]
    assert announcements == ["Selected branch feature/branch."]


def test_commit_reference_fetches_the_exact_sha() -> None:
    reference = parse_github_reference("https://github.com/owner/repo/commit/abcdef123456")
    commit = GitHubCommit(sha="abcdef123456", short_sha="abcdef1", message="Fix issue")
    fetched: list[tuple[str, str]] = []
    loaded: list[tuple[list[object], str]] = []
    provider = SimpleNamespace(
        fetch_commit_by_sha=lambda repo, sha: fetched.append((repo, sha)) or commit
    )
    dialog = SimpleNamespace(
        _wx=SimpleNamespace(CallAfter=lambda callback, *args: callback(*args)),
        _initial_reference=reference,
        _provider=provider,
        _fetch=lambda *_args: [],
        _on_rows_loaded=lambda rows, view: loaded.append((rows, view)),
        _on_load_error=lambda message: (_ for _ in ()).throw(AssertionError(message)),
    )
    _attach_reference_loader(dialog)

    GitHubItemsDialog._load_worker(dialog, "owner/repo", VIEW_COMMITS, "both", "open", 30)

    assert fetched == [("owner/repo", "abcdef123456")]
    assert loaded == [([commit], VIEW_COMMITS)]


def test_release_reference_fetches_exact_tag_even_outside_recent_page() -> None:
    reference = parse_github_reference("https://github.com/owner/repo/releases/tag/v1.2.3")
    release = GitHubRelease(tag="v1.2.3", name="Version 1.2.3")
    fetched: list[tuple[str, str]] = []
    loaded: list[tuple[list[object], str]] = []
    provider = SimpleNamespace(
        fetch_release_by_tag=lambda repo, tag: fetched.append((repo, tag)) or release
    )
    dialog = SimpleNamespace(
        _wx=SimpleNamespace(CallAfter=lambda callback, *args: callback(*args)),
        _initial_reference=reference,
        _provider=provider,
        _fetch=lambda *_args: [],
        _on_rows_loaded=lambda rows, view: loaded.append((rows, view)),
        _on_load_error=lambda message: (_ for _ in ()).throw(AssertionError(message)),
    )
    _attach_reference_loader(dialog)

    GitHubItemsDialog._load_worker(dialog, "owner/repo", VIEW_RELEASES, "both", "open", 30)

    assert fetched == [("owner/repo", "v1.2.3")]
    assert loaded == [([release], VIEW_RELEASES)]


def test_workflow_run_reference_fetches_exact_run_id() -> None:
    reference = parse_github_reference("https://github.com/owner/repo/actions/runs/101")
    run = GitHubWorkflowRun(name="CI", status="completed", id=101)
    fetched: list[tuple[str, int]] = []
    loaded: list[tuple[list[object], str]] = []
    provider = SimpleNamespace(
        fetch_workflow_run_by_id=lambda repo, run_id: fetched.append((repo, run_id)) or run
    )
    dialog = SimpleNamespace(
        _wx=SimpleNamespace(CallAfter=lambda callback, *args: callback(*args)),
        _initial_reference=reference,
        _provider=provider,
        _fetch=lambda *_args: [],
        _on_rows_loaded=lambda rows, view: loaded.append((rows, view)),
        _on_load_error=lambda message: (_ for _ in ()).throw(AssertionError(message)),
    )
    _attach_reference_loader(dialog)

    GitHubItemsDialog._load_worker(dialog, "owner/repo", VIEW_RUNS, "both", "open", 30)

    assert fetched == [("owner/repo", 101)]
    assert loaded == [([run], VIEW_RUNS)]


def test_workflow_definition_reference_fetches_workflow_file() -> None:
    reference = parse_github_reference("https://github.com/owner/repo/actions/workflows/ci.yml")
    workflow = GitHubWorkflow(id=10, name="CI", path=".github/workflows/ci.yml", state="active")
    fetched: list[tuple[str, str]] = []
    loaded: list[tuple[list[object], str]] = []
    provider = SimpleNamespace(
        fetch_workflow_by_reference=lambda repo, ref: fetched.append((repo, ref)) or workflow
    )
    dialog = SimpleNamespace(
        _wx=SimpleNamespace(CallAfter=lambda callback, *args: callback(*args)),
        _initial_reference=reference,
        _provider=provider,
        _fetch=lambda *_args: [],
        _on_rows_loaded=lambda rows, view: loaded.append((rows, view)),
        _on_load_error=lambda message: (_ for _ in ()).throw(AssertionError(message)),
    )
    _attach_reference_loader(dialog)

    GitHubItemsDialog._load_worker(dialog, "owner/repo", VIEW_WORKFLOWS, "both", "open", 30)

    assert fetched == [("owner/repo", "ci.yml")]
    assert loaded == [([workflow], VIEW_WORKFLOWS)]


def test_reference_kind_selects_the_native_view() -> None:
    reference = parse_github_reference("https://github.com/owner/repo/actions/runs/101")
    dialog = SimpleNamespace(
        _view_choice=SimpleNamespace(
            SetSelection=lambda index: setattr(dialog, "view_index", index)
        ),
        _show_choice=SimpleNamespace(
            SetSelection=lambda index: setattr(dialog, "show_index", index)
        ),
        _state_choice=SimpleNamespace(
            SetSelection=lambda index: setattr(dialog, "state_index", index)
        ),
        _repo_ctrl=SimpleNamespace(SetValue=lambda value: setattr(dialog, "repo_value", value)),
        _search_ctrl=SimpleNamespace(ChangeValue=lambda value: None),
        _quick_filter_ctrl=SimpleNamespace(ChangeValue=lambda value: None),
        _rebuild_columns=lambda: None,
        _apply_filter_enablement=lambda: None,
        _on_load=lambda _event: None,
    )
    GitHubReferenceMixin._apply_initial_reference(dialog, reference)

    assert dialog._view == VIEW_RUNS
    assert dialog.view_index == next(
        index for index, (view, _) in enumerate(VIEWS) if view == VIEW_RUNS
    )
    assert dialog.repo_value == "owner/repo"


def test_discussion_link_opens_the_native_explore_discussion() -> None:
    opened: list[dict[str, object]] = []

    class _Entry:
        def __init__(self, *_args, **_kwargs) -> None:
            pass

        def SetName(self, _name: str) -> None:
            pass

        def GetValue(self) -> str:
            return "https://github.com/owner/repo/discussions/18"

        def Destroy(self) -> None:
            pass

    class _ExploreDialog:
        def __init__(self, *_args, **kwargs) -> None:
            opened.append(kwargs)

        def show(self) -> None:
            pass

    class _Wx:
        ID_OK = 1
        TextEntryDialog = _Entry

    dialog = SimpleNamespace(
        _wx=_Wx,
        dialog=object(),
        _show_modal=lambda *_args: _Wx.ID_OK,
        _provider=SimpleNamespace(is_authenticated=True),
        _announce=lambda _message: None,
        _start_issue_worktree_cb=None,
        _set_status=lambda _message: None,
    )
    from unittest.mock import patch

    with patch("quill.ui.github_explore_dialog.GitHubExploreDialog", _ExploreDialog):
        GitHubReferenceMixin._on_open_reference(dialog, None)

    assert opened == [
        {
            "initial_repo": "owner/repo",
            "initial_view": "discussions",
            "initial_discussion": 18,
            "announce_cb": dialog._announce,
            "on_start_issue_worktree": None,
        }
    ]
