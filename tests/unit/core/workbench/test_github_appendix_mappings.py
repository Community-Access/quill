"""GATE-GITHUB-APPENDIX: the PRD's Appendix A, B and C are true against the code, and generated.

Appendix A and B ("nothing dropped"): every home a row names is a real node,
menu row, context-menu command, sheet page or field, Workbench option, editor
command or control; a retired window's control, an editor GitHub menu row or a
door that no row maps fails. Appendix C: every object has a sheet or a written
reason, every sheet kind and row type is claimed, and every filter qualifier is
answered here, sent to GitHub's search, or not yet with why. The PRD's tables
are written from the same rows, so they cannot drift.
"""

from __future__ import annotations

from typing import Any

import pytest

from quill.core.github import appendix_c_rows
from quill.core.github.explore_models import ExploreRow
from quill.core.github.items_provider import GitHubBranch, GitHubRelease
from quill.core.github.object_filters import filter_note, filter_rows
from quill.core.workbench.filters import parse
from quill.tools import github_appendix_reference as gate


def test_every_appendix_a_and_b_home_is_real_and_nothing_is_unmapped() -> None:
    assert gate.ab_problems() == []


def test_every_appendix_c_object_has_a_real_sheet_rows_and_filters() -> None:
    assert gate.c_problems() == []


def test_the_prds_tables_are_the_generated_ones() -> None:
    current = gate.PRD_PATH.read_text(encoding="utf-8")
    assert gate.render(current) == current, (
        "run python -m quill.tools.github_appendix_reference --write"
    )


@pytest.mark.parametrize(
    ("ref", "words"),
    [
        ("node:repository.nope", "no node"),
        ("menu:nope", "no menu row"),
        ("row:issue.nope", "no nope on issue rows"),
        ("sheet:issue.general.nope", "has no nope field"),
        ("sheet:nope.general", "no nope sheet"),
        ("pref:nope", "no Workbench option"),
        ("editor:github.nope", "no editor GitHub menu row"),
        ("door:github.nope", "opens nothing"),
        ("repoaction:github.nope", "Repository Actions... has no"),
        ("code:quill/ui/github_pr_review_menus.py#No Such Row", "has no"),
    ],
)
def test_a_home_that_disappears_is_named(ref: str, words: str) -> None:
    assert words in gate.resolve(ref)


def test_the_new_quick_commands_resolve() -> None:
    for verb in ("sync_fork", "use_template", "delete_repository"):
        assert gate.resolve(f"row:repository.{verb}") == ""


def test_a_new_control_in_a_retired_window_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    labels = gate.retired_labels() | {"Frobnicate..."}
    monkeypatch.setattr(gate, "retired_labels", lambda: labels)
    assert any("Frobnicate..." in p for p in gate.ab_problems())


def test_a_new_editor_menu_row_without_a_home_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    real = gate._registries

    def more() -> Any:
        found = real()
        found.editor = found.editor | {"github.brand_new_row"}
        return found

    monkeypatch.setattr(gate, "_registries", more)
    assert any("github.brand_new_row" in p for p in gate.ab_problems())


def test_an_object_dropped_from_appendix_c_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    kept = tuple(e for e in appendix_c_rows.APPENDIX_C if e.name != "Branch")
    monkeypatch.setattr(appendix_c_rows, "APPENDIX_C", kept)
    found = gate.c_problems()
    assert "the branch sheet is in no Appendix C object" in found
    assert "the row type branch is in no Appendix C object" in found


def test_a_promised_qualifier_the_list_cannot_answer_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    from quill.core.github.appendix_map import Filter, ObjectEntry

    extra = ObjectEntry("Branch again", ("branch",), ("branch",), (Filter("colour", "colour"),))
    monkeypatch.setattr(appendix_c_rows, "APPENDIX_C", (*appendix_c_rows.APPENDIX_C, extra))
    assert "Branch again: a branch list does not answer colour" in gate.c_problems()


def test_the_explore_resource_views_read_as_words() -> None:
    from quill.core.github import explore_views

    labels = dict(explore_views.VIEWS)
    assert labels["res_custom_properties"] == "Organization Custom Properties"
    assert labels["res_my_emails"] == "My Email Addresses"
    assert not any(word in label for label in labels.values() for word in ("ertys", "sss"))


# -- the qualifiers, over loaded rows ------------------------------------------------


def _branches() -> list[GitHubBranch]:
    return [
        GitHubBranch("main", "a1", protected=True, ahead=0, behind=0, commit_author="jo",
                     commit_date="2026-11-01T10:00:00Z"),
        GitHubBranch("release-1", "b2", protected=True, ahead=3, behind=1, commit_author="al",
                     commit_date="2026-10-01T10:00:00Z"),
        GitHubBranch("feature", "c3", ahead=5, behind=9, commit_author="jo",
                     commit_date="2026-09-01T10:00:00Z"),
    ]  # fmt: skip


def _names(text: str, rows: list[Any], row_type: str = "branch") -> list[str]:
    kept, _unknown = filter_rows(rows, parse(text).conditions, lambda _r: row_type)
    return [str(getattr(r, "name", "") or getattr(r, "label", "")) for r in kept]


def test_branch_qualifiers_filter_the_loaded_rows() -> None:
    rows = _branches()
    assert _names("name:release-*", rows) == ["release-1"]
    assert _names("protected:true", rows) == ["main", "release-1"]
    assert _names("-protected:true", rows) == ["feature"]
    assert _names("ahead:>=3", rows) == ["release-1", "feature"]
    assert _names("behind:<2", rows) == ["main", "release-1"]
    assert _names("author:jo committed:>2026-10", rows) == ["main"]
    assert _names("ahead:1..4", rows) == ["release-1"]


def test_release_flags_and_dates() -> None:
    rows = [
        GitHubRelease("v1", "One", draft=True, created_at="2026-01-02"),
        GitHubRelease("v2", "Two", prerelease=True, created_at="2026-06-02"),
    ]
    kept, _ = filter_rows(
        rows, parse("draft:false created:>=2026-03").conditions, lambda _r: "release"
    )
    assert [r.tag for r in kept] == ["v2"]


def test_explore_rows_answer_name_repository_owner_and_has_none() -> None:
    rows = [
        ExploreRow("bug", "d", "u", "acme/app", "label", "bug", "2026-11-02"),
        ExploreRow("docs", "d", "u", "jo/site", "label", "docs", ""),
    ]
    assert _names("owner:acme", rows, "label") == ["bug"]
    assert _names("-repo:acme/app", rows, "label") == ["docs"]
    assert _names("no:updated", rows, "label") == ["docs"]


def test_a_qualifier_no_row_answers_is_said_once() -> None:
    kept, unknown = filter_rows(_branches(), parse("colour:red name:main").conditions,
                                lambda _r: "branch")  # fmt: skip
    assert [r.name for r in kept] == ["main"]
    assert unknown == ["colour"]
    assert filter_note(3, 1, unknown, complete=False) == (
        "Filtered here: 1 of 3 loaded. Load All to be sure. Not a filter for this list: colour."
    )


def test_the_workbench_filters_a_branch_list_but_leaves_issues_to_github() -> None:
    from quill.core.workbench.tree import NodeSpec
    from quill.ui.github_workbench_view import GitHubWorkbenchViewMixin

    class _Host(GitHubWorkbenchViewMixin):
        def load_rows(self, _ref: Any, _node: Any, _query: Any) -> list[object]:
            return list(_branches())

        def row_type(self, _node: Any, _row: object) -> str:
            return "branch"

    host = _Host()
    branches = NodeSpec("branches", "Branches", loader="items:branches", row_type="branch")
    kept = host.load(None, branches, parse("protected:true"))
    assert [r.name for r in kept] == ["main", "release-1"]  # type: ignore[attr-defined]
    assert host.local_note.startswith("Filtered here: 2 of 3")
    issues = NodeSpec("issues", "Issues", loader="items:issues", row_type="issue")
    assert len(host.load(None, issues, parse("protected:true"))) == 3


# -- the commands that were only in the retired Explore window -------------------------


class _Reply:
    def __init__(self, data: Any) -> None:
        self.data = data


class _Api:
    def __init__(self, replies: dict[str, Any]) -> None:
        self.replies, self.sent = replies, []

    def rest(self, method: str, path: str, **kw: Any) -> _Reply:
        self.sent.append((method, path, kw.get("body")))
        return _Reply(self.replies.get(f"{method} {path}"))


def _quick(verb: str) -> Any:
    from quill.core.github.quick_tables import QUICK

    return next(q for q in QUICK if q.verb == verb)


def test_sync_fork_merges_the_upstream_into_the_default_branch() -> None:
    api = _Api({
        "GET /repos/me/app": {"default_branch": "trunk", "parent": {"full_name": "acme/app"}},
        "POST /repos/me/app/merge-upstream": {"merge_type": "fast-forward",
                                              "base_branch": "acme:trunk", "message": "ok"},
    })  # fmt: skip
    said = _quick("sync_fork").run(api, {"repo": "me/app"})
    assert api.sent[-1] == ("POST", "/repos/me/app/merge-upstream", {"branch": "trunk"})
    assert "acme:trunk" in said


def test_sync_fork_on_a_repository_that_is_no_fork_says_so() -> None:
    from quill.core.github.quick_actions import QuickError

    api = _Api({"GET /repos/me/app": {"default_branch": "main"}})
    with pytest.raises(QuickError, match="not a fork"):
        _quick("sync_fork").run(api, {"repo": "me/app"})
    assert [m for m, _p, _b in api.sent] == ["GET"]


def test_delete_repository_needs_the_name_typed_exactly() -> None:
    from quill.core.github.quick_actions import QuickError

    quick = _quick("delete_repository")
    assert quick.tier == "D"
    api = _Api({})
    with pytest.raises(QuickError, match="nothing was deleted"):
        quick.run(api, {"repo": "me/app", "typed": "me/ap"})
    assert api.sent == []
    quick.run(api, {"repo": "me/app", "typed": "Me/App"})
    assert api.sent == [("DELETE", "/repos/me/app", None)]


def test_use_template_makes_the_repository_it_was_asked_for() -> None:
    api = _Api({"POST /repos/acme/tpl/generate": {"full_name": "jo/new"}})
    quick = _quick("use_template")
    data = quick.run(api, {"repo": "acme/tpl", "new_name": " new ", "owner": "", "private": "true"})
    assert api.sent == [("POST", "/repos/acme/tpl/generate", {"name": "new", "private": True})]
    assert quick.said(data, {}) == "Created jo/new."
