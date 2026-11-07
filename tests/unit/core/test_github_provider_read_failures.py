"""A provider read that is rate-limited, or made with an expired token, says what to do.

Two transports reach GitHub for a read: PyGithub (``GitHubItemsProvider._repo``)
and the REST transport (every Wave 1 and Wave 3 read). Both must turn a 401 into
"the token is invalid or expired" and a rate-limit 403 or 429 into "wait before
retrying", never a bare status code, and never anything from the token itself.
"""

from __future__ import annotations

import io
from email.message import Message
from urllib.error import HTTPError

import pytest

from quill.core.github import rest_transport
from quill.core.github.items_errors import GitHubItemsError
from quill.core.github.items_provider import GitHubItemsProvider

SECRET = "ghp_secret_token_value"


def _http_error(code: int, body: bytes, headers: dict[str, str] | None = None) -> HTTPError:
    message = Message()
    for name, value in (headers or {}).items():
        message[name] = value
    return HTTPError("https://api.github.com/x", code, "error", message, io.BytesIO(body))


class _Opener:
    def __init__(self, error: HTTPError) -> None:
        self.error = error

    def open(self, request, timeout=None):  # noqa: ARG002 - urllib's shape
        raise self.error


def _provider(monkeypatch: pytest.MonkeyPatch, error: HTTPError) -> GitHubItemsProvider:
    provider = GitHubItemsProvider.__new__(GitHubItemsProvider)
    provider._token = SECRET
    monkeypatch.setattr(rest_transport, "build_opener", lambda *_a, **_k: _Opener(error))
    return provider


def test_expired_token_on_a_rest_read(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = _provider(monkeypatch, _http_error(401, b'{"message": "Bad credentials"}'))
    with pytest.raises(GitHubItemsError) as caught:
        provider.fetch_milestones("o/r")
    message = str(caught.value)
    assert "Could not list the milestones." in message
    assert "invalid or expired" in message
    assert SECRET not in message


@pytest.mark.parametrize(
    ("code", "headers", "expected"),
    [
        (403, {"X-RateLimit-Remaining": "0"}, "rate-limited"),
        # A secondary limit is said as the wait GitHub asked for (rate_limits.py).
        (429, {"Retry-After": "30"}, "GitHub asked QUILL to wait 30 seconds."),
    ],
)
def test_rate_limited_rest_read(
    monkeypatch: pytest.MonkeyPatch, code: int, headers: dict[str, str], expected: str
) -> None:
    error = _http_error(code, b'{"message": "API rate limit exceeded"}', headers)
    provider = _provider(monkeypatch, error)
    with pytest.raises(GitHubItemsError) as caught:
        provider.fetch_repo_folder("o/r", "main")
    message = str(caught.value)
    assert expected in message
    assert SECRET not in message


class _GithubException(Exception):
    def __init__(self, status: int, data: dict[str, str], headers: dict[str, str]) -> None:
        super().__init__(status, data)
        self.status, self.data, self.headers = status, data, headers


class _Gh:
    GithubException = _GithubException


class _Client:
    def __init__(self, error: Exception) -> None:
        self.error = error

    def get_repo(self, _name: str) -> object:
        raise self.error


def _pygithub_provider(monkeypatch: pytest.MonkeyPatch, error: Exception) -> GitHubItemsProvider:
    from quill.core.github import items_provider

    monkeypatch.setattr(items_provider, "_get_gh_module", lambda: _Gh)
    provider = GitHubItemsProvider.__new__(GitHubItemsProvider)
    provider._token = SECRET
    provider._gh = _Client(error)
    return provider


def test_expired_token_on_a_pygithub_read(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = _pygithub_provider(
        monkeypatch, _GithubException(401, {"message": "Bad credentials"}, {})
    )
    with pytest.raises(GitHubItemsError, match="invalid or expired"):
        provider._repo("o/r")


def test_rate_limited_pygithub_read(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = _pygithub_provider(
        monkeypatch,
        _GithubException(
            403, {"message": "API rate limit exceeded"}, {"X-RateLimit-Remaining": "0"}
        ),
    )
    with pytest.raises(GitHubItemsError, match="rate-limited"):
        provider._repo("o/r")
