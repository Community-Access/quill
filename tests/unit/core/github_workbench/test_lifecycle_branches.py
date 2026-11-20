"""Branches, rulesets and classic protection, end to end over recorded answers.

complete.md 1.3, "Verify ... branches/rulesets/protection": list, open,
Properties, create, change and delete, and the refusals (no permission, Read
Only, not found). What other files already prove is not repeated here:

- tags (make, delete, read): ``test_tags.py``;
- the Ruleset sheet's rules and whole-body PUT, and the classic summary:
  ``test_github_phase8_sheets.py``;
- an organization's rulesets (enforcement, history, delete): ``test_github_org_admin.py``;
- Delete Branch's typed confirmation: ``ui/test_github_workbench_items_actions.py``;
- New Branch from an issue: ``ui/test_github_workbench_development.py``;
- every branch and protection command refused at Read Only and Organize:
  ``ui/test_github_workbench_level_gate.py``.

Nothing here reaches GitHub.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from quill.core.github import repo_admin
from quill.core.github.items_provider import GitHubBranch
from quill.core.github.permissions import AccessLevel, ViewerContext
from quill.core.github.repo_admin import GitHubRepoAdminError, GitHubRepoAdminProvider
from quill.core.github.rest_transport import GitHubRestError
from quill.core.github.sheet_catalog import SHEETS, target_for
from quill.core.github.sheet_engine import load, locked_fields, plan, save, sentence
from quill.core.workbench.properties import FieldChange
from tests.github_api_fake import FakeGitHubApi

REPO = "o/r"


# ---------------------------------------------------------------------------
# Branches: list row -> sheet, rename, refusals
# ---------------------------------------------------------------------------


def _branch_json(name: str) -> dict[str, Any]:
    return {
        "name": name,
        "protected": name == "main",
        "commit": {
            "sha": "abc123",
            "commit": {
                "message": "Fix the build\n\nLonger body.",
                "author": {"name": "Kim", "date": "2026-11-09T14:05:00Z"},
            },
        },
        "_links": {"html": f"https://github.com/o/r/tree/{name}"},
    }


def _branch_api() -> tuple[FakeGitHubApi, dict[str, str]]:
    api = FakeGitHubApi()
    state = {"name": "feature"}
    api.answer("GET", "/repos/o/r/branches/feature", lambda: _branch_json(state["name"]))
    api.answer("GET", "/repos/o/r/branches/topic", lambda: _branch_json(state["name"]))
    api.answer(
        "GET",
        "/repos/o/r/rules/branches/feature",
        [{"type": "deletion"}, {"type": "non_fast_forward"}],
    )

    def on_write(method: str, path: str, body: Any) -> None:
        if (method, path) == ("POST", "/repos/o/r/branches/feature/rename"):
            state["name"] = body["new_name"]

    api.on_write = on_write
    return api, state


def test_a_branch_row_opens_its_sheet_with_the_rules_that_apply_as_sentences() -> None:
    api, _state = _branch_api()
    target = target_for(GitHubBranch("feature", "abc123"), REPO)
    assert target is not None and target.kind == "branch"
    assert dict(target.ident) == {"repo": REPO, "branch": "feature"}
    loaded = load(api, target.sheet, target.ident)
    assert loaded.values["message"] == "Fix the build"
    assert loaded.values["author"] == "Kim"
    assert loaded.values["rules_here"] == "the branch cannot be deleted; force pushes are blocked."


def test_a_branch_whose_rules_github_will_not_say_still_opens_and_says_so() -> None:
    api, _state = _branch_api()
    api.answers.pop(("GET", "/repos/o/r/rules/branches/feature"))
    loaded = load(api, SHEETS["branch"], {"repo": REPO, "branch": "feature"})
    assert loaded.values["name"] == "feature"
    assert loaded.values["rules_here"] == "GitHub did not say which rules apply."
    assert loaded.missing == ("/repos/{repo}/rules/branches/{branch}",)


def test_renaming_a_branch_posts_the_new_name_and_proves_it_under_that_name() -> None:
    api, _state = _branch_api()
    sheet = SHEETS["branch"]
    ident = {"repo": REPO, "branch": "feature"}
    loaded = load(api, sheet, ident)
    outcome = save(
        api, sheet, ident, [FieldChange("name", "Name", "feature", "topic")], loaded=loaded.values
    )
    assert api.writes() == [("POST", "/repos/o/r/branches/feature/rename", {"new_name": "topic"})]
    # The verify-after-save read the branch at its new name, not the old one.
    assert api.calls[-2][1] == "/repos/o/r/branches/topic"
    assert [c.key for c in outcome.done] == ["name"]
    assert sentence("Branch feature", outcome) == "Branch feature: name topic."
    assert sheet.ident_after(ident, outcome.done)["branch"] == "topic"


def test_a_rename_github_refuses_is_said_with_githubs_reason_and_never_claimed() -> None:
    api, _state = _branch_api()
    api.answer(
        "POST",
        "/repos/o/r/branches/feature/rename",
        GitHubRestError("Must have admin rights to Repository.", status=403),
    )
    ident = {"repo": REPO, "branch": "feature"}
    loaded = load(api, SHEETS["branch"], ident)
    outcome = save(
        api,
        SHEETS["branch"],
        ident,
        [FieldChange("name", "Name", "feature", "topic")],
        loaded=loaded.values,
    )
    assert outcome.done == []
    assert sentence("Branch feature", outcome) == (
        "Could not change name: Must have admin rights to Repository."
    )


def test_a_branch_that_is_gone_is_not_found_rather_than_shown_empty() -> None:
    api = FakeGitHubApi()
    with pytest.raises(GitHubRestError) as raised:
        load(api, SHEETS["branch"], {"repo": REPO, "branch": "gone"})
    assert raised.value.status == 404


def test_branch_rename_needs_write_access_and_full_in_the_workbench() -> None:
    sheet = SHEETS["branch"]
    assert (
        "read only in the Workbench"
        in locked_fields(sheet, ViewerContext(repo_role="admin", level=AccessLevel.READ_ONLY))[
            "name"
        ]
    )
    assert (
        "set to Organize in the Workbench"
        in locked_fields(sheet, ViewerContext(repo_role="admin", level=AccessLevel.ORGANIZE))[
            "name"
        ]
    )
    assert "write access" in locked_fields(sheet, ViewerContext(repo_role="read"))["name"]
    assert locked_fields(sheet, ViewerContext(repo_role="write")) == {}


# ---------------------------------------------------------------------------
# The default branch: the Repository sheet's General page
# ---------------------------------------------------------------------------


def test_changing_the_default_branch_patches_the_repository_and_is_proven() -> None:
    api = FakeGitHubApi()
    state = {"default_branch": "main"}
    api.answer("GET", "/repos/o/r", lambda: {"name": "r", "full_name": REPO, **state})
    api.on_write = lambda m, p, b: (
        state.update(b or {}) if (m, p) == ("PATCH", "/repos/o/r") else None
    )
    sheet = SHEETS["repository"]
    loaded = load(api, sheet, {"repo": REPO})
    change = FieldChange("default_branch", "Default branch", "main", "develop")
    outcome = save(api, sheet, {"repo": REPO}, [change], loaded=loaded.values)
    assert api.writes() == [("PATCH", "/repos/o/r", {"default_branch": "develop"})]
    assert [c.key for c in outcome.done] == ["default_branch"]


def test_a_default_branch_github_ignores_is_named_not_claimed() -> None:
    api = FakeGitHubApi()
    api.answer("GET", "/repos/o/r", {"name": "r", "full_name": REPO, "default_branch": "main"})
    sheet = SHEETS["repository"]
    loaded = load(api, sheet, {"repo": REPO})
    change = FieldChange("default_branch", "Default branch", "main", "no-such-branch")
    outcome = save(api, sheet, {"repo": REPO}, [change], loaded=loaded.values)
    assert outcome.done == [] and outcome.not_taken == [change]
    assert "did not change default branch" in sentence("o/r", outcome)


def test_the_default_branch_needs_admin_and_full() -> None:
    sheet = SHEETS["repository"]
    assert "default_branch" in locked_fields(sheet, ViewerContext(repo_role="write"))
    reason = locked_fields(sheet, ViewerContext(repo_role="admin", level=AccessLevel.ORGANIZE))
    assert "not access, settings or deleting" in reason["default_branch"]
    assert "default_branch" not in locked_fields(sheet, ViewerContext(repo_role="admin"))


# ---------------------------------------------------------------------------
# A repository ruleset: open, change, the refusals
# ---------------------------------------------------------------------------

RULESET: dict[str, Any] = {
    "id": 9,
    "name": "main",
    "target": "branch",
    "enforcement": "active",
    "conditions": {"ref_name": {"include": ["~DEFAULT_BRANCH"], "exclude": []}},
    "bypass_actors": [{"actor_type": "Team", "actor_id": 77, "bypass_mode": "pull_request"}],
    "rules": [
        {"type": "deletion"},
        {"type": "workflows", "parameters": {"workflows": [{"path": ".github/ci.yml"}]}},
    ],
}
IDENT = {"repo": REPO, "id": "9"}


def _ruleset_api() -> FakeGitHubApi:
    api = FakeGitHubApi()
    state: dict[str, Any] = {"ruleset": dict(RULESET)}
    api.answer("GET", "/repos/o/r/rulesets/9", lambda: state["ruleset"])

    def on_write(method: str, path: str, body: Any) -> None:
        if (method, path) == ("PUT", "/repos/o/r/rulesets/9"):
            state["ruleset"] = {"id": 9, **body}

    api.on_write = on_write
    return api


def test_a_ruleset_changes_enforcement_targets_and_rules_and_keeps_what_it_does_not_show() -> None:
    api = _ruleset_api()
    sheet = SHEETS["ruleset"]
    loaded = load(api, sheet, IDENT)
    assert loaded.values["rules"] == ("restrict deletion", "require workflows to pass")
    changes = [
        FieldChange("enforcement", "Enforcement", "active", "evaluate"),
        FieldChange("include", "Include", ("~DEFAULT_BRANCH",), ("main", "release/*")),
        FieldChange("exclude", "Exclude", (), ("release/old",)),
        FieldChange(
            "rules",
            "Rules",
            loaded.values["rules"],
            ("require workflows to pass", "block force pushes", "require status checks"),
        ),
        FieldChange("status_checks", "Required status checks", (), ("build",)),
    ]
    outcome = save(api, sheet, IDENT, changes, loaded=loaded.values)
    [(method, path, body)] = api.writes()
    assert (method, path) == ("PUT", "/repos/o/r/rulesets/9")
    assert body["enforcement"] == "evaluate"
    assert body["conditions"] == {
        "ref_name": {"include": ["main", "release/*"], "exclude": ["release/old"]}
    }
    assert body["bypass_actors"] == RULESET["bypass_actors"]  # a team, not on the sheet
    kinds = [rule["type"] for rule in body["rules"]]
    assert "deletion" not in kinds and "non_fast_forward" in kinds
    workflows = next(r for r in body["rules"] if r["type"] == "workflows")
    assert workflows == RULESET["rules"][1]  # its settings travel back untouched
    checks = next(r for r in body["rules"] if r["type"] == "required_status_checks")
    assert checks["parameters"]["required_status_checks"] == [{"context": "build"}]
    # Re-read: every change took, so every change is said.
    assert {c.key for c in outcome.done} == {c.key for c in changes}
    assert outcome.not_taken == [] and outcome.failed == []
    assert "Evaluate mode" in str(outcome.after["summary"])


def test_approvals_on_a_ruleset_without_a_pull_request_rule_add_one() -> None:
    api = _ruleset_api()
    sheet = SHEETS["ruleset"]
    loaded = load(api, sheet, IDENT)
    requests = plan(
        sheet,
        {**IDENT, "raw_json": str(loaded.values["raw_json"])},
        [FieldChange("approvals", "Approvals needed", 0, 2)],
    )
    body = requests[0].body or {}
    pr = next(r for r in body["rules"] if r["type"] == "pull_request")  # type: ignore[union-attr]
    assert pr["parameters"]["required_approving_review_count"] == 2


def test_a_ruleset_put_github_refuses_is_said_and_one_it_ignores_is_named() -> None:
    api = _ruleset_api()
    sheet = SHEETS["ruleset"]
    loaded = load(api, sheet, IDENT)
    api.answer("PUT", "/repos/o/r/rulesets/9", GitHubRestError("Not Found", status=404))
    change = FieldChange("enforcement", "Enforcement", "active", "disabled")
    outcome = save(api, sheet, IDENT, [change], loaded=loaded.values)
    assert sentence("Ruleset main", outcome) == "Could not change enforcement: Not Found"

    quiet = FakeGitHubApi()
    quiet.answer("GET", "/repos/o/r/rulesets/9", RULESET)  # GitHub said 200 and kept it
    outcome = save(quiet, sheet, IDENT, [change], loaded=load(quiet, sheet, IDENT).values)
    assert outcome.not_taken == [change]


def test_a_ruleset_changed_on_github_since_it_opened_is_a_conflict_and_nothing_is_sent() -> None:
    api = _ruleset_api()
    sheet = SHEETS["ruleset"]
    loaded = load(api, sheet, IDENT)
    api.answer("GET", "/repos/o/r/rulesets/9", {**RULESET, "enforcement": "disabled"})
    change = FieldChange("enforcement", "Enforcement", "active", "evaluate")
    outcome = save(api, sheet, IDENT, [change], loaded=loaded.values)
    assert [c.key for c in outcome.conflicts] == ["enforcement"]
    assert api.writes() == []


def test_a_ruleset_that_is_gone_is_not_found() -> None:
    with pytest.raises(GitHubRestError) as raised:
        load(FakeGitHubApi(), SHEETS["ruleset"], IDENT)
    assert raised.value.status == 404


@pytest.mark.parametrize("kind", ["ruleset", "branch_protection"])
def test_every_rule_field_needs_repository_admin_and_full(kind: str) -> None:
    sheet = SHEETS[kind]
    editable = set(sheet.editable_keys())
    assert set(locked_fields(sheet, ViewerContext(repo_role="maintain"))) == editable
    read_only = locked_fields(sheet, ViewerContext(repo_role="admin", level=AccessLevel.READ_ONLY))
    assert set(read_only) == editable
    assert all("read only in the Workbench" in reason for reason in read_only.values())
    organize = locked_fields(sheet, ViewerContext(repo_role="admin", level=AccessLevel.ORGANIZE))
    assert set(organize) == editable
    assert locked_fields(sheet, ViewerContext(repo_role="admin")) == {}


# ---------------------------------------------------------------------------
# Classic protection: the sheet, and the editor's Configure Branch Protection
# ---------------------------------------------------------------------------

PROTECTION: dict[str, Any] = {
    "required_status_checks": {"strict": False, "contexts": ["build"]},
    "enforce_admins": {"enabled": True},
    "required_pull_request_reviews": {
        "required_approving_review_count": 2,
        "dismiss_stale_reviews": True,
        "require_code_owner_reviews": True,
        "require_last_push_approval": True,
        "dismissal_restrictions": {"users": [{"login": "kim"}], "teams": [], "apps": []},
        "bypass_pull_request_allowances": {"users": [], "teams": [{"slug": "release"}]},
    },
    "restrictions": {"users": [{"login": "jeff"}], "teams": [{"slug": "core"}], "apps": []},
    "required_linear_history": {"enabled": True},
    "allow_force_pushes": {"enabled": False},
    "allow_deletions": {"enabled": False},
    "required_conversation_resolution": {"enabled": True},
    "block_creations": {"enabled": True},
    "lock_branch": {"enabled": False},
}


def test_the_protection_sheet_turns_reviews_and_checks_off_and_force_pushes_on() -> None:
    api = FakeGitHubApi()
    path = "/repos/o/r/branches/main/protection"
    api.answer("GET", path, PROTECTION)
    sheet = SHEETS["branch_protection"]
    ident = {"repo": REPO, "branch": "main"}
    loaded = load(api, sheet, ident)
    assert loaded.values["approvals"] == 2 and loaded.values["linear_history"] is True
    requests = plan(
        sheet,
        {**ident, "raw_json": str(loaded.values["raw_json"])},
        [
            FieldChange("approvals", "Approvals needed", 2, 0),
            FieldChange("status_checks", "Required status checks", ("build",), ()),
            FieldChange("allow_force_pushes", "Allow force pushes", False, True),
        ],
    )
    [request] = requests
    assert (request.method, request.path) == ("PUT", path)
    body = request.body or {}
    assert body["required_pull_request_reviews"] is None
    assert body["required_status_checks"] is None
    assert body["allow_force_pushes"] is True
    assert body["required_linear_history"] is True and body["enforce_admins"] is True
    # Allowing force pushes or deletion is the destructive tier: asked as such.
    assert sheet.writes["allow_force_pushes"].tier > sheet.writes["approvals"].tier


class _Protection:
    def __init__(self, raw: dict[str, Any]) -> None:
        self.raw_data = raw


class _Branch:
    def __init__(self, raw: dict[str, Any] | None) -> None:
        self.raw = raw
        self.sent: list[dict[str, Any]] = []

    def get_protection(self) -> _Protection:
        if self.raw is None:
            raise _GithubError(404, "Branch not protected")
        return _Protection(self.raw)

    def edit_protection(self, **settings: Any) -> None:
        self.sent.append(settings)


class _GithubError(Exception):
    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.data = {"message": message}


def _admin(monkeypatch: pytest.MonkeyPatch, branch: _Branch) -> GitHubRepoAdminProvider:
    repo = SimpleNamespace(get_branch=lambda _name: branch)
    client = SimpleNamespace(get_repo=lambda _name: repo, close=lambda: None)
    module = SimpleNamespace(
        Github=lambda auth=None: client,
        Auth=SimpleNamespace(Token=lambda token: token),
        GithubException=_GithubError,
    )
    monkeypatch.setattr(repo_admin, "_get_gh_module", lambda: module)
    return GitHubRepoAdminProvider("tok")


def test_configure_protection_keeps_every_setting_the_dialog_does_not_ask_about(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    branch = _Branch(PROTECTION)
    _admin(monkeypatch, branch).set_branch_protection(
        REPO, "main", required_approving_review_count=1, required_status_checks=("test",)
    )
    [sent] = branch.sent
    assert sent["required_approving_review_count"] == 1
    assert sent["contexts"] == ["test"] and sent["strict"] is False  # strict kept
    assert sent["enforce_admins"] is False  # the dialog's own answer
    # GitHub replaces protection whole: before this fix these were reset.
    assert sent["user_push_restrictions"] == ["jeff"]
    assert sent["team_push_restrictions"] == ["core"]
    assert sent["required_linear_history"] is True
    assert sent["required_conversation_resolution"] is True
    assert sent["block_creations"] is True
    assert sent["allow_force_pushes"] is False and sent["allow_deletions"] is False
    assert sent["dismiss_stale_reviews"] is True and sent["require_code_owner_reviews"] is True
    assert sent["require_last_push_approval"] is True
    assert sent["dismissal_users"] == ["kim"]
    assert sent["teams_bypass_pull_request_allowances"] == ["release"]


def test_configure_protection_with_no_reviews_or_checks_turns_those_rules_off(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    branch = _Branch(PROTECTION)
    _admin(monkeypatch, branch).set_branch_protection(
        REPO, "main", required_approving_review_count=None, enforce_admins=True
    )
    [sent] = branch.sent
    # Not sent at all: PyGithub then sends null, which turns the rule off. A None
    # count was sent before, as {"required_approving_review_count": null}, which
    # GitHub refuses.
    for key in (
        "required_approving_review_count",
        "dismiss_stale_reviews",
        "dismissal_users",
        "contexts",
        "strict",
    ):
        assert key not in sent
    assert sent["enforce_admins"] is True and sent["required_linear_history"] is True


def test_protecting_an_unprotected_branch_sends_only_what_was_asked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    branch = _Branch(None)
    _admin(monkeypatch, branch).set_branch_protection(
        REPO, "dev", required_approving_review_count=2, required_status_checks=("ci",)
    )
    assert branch.sent == [
        {
            "strict": True,
            "contexts": ["ci"],
            "enforce_admins": False,
            "required_approving_review_count": 2,
        }
    ]


def test_protection_github_refuses_is_said_plainly(monkeypatch: pytest.MonkeyPatch) -> None:
    branch = _Branch(None)

    def refuse(**_settings: Any) -> None:
        raise _GithubError(403, "Resource not accessible by integration")

    branch.edit_protection = refuse  # type: ignore[method-assign]
    monkeypatch.setattr(repo_admin, "github_exception_hint", lambda _exc: "")
    with pytest.raises(GitHubRepoAdminError) as raised:
        _admin(monkeypatch, branch).set_branch_protection(
            REPO, "main", required_approving_review_count=1
        )
    assert raised.value.args[0].startswith("Could not protect 'main' on o/r: Access denied.")
