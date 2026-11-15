"""GH-E in the window: named sets, honest category lists, Enter and Back, ] and [,
View More, issue types and fields, by-name changes and the Fleet.

A real frame over fakes, with background work run inline; GitHub is a recorded
fake of the Workbench's GitHubApi, so nothing leaves the machine.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.core.github import across  # noqa: E402
from quill.core.github.items_provider import GitHubItem, GitHubRelease  # noqa: E402
from quill.core.github.navigation_state import account_key_for_token  # noqa: E402
from quill.core.github.repository_sets import RepositorySets  # noqa: E402
from quill.ui.github_workbench_window import GitHubWorkbenchProvider  # noqa: E402
from quill.ui.workbench_frame import NodeRef, WorkbenchFrame  # noqa: E402

TOKEN = "test-token-not-real"


class _Items:
    is_authenticated = True
    token = TOKEN

    def fetch_issues(self, repo: str, **_kw: Any) -> list[GitHubItem]:
        return [_issue(repo, 4, "Crash")]

    def fetch_pulls(self, _repo: str, **_kw: Any) -> list[GitHubItem]:
        return []

    def search_items(self, repo: str, _query: str, **_kw: Any) -> list[GitHubItem]:
        return [_issue(repo, 4, "Crash")]

    def close(self) -> None:
        pass


def _issue(repo: str, number: int, title: str, when: str = "2026-11-01") -> GitHubItem:
    url = f"https://github.com/{repo}/issues/{number}"
    return GitHubItem(number, title, "open", url, False, updated_at=when)


class FakeApi:
    def __init__(self, answers: dict[tuple[str, str], Any]) -> None:
        self.answers = answers
        self.sent: list[tuple[str, str, Any]] = []

    def rest(self, method: str, path: str, *, body: Any = None, query: Any = None) -> Any:
        if method != "GET":
            self.sent.append((method, path, body))
            return SimpleNamespace(status=200, data={}, headers={})
        answer = self.answers.get((method, path))
        if isinstance(answer, Exception):
            raise answer
        if answer is None:
            raise RuntimeError(f"404 Not Found: {path}")
        return SimpleNamespace(status=200, data=answer, headers={})


def _inline(_name: str, work: Any, done: Any, failed: Any) -> None:
    try:
        result = work()
    except Exception as exc:  # noqa: BLE001
        failed(exc)
        return
    done(result)


@pytest.fixture
def bench(wx_session_app, quill_data_dir):
    said: list[str] = []
    provider = GitHubWorkbenchProvider(_Items(), "", announce=said.append)
    frame = WorkbenchFrame(provider, announce=said.append, run_background=_inline)
    frame.said = said  # type: ignore[attr-defined]
    yield frame
    frame.frame.Destroy()


def _go(frame: WorkbenchFrame, ref: NodeRef) -> None:
    assert frame.select(ref)
    if frame.current != ref:  # no event loop: deliver the selection ourselves
        frame._show_node(ref, remember=True)


def _sets() -> RepositorySets:
    return RepositorySets.load(account_key_for_token(TOKEN))


def _choose(*repos: str) -> None:
    sets = _sets()
    sets.set_repositories("My Repositories", list(repos))
    sets.save()


def _fake_fetch(asked: list[dict[str, Any]]) -> Any:
    def fake(_items: Any, kind: str, repos: Any, **kw: Any) -> across.AcrossResult:
        asked.append({"kind": kind, "repos": list(repos), **kw})
        if kind == "releases":
            rel = GitHubRelease(tag="v1", name="One", url="https://github.com/o/one/releases/v1")
            return across.AcrossResult(
                kind, (("o/one", rel),), (across.RepoOutcome("o/one", 1, limit=30),)
            )
        rows = (
            ("o/one", _issue("o/one", 4, "Crash", "2026-11-02")),
            ("o/two", _issue("o/two", 9, "Hang", "2026-11-03")),
            ("o/one", _issue("o/one", 5, "Slow", "2026-11-01")),
        )
        outcomes = (
            across.RepoOutcome("o/one", 2, more=True, limit=30),
            across.RepoOutcome("o/two", 1, limit=30),
            across.RepoOutcome("o/three", error="no access", limit=30),
        )
        return across.AcrossResult(kind, rows, outcomes)

    return fake


def test_named_sets_are_made_used_renamed_filtered_and_deleted(bench, monkeypatch) -> None:
    provider = bench.provider
    monkeypatch.setattr(provider, "_ask_text", lambda *_a, **_kw: "Docs sites")
    monkeypatch.setattr(provider, "_choose", lambda *_a: 0)  # from a list
    api = FakeApi({("GET", "/user/repos"): [{"full_name": "o/one"}, {"full_name": "o/two"}]})
    monkeypatch.setattr(provider, "github_api", lambda: api)
    offered: list[Any] = []
    monkeypatch.setattr(provider, "_checklist", lambda *a: offered.append(a) or ["o/one"])
    provider._do_across_new_set(NodeRef("", "across_sets"), None)
    assert offered[0][1] == ["o/one", "o/two"] and offered[0][2] == []
    assert bench.said[-1] == "1 repositories in Docs sites."
    _go(bench, NodeRef("", "across_sets"))
    (row,) = bench.rows
    assert row.kind == "repository_set" and row.title == "Docs sites"
    monkeypatch.setattr(provider, "_ask_text", lambda *_a, **_kw: "org:o topic:docs")
    provider._do_across_set_filter(NodeRef("", "across_sets"), row)
    assert _sets().filter_for("Docs sites") == "org:o topic:docs"
    monkeypatch.setattr(provider, "_ask_text", lambda *_a, **_kw: "Docs")
    provider._do_across_rename_set(NodeRef("", "across_sets"), row)
    assert _sets().current_name == "Docs"
    renamed = next(r for r in bench.rows if r.title == "Docs")
    provider._do_across_use_set(NodeRef("", "across_sets"), renamed)
    assert bench.said[-1] == "Using Docs."
    monkeypatch.setattr(provider, "_confirm", lambda *_a: False)
    provider._do_across_delete_set(NodeRef("", "across_sets"), renamed)
    assert "Docs" in _sets().names()  # No keeps it
    monkeypatch.setattr(provider, "_confirm", lambda *_a: True)
    provider._do_across_delete_set(NodeRef("", "across_sets"), renamed)
    assert _sets().names() == []
    assert provider.remove_command("repository_set") == "github.workbench.across_delete_set"


def test_a_filter_set_runs_the_search_and_keeps_what_it_found(bench, monkeypatch) -> None:
    sets = _sets()
    sets.set_filter("Family", "org:o topic:quill")
    sets.choose("Family")
    sets.save()
    api = FakeApi({("GET", "/search/repositories"): {"items": [{"full_name": "o/quill"}]}})
    monkeypatch.setattr(bench.provider, "github_api", lambda: api)
    _go(bench, NodeRef("", "across"))
    assert [r.repo for r in bench.rows] == ["o/quill"]
    assert _sets().repositories("Family") == ["o/quill"]


def test_category_rows_keep_every_repository_and_enter_then_back_returns(
    bench, monkeypatch
) -> None:
    provider = bench.provider
    _choose("o/one", "o/two", "o/three")
    asked: list[dict[str, Any]] = []
    monkeypatch.setattr(across, "fetch_across", _fake_fetch(asked))
    _go(bench, NodeRef("", "across_issues"))
    labels = [r.label for r in bench.rows]
    assert labels[-1] == "o/three: could not be read, no access"
    assert all(r.label.startswith(r.repo + ": ") for r in bench.rows)
    assert "o/one: first 2 shown, it has more; View More reads more" in provider.local_note
    # Group By Repository keeps the set's order, status rows in place.
    provider.view_choice("group")
    provider._view["group"] = "repository"
    bench.reload()
    assert [r.repo for r in bench.rows] == ["o/one", "o/one", "o/two", "o/three"]
    # ] and [ move between repositories.
    bench.focus_row(0)
    provider._do_next_repository(None, None)
    assert bench.selected_indices() == [2]
    event = SimpleNamespace(
        GetUnicodeKey=lambda: ord("]"), HasAnyModifiers=lambda: False, Skip=lambda: None
    )
    provider._on_list_char(event)
    assert bench.selected_indices() == [3]
    provider._do_previous_repository(None, None)
    assert bench.selected_indices() == [2]
    # View More reads 30 more from that repository only.
    bench.focus_row(0)
    provider._do_across_view_more(None, bench.rows[0])
    assert asked[-1]["per_repo_limits"] == {"o/one": 60}
    # Enter opens the exact item in its own repository; Back returns to the row.
    provider._view["group"] = "none"
    bench.show_groups([])
    bench.reload()
    index = next(i for i, r in enumerate(bench.rows) if r.title == "Hang")
    bench.focus_row(index)
    chosen = bench.rows[index]
    provider._do_across_open_source(None, chosen)
    assert bench.current == NodeRef("repository", "issues", "o/two")
    assert bench.filter.GetValue() == "number:9"
    bench.back()
    assert bench.current == NodeRef("", "across_issues")
    assert bench.selected_row().key == chosen.key


def test_releases_are_latest_only_until_asked(bench, monkeypatch) -> None:
    _choose("o/one")
    asked: list[dict[str, Any]] = []
    monkeypatch.setattr(across, "fetch_across", _fake_fetch(asked))
    _go(bench, NodeRef("", "across_releases"))
    assert asked[-1]["latest_only"] is True
    assert "Latest release only." in bench.provider.local_note
    bench.provider._do_across_all_releases(None, bench.rows[0])
    assert asked[-1]["latest_only"] is False


def test_issue_type_and_fields_are_read_shown_and_filtered(bench, monkeypatch) -> None:
    provider = bench.provider
    _choose("o/one", "o/two", "o/three")
    monkeypatch.setattr(across, "fetch_across", _fake_fetch([]))
    api = FakeApi({
        ("GET", "/repos/o/one/issues"): [{"number": 4, "type": {"name": "Bug"}}],
        ("GET", "/repos/o/two/issues"): RuntimeError("403 Forbidden"),
        ("GET", "/orgs/o/issue-fields"): [{"id": 1, "name": "Priority", "data_type": "text"}],
        ("GET", "/repos/o/one/issues/4/issue-field-values"): [{"field_id": 1, "value": "High"}],
        ("GET", "/repos/o/one/issues/5/issue-field-values"): [],
        ("GET", "/repos/o/two/issues/9/issue-field-values"): [],
    })
    monkeypatch.setattr(provider, "github_api", lambda: api)
    _go(bench, NodeRef("", "across_issues"))
    provider._do_across_issue_fields(None, bench.rows[0])
    crash = next(r for r in bench.rows if r.title == "Crash")
    assert crash.label.endswith(", type Bug")
    assert "Field Priority (text, field 1): High" in crash.detail
    slow = next(r for r in bench.rows if r.title == "Slow")
    assert "Field Priority (text, field 1): not set" in slow.detail
    hang = next(r for r in bench.rows if r.title == "Hang")
    assert "Issue type: could not be read: no access" in hang.detail
    bench.filter.ChangeValue("type:Bug")
    bench.apply_filter()
    assert [r.title for r in bench.rows if r.kind == "across_item"] == ["Crash"]
    assert "1 issues could not be checked" in provider.local_note


def _label_api() -> FakeApi:
    return FakeApi({
        ("GET", "/repos/o/one"): {"default_branch": "main", "permissions": {"push": True}},
        ("GET", "/repos/o/two"): {"default_branch": "main", "permissions": {"push": True}},
        ("GET", "/repos/o/one/labels"): [{"name": "bug", "color": "d73a4a"}],
        ("GET", "/repos/o/two/labels"): [{"name": "bug", "color": "ffffff"}],
        ("GET", "/repos/o/one/labels/bug"): {"color": "d73a4a", "description": ""},
        ("GET", "/repos/o/two/labels/bug"): {"color": "ffffff", "description": ""},
    })


def test_labels_by_name_make_the_same_with_a_preview_and_a_result_each(bench, monkeypatch) -> None:
    provider = bench.provider
    _choose("o/one", "o/two")
    api = _label_api()
    monkeypatch.setattr(provider, "github_api", lambda: api)
    _go(bench, NodeRef("", "across_by_labels"))
    (row,) = bench.rows
    assert row.label == "bug: in 2 of 2 repositories, 2 colours"
    assert "Variant 1" in row.detail and "Missing From: none of them" in row.detail
    shown: list[Any] = []
    monkeypatch.setattr(provider, "_choose", lambda *_a: 0)
    monkeypatch.setattr(provider, "_preview", lambda _t, plan, _y: shown.append(plan) or True)
    provider._do_across_make_same(None, row)
    assert shown and len(shown[0].runnable) == 1
    assert [s[0] for s in api.sent] == ["PATCH"]
    assert bench.details.GetValue().startswith("1 of 2 repositories changed.")
    assert "F5 reads the repositories again." in bench.said[-1]
    monkeypatch.setattr(provider, "_go_filtered", lambda *a: shown.append(a))
    provider._do_across_find_uses(None, row)
    assert shown[-1] == ("", "search_issues", "", 'label:"bug" repo:o/one repo:o/two')


def test_a_read_only_account_writes_nothing(bench, monkeypatch) -> None:
    from quill.core.github.permissions import AccessLevel

    provider = bench.provider
    _choose("o/one", "o/two")
    api = _label_api()
    monkeypatch.setattr(provider, "github_api", lambda: api)
    monkeypatch.setattr(provider, "access_level", lambda: AccessLevel.READ_ONLY)
    _go(bench, NodeRef("", "across_by_labels"))
    monkeypatch.setattr(provider, "_choose", lambda *_a: 0)
    provider._do_across_make_same(None, bench.rows[0])
    assert api.sent == [] and "read only" in bench.said[-1]


def test_the_fleet_lists_every_repository_with_its_revision(bench, monkeypatch) -> None:
    provider = bench.provider
    _choose("o/one", "o/gone")
    api = FakeApi({
        ("GET", "/repos/o/one"): {"default_branch": "main"},
        ("GET", "/repos/o/one/commits/main"): {"sha": "abcdef1234"},
        ("GET", "/repos/o/one/commits/abcdef1234/status"): {"state": "failure", "total_count": 1},
        ("GET", "/repos/o/one/pulls"): [],
        ("GET", "/repos/o/one/dependabot/alerts"): [],
    })
    monkeypatch.setattr(provider, "github_api", lambda: api)
    _go(bench, NodeRef("", "across_fleet"))
    one, gone = bench.rows
    assert one.label.startswith("o/one: main at abcdef1, checks failing, 0 open pull requests")
    assert "no releases" in one.label and "no open Dependabot alerts" in one.label
    assert gone.label.startswith("o/gone: could not be read, not found, or no access")
    assert "1 could not be read" in provider.local_note
    monkeypatch.setattr(provider, "_go_repository", lambda repo: bench.said.append(repo))
    provider._do_across_open_repository(None, one)
    assert bench.said[-1] == "o/one"


def test_every_repository_i_can_reach_is_bounded_and_says_so(bench, monkeypatch) -> None:
    from quill.core.github.repository_sets import EVERY

    provider = bench.provider
    monkeypatch.setattr(provider, "_ask_text", lambda *_a, **_kw: "Everything")
    monkeypatch.setattr(provider, "_choose", lambda *_a: 2)
    provider._do_across_new_set(NodeRef("", "across_sets"), None)
    assert _sets().filter_for("Everything") == EVERY
    page = [{"full_name": f"o/r{n}"} for n in range(100)]

    class Pages(FakeApi):
        def rest(self, method: str, path: str, *, body: Any = None, query: Any = None) -> Any:
            return SimpleNamespace(status=200, data=page, headers={})

    monkeypatch.setattr(provider, "github_api", lambda: Pages({}))
    _go(bench, NodeRef("", "across"))
    assert len(bench.rows) == 100  # the same 100 twice, kept once each
    assert "200 most recently pushed are used; GitHub may list more" in provider.local_note


def test_the_checklist_checks_adds_once_and_returns_the_checked(wx_session_app) -> None:
    import wx

    from quill.ui.github_repository_checklist import RepositoryChecklistDialog

    dialog = RepositoryChecklistDialog(
        None, title="Repositories", repositories=["o/one", "o/two"], checked=["o/two"]
    )
    try:
        assert dialog.chosen() == ["o/two"]
        dialog.add_box.ChangeValue("https://github.com/o/one")
        assert dialog.add() == "o/one"
        assert dialog.rows() == ["o/one", "o/two"] and dialog.chosen() == ["o/one", "o/two"]
        dialog.add_box.ChangeValue("o/three")
        dialog.add()
        assert dialog.chosen() == ["o/one", "o/two", "o/three"]
        dialog.add_box.ChangeValue("not a repo")
        assert dialog.add() == "" and len(dialog.rows()) == 3
        assert dialog.scroller.GetHelpText() and dialog.add_box.GetHelpText()
        # A11Y-SR-1: one real check box per repository, named owner/name.
        boxes = dialog.group.boxes
        assert all(isinstance(box, wx.CheckBox) for box in boxes.values())
        assert [box.GetLabel() for box in boxes.values()] == ["o/one", "o/two", "o/three"]
        assert boxes["o/three"].GetValue() is True
    finally:
        dialog.Destroy()


def test_an_empty_checklist_drops_its_placeholder_when_a_row_is_added(wx_session_app) -> None:
    from quill.ui.github_repository_checklist import RepositoryChecklistDialog

    dialog = RepositoryChecklistDialog(None, title="Repositories", repositories=[], checked=[])
    try:
        assert dialog.group._empty is not None
        dialog.add_box.ChangeValue("o/new")
        assert dialog.add() == "o/new" and dialog.chosen() == ["o/new"]
        assert dialog.group._empty is None
    finally:
        dialog.Destroy()


def test_across_writes_go_to_change_history_with_undo_where_a_sheet_can(bench, monkeypatch) -> None:
    from quill.core.github.change_log import ChangeLog

    provider = bench.provider
    _choose("o/one", "o/two")
    api = _label_api()
    monkeypatch.setattr(provider, "github_api", lambda: api)
    log = ChangeLog.load()
    monkeypatch.setattr(provider, "change_log", lambda: log)
    _go(bench, NodeRef("", "across_by_labels"))
    monkeypatch.setattr(provider, "_choose", lambda *_a: 0)
    monkeypatch.setattr(provider, "_preview", lambda *_a: True)
    provider._do_across_make_same(None, bench.rows[0])
    (entry,) = log.entries
    assert entry.kind == "label" and dict(entry.ident) == {"repo": "o/two", "name": "bug"}
    assert entry.can_undo and entry.summary.startswith("Across Repositories: made the same")
    assert [(f.key, f.before, f.after) for f in entry.fields][0] == ("colour", "ffffff", "d73a4a")
