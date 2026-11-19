"""GH-R-035: the Issue type and Into branch pickers end with New..., like every picker.

Both were typed text boxes, so a person had to know the exact name of a type
or branch and spell it. Now each is a list of what GitHub has, and New Issue
Type... or New Branch... makes one and selects it. "(none)" clears an issue
type, but never a pull request's Into branch, which always has to be one.
"""

from __future__ import annotations

from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.core.github.sheet_catalog import SHEETS  # noqa: E402
from quill.core.github.sheet_engine import load_options  # noqa: E402
from quill.core.github.sheets_items import _type_encode  # noqa: E402
from quill.core.workbench.properties import FieldChange, FieldKind  # noqa: E402
from quill.ui.workbench_properties_sheet import PropertiesSheet  # noqa: E402
from tests.github_api_fake import FakeGitHubApi  # noqa: E402
from tests.unit.ui.test_github_workbench_properties import (  # noqa: E402,F401
    _pick,
    _script,
    bench,
)

_TYPES = [
    {"id": 1, "name": "Bug", "is_enabled": True},
    {"id": 2, "name": "Feature", "is_enabled": True},
    {"id": 3, "name": "Old", "is_enabled": False},
]


def test_both_fields_are_pickers_with_new() -> None:
    issue = SHEETS["issue"].sheet.field("issue_type")
    base = SHEETS["pull_request"].sheet.field("base")
    assert (issue.kind, issue.create) == (FieldKind.CHOICE, "New Issue Type...")
    assert (base.kind, base.create) == (FieldKind.CHOICE, "New Branch...")


def test_the_choices_come_from_the_organization_and_the_repository() -> None:
    api = FakeGitHubApi()
    api.answer("GET", "/orgs/owner/issue-types", _TYPES)
    api.answer("GET", "/repos/owner/repo/branches", [{"name": "main"}, {"name": "release"}])
    for path in ("labels", "milestones", "assignees", "collaborators", "teams"):
        api.answer("GET", f"/repos/owner/repo/{path}", [])
    ident = {"repo": "owner/repo", "number": "1"}
    issue = load_options(api, SHEETS["issue"], ident)
    assert [name for name in issue["issue_type"] if name] == ["Bug", "Feature"]
    pull = load_options(api, SHEETS["pull_request"], ident)
    assert list(pull["base"]) == ["main", "release"]


def test_a_personal_repository_has_no_issue_types_and_keeps_the_typed_value() -> None:
    api = FakeGitHubApi()  # /orgs/owner/issue-types answers 404, as for a person
    for path in ("labels", "milestones", "assignees"):
        api.answer("GET", f"/repos/owner/repo/{path}", [])
    found = load_options(api, SHEETS["issue"], {"repo": "owner/repo", "number": "1"})
    assert "issue_type" not in found


def test_none_clears_the_issue_type_rather_than_naming_an_empty_one() -> None:
    assert _type_encode("", {}, {}) == {"type": None}
    assert _type_encode("Bug", {}, {}) == {"type": "Bug"}


def test_new_issue_type_creates_it_on_the_organization_and_uses_it(bench, monkeypatch) -> None:
    api = bench.provider.api
    api.answer("GET", "/orgs/owner/issue-types", _TYPES)
    monkeypatch.setattr(bench.provider, "_ask_text", lambda *_a: "Task", raising=False)
    shown: list[list[str]] = []

    def edit(sheet: PropertiesSheet) -> None:
        shown.append(list(sheet._items["issue_type"]))
        sheet._create(sheet.sheet.field("issue_type"))
        control = sheet.controls["issue_type"]
        assert control.GetString(control.GetSelection()) == "Task"
        sheet.apply(close=True)

    _script(monkeypatch, edit)
    _pick(bench, 1)
    bench.run("github.workbench.properties")
    assert "Bug" in shown[0] and "Old" not in shown[0]
    writes = api.writes()
    assert ("POST", "/orgs/owner/issue-types", {"name": "Task", "is_enabled": True}) in writes
    assert ("PATCH", "/repos/owner/repo/issues/1", {"type": "Task"}) in writes
    assert "Created Task." in bench.said


def _host(api: FakeGitHubApi) -> Any:
    from quill.ui.github_workbench_create import GitHubWorkbenchCreateMixin
    from quill.ui.github_workbench_properties import GitHubWorkbenchPropertiesMixin

    class Host(GitHubWorkbenchPropertiesMixin):
        def __init__(self) -> None:
            self.said: list[str] = []

        def github_api(self) -> FakeGitHubApi:
            return api

        def _say(self, text: str) -> None:
            self.said.append(text)

    assert issubclass(Host, GitHubWorkbenchCreateMixin)
    return Host()


def test_new_branch_starts_from_the_branch_it_merges_into_now() -> None:
    api = FakeGitHubApi()
    api.answer("GET", "/repos/owner/repo/git/ref/heads/release/2", {"object": {"sha": "abc123"}})
    host = _host(api)
    choices: dict[str, dict[str, object]] = {"base": {"main": "main", "release/2": "release/2"}}
    assert host._create_branch("owner/repo", "hotfix", "release/2", choices) == "hotfix"
    assert api.writes() == [
        ("POST", "/repos/owner/repo/git/refs", {"ref": "refs/heads/hotfix", "sha": "abc123"})
    ]
    assert choices["base"]["hotfix"] == "hotfix"
    assert host.said == ["Created hotfix from release/2."]


def test_new_branch_falls_back_to_the_default_branch() -> None:
    api = FakeGitHubApi()
    api.answer("GET", "/repos/owner/repo", {"default_branch": "trunk"})
    api.answer("GET", "/repos/owner/repo/git/ref/heads/trunk", {"object": {"sha": "def456"}})
    host = _host(api)
    assert host._create_branch("owner/repo", "next", "", {}) == "next"
    assert api.writes()[0][2] == {"ref": "refs/heads/next", "sha": "def456"}


def test_a_branch_that_exists_is_used_not_made_again() -> None:
    api = FakeGitHubApi()
    host = _host(api)
    assert host._create_branch("owner/repo", "main", "main", {"base": {"main": "main"}}) == "main"
    assert api.calls == []
    assert host.said == ["main already exists; using it."]


def test_a_branch_github_cannot_find_is_said_and_nothing_is_made() -> None:
    api = FakeGitHubApi()  # the ref read answers 404
    host = _host(api)
    assert host._create_branch("owner/repo", "x", "gone", {}) is None
    assert api.writes() == []
    assert host.said and host.said[0].startswith("Could not create x:")


def test_into_branch_cannot_be_set_to_none() -> None:
    api = FakeGitHubApi()
    host = _host(api)
    change = FieldChange("base", "Into branch", "main", "")
    host._apply_one(None, {}, [change], {}, None, True)
    assert api.calls == []
    assert host.said == [
        "A pull request always merges into a branch, so Into branch was left as it is."
    ]
