"""The workbench REST transport keeps the token on api.github.com and explains failures."""

from __future__ import annotations

import io
import json
from email.message import Message
from urllib.error import HTTPError

import pytest

from quill.core.github.rest_transport import (
    GitHubRestError,
    request_json,
    rest_failure_message,
)


class _Response:
    def __init__(self, status: int, body: bytes, headers: dict[str, str]) -> None:
        self.status = status
        self._body = body
        self.headers = headers

    def read(self, _limit: int) -> bytes:
        return self._body

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_exc: object) -> None:
        return None


class _Opener:
    def __init__(self, outcome: object) -> None:
        self.outcome = outcome
        self.requests: list[object] = []

    def open(self, request: object, timeout: int) -> object:
        self.requests.append(request)
        if isinstance(self.outcome, BaseException):
            raise self.outcome
        return self.outcome


def _http_error(code: int, body: dict[str, object] | None = None, **headers: str) -> HTTPError:
    message = Message()
    for key, value in headers.items():
        message[key.replace("_", "-")] = value
    payload = json.dumps(body or {}).encode()
    return HTTPError("https://api.github.com/x", code, "error", message, io.BytesIO(payload))


def test_sends_bearer_json_body_and_reads_headers() -> None:
    opener = _Opener(_Response(201, b'{"ok": true}', {"X-Poll-Interval": "60"}))
    response = request_json("tok", "post", "/repos/o/r/x", body={"a": 1}, opener=opener)
    request = opener.requests[0]
    assert request.full_url == "https://api.github.com/repos/o/r/x"
    assert request.get_method() == "POST"
    assert request.get_header("Authorization") == "Bearer tok"
    assert json.loads(request.data) == {"a": 1}
    assert response.status == 201 and response.data == {"ok": True}
    assert response.header("X-Poll-Interval") == "60"


def test_refuses_paths_that_could_leave_the_api_host() -> None:
    with pytest.raises(GitHubRestError, match="plain absolute path"):
        request_json("tok", "GET", "//evil.example/x", opener=_Opener(None))
    with pytest.raises(GitHubRestError, match="plain absolute path"):
        request_json("tok", "GET", "https://evil.example/x", opener=_Opener(None))


def test_not_modified_is_returned_not_raised() -> None:
    response = request_json("tok", "GET", "/notifications", opener=_Opener(_http_error(304)))
    assert response.status == 304


def test_redirects_are_refused() -> None:
    with pytest.raises(GitHubRestError, match="did not follow"):
        request_json("tok", "GET", "/x", opener=_Opener(_http_error(302, Location="https://x")))


def test_error_body_message_and_status_are_kept() -> None:
    with pytest.raises(GitHubRestError) as caught:
        request_json(
            "tok", "POST", "/x", opener=_Opener(_http_error(422, {"message": "Bad state"}))
        )
    assert caught.value.status == 422
    assert "Could not cancel the run. GitHub refused the request: Bad state." == (
        rest_failure_message("cancel the run", caught.value)
    )


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (401, "token is invalid or expired"),
        (403, "Access denied"),
        (404, "could not find it"),
        (409, "conflict"),
        (502, "server error"),
    ],
)
def test_failure_messages_name_the_next_step(status: int, expected: str) -> None:
    error = GitHubRestError("x", status=status, data={"message": "detail"})
    assert expected in rest_failure_message("delete the run", error)


def test_rate_limit_is_recognised() -> None:
    error = GitHubRestError(
        "x", status=403, headers={"X-RateLimit-Remaining": "0"}, data={"message": "limit"}
    )
    assert "rate-limited" in rest_failure_message("load notifications", error)


def test_rate_limit_header_survives_the_real_error_path() -> None:
    with pytest.raises(GitHubRestError) as caught:
        request_json(
            "tok",
            "GET",
            "/x",
            opener=_Opener(_http_error(403, {"message": "Forbidden"}, X_RateLimit_Remaining="0")),
        )
    assert "rate-limited" in rest_failure_message("load notifications", caught.value)
