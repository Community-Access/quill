"""Every CODEOWNERS owner exists and can write (GitHub Workbench PRD 21.8). Pure."""

from __future__ import annotations

from types import SimpleNamespace

from quill.core.github.codeowners_check import check_owners, github_lookups, summary

RULES = """# owners
*        @alice @org/docs
/docs/   @bob docs@example.com
/src/    @alice @ghost @org/nobody
/build/  @org/readers notanowner
"""


class _NotFound(Exception):
    status = 404


def _user(login: str) -> str | None:
    return {"alice": "admin", "bob": "read"}.get(login)


def _team(org: str, slug: str) -> bool | None:
    return {"docs": True, "readers": False}.get(slug)


def _states() -> dict[str, str]:
    results = check_owners(RULES, user_permission=_user, team_can_push=_team)
    return {result.owner: result.state for result in results}


def test_each_owner_is_judged_once() -> None:
    assert _states() == {
        "@alice": "ok",
        "@org/docs": "ok",
        "@bob": "problem",  # read access only
        "docs@example.com": "unchecked",
        "@ghost": "problem",  # no such account
        "@org/nobody": "problem",  # no such team
        "@org/readers": "problem",  # cannot push
        "notanowner": "problem",  # no @
    }


def test_a_failed_lookup_is_never_a_pass() -> None:
    def broken(_login: str) -> str | None:
        raise TimeoutError("timed out")

    results = check_owners("* @alice", user_permission=broken, team_can_push=_team)
    assert results[0].state == "unchecked"
    assert "timed out" in results[0].sentence


def test_summary_counts() -> None:
    results = check_owners(RULES, user_permission=_user, team_can_push=_team)
    assert summary(results) == "8 owners checked, 5 need fixing, 1 could not be checked."
    assert summary([]) == "There are no owners to check."


def test_github_lookups_turn_404_into_not_found() -> None:
    class Repo:
        def get_collaborator_permission(self, login: str) -> str:
            if login == "ghost":
                raise _NotFound()
            return "write"

    class Team:
        def get_repo_permission(self, _repo: object) -> object:
            return SimpleNamespace(push=False, maintain=True, admin=False)

    class Org:
        def get_team_by_slug(self, slug: str) -> Team:
            if slug == "nobody":
                raise _NotFound()
            return Team()

    user_permission, team_can_push = github_lookups(Repo(), lambda _name: Org())
    assert user_permission("ghost") is None
    assert user_permission("alice") == "write"
    assert team_can_push("org", "nobody") is None
    assert team_can_push("org", "docs") is True
