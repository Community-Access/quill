"""One account's data can never show under another (complete.md 1.3, Compare Accounts and Act As).

Caches are keyed per account: the in-memory ETag cache behind ``TokenApi``,
the on-disk ``EtagCache``, saved items (pins, favorites, searches) and the
navigation state. Each test would fail on a leak: account B reading what A
read, sending A's ETag, or seeing A's pins.
"""

from __future__ import annotations

from typing import Any

import pytest

from quill.core.github import act_as, workbench_api
from quill.core.github.conditional_requests import EtagCache
from quill.core.github.navigation_state import GitHubNavigationState, account_key_for_token
from quill.core.github.permissions import WriteTier
from quill.core.github.rest_transport import RestResponse
from quill.core.github.saved_items import GitHubSavedItems


@pytest.fixture(autouse=True)
def _fresh_memory():
    workbench_api.forget_remembered_reads()
    yield
    workbench_api.forget_remembered_reads()


class _Server:
    """GitHub as each token sees it: a 304 whenever the ETag sent is the current one."""

    def __init__(self) -> None:
        self.sent: list[tuple[str | None, dict[str, str]]] = []
        self.bodies = {"token-a": {"secret": "only A sees this"}, "token-b": {"mine": "B"}}

    def __call__(self, token: str | None, method: str, path: str, **kw: Any) -> RestResponse:
        headers = dict(kw.get("extra_headers") or {})
        self.sent.append((token, headers))
        etag = f'"{token}"'
        if headers.get("If-None-Match") == etag:
            return RestResponse(304, {"etag": etag}, None)
        if headers.get("If-None-Match"):
            # The leak this guards against: another account's ETag. A real server
            # might match it for a public resource and answer 304.
            return RestResponse(304, {"etag": headers["If-None-Match"]}, None)
        return RestResponse(200, {"etag": etag}, self.bodies[str(token)])


def test_token_api_never_sends_or_returns_another_accounts_remembered_read(monkeypatch) -> None:
    server = _Server()
    monkeypatch.setattr(workbench_api, "request_json", server)
    a, b = workbench_api.TokenApi("token-a"), workbench_api.TokenApi("token-b")

    assert a.rest("GET", "/repos/o/r").data == {"secret": "only A sees this"}
    assert b.rest("GET", "/repos/o/r").data == {"mine": "B"}
    assert server.sent[1] == ("token-b", {})  # B sent no validator of A's
    assert a.rest("GET", "/repos/o/r").data == {"secret": "only A sees this"}  # A's own 304
    assert server.sent[2] == ("token-a", {"If-None-Match": '"token-a"'})


def test_the_etag_file_keeps_each_account_apart(tmp_path) -> None:
    path = tmp_path / "etags.json"
    first = EtagCache.load("token-a", path=path)
    first.put("/repos/o/r", '"a"', {"secret": "A"})
    second = EtagCache.load("token-b", path=path)
    assert second.get("/repos/o/r") is None
    second.put("/repos/o/r", '"b"', {"mine": "B"})
    assert EtagCache.load("token-a", path=path).get("/repos/o/r") == ('"a"', {"secret": "A"})


def test_saved_items_and_navigation_are_per_account(quill_data_dir) -> None:
    a_key, b_key = account_key_for_token("secret-alpha"), account_key_for_token("secret-beta")
    assert a_key != b_key and "secret-alpha" not in a_key
    pins = GitHubSavedItems.load(account_key=a_key)
    pins.pinned.append("acme/private")
    pins.save()
    assert "acme/private" not in GitHubSavedItems.load(account_key=b_key).pinned
    assert "acme/private" in GitHubSavedItems.load(account_key=a_key).pinned
    assert GitHubNavigationState.load("secret-beta").account_key == b_key


def test_act_as_plans_name_the_account_and_never_another() -> None:
    approve = next(a for a in act_as.ACT_AS_ACTIONS if a.key == "approve")
    request = act_as.plan(approve, "acme/web", number=12)
    assert (request.method, request.path, request.body) == (
        "POST",
        "/repos/acme/web/pulls/12/reviews",
        {"event": "APPROVE"},
    )
    asked = act_as.confirmation("kelly-test", "github.com", request)
    assert asked.startswith("As kelly-test on github.com, not as you: approve pull request #12")
    assert act_as.outcome("kelly-test", request) == (
        "Approved pull request #12 in acme/web as kelly-test."
    )
    failed = act_as.outcome("kelly-test", request, "GitHub refused.")
    assert failed.startswith("Could not approve pull request #12 in acme/web as kelly-test")


def test_act_as_refuses_a_token_that_now_belongs_to_somebody_else() -> None:
    assert act_as.identity_problem("kelly-test", "github.com", {"login": "Kelly-Test"}) == ""
    said = act_as.identity_problem("kelly-test", "github.com", {"login": "mallory"})
    assert said.startswith("Cannot act as kelly-test on github.com") and "mallory" in said
    assert act_as.identity_problem("kelly-test", "github.com", None).startswith("Cannot act as")


def test_act_as_offers_actions_that_fit_the_selection() -> None:
    keys = lambda kind: [a.key for a in act_as.actions_for(kind)]  # noqa: E731
    assert keys("pull_request") == ["approve", "comment", "close_reopen", "star"]
    assert keys("issue") == ["comment", "close_reopen", "star"]
    assert keys("repository") == ["star"]
    star = act_as.plan(act_as.ACT_AS_ACTIONS[-1], "acme/web")
    assert (star.method, star.path, star.tier) == (
        "PUT",
        "/user/starred/acme/web",
        WriteTier.ORGANIZING,
    )
