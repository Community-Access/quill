"""Your account's and an organization's objects, list to delete, over recorded answers.

complete.md 1.3, "Verify ... account/organization objects". The doors proved
here, each end to end against a fake GitHub:

* the Organization sheet: open (every page), Properties saves (profile, the
  base permission, member privileges, Actions, showing your membership), who
  may change what, and an organization GitHub will not show;
* an organization's lists through the resource engine: Members (invite,
  remove), Invitations (invite by email, cancel), Blocked People (block,
  unblock) and Outside Collaborators (remove); Make Someone an Outside
  Collaborator...;
* your own lists: email addresses, social accounts and blocked people; your
  followers, which cannot be removed;
* refusals: GitHub's 403 and 404 said plainly, Read Only at the level gate.

Keys, your status, star lists and your profile already have their own
lifecycle tests (test_account_keys.py, test_user_status.py,
test_star_lists.py, test_profile.py); the You page's follow and the person
sheet's block are in test_github_you_page.py.
"""

from __future__ import annotations

from typing import Any

import pytest

from quill.core.github import resource_engine as engine
from quill.core.github.permissions import AccessLevel, ViewerContext
from quill.core.github.quick_actions import QuickError
from quill.core.github.quick_table_org import ORG_QUICK
from quill.core.github.resource_specs import spec_for
from quill.core.github.rest_transport import GitHubRestError
from quill.core.github.sheet_catalog import context_for
from quill.core.github.sheet_engine import load, locked_fields, plan, save
from quill.core.github.sheets_orgs import ORGANIZATION
from quill.core.github.write_gate import command_refusal
from quill.core.workbench.properties import FieldChange
from tests.github_api_fake import FakeGitHubApi

_P = "github.workbench."
_QUICK = {q.verb: q for q in ORG_QUICK}
IDENT = {"org": "acme", "me": "jeff"}


def _spec(key: str) -> engine.ResourceSpec:
    found = spec_for(key)
    assert found is not None, key
    return found


def _org_json(**changes: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "login": "acme",
        "name": "Acme",
        "description": "Makes things.",
        "email": "",
        "location": "Seattle",
        "blog": "",
        "default_repository_permission": "read",
        "two_factor_requirement_enabled": True,
        "public_repos": 3,
        "total_private_repos": 2,
        "members_can_create_public_repositories": True,
        "created_at": "2020-01-02T03:04:05Z",
        "html_url": "https://github.com/acme",
    }
    data.update(changes)
    return data


@pytest.fixture
def api() -> FakeGitHubApi:
    fake = FakeGitHubApi()
    state = {"org": _org_json()}

    def on_write(method: str, path: str, body: Any) -> None:
        if method == "PATCH" and path == "/orgs/acme" and body:
            state["org"] = {**state["org"], **body}

    fake.on_write = on_write
    fake.answer("GET", "/orgs/acme", lambda: state["org"])
    fake.answer("GET", "/user/memberships/orgs/acme", {"role": "admin", "state": "active"})
    fake.answer("GET", "/orgs/acme/members", [{"login": "jeff"}, {"login": "kelly"}])
    fake.answer("GET", "/orgs/acme/teams", [
        {"name": "Docs", "privacy": "closed"}, {"name": "Security", "privacy": "secret"},
    ])  # fmt: skip
    fake.answer("GET", "/orgs/acme/outside_collaborators", [{"login": "sam"}])
    fake.answer(
        "GET", "/orgs/acme/invitations", [{"email": "new@example.com", "role": "direct_member"}]
    )
    fake.answer("GET", "/orgs/acme/hooks", [{"config": {"url": "https://ci.example.com/hook"}}])
    fake.answer("GET", "/orgs/acme/actions/secrets", {"secrets": [{"name": "DEPLOY"}]})
    fake.answer("GET", "/orgs/acme/actions/permissions", {"enabled_repositories": "all"})
    fake.answer_graphql(
        "viewerIsFollowing", {"organization": {"id": "O_1", "viewerIsFollowing": False}}
    )
    fake.state = state  # type: ignore[attr-defined]
    return fake


# -- the Organization sheet: open --------------------------------------------------------


def test_the_organization_sheet_reads_its_pages_and_your_role(api: FakeGitHubApi) -> None:
    loaded = load(api, ORGANIZATION, IDENT)
    values = loaded.values
    assert (values["login"], values["name"], values["repositories"]) == ("acme", "Acme", 5)
    assert values["your_org_role"] == "owner"  # GitHub's "admin" is said as owner
    assert values["public_member"] is False  # 404 on public_members/jeff: not shown
    assert values["members"] == ("jeff", "kelly")
    assert values["teams"] == ("Docs, visible", "Security, secret")  # never "closed"
    assert values["outside"] == ("sam",)
    assert values["invitations"] == ("new@example.com, direct_member",)
    assert values["hooks"] == ("https://ci.example.com/hook",)
    assert values["secrets"] == ("DEPLOY",)
    assert values["base_permission"] == "read" and values["two_factor"] is True
    # Lists GitHub would not show (roles, variables, ...) are named, not shown as empty.
    assert "/orgs/{org}/organization-roles" in loaded.missing


def test_an_organization_github_will_not_show_is_refused_on_open() -> None:
    with pytest.raises(GitHubRestError) as caught:
        load(FakeGitHubApi(), ORGANIZATION, {"org": "nobody", "me": "jeff"})
    assert caught.value.status == 404


# -- the Organization sheet: Properties --------------------------------------------------


def test_profile_fields_go_in_one_patch_and_are_proven_by_a_re_read(api: FakeGitHubApi) -> None:
    loaded = load(api, ORGANIZATION, IDENT)
    changed = [
        FieldChange("description", "Description", "Makes things.", "Makes good things."),
        FieldChange("location", "Location", "Seattle", "Remote"),
        FieldChange("base_permission", "Base repository permission", "read", "none"),
    ]
    requests = plan(ORGANIZATION, IDENT, changed)
    assert [(r.method, r.path, r.body) for r in requests] == [
        ("PATCH", "/orgs/acme",
         {"description": "Makes good things.", "location": "Remote",
          "default_repository_permission": "none"}),
    ]  # fmt: skip
    outcome = save(api, ORGANIZATION, IDENT, changed, loaded=loaded.values)
    assert sorted(c.key for c in outcome.done) == ["base_permission", "description", "location"]
    assert outcome.not_taken == [] and outcome.failed == []


def test_showing_your_membership_and_actions_permissions_are_their_own_requests() -> None:
    changed = [
        FieldChange("public_member", "Show my membership publicly", False, True),
        FieldChange("allowed_actions", "Allowed actions", "all", "local_only"),
        FieldChange("actions_repositories", "Repositories that may use Actions", "all", "none"),
    ]
    sent = {(r.method, r.path): r.body for r in plan(ORGANIZATION, IDENT, changed)}
    assert ("PUT", "/orgs/acme/public_members/jeff") in sent
    assert sent[("PUT", "/orgs/acme/actions/permissions")] == {
        "allowed_actions": "local_only",
        "enabled_repositories": "none",
    }
    hide = plan(ORGANIZATION, IDENT, [FieldChange("public_member", "Show", True, False)])
    assert [(r.method, r.path) for r in hide] == [("DELETE", "/orgs/acme/public_members/jeff")]


def test_a_save_github_refuses_fails_that_field_and_claims_nothing(api: FakeGitHubApi) -> None:
    loaded = load(api, ORGANIZATION, IDENT)
    api.answer("PATCH", "/orgs/acme", GitHubRestError("Must be an organization owner", status=403))
    change = FieldChange("name", "Name", "Acme", "Acme Inc")
    outcome = save(api, ORGANIZATION, IDENT, [change], loaded=loaded.values)
    assert outcome.done == [] and [c.key for c, _ in outcome.failed] == ["name"]
    assert "organization owner" in outcome.failed[0][1]


def test_a_member_may_show_their_membership_but_not_change_the_organization(
    api: FakeGitHubApi,
) -> None:
    api.answer("GET", "/user/memberships/orgs/acme", {"role": "member", "state": "active"})
    loaded = load(api, ORGANIZATION, IDENT)
    ctx = context_for(loaded.values, loaded.viewer, signed_in=True, login="jeff")
    locked = locked_fields(ORGANIZATION, ctx)
    assert "public_member" not in locked and "following" not in locked
    assert "This needs the owner role in the organization. You are a member." in locked["name"]
    assert "base_permission" in locked and "allowed_actions" in locked


def test_read_only_locks_every_organization_field() -> None:
    ctx = ViewerContext(org_role="owner", level=AccessLevel.READ_ONLY)
    locked = locked_fields(ORGANIZATION, ctx)
    assert set(locked) == set(ORGANIZATION.writes)
    assert all("read only in the Workbench" in why for why in locked.values())


# -- an organization's lists -------------------------------------------------------------


def test_members_list_invite_and_remove() -> None:
    spec, fake = _spec("org_members"), FakeGitHubApi()
    fake.answer("GET", "/orgs/acme/members", [{"login": "kelly"}])
    rows = engine.fetch(fake, spec, "acme")
    assert [(r.label, r.key) for r in rows] == [("kelly.", "org_members:kelly")]
    fake.answer("PUT", "/orgs/acme/memberships/sam", {"state": "pending", "role": "member"})
    said = engine.create(fake, spec, "acme", {"username": "sam", "role": "member"})
    assert fake.writes()[-1] == ("PUT", "/orgs/acme/memberships/sam", {"role": "member"})
    # GitHub invites someone who is not a member yet: never "Added".
    assert said == "Invited sam. GitHub sends them an invitation to accept."
    fake.answer("PUT", "/orgs/acme/memberships/kelly", {"state": "active", "role": "admin"})
    assert engine.create(fake, spec, "acme", {"username": "kelly", "role": "admin"}) == (
        "Added the member kelly."
    )
    assert engine.delete(fake, spec, "acme", "kelly") == "Deleted the member kelly."
    assert fake.writes()[-1] == ("DELETE", "/orgs/acme/members/kelly", None)


def test_invitations_by_email_and_cancelled_by_id() -> None:
    spec, fake = _spec("org_invitations"), FakeGitHubApi()
    engine.create(fake, spec, "acme", {"email": "new@example.com", "role": "direct_member"})
    assert fake.writes()[-1] == (
        "POST", "/orgs/acme/invitations", {"email": "new@example.com", "role": "direct_member"}
    )  # fmt: skip
    engine.delete(fake, spec, "acme", "12")
    assert fake.writes()[-1] == ("DELETE", "/orgs/acme/invitations/12", None)


def test_blocking_and_unblocking_for_an_organization_and_for_you() -> None:
    for key, base in (("org_blocks", "/orgs/acme/blocks"), ("my_blocks", "/user/blocks")):
        spec, fake = _spec(key), FakeGitHubApi()
        fake.answer("GET", base, [{"login": "spammer"}])
        assert engine.fetch(fake, spec, "acme")[0].label == "spammer is blocked."
        assert engine.create(fake, spec, "acme", {"username": "spammer"}) == (
            "Added the blocked person spammer."
        )
        engine.delete(fake, spec, "acme", "spammer")
        assert fake.writes() == [
            ("PUT", f"{base}/spammer", {}),
            ("DELETE", f"{base}/spammer", None),
        ]


def test_outside_collaborators_are_removed_from_the_list_and_made_by_a_quick_command() -> None:
    spec, fake = _spec("outside_collaborators"), FakeGitHubApi()
    assert spec.create == ()  # made from a member, never invited from here
    engine.delete(fake, spec, "acme", "sam")
    assert fake.writes() == [("DELETE", "/orgs/acme/outside_collaborators/sam", None)]
    quick = _QUICK["make_outside_collaborator"]
    ctx = {"org": "acme", "who": "kelly"}
    assert "stop being a member" in quick.confirm.format_map(ctx)
    said = quick.said(quick.run(fake, ctx), ctx)
    assert fake.writes()[-1] == ("PUT", "/orgs/acme/outside_collaborators/kelly", {})
    assert said == "kelly is an outside collaborator now."


@pytest.mark.parametrize(
    ("status", "words"),
    [
        (403, "GitHub refused to delete the member. It needs you to administer this"),
        (404, "GitHub found nothing to delete the member, or will not show it to you."),
        (422, "GitHub could not delete the member"),
    ],
)
def test_an_organization_list_refused_by_github_is_said_plainly(status: int, words: str) -> None:
    fake = FakeGitHubApi()
    fake.answer("DELETE", "/orgs/acme/members/kelly", GitHubRestError("No", status=status))
    with pytest.raises(engine.ResourceError, match=words):
        engine.delete(fake, _spec("org_members"), "acme", "kelly")


def test_a_list_github_will_not_show_is_said_not_shown_as_empty() -> None:
    with pytest.raises(engine.ResourceError, match="list the members"):
        engine.fetch(FakeGitHubApi(), _spec("org_members"), "nobody")


# -- your own lists ----------------------------------------------------------------------


def test_your_email_addresses_add_and_delete_by_body() -> None:
    spec, fake = _spec("my_emails"), FakeGitHubApi()
    fake.answer("GET", "/user/emails", [
        {"email": "jeff@example.com", "primary": True, "verified": True, "visibility": "private"},
    ])  # fmt: skip
    assert engine.fetch(fake, spec, "")[0].label == (
        "jeff@example.com, primary, verified, private."
    )
    assert engine.create(fake, spec, "", {"emails": "new@example.com"}) == (
        "Added the email address new@example.com."
    )
    engine.delete(fake, spec, "", "old@example.com")
    assert fake.writes() == [
        ("POST", "/user/emails", {"emails": ["new@example.com"]}),
        ("DELETE", "/user/emails", {"emails": ["old@example.com"]}),
    ]


def test_your_social_accounts_add_and_delete_by_address() -> None:
    spec, fake = _spec("my_social_accounts"), FakeGitHubApi()
    engine.create(fake, spec, "", {"account_urls": "https://mastodon.social/@jeff"})
    engine.delete(fake, spec, "", "https://mastodon.social/@jeff")
    assert fake.writes() == [
        ("POST", "/user/social_accounts", {"account_urls": ["https://mastodon.social/@jeff"]}),
        ("DELETE", "/user/social_accounts", {"account_urls": ["https://mastodon.social/@jeff"]}),
    ]


def test_lists_github_cannot_change_offer_no_add_or_delete() -> None:
    for key in ("my_followers", "my_org_memberships", "org_public_members", "org_roles"):
        spec = _spec(key)
        assert spec.create == () and spec.delete is False, key
    fake = FakeGitHubApi()
    fake.answer("GET", "/user/followers", [])
    warnings: list[str] = []
    engine.fetch(fake, _spec("my_followers"), "", warnings)
    assert warnings == ["No followers."]  # no "Ctrl+N adds one" where nothing can be added


def test_an_address_github_refuses_to_add_is_said() -> None:
    fake = FakeGitHubApi()
    fake.answer("POST", "/user/emails", GitHubRestError("email is already in use", status=422))
    with pytest.raises(engine.ResourceError, match="could not add the email address") as caught:
        engine.create(fake, _spec("my_emails"), "", {"emails": "taken@example.com"})
    assert "email is already in use" in str(caught.value)
    with pytest.raises(engine.ResourceError, match="is needed"):
        engine.create(FakeGitHubApi(), _spec("my_emails"), "", {"emails": " "})


# -- the level gate ----------------------------------------------------------------------


@pytest.mark.parametrize(
    "verb",
    [
        "resource_new",
        "resource_edit",
        "resource_delete",
        "make_outside_collaborator",
        "email_visibility",
        "accept_membership",
        "access_add",
        "access_remove",
    ],
)
def test_read_only_refuses_every_account_and_organization_write(
    verb: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("QUILL_SAFE_MODE", raising=False)
    said = command_refusal(_P + verb, lambda: AccessLevel.READ_ONLY)
    assert said.startswith("Cannot run ") and "this account is Read Only" in said


def test_reading_an_organization_is_never_refused() -> None:
    for verb in ("invitation_teams", "my_org_activity", "my_interaction_limits"):
        assert command_refusal(_P + verb, lambda: AccessLevel.READ_ONLY) == ""


def test_the_quick_commands_refusals_are_said_plainly() -> None:
    fake = FakeGitHubApi()
    fake.answer("PUT", "/orgs/acme/outside_collaborators/kelly", GitHubRestError("x", status=403))
    with pytest.raises(QuickError, match="GitHub refused"):
        _QUICK["make_outside_collaborator"].run(fake, {"org": "acme", "who": "kelly"})
