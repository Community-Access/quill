"""Rulesets, organization people, teams, custom roles, the audit log and the access matrices.

complete.md 1.3: "Rulesets/protection management, organization/member/team
access, custom roles and audit logs" and "People/teams/settings/custom
properties/issue types: access and setting matrices with inherited-role
explanations". Everything here runs against recorded answers; nothing reaches
GitHub.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pytest

from quill.core.github import access, access_matrix, branch_protection, org_people
from quill.core.github.quick_actions import QuickError
from quill.core.github.resource_engine import ResourceError, delete, fetch
from quill.core.github.resource_specs import spec_for
from quill.core.github.rest_transport import GitHubRestError, RestResponse
from quill.core.github.rulesets import rule_details, ruleset_body, ruleset_values, summary
from quill.core.github.sheet_catalog import SHEETS, target_for
from quill.core.github.sheet_engine import adopted, load, plan, save
from quill.core.workbench.properties import FieldChange
from tests.github_api_fake import FakeGitHubApi


class QueryApi(FakeGitHubApi):
    """A recorded API that also tells reads apart by their query (?role=admin)."""

    def __init__(self) -> None:
        super().__init__()
        self.by_query: dict[tuple[str, str, str], Any] = {}

    def answer_query(self, path: str, query: Mapping[str, str], data: Any) -> None:
        self.by_query[("GET", path, _q(query))] = data

    def rest(self, method: str, path: str, *, body: Any = None, query: Any = None) -> RestResponse:
        key = (method, path, _q(query or {}))
        if key in self.by_query:
            self.calls.append((method, path, None))
            data = self.by_query[key]
            if isinstance(data, BaseException):
                raise data
            return RestResponse(200, {}, data)
        return super().rest(method, path, body=body, query=query)


def _q(query: Mapping[str, str]) -> str:
    return "&".join(f"{k}={v}" for k, v in sorted(query.items()) if k not in ("per_page",))


# ---------------------------------------------------------------------------
# Rulesets: every rule GitHub returns, the repositories, who may bypass
# ---------------------------------------------------------------------------

ORG_RULESET = {
    "id": 5,
    "name": "Protect main",
    "target": "branch",
    "enforcement": "active",
    "conditions": {
        "ref_name": {"include": ["~DEFAULT_BRANCH"], "exclude": []},
        "repository_property": {
            "include": [{"name": "tier", "property_values": ["gold"], "source": "custom"}],
            "exclude": [],
        },
    },
    "bypass_actors": [
        {"actor_type": "Team", "actor_id": 77, "bypass_mode": "pull_request"},
        {"actor_type": "OrganizationAdmin", "actor_id": 1, "bypass_mode": "always"},
    ],
    "rules": [
        {"type": "file_path_restriction", "parameters": {"restricted_file_paths": ["secrets/*"]}},
        {"type": "max_file_size", "parameters": {"max_file_size": 10}},
        {"type": "copilot_code_review", "parameters": {"review_on_push": True}},
        {"type": "brand_new_rule", "parameters": {"some_setting": 3, "flag": False}},
    ],
}


def test_every_rule_github_returns_is_read_with_every_setting() -> None:
    lines = rule_details(ORG_RULESET)
    assert lines == (
        "Restrict file paths: restricted file paths: secrets/*",
        "Restrict file size: max file size: 10",
        "Request a Copilot code review: review on push: yes",
        "Brand new rule: some setting: 3; flag: no",
    )
    said = summary(ORG_RULESET)
    assert said.startswith("On the default branch in repositories with tier gold: ")
    assert "pushes may not change secrets/*" in said
    assert "files may be at most 10 MB" in said
    assert "organization admins, always" in said


def test_a_bypass_check_list_keeps_teams_and_apps() -> None:
    values = ruleset_values(ORG_RULESET)
    assert values["bypass_roles"] == ("organization admins",)
    body = ruleset_body(ORG_RULESET, {"bypass_roles": ("admins", "deploy keys")})
    actors = body["bypass_actors"]
    assert {"actor_type": "Team", "actor_id": 77, "bypass_mode": "pull_request"} in actors
    assert {"actor_type": "RepositoryRole", "actor_id": 5, "bypass_mode": "always"} in actors
    assert {"actor_type": "DeployKey", "actor_id": None, "bypass_mode": "always"} in actors
    assert not any(a["actor_type"] == "OrganizationAdmin" for a in actors)


def test_choosing_repositories_by_name_replaces_the_property_condition() -> None:
    body = ruleset_body(ORG_RULESET, {"repo_include": ("quill", "site-*"), "repo_protected": True})
    conditions = body["conditions"]
    assert "repository_property" not in conditions
    assert conditions["repository_name"] == {
        "include": ["quill", "site-*"],
        "exclude": [],
        "protected": True,
    }
    assert conditions["ref_name"] == ORG_RULESET["conditions"]["ref_name"]
    assert "quill and site-*; nobody may rename" in summary({**ORG_RULESET, **body})


def test_an_organization_ruleset_opens_from_its_row_and_saves_whole_to_the_org() -> None:
    from quill.core.github.explore_models import ExploreRow

    row = ExploreRow("Protect main: Active, on branches.", "", "", "acme", "resource",
                     "org_rulesets:5", title="Protect main")  # fmt: skip
    target = target_for(row)
    assert target is not None and target.kind == "org_ruleset"
    assert dict(target.ident) == {"org": "acme", "id": "5", "name": "Protect main"}
    api = FakeGitHubApi()
    api.answer("GET", "/orgs/acme/rulesets/5", ORG_RULESET)
    sheet = SHEETS["org_ruleset"]
    loaded = load(api, sheet, target.ident)
    assert loaded.values["repositories"] == "repositories with tier gold"
    assert "Brand new rule: some setting: 3; flag: no" in str(loaded.values["rule_details"])
    save(api, sheet, adopted(sheet, target.ident, loaded.values),
         [FieldChange("enforcement", "Enforcement", "active", "evaluate")],
         loaded=loaded.values, check_conflicts=False)  # fmt: skip
    method, path, body = api.writes()[0]
    assert (method, path) == ("PUT", "/orgs/acme/rulesets/5")
    assert body["enforcement"] == "evaluate"
    assert body["rules"] == ORG_RULESET["rules"]  # nothing GitHub sent is dropped
    assert sheet.writes["enforcement"].requirement == "org:owner"


def test_a_repositorys_rulesets_list_opens_each_ruleset_sheet() -> None:
    spec = spec_for("repo_rulesets")
    assert spec is not None
    api = FakeGitHubApi()
    api.answer("GET", "/repos/o/r/rulesets", [
        {"id": 9, "name": "main", "target": "branch", "enforcement": "evaluate",
         "source_type": "Repository", "source": "o/r"},
        {"id": 5, "name": "Protect main", "target": "branch", "enforcement": "active",
         "source_type": "Organization", "source": "o"},
    ])  # fmt: skip
    rows = fetch(api, spec, "o/r")
    assert [r.label for r in rows] == [
        "main: Evaluate only, on branches.",
        "Protect main: Active, on branches, from the organization o.",
    ]
    target = target_for(rows[0])
    assert target is not None and target.kind == "ruleset"
    assert dict(target.ident) == {"repo": "o/r", "id": "9", "name": "main"}


# ---------------------------------------------------------------------------
# Classic branch protection: nothing GitHub holds is dropped on a save
# ---------------------------------------------------------------------------

PROTECTION = {
    "required_status_checks": {"strict": True, "contexts": ["build"]},
    "enforce_admins": {"enabled": False},
    "required_pull_request_reviews": {
        "required_approving_review_count": 2,
        "dismiss_stale_reviews": True,
        "require_code_owner_reviews": False,
        "require_last_push_approval": False,
        "dismissal_restrictions": {"users": [{"login": "kim"}], "teams": [], "apps": []},
        "bypass_pull_request_allowances": {"users": [], "teams": [{"slug": "release"}]},
    },
    "required_signatures": {"enabled": False},
    "restrictions": {"users": [{"login": "jeff"}], "teams": [{"slug": "core"}], "apps": []},
    "allow_force_pushes": {"enabled": False},
    "allow_deletions": {"enabled": False},
    "block_creations": {"enabled": True},
    "lock_branch": {"enabled": False},
}


def test_classic_protection_keeps_who_may_push_and_sends_signatures_apart() -> None:
    api = FakeGitHubApi()
    path = "/repos/o/r/branches/main/protection"
    api.answer("GET", path, PROTECTION)
    sheet = SHEETS["branch_protection"]
    ident = {"repo": "o/r", "branch": "main"}
    loaded = load(api, sheet, ident)
    assert loaded.values["push_restrictions"] == "users jeff; teams core"
    assert loaded.values["dismissers"] == "users kim"
    assert loaded.values["pr_bypass"] == "teams release"
    assert loaded.values["block_creations"] is True
    requests = plan(sheet, adopted(sheet, ident, loaded.values), [
        FieldChange("code_owners", "Code owner", False, True),
        FieldChange("signatures", "Signed", False, True),
    ])  # fmt: skip
    assert [(r.method, r.path) for r in requests] == [
        ("PUT", path),
        ("POST", path + "/required_signatures"),
    ]
    body = requests[0].body or {}
    assert body["restrictions"] == {"users": ["jeff"], "teams": ["core"], "apps": []}
    reviews = body["required_pull_request_reviews"]
    assert reviews["require_code_owner_reviews"] is True
    assert reviews["dismissal_restrictions"]["users"] == ["kim"]
    assert reviews["bypass_pull_request_allowances"]["teams"] == ["release"]
    assert body["block_creations"] is True and body["required_status_checks"]["strict"] is True


def test_turning_off_signed_commits_alone_sends_only_that() -> None:
    found = branch_protection.requests("o/r", "main", PROTECTION, {"signatures": False})
    assert found == [("DELETE", "/repos/o/r/branches/main/protection/required_signatures", {})]


# ---------------------------------------------------------------------------
# Organization members: roles, two-factor, and the lockout checks
# ---------------------------------------------------------------------------


def _org_api(*, two_factor_hidden: bool = False) -> QueryApi:
    api = QueryApi()
    api.answer("GET", "/orgs/acme", {"login": "acme", "default_repository_permission": "read"})
    api.answer("GET", "/user", {"login": "me"})
    api.answer_query(
        "/orgs/acme/members", {}, [{"login": "me"}, {"login": "kim"}, {"login": "ana"}]
    )
    api.answer_query("/orgs/acme/members", {"role": "admin"}, [{"login": "me"}])
    api.answer_query(
        "/orgs/acme/members",
        {"filter": "2fa_disabled"},
        GitHubRestError("Forbidden", status=403) if two_factor_hidden else [{"login": "kim"}],
    )
    api.answer("GET", "/orgs/acme/outside_collaborators", [{"login": "zed"}])
    return api


def test_the_organization_sheet_says_each_members_role_and_two_factor() -> None:
    loaded = load(_org_api(), SHEETS["organization"], {"org": "acme", "me": "me"})
    assert loaded.values["members"] == (
        "me, person, owner, direct, two-factor on",
        "kim, person, member, direct, two-factor off",
        "ana, person, member, direct, two-factor on",
    )
    assert loaded.values["outside"] == ("zed, person, outside collaborator, repositories only",)
    hidden = load(_org_api(two_factor_hidden=True), SHEETS["organization"], {"org": "acme"})
    assert hidden.values["members"][1] == "kim, person, member, direct, two-factor not shown to you"


def test_the_members_node_names_roles_and_removing_the_last_owner_is_refused() -> None:
    api = _org_api()
    spec = spec_for("org_members")
    assert spec is not None and spec.typed_delete
    warnings: list[str] = []
    rows = fetch(api, spec, "acme", warnings)
    assert [r.label for r in rows] == [
        "me, owner, two-factor on.",
        "kim, member, two-factor off.",
        "ana, member, two-factor on.",
    ]
    with pytest.raises(ResourceError, match="leave nobody who can manage it"):
        delete(api, spec, "acme", "me")
    assert api.writes() == []
    assert delete(api, spec, "acme", "kim") == "Deleted the member kim."
    assert api.writes() == [("DELETE", "/orgs/acme/members/kim", None)]


def test_owners_and_yourself_are_never_made_outside_collaborators() -> None:
    api = _org_api()
    assert org_people.convert_problem(api, "acme", "me").startswith("That takes you out")
    api.answer_query("/orgs/acme/members", {"role": "admin"}, [{"login": "me"}, {"login": "ana"}])
    assert "is an owner of acme" in org_people.convert_problem(api, "acme", "ana")
    assert org_people.convert_problem(api, "acme", "kim") == ""
    assert "Ask ana" in org_people.member_problem(api, "acme", "me")


def test_access_rows_convert_and_remove_outside_collaborators_at_tier_three() -> None:
    from quill.core.github.permissions import WriteTier

    ident = {"org": "acme"}
    kim = access.AccessRow("kim", "person", "member", "direct, two-factor on")
    change = access.plan_change("organization", ident, kim, access.OUTSIDE)
    assert (change.method, change.path) == ("PUT", "/orgs/acme/outside_collaborators/kim")
    assert change.tier is WriteTier.DESTRUCTIVE and change.undo is None
    zed = access.parse_row("zed, person, outside collaborator, repositories only")
    gone = access.plan_remove("organization", ident, zed)
    assert (gone.method, gone.path) == ("DELETE", "/orgs/acme/outside_collaborators/zed")
    assert gone.tier is WriteTier.DESTRUCTIVE
    me = access.AccessRow("me", "person", "owner")
    rows = [me, kim]
    assert access.lockout_problem(rows, me, "me", new_role=access.OUTSIDE).startswith(
        "That takes you out"
    )


def test_a_team_keeps_a_maintainer_and_its_repositories_change_from_its_sheet() -> None:
    team = {"org": "acme", "team": "docs"}
    me = access.parse_row("me, maintainer")
    kim = access.parse_row("kim, member")
    managers = frozenset({"maintainer"})
    problem = access.lockout_problem([me, kim], me, "me", top=managers)
    assert problem.startswith("That would leave nobody who can manage it")
    assert access.lockout_problem([me, kim], kim, "me", top=managers) == ""
    repo = access.parse_row("acme/site, repository, admin, team")
    assert repo == access.AccessRow("acme/site", "repository", "admin", "team")
    add = access.plan_add("team", team, "acme/quill", "repository", "write")
    assert (add.method, add.path, add.body) == (
        "PUT",
        "/orgs/acme/teams/docs/repos/acme/quill",
        {"permission": "push"},
    )
    gone = access.plan_remove("team", team, repo)
    assert (gone.method, gone.path) == ("DELETE", "/orgs/acme/teams/docs/repos/acme/site")


def test_taking_admin_from_your_own_team_is_refused_when_it_is_your_way_in() -> None:
    api = _org_api()
    api.answer_query("/orgs/acme/members", {"role": "admin"}, [{"login": "ana"}])
    api.answer("GET", "/orgs/acme/teams/docs/memberships/me", {"state": "active"})
    api.answer_query("/repos/acme/site/collaborators", {"affiliation": "direct"}, [])
    said = org_people.team_repo_problem(api, "acme", "docs", "acme/site")
    assert said.startswith("That takes away your own admin access to acme/site")
    api.answer_query(
        "/repos/acme/site/collaborators",
        {"affiliation": "direct"},
        [{"login": "me", "permissions": {"admin": True}}],
    )
    assert org_people.team_repo_problem(api, "acme", "docs", "acme/site") == ""


def test_a_teams_parent_is_chosen_by_name_and_sent_as_its_id() -> None:
    sheet = SHEETS["team"]
    ident = {"org": "acme", "team": "docs"}
    choices = {"parent": {"eng": 12, "docs": 4}}
    (request,) = plan(sheet, ident, [FieldChange("parent", "Parent team", "", "eng")], choices)
    assert (request.method, request.path, request.body) == (
        "PATCH",
        "/orgs/acme/teams/docs",
        {"parent_team_id": 12},
    )
    (top,) = plan(sheet, ident, [FieldChange("parent", "Parent team", "eng", "")], choices)
    assert top.body == {"parent_team_id": None}


def test_a_new_team_can_start_under_a_parent_with_notifications_off() -> None:
    from quill.core.github.quick_tables import QUICK

    quick = next(q for q in QUICK if q.verb == "new_team")
    api = FakeGitHubApi()
    api.answer("GET", "/orgs/acme/teams/eng", {"id": 12, "slug": "eng"})
    ctx = {"org": "acme", "team": "Docs", "privacy": "closed", "parent": "eng",
           "notify": "notifications_disabled"}  # fmt: skip
    quick.run(api, ctx)
    assert api.writes() == [
        (
            "POST",
            "/orgs/acme/teams",
            {
                "name": "Docs",
                "privacy": "closed",
                "notification_setting": "notifications_disabled",
                "parent_team_id": 12,
            },
        )
    ]
    with pytest.raises(QuickError, match="secret team"):
        quick.run(api, {**ctx, "privacy": "secret"})


# ---------------------------------------------------------------------------
# Typed names and guards; nothing that is GitHub Enterprise Cloud only
# ---------------------------------------------------------------------------


def test_converting_is_typed_and_guarded_and_enterprise_only_commands_are_absent() -> None:
    from quill.core.github.quick_tables import QUICK, QUICK_ENDPOINTS

    by_verb = {q.verb: q for q in QUICK}
    convert = by_verb["make_outside_collaborator"]
    assert convert.tier == "D" and convert.typed == "who" and convert.guard is not None
    assert by_verb["two_factor_off"].tier == ""  # a read
    for endpoint in (
        "GET /orgs/{org}/audit-log",
        "GET /orgs/{org}/custom-repository-roles",
        "POST /orgs/{org}/organization-roles",
    ):
        assert endpoint not in QUICK_ENDPOINTS, endpoint


# ---------------------------------------------------------------------------
# The matrices: who has what, and where it comes from
# ---------------------------------------------------------------------------


def _matrix_api() -> QueryApi:
    api = QueryApi()
    api.answer("GET", "/orgs/acme", {"default_repository_permission": "read"})
    api.answer_query(
        "/orgs/acme/repos", {}, [{"full_name": "acme/quill"}, {"full_name": "acme/site"}]
    )
    api.answer_query("/orgs/acme/members", {}, [{"login": "jeff"}, {"login": "ana"}])
    api.answer_query("/orgs/acme/members", {"role": "admin"}, [])
    api.answer_query("/orgs/acme/outside_collaborators", {}, [{"login": "kim"}])
    api.answer_query("/orgs/acme/teams", {}, [
        {"slug": "maintainers", "name": "Maintainers"},
        {"slug": "docs", "name": "Docs", "parent": {"slug": "maintainers", "name": "Maintainers"}},
    ])  # fmt: skip
    api.answer_query("/orgs/acme/teams/maintainers/members", {}, [{"login": "jeff"}])
    api.answer_query("/orgs/acme/teams/maintainers/repos", {}, [
        {"full_name": "acme/quill", "role_name": "admin", "permissions": {"admin": True}},
    ])  # fmt: skip
    api.answer_query("/orgs/acme/teams/docs/members", {}, [{"login": "ana"}])
    api.answer_query("/orgs/acme/teams/docs/repos", {}, [
        {"full_name": "acme/site", "role_name": "Reviewer", "permissions": {"triage": True}},
    ])  # fmt: skip
    api.answer_query("/repos/acme/quill/collaborators", {"affiliation": "direct"}, [
        {"login": "jeff", "role_name": "write", "permissions": {"push": True}},
    ])  # fmt: skip
    api.answer_query(
        "/repos/acme/site/collaborators",
        {"affiliation": "direct"},
        [{"login": "kim", "role_name": "write", "permissions": {"push": True}}],
    )
    return api


def test_the_people_matrix_says_each_role_and_where_it_comes_from() -> None:
    warnings: list[str] = []
    spec = spec_for("access_people")
    assert spec is not None
    rows = fetch(_matrix_api(), spec, "acme", warnings)
    assert [r.label for r in rows] == [
        "ana on quill: Read, from the organization's base permission.",
        "ana on site: Reviewer, from team Docs; also Read from the organization's base permission.",
        "jeff on quill: Admin, from team Maintainers; also Write directly; also Read from "
        "the organization's base permission.",
        "jeff on site: Read, from the organization's base permission.",
        "kim on site: Write, directly, as an outside collaborator.",
    ]
    assert rows[2].key == "access_people:jeff:acme/quill"
    person = target_for(rows[2])
    assert person is not None and person.kind == "person" and person.ident["login"] == "jeff"
    assert warnings == []


def test_a_list_github_hides_is_named_never_shown_as_nobody() -> None:
    api = _matrix_api()
    api.answer_query(
        "/repos/acme/site/collaborators",
        {"affiliation": "direct"},
        GitHubRestError("Forbidden", status=403),
    )
    warnings: list[str] = []
    rows = access_matrix.people_rows(api, "acme", warnings)
    assert warnings == [
        "Direct access to 1 repository is shown only to its admins, so those rows leave "
        "direct access out."
    ]
    assert not any(r.label.startswith("kim") for r in rows)


def test_the_teams_matrix_and_the_custom_properties_matrix() -> None:
    warnings: list[str] = []
    teams = access_matrix.team_rows(_matrix_api(), "acme", warnings)
    assert [r.label for r in teams] == [
        "Docs on site: Reviewer, for 1 member, a child team of Maintainers.",
        "Maintainers on quill: Admin, for 1 member.",
    ]
    api = FakeGitHubApi()
    api.answer("GET", "/orgs/acme/properties/schema", [
        {"property_name": "tier"}, {"property_name": "areas"},
    ])  # fmt: skip
    api.answer("GET", "/orgs/acme/properties/values", [
        {"repository_full_name": "acme/quill", "properties": [
            {"property_name": "tier", "value": "gold"},
            {"property_name": "areas", "value": ["docs", "ui"]},
        ]},
        {"repository_full_name": "acme/site", "properties": []},
    ])  # fmt: skip
    spec = spec_for("org_property_values")
    assert spec is not None
    rows = fetch(api, spec, "acme")
    assert [r.label for r in rows] == [
        "quill: tier is gold; areas is docs and ui.",
        "site: tier is not set; areas is not set.",
    ]


def test_cells_rank_a_custom_role_by_its_base() -> None:
    found = access_matrix.OrgAccess("acme", base="none", members=["kim"], repos=["acme/x"])
    found.team_repos = {"docs": [("acme/x", "Reviewer", 1)]}
    found.team_members = {"docs": ["kim"]}
    found.direct = {"acme/x": [("kim", "read", 0)]}
    (cell,) = access_matrix.cells(found)
    assert cell.sentence() == "kim on x: Reviewer, from team docs; also Read directly."
