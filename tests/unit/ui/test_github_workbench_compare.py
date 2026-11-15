"""Compare from a row, compare links, and the list read once (complete.md 10B.1).

A real Workbench frame over a fake GitHub Items provider, background work
inline. The comparison window itself is replaced by a recorder: what is under
test is which two refs each command asks GitHub to compare.
"""

from __future__ import annotations

from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.core.github.branch_compare import GitHubBranchComparison  # noqa: E402
from quill.core.github.items_provider import (  # noqa: E402
    GitHubBranch,
    GitHubCommit,
    GitHubRelease,
    GitHubTag,
)
from quill.ui.github_workbench_window import GitHubWorkbenchProvider  # noqa: E402
from quill.ui.workbench_frame import NodeRef, WorkbenchFrame  # noqa: E402

REPO = "owner/repo"
_P = "github.workbench."


class _Items:
    is_authenticated = True
    token = "test-token-not-real"

    def __init__(self) -> None:
        self.compared: list[tuple[str, str, str]] = []
        self.tags = [GitHubTag("v2.0"), GitHubTag("v1.0")]

    def compare_branches(self, repo: str, base: str, head: str) -> GitHubBranchComparison:
        self.compared.append((repo, base, head))
        return GitHubBranchComparison(base=base or "main", head=head or "main")

    def fetch_tags(self, _repo: str, **_kw: Any) -> list[GitHubTag]:
        return list(self.tags)

    def fetch_default_branch(self, _repo: str) -> str:
        return "main"

    def close(self) -> None:
        pass


def _inline(_name: str, work: Any, done: Any, failed: Any) -> None:
    try:
        result = work()
    except Exception as exc:  # noqa: BLE001
        failed(exc)
        return
    done(result)


@pytest.fixture
def bench(wx_session_app, quill_data_dir, monkeypatch: pytest.MonkeyPatch):
    shown: list[GitHubBranchComparison] = []

    def _show(dialog: Any) -> None:
        shown.append(dialog._comparison)
        dialog.dialog.Destroy()

    monkeypatch.setattr(
        "quill.ui.github_compare_branches_dialog.GitHubCompareBranchesDialog.show", _show
    )
    said: list[str] = []
    items = _Items()
    provider = GitHubWorkbenchProvider(items, REPO, announce=said.append)
    frame = WorkbenchFrame(provider, announce=said.append, run_background=_inline)
    frame.said = said  # type: ignore[attr-defined]
    frame.items = items  # type: ignore[attr-defined]
    frame.shown = shown  # type: ignore[attr-defined]
    yield frame
    frame.frame.Destroy()


_REF = NodeRef("repository", "tags", REPO)


def test_compare_with_default_on_each_row_kind(bench) -> None:
    provider = bench.provider
    branch = GitHubBranch("feature", "abc", default_branch="main")
    commit = GitHubCommit(sha="c" * 40, short_sha="ccccccc", message="Fix")
    release = GitHubRelease(tag="v2.0", name="Two")
    for row in (branch, commit, release, GitHubTag("v1.0")):
        assert provider.run_action(f"{_P}compare_default", _REF, row)
    assert bench.items.compared == [
        (REPO, "", "feature"),
        (REPO, "c" * 40, ""),
        (REPO, "v2.0", ""),
        (REPO, "v1.0", ""),
    ]
    assert len(bench.shown) == 4


def test_compare_with_previous_tag_release_commit_and_branch(bench) -> None:
    provider = bench.provider
    v2, v1 = GitHubTag("v2.0"), GitHubTag("v1.0")
    draft = GitHubRelease(tag="v3.0", name="Draft", draft=True)
    r2, r1 = GitHubRelease(tag="v2.0", name="Two"), GitHubRelease(tag="v1.0", name="One")
    bench.rows = [v2, v1]
    assert provider.run_action(f"{_P}compare_previous", _REF, v2)
    bench.rows = [r2, draft, r1]
    assert provider.run_action(f"{_P}compare_previous", _REF, r2)
    commit = GitHubCommit(sha="d" * 40, short_sha="ddddddd", message="Fix")
    assert provider.run_action(f"{_P}compare_previous", _REF, commit)
    assert provider.run_action(f"{_P}compare_previous", _REF, GitHubBranch("feature", "abc"))
    assert bench.items.compared == [
        (REPO, "v1.0", "v2.0"),
        (REPO, "v1.0", "v2.0"),
        (REPO, "d" * 40 + "^", "d" * 40),
        (REPO, "feature^", "feature"),
    ]


def test_the_last_tag_has_no_previous_and_says_why(bench) -> None:
    provider = bench.provider
    v2, v1 = GitHubTag("v2.0"), GitHubTag("v1.0")
    bench.rows = [v2, v1]
    assert not provider.run_action(f"{_P}compare_previous", _REF, v1)
    bench.list.InsertColumn(0, "Name")
    for index, row in enumerate(bench.rows):
        bench.list.InsertItem(index, row.name)
    bench.focus_row(1)
    assert not provider.supports(f"{_P}compare_previous")
    assert "last one listed" in provider.reason(f"{_P}compare_previous")
    assert bench.items.compared == []


def test_a_pasted_compare_link_opens_the_comparison(bench) -> None:
    provider = bench.provider
    assert provider.open_link("https://github.com/other/thing/compare/main...feat/x?expand=1")
    assert provider.open_link("https://github.com/other/thing/compare/v1.0")
    assert not provider.open_link("https://github.com/other/thing/issues/4")
    assert not provider.open_link("not a link")
    assert bench.items.compared == [
        ("other/thing", "main", "feat/x"),
        ("other/thing", "", "v1.0"),
    ]


def test_open_address_with_a_compare_link_opens_it(bench, monkeypatch) -> None:
    url = "https://github.com/other/thing/compare/main...feature"

    def _answer(dialog: Any, _title: str) -> int:
        dialog.SetValue(url)
        return wx.ID_OK

    monkeypatch.setattr("quill.ui.workbench_frame_actions.show_modal_dialog", _answer)
    bench.open_address()
    assert bench.items.compared == [("other/thing", "main", "feature")]
    assert bench.current is not None and bench.current.instance == "other/thing"


def test_a_compare_favorite_opens_the_comparison_not_the_browser(bench) -> None:
    bench.provider._open_classic(None, None, reference=f"https://github.com/{REPO}/compare/a...b")
    assert bench.items.compared == [(REPO, "a", "b")]


# -- the list is read once ---------------------------------------------------------


def _load_tags(bench) -> None:
    ref = NodeRef("repository", "tags", REPO)
    assert bench.select(ref)
    if bench.current != ref:
        bench._show_node(ref, remember=True)


def test_a_refill_keeps_the_place_in_one_state_change(bench, monkeypatch) -> None:
    bench.items.tags = [GitHubTag("v3.0"), GitHubTag("v2.0"), GitHubTag("v1.0")]
    _load_tags(bench)
    assert bench.list.GetItemCount() == 3
    bench.focus_row(1)  # on v2.0
    calls: list[str] = []
    monkeypatch.setattr(bench.list, "Select", lambda *a: calls.append("Select"), raising=False)
    monkeypatch.setattr(bench.list, "Focus", lambda *a: calls.append("Focus"), raising=False)
    bench.items.tags = [GitHubTag("v4.0"), GitHubTag("v3.0"), GitHubTag("v2.0"), GitHubTag("v1.0")]
    bench.reload()
    assert bench.list.GetItemCount() == 4
    assert bench.selected_indices() == [2]  # still v2.0, which moved down one
    assert bench.list.GetFocusedItem() == 2
    assert calls == []  # never Select-then-Focus, which a reader reads twice


def test_a_refresh_that_changed_nothing_leaves_the_list_alone(bench, monkeypatch) -> None:
    _load_tags(bench)
    bench.focus_row(1)
    cleared: list[bool] = []
    monkeypatch.setattr(bench.list, "DeleteAllItems", lambda: cleared.append(True), raising=False)
    bench.reload()
    assert cleared == []
    assert bench.selected_indices() == [1]
