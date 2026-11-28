"""People and organization discovery: search, follow, star, local state. No network."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pytest

from quill.core.github.account_desk import SAFE_MODE_SENTENCE, AccountDesk
from quill.core.github.account_discovery import (
    KIND_ORGANIZATION,
    KIND_PERSON,
    AccountError,
    AccountHit,
    disambiguate,
    list_repositories,
    search_accounts,
    set_following,
    set_starred,
)
from quill.core.github.rest_transport import GitHubRestError, RestResponse
from quill.core.github.tracked_accounts import TrackedAccounts


class FakeApi:
    """Answers recorded replies by (method, path); records every call."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, Mapping[str, str] | None]] = []
        self.following: set[str] = set()
        self.starred: set[str] = set()

    def rest(self, method: str, path: str, *, body: Any = None, query: Any = None) -> RestResponse:
        self.calls.append((method, path, query))
        if path == "/search/users":
            return RestResponse(
                200,
                {},
                {
                    "items": [
                        {
                            "login": "octocat",
                            "type": "User",
                            "html_url": "https://github.com/octocat",
                        },
                        {"login": "octo-org", "type": "Organization"},
                        {"login": "ghost-gone", "type": "User"},
                    ]
                },
            )
        if path == "/users/octocat":
            return RestResponse(
                200,
                {},
                {
                    "login": "octocat",
                    "type": "User",
                    "name": "The Octocat",
                    "bio": "Cat.",
                    "public_repos": 8,
                    "followers": 9,
                },
            )
        if path == "/users/octo-org":
            return RestResponse(
                200,
                {},
                {
                    "login": "octo-org",
                    "type": "Organization",
                    "name": "Octo",
                    "bio": "Org.",
                    "public_repos": 1,
                },
            )
        if path == "/users/ghost-gone":
            raise GitHubRestError("nope", status=404)
        if path.startswith("/user/following/"):
            who = path.rsplit("/", 1)[1]
            return self._toggle(method, who, self.following)
        if path.startswith("/user/starred/"):
            repo = path.removeprefix("/user/starred/")
            return self._toggle(method, repo, self.starred)
        if path.endswith("/repos"):
            return RestResponse(
                200,
                {},
                [{"full_name": "octocat/hello", "stargazers_count": 1, "language": "Python"}],
            )
        raise AssertionError(path)

    @staticmethod
    def _toggle(method: str, key: str, bag: set[str]) -> RestResponse:
        if method == "PUT":
            bag.add(key)
            return RestResponse(204)
        if method == "DELETE":
            bag.discard(key)
            return RestResponse(204)
        if key in bag:
            return RestResponse(204)
        raise GitHubRestError("not found", status=404)

    def graphql(self, query: str, variables: Mapping[str, object]) -> dict[str, Any]:
        raise AssertionError("no GraphQL here")


def test_search_reads_type_name_description_and_counts() -> None:
    api = FakeApi()
    hits = search_accounts(api, "octo")
    assert [h.login for h in hits] == ["octocat", "octo-org", "ghost-gone"]
    assert hits[0].kind == KIND_PERSON and hits[0].name == "The Octocat"
    assert hits[1].kind == KIND_ORGANIZATION and hits[1].public_repos == 1
    # an unreadable profile keeps the search's own answer instead of losing the list
    assert hits[2].name == "" and hits[2].kind == KIND_PERSON
    row = hits[0].label()
    assert row.startswith("Person: octocat (The Octocat), 8 public repositories")
    assert "Organization: octo-org (Octo), 1 public repository" in hits[1].label()


def test_a_short_search_sends_nothing() -> None:
    api = FakeApi()
    assert search_accounts(api, " o ") == []
    assert api.calls == []


def test_similar_names_say_followers() -> None:
    a = AccountHit("jeff-b", KIND_PERSON, "Jeff Bishop", followers=3)
    b = AccountHit("jbishop", KIND_PERSON, "Jeff Bishop", followers=1200)
    c = AccountHit("someone", KIND_PERSON, "Other", followers=5)
    labels = disambiguate([a, b, c])
    assert "3 followers" in labels[0] and "1,200 followers" in labels[1]
    assert "followers" not in labels[2]


def test_follow_is_confirmed_from_github() -> None:
    api = FakeApi()
    hit = AccountHit("octocat", KIND_PERSON)
    assert set_following(api, hit, True) == "You now follow octocat."
    assert "octocat" in api.following
    assert set_following(api, hit, False) == "You no longer follow octocat."
    methods = [(m, p) for m, p, _q in api.calls]
    assert methods[:2] == [("PUT", "/user/following/octocat"), ("GET", "/user/following/octocat")]


def test_follow_that_did_not_take_is_reported_honestly() -> None:
    class Stubborn(FakeApi):
        def _toggle(self, method: str, key: str, bag: set[str]) -> RestResponse:  # type: ignore[override]
            if method == "GET":
                raise GitHubRestError("not found", status=404)
            return RestResponse(204)

    said = set_following(Stubborn(), AccountHit("octocat", KIND_PERSON), True)
    assert "reports that you do not follow octocat" in said


def test_organizations_are_never_followed_in_app() -> None:
    api = FakeApi()
    org = AccountHit("octo-org", KIND_ORGANIZATION)
    with pytest.raises(AccountError):
        set_following(api, org, True)
    assert api.calls == []
    desk = AccountDesk(api, _store(), refuse=lambda _w: "")
    said = desk.toggle_follow(org)
    assert "Open on GitHub" in said and api.calls == []


def test_star_is_public_and_says_so() -> None:
    api = FakeApi()
    assert "Your stars are public" in set_starred(api, "octocat/hello", True)
    assert "octocat/hello" in api.starred
    assert "removed your star" in set_starred(api, "octocat/hello", False)
    with pytest.raises(AccountError):
        set_starred(api, "../evil", True)


def _store(tmp: Any = None) -> TrackedAccounts:
    import tempfile
    from pathlib import Path

    return TrackedAccounts.load("acct", data_dir=Path(tmp or tempfile.mkdtemp()))


def test_desk_toggles_follow_and_star_by_reading_state() -> None:
    api = FakeApi()
    desk = AccountDesk(api, _store(), refuse=lambda _w: "")
    person = AccountHit("octocat", KIND_PERSON)
    assert desk.toggle_follow(person) == "You now follow octocat."
    assert desk.toggle_follow(person) == "You no longer follow octocat."
    assert "starred octocat/hello" in desk.toggle_star("octocat/hello")
    assert "removed your star" in desk.toggle_star("octocat/hello")


def test_read_only_level_refuses_writes_but_not_looking() -> None:
    api = FakeApi()
    desk = AccountDesk(api, _store(), refuse=lambda what: f"Cannot {what}: needs Organize.")
    assert desk.toggle_follow(AccountHit("octocat", KIND_PERSON)).startswith("Cannot")
    assert desk.toggle_star("octocat/hello").startswith("Cannot")
    assert not any(m in ("PUT", "DELETE") for m, _p, _q in api.calls)
    hits, labels = desk.search("octo")
    assert hits and labels
    assert desk.repositories(hits[0])[0].full_name == "octocat/hello"


def test_safe_mode_refuses_the_network() -> None:
    api = FakeApi()
    desk = AccountDesk(api, _store(), safe_mode=lambda: True)
    with pytest.raises(AccountError) as caught:
        desk.search("octo")
    assert SAFE_MODE_SENTENCE in str(caught.value.args[0])
    with pytest.raises(AccountError):
        desk.repositories(AccountHit("octocat", KIND_PERSON))
    assert desk.following(AccountHit("octocat", KIND_PERSON)) is None
    assert api.calls == []


def test_repositories_use_the_right_endpoint() -> None:
    api = FakeApi()
    list_repositories(api, "octo-org", KIND_ORGANIZATION)
    list_repositories(api, "octocat", KIND_PERSON)
    paths = [p for _m, p, _q in api.calls]
    assert paths == ["/orgs/octo-org/repos", "/users/octocat/repos"]


def test_local_state_is_separate_and_persists(tmp_path: Any) -> None:
    store = TrackedAccounts.load("acct", data_dir=tmp_path)
    hit = AccountHit("octocat", KIND_PERSON, "The Octocat")
    assert "this computer only" in store.track(hit)
    assert store.is_tracked("OctoCat") and not store.is_favorite("octocat")
    assert "GitHub is not told" in store.set_favorite(hit, True)
    other = AccountHit("fav-first", KIND_PERSON)
    store.set_favorite(other, True)  # favorite implies tracked
    assert store.is_tracked("fav-first")
    assert "not a GitHub star" not in store.set_favorite_repository("a/b", True)
    assert "That does not star it on GitHub." in store.set_favorite_repository("c/d", True)
    again = TrackedAccounts.load("acct", data_dir=tmp_path)
    assert [a.login for a in again.listed()] == ["fav-first", "octocat"]
    assert again.is_favorite_repository("A/B")
    assert "still" not in again.untrack("octocat")
    assert TrackedAccounts.load("someone-else", data_dir=tmp_path).listed() == []


def test_local_wording_never_claims_a_public_action() -> None:
    store = _store()
    hit = AccountHit("octocat", KIND_PERSON)
    sentences = [
        store.track(hit),
        store.set_favorite(hit, True),
        store.set_favorite_repository("a/b", True),
        store.set_favorite_repository("a/b", False),
        store.untrack("octocat"),
    ]
    for said in sentences:
        assert "you now follow" not in said.lower() and "you starred" not in said.lower()


def test_corrupt_file_reads_empty(tmp_path: Any) -> None:
    store = TrackedAccounts.load("acct", data_dir=tmp_path)
    store.path.write_text("{not json", encoding="utf-8")
    assert TrackedAccounts.load("acct", data_dir=tmp_path).listed() == []
