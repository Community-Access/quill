"""A team from New Team... to Delete Team..., over recorded answers (complete.md 1.3).

"Verify ... team lifecycle": the Workbench's own doors for a team, each proved
end to end against a fake GitHub:

* list: Organizations > org > Teams and People > My Teams (``load_teams``);
* create: New Team... on an organization (quick ``new_team``);
* open and Properties: the Team sheet's reads, and its saves (name, which
  moves the team to its new slug, description, visibility, notifications);
* members: Add, Change Role and Remove on the sheet's Members page
  (``access.plan_*`` with the team scope), and its Pending Invitations;
* delete: Delete Team... (quick ``delete_team_now``);
* refusals: GitHub's 403 and 404 said plainly, Read Only and Safe Mode at the
  level gate, and a member who is not a maintainer locked with the reason.

Choosing a parent, and giving a team repositories from its sheet, are
PR #1961's (``sheets_teams``); this file proves what main has.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from quill.core.github.access import parse_row, plan_add, plan_change, plan_remove
from quill.core.github.permissions import AccessLevel, AccessStore, ViewerContext
from quill.core.github.quick_actions import QuickError
from quill.core.github.quick_table_org import ORG_QUICK
from quill.core.github.rest_transport import GitHubRestError, RestResponse
from quill.core.github.sheet_catalog import SHEETS, context_for, target_for
from quill.core.github.sheet_engine import load, locked_fields, plan, save
from quill.core.github.sheets_teams import TEAM, team_privacy
from quill.core.github.write_gate import command_refusal, gated_tier
from quill.core.workbench.properties import FieldChange
from tests.github_api_fake import FakeGitHubApi

_QUICK = {q.verb: q for q in ORG_QUICK}
_P = "github.workbench."
IDENT = {"org": "acme", "team": "docs", "me": "jeff"}


class _TeamApi(FakeGitHubApi):
    """The fake, with the members list answered by its ``role`` query."""

    def __init__(self) -> None:
        super().__init__()
        self.by_role: dict[str, Any] = {}

    def rest(self, method: str, path: str, *, body: Any = None, query: Any = None) -> RestResponse:
        role = (query or {}).get("role")
        if method == "GET" and role and path.endswith("/members") and role in self.by_role:
            self.calls.append((method, path, None))
            return RestResponse(200, {}, self.by_role[role])
        return super().rest(method, path, body=body, query=query)


def _team_json(**changes: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": 7,
        "name": "Docs",
        "slug": "docs",
        "description": "Writes the guide.",
        "privacy": "closed",
        "notification_setting": "notifications_enabled",
        "parent": {"slug": "writers", "name": "Writers"},
        "members_count": 2,
        "repos_count": 1,
        "created_at": "2026-11-01T10:00:00Z",
        "html_url": "https://github.com/orgs/acme/teams/docs",
    }
    data.update(changes)
    return data


@pytest.fixture
def api() -> _TeamApi:
    fake = _TeamApi()
    state = {"team": _team_json()}

    def on_write(method: str, path: str, body: Any) -> None:
        if method == "PATCH" and path == "/orgs/acme/teams/docs" and body:
            team = dict(state["team"])
            for key in ("name", "description", "privacy", "notification_setting"):
                if key in body:
                    team[key] = body[key]
            if "name" in body:
                team["slug"] = str(body["name"]).lower().replace(" ", "-")
            state["team"] = team

    fake.on_write = on_write
    fake.answer("GET", "/orgs/acme/teams/docs", lambda: state["team"])
    fake.answer("GET", "/orgs/acme/teams/doc-writers", lambda: state["team"])
    fake.answer("GET", "/user/memberships/orgs/acme", {"role": "member", "state": "active"})
    fake.answer("GET", "/orgs/acme/teams/docs/memberships/jeff", {"role": "maintainer"})
    fake.by_role = {"maintainer": [{"login": "jeff"}], "member": [{"login": "kelly"}]}
    fake.answer(
        "GET", "/orgs/acme/teams/docs/repos", [{"full_name": "acme/guide", "role_name": "write"}]
    )
    fake.answer("GET", "/orgs/acme/teams/docs/teams", [{"name": "Translators"}])
    fake.answer(
        "GET",
        "/orgs/acme/teams/docs/team-sync/group-mappings",
        {"groups": [{"group_name": "Okta docs"}]},
    )
    fake.answer_graphql(
        "reviewRequestDelegation",
        {"organization": {"team": {"id": "T_docs", "viewerCanAdminister": True,
                                   "reviewRequestDelegationEnabled": False,
                                   "projectsV2": {"nodes": [{"title": "Guide"}]}}}},
    )  # fmt: skip
    fake.state = state  # type: ignore[attr-defined]
    return fake


# -- list ------------------------------------------------------------------------------


def test_the_teams_list_names_each_team_its_parent_and_visibility_in_the_sheets_words() -> None:
    pytest.importorskip("wx")
    from quill.ui.github_workbench_tools import GitHubWorkbenchToolsMixin

    fake = FakeGitHubApi()
    fake.answer("GET", "/orgs/acme/teams", [
        {"name": "Docs", "slug": "docs", "privacy": "closed", "parent": {"name": "Writers"},
         "html_url": "https://github.com/orgs/acme/teams/docs"},
        {"name": "Security", "slug": "security", "privacy": "secret", "parent": None},
    ])  # fmt: skip
    tools = SimpleNamespace(github_api=lambda: fake)
    rows = GitHubWorkbenchToolsMixin.load_teams(tools, "teams:organization", "acme")  # type: ignore[arg-type]
    assert [r.label for r in rows] == ["Docs, child of Writers, visible", "Security, secret"]
    assert (rows[0].kind, rows[0].key, rows[0].repo) == ("team", "docs", "acme")
    # GitHub's "closed" is never said: the sheet calls it visible too.
    assert team_privacy({"privacy": "closed"}) == "visible"


def test_a_team_row_opens_the_team_sheet() -> None:
    from quill.core.github.explore_models import ExploreRow

    row = ExploreRow(
        "Docs, visible", "", "https://github.com/orgs/acme/teams/docs", "acme", "team", "docs"
    )
    target = target_for(row, "acme")
    assert target is not None and target.kind == "team"
    assert target.ident == {"org": "acme", "team": "docs"}
    assert SHEETS["team"] is TEAM


# -- create ------------------------------------------------------------------------------


def test_new_team_sends_name_visibility_and_description_and_says_what_it_made() -> None:
    fake = FakeGitHubApi()
    fake.answer("POST", "/orgs/acme/teams", {"name": "Docs", "slug": "docs"})
    quick = _QUICK["new_team"]
    ctx = {"org": "acme", "team": "Docs", "privacy": "closed", "about": "Writes the guide."}
    said = quick.said(quick.run(fake, ctx), ctx)
    assert fake.writes() == [
        ("POST", "/orgs/acme/teams",
         {"name": "Docs", "privacy": "closed", "description": "Writes the guide."}),
    ]  # fmt: skip
    assert said == "Made the team Docs."
    assert quick.reload and quick.tier == "A" and quick.need == "org:member"


def test_new_team_without_a_description_sends_none() -> None:
    fake = FakeGitHubApi()
    quick = _QUICK["new_team"]
    quick.run(fake, {"org": "acme", "team": "Docs", "privacy": "secret", "about": ""})
    assert fake.writes() == [("POST", "/orgs/acme/teams", {"name": "Docs", "privacy": "secret"})]


@pytest.mark.parametrize(
    ("status", "words"),
    [(403, "GitHub refused"), (404, "does not show that to you"), (422, "could not do it")],
)
def test_new_team_refused_by_github_is_said_plainly(status: int, words: str) -> None:
    fake = FakeGitHubApi()
    fake.answer("POST", "/orgs/acme/teams", GitHubRestError("Name must be unique", status=status))
    with pytest.raises(QuickError, match=words):
        _QUICK["new_team"].run(fake, {"org": "acme", "team": "Docs", "privacy": "closed"})


# -- open and Properties -----------------------------------------------------------------


def test_the_team_sheet_reads_every_page(api: _TeamApi) -> None:
    loaded = load(api, TEAM, IDENT)
    values = loaded.values
    assert (values["name"], values["slug"], values["privacy"]) == ("Docs", "docs", "visible")
    assert values["parent"] == "writers" and values["notifications"] is True
    assert values["you_maintain"] == "You are a maintainer of this team."
    assert values["maintainers"] == ("jeff, maintainer",)
    assert values["members"] == ("kelly, member",)
    assert values["team_repos"] == ("acme/guide, repository, write, team",)
    assert values["children"] == ("Translators",)
    assert values["idp_groups"] == ("Okta docs",)  # was never filled: read under "groups"
    assert values["projects"] == ("Guide",)
    assert values["your_org_role"] == "member"
    assert loaded.missing == ()


def test_members_and_repositories_ask_for_a_full_page() -> None:
    queries = {r.path: r.query(IDENT) for r in TEAM.reads if r.query is not None}
    assert queries["/orgs/{org}/teams/{team}/repos"] == {"per_page": "100"}
    roles = [r.query(IDENT) for r in TEAM.reads if r.path.endswith("/members") and r.query]
    assert {"role": "maintainer", "per_page": "100"} in roles
    assert {"role": "member", "per_page": "100"} in roles


def test_a_team_github_will_not_show_you_is_refused_on_open() -> None:
    fake = FakeGitHubApi()  # nothing recorded: every read is a 404
    with pytest.raises(GitHubRestError) as caught:
        load(fake, TEAM, IDENT)
    assert caught.value.status == 404


def test_renaming_moves_the_team_to_its_new_slug_and_proves_it(api: _TeamApi) -> None:
    loaded = load(api, TEAM, IDENT)
    change = FieldChange("name", "Name", "Docs", "Doc Writers")
    outcome = save(api, TEAM, IDENT, [change], loaded=loaded.values)
    assert ("PATCH", "/orgs/acme/teams/docs", {"name": "Doc Writers"}) in api.writes()
    assert [c.key for c in outcome.done] == ["name"] and not outcome.failed
    assert TEAM.ident_after(IDENT, outcome.done)["team"] == "doc-writers"


def test_visibility_and_notifications_go_in_githubs_words(api: _TeamApi) -> None:
    loaded = load(api, TEAM, IDENT)
    changed = [
        FieldChange("privacy", "Visibility", "visible", "secret"),
        FieldChange("notifications", "Notifications", True, False),
        FieldChange("description", "Description", "Writes the guide.", "The guide."),
    ]
    requests = plan(TEAM, IDENT, changed)
    assert [(r.method, r.path) for r in requests] == [("PATCH", "/orgs/acme/teams/docs")]
    assert requests[0].body == {
        "privacy": "secret",
        "notification_setting": "notifications_disabled",
        "description": "The guide.",
    }
    outcome = save(api, TEAM, IDENT, changed, loaded=loaded.values)
    assert sorted(c.key for c in outcome.done) == ["description", "notifications", "privacy"]


def test_a_save_github_refuses_is_reported_per_field_and_nothing_claimed(api: _TeamApi) -> None:
    loaded = load(api, TEAM, IDENT)
    api.answer(
        "PATCH", "/orgs/acme/teams/docs", GitHubRestError("Must have admin rights", status=403)
    )
    change = FieldChange("description", "Description", "Writes the guide.", "Gone")
    outcome = save(api, TEAM, IDENT, [change], loaded=loaded.values)
    assert outcome.done == []
    assert [c.key for c, _why in outcome.failed] == ["description"]
    assert "admin rights" in outcome.failed[0][1]


# -- who may change it -------------------------------------------------------------------


def test_a_member_who_is_not_a_maintainer_is_locked_with_the_reason() -> None:
    ctx = ViewerContext(org_role="member", team_role="member")
    locked = locked_fields(TEAM, ctx)
    assert set(locked) == set(TEAM.writes)
    assert "maintainer of the team or an owner of the organization" in locked["name"]


def test_an_organization_owner_not_on_the_team_may_change_it(api: _TeamApi) -> None:
    api.answer("GET", "/user/memberships/orgs/acme", {"role": "admin", "state": "active"})
    api.answers.pop(("GET", "/orgs/acme/teams/docs/memberships/jeff"))
    loaded = load(api, TEAM, IDENT)
    assert loaded.values["you_maintain"] == "You are not on this team."
    ctx = context_for(loaded.values, loaded.viewer, signed_in=True, login="jeff")
    assert ctx.org_role == "owner"
    assert locked_fields(TEAM, ctx) == {}  # was all locked: the sheet never read the org role


def test_read_only_locks_every_team_field_and_the_level_gate_refuses_its_commands(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("QUILL_SAFE_MODE", raising=False)
    ctx = ViewerContext(team_role="maintainer", org_role="owner", level=AccessLevel.READ_ONLY)
    assert all("read only in the Workbench" in why for why in locked_fields(TEAM, ctx).values())
    for verb in ("new_team", "delete_team_now", "access_add", "access_change", "access_remove"):
        said = command_refusal(_P + verb, lambda: AccessLevel.READ_ONLY)
        assert said.startswith("Cannot run ") and "this account is Read Only" in said, verb
    # Making a team gives access (tier 2) and deleting one destroys (tier 3): both need Full.
    assert command_refusal(_P + "new_team", lambda: AccessLevel.ORGANIZE)
    assert command_refusal(_P + "delete_team_now", lambda: AccessLevel.ORGANIZE)
    assert command_refusal(_P + "new_team", lambda: AccessLevel.FULL) == ""
    assert command_refusal(_P + "team_invitations", lambda: AccessLevel.READ_ONLY) == ""
    assert gated_tier(_P + "team_invitations") is None


def test_safe_mode_refuses_new_team_on_a_full_account(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QUILL_SAFE_MODE", "1")
    monkeypatch.setattr(AccessStore, "load", classmethod(lambda cls, path=None: cls(path)))
    from quill.core.github.permissions import effective_level

    said = command_refusal(_P + "new_team", lambda: effective_level(AccessLevel.FULL))
    assert "Safe Mode" in said


# -- members -----------------------------------------------------------------------------


def test_members_are_added_changed_and_removed_on_the_teams_own_memberships() -> None:
    added = plan_add("team", IDENT, "@kelly", "person", "member")
    assert (added.method, added.path, added.body) == (
        "PUT", "/orgs/acme/teams/docs/memberships/kelly", {"role": "member"}
    )  # fmt: skip
    assert added.words == "Add kelly to the team docs as a member."
    assert added.undo == ("DELETE", "/orgs/acme/teams/docs/memberships/kelly", None)

    row = parse_row("kelly, member")  # the Members page's row
    changed = plan_change("team", IDENT, row, "maintainer")
    assert (changed.path, changed.body) == (
        "/orgs/acme/teams/docs/memberships/kelly", {"role": "maintainer"}
    )  # fmt: skip
    assert changed.words == "Change kelly from member to maintainer on docs."
    assert changed.undo == ("PUT", "/orgs/acme/teams/docs/memberships/kelly", {"role": "member"})

    removed = plan_remove("team", IDENT, parse_row("jeff, maintainer"))
    assert (removed.method, removed.path) == ("DELETE", "/orgs/acme/teams/docs/memberships/jeff")
    assert removed.words.startswith("Remove jeff (maintainer) from docs.")
    assert removed.undo == ("PUT", "/orgs/acme/teams/docs/memberships/jeff", {"role": "maintainer"})


def test_pending_invitations_to_a_team_are_listed_or_said_to_be_none() -> None:
    fake = FakeGitHubApi()
    quick = _QUICK["team_invitations"]
    fake.answer("GET", "/orgs/acme/teams/docs/invitations", [
        {"login": "sam", "role": "direct_member", "inviter": {"login": "jeff"}},
    ])  # fmt: skip
    ctx = {"org": "acme", "key": "docs"}
    assert "sam, as direct_member, invited by jeff" in quick.said(quick.run(fake, ctx), ctx)
    fake.answer("GET", "/orgs/acme/teams/docs/invitations", [])
    assert quick.said(quick.run(fake, ctx), ctx) == "Nobody is waiting to join this team."


# -- delete ------------------------------------------------------------------------------


def test_delete_team_asks_first_says_child_teams_go_too_and_deletes_by_slug() -> None:
    fake = FakeGitHubApi()
    quick = _QUICK["delete_team_now"]
    ctx = {"org": "acme", "key": "docs", "name": "Docs"}
    assert "every team inside it" in quick.confirm.format_map(ctx)
    said = quick.said(quick.run(fake, ctx), ctx)
    assert fake.writes() == [("DELETE", "/orgs/acme/teams/docs", None)]
    assert said == "Deleted the team Docs." and quick.reload and quick.tier == "D"
    # The sheet's Danger Zone says what the command does, not that child teams move up.
    danger = next(f for f in TEAM.sheet.fields() if f.key == "danger_note")
    assert "every team inside it" in danger.help and "move up" not in danger.help


def test_deleting_a_team_that_is_gone_or_not_yours_is_said() -> None:
    fake = FakeGitHubApi()
    quick = _QUICK["delete_team_now"]
    fake.answer("DELETE", "/orgs/acme/teams/docs", GitHubRestError("Not Found", status=404))
    with pytest.raises(QuickError, match="does not show that to you, or it is gone"):
        quick.run(fake, {"org": "acme", "key": "docs"})
    fake.answer("DELETE", "/orgs/acme/teams/docs", GitHubRestError("Forbidden", status=403))
    with pytest.raises(QuickError, match="GitHub refused"):
        quick.run(fake, {"org": "acme", "key": "docs"})
