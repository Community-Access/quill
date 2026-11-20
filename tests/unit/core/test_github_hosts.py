"""GitHub Enterprise Server hosts: a token goes only to its own host; a missing endpoint is said.

Every request is caught by a fake opener; nothing reaches a network.
"""

from __future__ import annotations

import io
import json
from typing import Any
from urllib.error import HTTPError

import pytest

from quill.core.github import hosts
from quill.core.github.rest_transport import GitHubRestError, request_json, rest_failure_message


@pytest.fixture(autouse=True)
def _clean_bindings():
    hosts.forget_bindings()
    yield
    hosts.forget_bindings()


class _Reply:
    status = 200

    def __init__(self, body: Any, headers: dict[str, str] | None = None) -> None:
        self._body = json.dumps(body).encode()
        self.headers = headers or {}

    def read(self, _limit: int = -1) -> bytes:
        return self._body

    def __enter__(self) -> _Reply:
        return self

    def __exit__(self, *_a: object) -> None:
        return None


class _Opener:
    def __init__(self, reply: Any = None, error: HTTPError | None = None) -> None:
        self.sent: list[Any] = []
        self.reply = reply if reply is not None else _Reply({"ok": True})
        self.error = error

    def open(self, request: Any, timeout: float = 0) -> Any:
        self.sent.append(request)
        if self.error is not None:
            raise self.error
        return self.reply


def _send(token: str, path: str, opener: _Opener, method: str = "GET") -> Any:
    from quill.core.github.rate_limits import RateLimitTracker

    return request_json(token, method, path, opener=opener, tracker=RateLimitTracker())


@pytest.mark.parametrize(
    ("typed", "host"),
    [
        ("github.com", "github.com"),
        ("https://api.github.com/", "github.com"),
        ("GHE.Example.com", "ghe.example.com"),
        ("https://ghe.example.com/api/v3", "ghe.example.com"),
        ("https://ghe.example.com/api/graphql", "ghe.example.com"),
        ("ghe.example.com:8443", "ghe.example.com:8443"),
    ],
)
def test_what_people_paste_becomes_the_server_name(typed: str, host: str) -> None:
    assert hosts.normalize_host(typed) == host


@pytest.mark.parametrize(
    "typed", ["http://ghe.example.com", "ghe.example.com/org/repo", "a@b.com", "", "localhost"]
)
def test_anything_else_is_refused(typed: str) -> None:
    with pytest.raises(hosts.GitHubHostError):
        hosts.normalize_host(typed)


def test_rest_and_graphql_addresses_for_each_kind_of_server() -> None:
    assert hosts.rest_root("github.com") == "https://api.github.com"
    assert hosts.graphql_url("github.com") == "https://api.github.com/graphql"
    assert hosts.rest_root("ghe.example.com") == "https://ghe.example.com/api/v3"
    assert hosts.graphql_url("ghe.example.com") == "https://ghe.example.com/api/graphql"


def test_an_enterprise_token_is_sent_to_its_server_and_never_to_github_com() -> None:
    hosts.bind_token("ghes-token", "ghe.example.com")
    opener = _Opener()
    _send("ghes-token", "/repos/o/r", opener)
    _send("ghes-token", "/graphql", opener, "POST")

    urls = [request.full_url for request in opener.sent]
    assert urls == [
        "https://ghe.example.com/api/v3/repos/o/r",
        "https://ghe.example.com/api/graphql",
    ]
    assert all("api.github.com" not in url for url in urls)
    assert opener.sent[0].get_header("X-github-api-version") == hosts.API_VERSION


def test_a_github_com_token_stays_on_api_github_com() -> None:
    hosts.bind_token("ghes-token", "ghe.example.com")
    opener = _Opener()
    _send("dotcom-token", "/repos/o/r", opener)
    assert opener.sent[0].full_url == "https://api.github.com/repos/o/r"


def test_pygithub_is_pointed_at_the_enterprise_server_only_for_its_token() -> None:
    hosts.bind_token("ghes-token", "ghe.example.com")
    assert hosts.pygithub_host("ghes-token") == {"base_url": "https://ghe.example.com/api/v3"}
    assert hosts.pygithub_host("dotcom-token") == {}


def _not_found(url: str) -> HTTPError:
    return HTTPError(url, 404, "Not Found", {}, io.BytesIO(b'{"message": "Not Found"}'))  # type: ignore[arg-type]


def test_a_404_from_an_older_enterprise_server_says_the_server_may_not_have_it() -> None:
    hosts.bind_token("ghes-token", "ghe.example.com")
    hosts.remember_server_version("ghe.example.com", "3.4.0")
    with pytest.raises(GitHubRestError) as caught:
        _send("ghes-token", "/repos/o/r/rules/branches/main", _Opener(error=_not_found("x")))
    said = str(caught.value.args[0])
    assert said.startswith("This server's GitHub does not have rules")
    assert "GitHub Enterprise Server at ghe.example.com, version 3.4.0," in said


def test_a_404_from_github_com_keeps_its_own_meaning() -> None:
    with pytest.raises(GitHubRestError) as caught:
        _send("dotcom-token", "/repos/o/r/rules/branches/main", _Opener(error=_not_found("x")))
    assert "server's GitHub" not in str(caught.value)


def test_a_fine_grained_refusal_names_the_permission_github_wanted() -> None:
    error = GitHubRestError(
        "Resource not accessible by personal access token",
        status=403,
        headers={"x-accepted-github-permissions": "administration=write"},
        data={"message": "Resource not accessible by personal access token"},
    )
    said = rest_failure_message("change the role", error)
    assert "administration=write" in said


def test_graphql_side_doors_follow_the_token_host() -> None:
    from quill.core.github import discussions, project_transport, review_graphql

    hosts.bind_token("ghes-token", "ghe.example.com")
    for module in (discussions, project_transport, review_graphql):
        assert module._graphql_address("ghes-token") == "https://ghe.example.com/api/graphql"
        assert module._graphql_address("dotcom-token") == "https://api.github.com/graphql"
