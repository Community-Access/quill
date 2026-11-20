"""Roles and Access answer from what GitHub returns, never from a guessed table (complete.md 1.3).

Each test records GitHub's answers and checks that the words shown come from
them: ``role_name`` from the collaborator-permission endpoint (a custom role
too), ``viewerPermission``, organization membership, teams, the rules on the
branch, the token's scopes, and, where GitHub will not say, an honest unknown.
"""

from __future__ import annotations

from quill.core.github import role_evidence as ev
from quill.core.github import role_reports as rr
from quill.core.github.access import bulk_plan
from quill.core.github.rest_transport import GitHubRestError, RestResponse
from tests.github_api_fake import FakeGitHubApi

REPO = "acme/web"


def _api() -> FakeGitHubApi:
    api = FakeGitHubApi()
    api.answer(
        "GET",
        f"/repos/{REPO}",
        {
            "permissions": {"admin": False, "maintain": False, "push": True, "pull": True},
            "owner": {"login": "acme", "type": "Organization"},
            "default_branch": "main",
        },
    )
    api.answer_graphql("viewerPermission", {"repository": {"viewerPermission": "WRITE"}})
    api.answer("GET", "/user/memberships/orgs/acme", {"role": "member", "state": "active"})
    api.answer("GET", "/orgs/acme", {"default_repository_permission": "read"})
    api.answer("GET", f"/repos/{REPO}/teams", [{"slug": "docs", "permission": "push"}])
    api.answer("GET", "/user/teams", [{"slug": "docs", "organization": {"login": "acme"}}])
    api.answer(
        "GET",
        f"/repos/{REPO}/rules/branches/main",
        [
            {
                "type": "pull_request",
                "ruleset_source_type": "Organization",
                "ruleset_source": "acme",
                "parameters": {"required_approving_review_count": 2},
            }
        ],
    )
    return api


def test_my_access_is_every_part_github_said_with_where_it_said_it() -> None:
    api = _api()
    api.answer(
        "GET",
        f"/repos/{REPO}/collaborators/kelly/permission",
        {"permission": "write", "role_name": "write"},
    )
    text = rr.my_access(api, REPO, "kelly", token="ghp_x", scopes_header="repo, read:org")
    assert f"You have write access to {REPO}. (GitHub: /repos/{REPO} permissions)" in text
    assert "viewerPermission is WRITE" in text
    assert "kelly's role on acme/web is write" in text
    assert "You are a member of acme" in text
    assert "base permission for members is read" in text
    assert "Through the team docs: write" in text
    assert "changes need a pull request (2 approving reviews), from the organization acme" in text
    assert "main has no classic branch protection" in text
    assert "scopes are repo, read:org" in text


def test_my_access_says_a_fine_grained_tokens_permissions_cannot_be_known() -> None:
    text = rr.my_access(_api(), REPO, "kelly", token="github_pat_abc", scopes_header=None)
    assert "fine-grained token. GitHub does not list its permissions" in text


def test_a_refusal_is_said_as_unknown_not_filled_in() -> None:
    api = _api()
    api.answer(
        "GET",
        f"/repos/{REPO}/collaborators/sam/permission",
        GitHubRestError(
            "Must have push access",
            status=403,
            headers={"x-accepted-github-permissions": "metadata=read"},
        ),
    )
    text = rr.why_cant_they(api, REPO, "sam", "merge pull requests", "main")
    assert "GitHub would not tell this account sam's role on acme/web (403)" in text
    assert "metadata=read" in text
    assert "cannot be known here" in text


def test_why_cant_they_reads_the_real_role_not_a_typed_one() -> None:
    api = _api()
    api.answer(
        "GET",
        f"/repos/{REPO}/collaborators/sam/permission",
        {"permission": "read", "role_name": "triage"},
    )
    text = rr.why_cant_they(api, REPO, "sam", "merge pull requests", "main")
    assert f"GitHub says sam's role on {REPO} is triage" in text
    assert "merge pull requests needs write" in text
    assert "documented defaults" in text


def test_why_cant_they_names_the_rule_that_stops_an_allowed_role() -> None:
    api = _api()
    api.answer(
        "GET",
        f"/repos/{REPO}/collaborators/sam/permission",
        {"permission": "admin", "role_name": "admin"},
    )
    text = rr.why_cant_they(api, REPO, "sam", "merge pull requests", "main")
    assert "What GitHub says can still stop it on main: changes need a pull request" in text


def test_a_custom_role_is_named_and_its_limits_said() -> None:
    api = _api()
    api.answer(
        "GET",
        f"/repos/{REPO}/collaborators/sam/permission",
        {"permission": "write", "role_name": "release-manager"},
    )
    text = rr.why_cant_they(api, REPO, "sam", "create releases", "")
    assert "release-manager is a custom role, built on write" in text
    assert "cannot be known from GitHub's API" in text


def test_view_as_role_says_its_source_and_who_has_the_role_here() -> None:
    api = _api()
    api.answer(
        "GET",
        f"/repos/{REPO}/collaborators",
        [
            {"login": "kelly", "role_name": "write"},
            {"login": "sam", "role_name": "write"},
            {"login": "ann", "role_name": "auditor"},
        ],
    )
    text = rr.role_report(api, "write", REPO)
    assert text.startswith(ev.DOCUMENTED)
    assert "GitHub says kelly, sam have write on acme/web." in text
    assert "custom role auditor" in text
    compared = rr.compare_report(api, "read", "write", REPO)
    assert compared.startswith(ev.DOCUMENTED) and "merge pull requests" in compared
    assert "GitHub says nobody has read on acme/web directly." in compared


def test_the_access_review_lists_effective_access_with_its_real_source() -> None:
    api = FakeGitHubApi()
    api.answer("GET", "/orgs/acme/repos", [{"full_name": REPO}])
    api.answer(
        "GET",
        f"/repos/{REPO}/collaborators",
        [
            {"login": "kelly", "role_name": "admin"},
            {"login": "sam", "role_name": "maintain"},
            {"login": "olly", "role_name": "read"},
        ],
    )
    api.answer(
        "GET",
        f"/repos/{REPO}/collaborators?affiliation=direct",
        [{"login": "kelly"}, {"login": "olly"}],
    )
    api.answer("GET", f"/repos/{REPO}/collaborators?affiliation=outside", [{"login": "olly"}])
    api.answer("GET", f"/repos/{REPO}/teams", [{"slug": "docs", "permission": "triage"}])
    rows = {r.name: r for r in rr.review_by_repository(api, "acme")[REPO]}
    assert (rows["kelly"].role, rows["kelly"].source) == ("admin", "direct")
    assert (rows["sam"].role, rows["sam"].source) == (
        "maintain",
        "through the organization or a team",
    )
    assert rows["olly"].source == "outside collaborator"
    assert (rows["docs"].kind, rows["docs"].role) == ("team", "triage")


def test_bulk_changes_preview_per_person_and_skip_what_is_already_so() -> None:
    api = FakeGitHubApi()
    api.answer(
        "GET",
        "/repos/acme/a/collaborators/kelly/permission",
        {"permission": "write", "role_name": "write"},
    )
    api.answer(
        "GET",
        "/repos/acme/b/collaborators/kelly/permission",
        {"permission": "write", "role_name": "maintain"},
    )
    api.answer("GET", "/repos/acme/c/collaborators/kelly/permission", {"permission": "none"})
    targets = [{"repo": "acme/a"}, {"repo": "acme/b"}, {"repo": "acme/c"}]
    changes = bulk_plan("repository", "kelly", "person", "maintain", targets)
    sending, lines = rr.bulk_preview(api, changes, "kelly", "person", "maintain", targets)
    assert lines == [
        "kelly on acme/a: write now, maintain after.",
        "kelly on acme/b: already maintain; nothing is sent.",
        "kelly on acme/c: no access now, maintain after.",
    ]
    assert [c.path for c in sending] == [
        "/repos/acme/a/collaborators/kelly",
        "/repos/acme/c/collaborators/kelly",
    ]
    assert sending[0].words == lines[0]


def test_a_teams_current_role_comes_from_the_team_repository_check() -> None:
    api = FakeGitHubApi()
    api.answer("GET", "/orgs/acme/teams/docs/repos/acme/a", {"role_name": "triage"})
    targets = [{"repo": "acme/a"}, {"repo": "acme/b"}]
    changes = bulk_plan("repository", "docs", "team", "write", targets)
    _sending, lines = rr.bulk_preview(api, changes, "docs", "team", "write", targets)
    assert lines == [
        "docs on acme/a: triage now, write after.",
        "docs on acme/b: no access now, write after.",
    ]


def test_compare_accounts_checks_each_token_is_whose_it_claims() -> None:
    mine = _api()
    mine.answer("GET", "/user", RestResponse(200, {"x-oauth-scopes": "repo"}, {"login": "kelly"}))
    mine.answer(
        "GET",
        f"/repos/{REPO}/collaborators/kelly/permission",
        {"permission": "admin", "role_name": "admin"},
    )
    theirs = FakeGitHubApi()
    theirs.answer("GET", "/user", {"login": "somebody-else"})
    first = rr.account_access(mine, "kelly (github.com)", "kelly", REPO, token="gho_x")
    second = rr.account_access(theirs, "kelly-test (github.com)", "kelly-test", REPO, token="gho_y")
    assert first.role == "admin" and "scopes are repo" in "\n".join(f.text for f in first.facts)
    assert second.identity_problem and "now belongs to somebody-else" in second.identity_problem
    text = rr.compare_accounts(REPO, first, second)
    assert "cannot be compared" in text
    assert not any(call[1].startswith("/repos") for call in theirs.calls)  # nothing read as them


def test_compare_accounts_says_what_one_may_do_that_the_other_may_not() -> None:
    first = rr.AccountAccess("kelly", "admin", ())
    second = rr.AccountAccess("kelly-test", "triage", ())
    text = rr.compare_accounts(REPO, first, second)
    assert "What kelly may do that kelly-test may not" in text
    assert "manage collaborators and teams" in text and ev.DOCUMENTED in text


def test_token_kinds_by_githubs_prefixes() -> None:
    assert [ev.token_kind(t) for t in ("ghp_1", "gho_1", "github_pat_1", "ghs_1", "x")] == [
        "classic",
        "oauth",
        "fine-grained",
        "app",
        "unknown",
    ]
