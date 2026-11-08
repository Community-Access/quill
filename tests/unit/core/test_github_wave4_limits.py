"""Wave 4: rate limits, secondary-limit waits, conditional requests and the new searches."""

from __future__ import annotations

import io
import json
from datetime import datetime
from email.message import Message
from typing import Any
from urllib.error import HTTPError

import pytest

from quill.core.github import conditional_requests, explore_extra_views, search_views
from quill.core.github.auth_diagnostics import github_auth_hint
from quill.core.github.conditional_requests import EtagCache, conditional_get
from quill.core.github.explore_extra_views import collapse_waits, explore_failure
from quill.core.github.explore_models import GitHubExploreError
from quill.core.github.rate_limits import (
    RateLimitBucket,
    RateLimitReport,
    RateLimitTracker,
    fetch_rate_limit_report,
    parse_graphql_rate_limit,
    parse_rest_rate_limit,
    secondary_wait_seconds,
    wait_message,
)
from quill.core.github.rest_transport import (
    GitHubRestError,
    RestResponse,
    request_json,
    rest_failure_message,
)


class _Response:
    def __init__(self, status: int, body: object, headers: dict[str, str]) -> None:
        self.status = status
        self._body = json.dumps(body).encode() if body is not None else b""
        self.headers = headers

    def read(self, _limit: int) -> bytes:
        return self._body

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_exc: object) -> None:
        return None


class _Opener:
    def __init__(self, *outcomes: object) -> None:
        self.outcomes = list(outcomes)
        self.requests: list[Any] = []

    def open(self, request: Any, timeout: int) -> object:
        self.requests.append(request)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


def _http_error(code: int, body: dict[str, object] | None = None, **headers: str) -> HTTPError:
    message = Message()
    for key, value in headers.items():
        message[key.replace("_", "-")] = value
    return HTTPError(
        "https://api.github.com/x",
        code,
        "error",
        message,
        io.BytesIO(json.dumps(body or {}).encode()),
    )


# -- Rate limits ---------------------------------------------------------------


def _local(epoch: float) -> datetime:
    return datetime(2026, 11, 7, 15, 40)


def test_readout_reads_as_one_plain_sentence() -> None:
    report = RateLimitReport((
        RateLimitBucket("core", 5000, 4212, 1.0),
        RateLimitBucket("graphql", 5000, 4990, 1.0),
    ))
    assert report.sentence(_local) == (
        "GitHub API: 4,212 of 5,000 left, resets at 3:40 PM. "
        "GraphQL: 4,990 of 5,000 left, resets at 3:40 PM."
    )


def test_rest_and_graphql_rate_limit_replies_are_parsed() -> None:
    rest = parse_rest_rate_limit({
        "resources": {
            "core": {"limit": 5000, "remaining": 12, "reset": 100},
            "search": {"limit": 30, "remaining": 30, "reset": 60},
        }
    })
    assert [(b.resource, b.remaining) for b in rest] == [("core", 12), ("search", 30)]
    graphql = parse_graphql_rate_limit({
        "rateLimit": {"limit": 5000, "remaining": 4000, "resetAt": "2026-11-07T22:40:00Z"}
    })
    assert graphql is not None and graphql.remaining == 4000 and graphql.reset_epoch > 0


def test_fetch_report_reads_both_and_says_when_graphql_is_missing() -> None:
    calls: list[tuple[str, str]] = []

    def send(token, method, path, **_kw):
        calls.append((method, path))
        if path == "/rate_limit":
            return RestResponse(
                200, {}, {"resources": {"core": {"limit": 60, "remaining": 59, "reset": 0}}}
            )
        raise GitHubRestError("nope", status=502)

    report = fetch_rate_limit_report("tok", request=send)
    assert calls == [("GET", "/rate_limit"), ("POST", "/graphql")]
    assert "GitHub API: 59 of 60 left" in report.sentence()
    assert "GraphQL's allowance could not be read." in report.sentence()
    anonymous = fetch_rate_limit_report(None, request=send)
    assert "Sign in to see the GraphQL allowance." in anonymous.sentence()


def test_polling_slows_down_as_the_allowance_runs_low() -> None:
    tracker = RateLimitTracker(clock=lambda: 0.0, wall=lambda: 1000.0)
    assert tracker.slowed(60) == 60
    tracker.observe({"X-RateLimit-Limit": "5000", "X-RateLimit-Remaining": "1000"})
    assert tracker.slowed(60) == 120 and tracker.is_low()
    tracker.observe({"X-RateLimit-Limit": "5000", "X-RateLimit-Remaining": "100"})
    assert tracker.slowed(60) == 240
    tracker.observe({
        "X-RateLimit-Limit": "5000",
        "X-RateLimit-Remaining": "0",
        "X-RateLimit-Reset": "1900",
    })
    assert tracker.slowed(60) == 901


@pytest.mark.parametrize(
    ("status", "headers", "message", "expected"),
    [
        (403, {"Retry-After": "30"}, "", 30),
        (403, {}, "You have exceeded a secondary rate limit", 60),
        (429, {}, "", 60),
        (403, {"X-RateLimit-Remaining": "0"}, "API rate limit exceeded", None),
        (403, {}, "Resource not accessible", None),
        (404, {"Retry-After": "5"}, "", None),
    ],
)
def test_secondary_limits_are_told_apart_from_primary_ones(
    status: int, headers: dict[str, str], message: str, expected: int | None
) -> None:
    assert secondary_wait_seconds(status, headers, message) == expected


def test_a_secondary_limit_stops_every_later_request_with_one_sentence() -> None:
    tracker = RateLimitTracker()
    opener = _Opener(_http_error(403, {"message": "secondary rate limit"}, Retry_After="60"))
    with pytest.raises(GitHubRestError) as first:
        request_json("tok", "GET", "/x", opener=opener, tracker=tracker)
    assert str(first.value.args[0]) == "GitHub asked QUILL to wait 60 seconds."
    second_opener = _Opener(_Response(200, {}, {}))
    with pytest.raises(GitHubRestError) as second:
        request_json("tok", "GET", "/y", opener=second_opener, tracker=tracker)
    assert second_opener.requests == []
    assert rest_failure_message("load notifications", second.value).startswith(
        "GitHub asked QUILL to wait"
    )


def test_replies_report_their_rate_limit_headers() -> None:
    tracker = RateLimitTracker()
    opener = _Opener(
        _Response(200, {}, {"X-RateLimit-Limit": "5000", "X-RateLimit-Remaining": "4212"})
    )
    request_json("tok", "GET", "/x", opener=opener, tracker=tracker)
    bucket = tracker.bucket()
    assert bucket is not None and bucket.remaining == 4212


def test_auth_hint_says_the_wait_and_keeps_the_primary_wording() -> None:
    assert github_auth_hint(429, headers={"Retry-After": "60"}) == wait_message(60)
    assert github_auth_hint(403, headers={"X-RateLimit-Remaining": "0"}) == (
        "GitHub rate-limited this request. Wait before retrying."
    )


def test_many_warnings_from_one_wait_collapse_to_one() -> None:
    wait = wait_message(60)
    warnings = [f"Assigned: could not load results: {wait}", f"Mentioned: {wait}", "other"]
    assert collapse_waits(warnings) == [wait, "other"]
    assert explore_failure("my_work", GitHubRestError(wait, status=429)) == wait


# -- Conditional requests -----------------------------------------------------------


def test_a_304_returns_the_stored_body_as_unchanged(tmp_path) -> None:
    cache = EtagCache.load("tok", path=tmp_path / "etags.json")
    first = _Opener(_Response(200, {"n": 1}, {"ETag": '"abc"'}))
    result = conditional_get("tok", "/repos/o/r/topics", cache=cache, opener=first)
    assert result.changed and result.data == {"n": 1}
    again = _Opener(_http_error(304))
    second = conditional_get("tok", "/repos/o/r/topics", cache=cache, opener=again)
    assert not second.changed and second.data == {"n": 1}
    assert again.requests[0].get_header("If-none-match") == '"abc"'
    reloaded = EtagCache.load("tok", path=tmp_path / "etags.json")
    assert reloaded.get("/repos/o/r/topics") == ('"abc"', {"n": 1})
    other_account = EtagCache.load("other", path=tmp_path / "etags.json")
    assert other_account.get("/repos/o/r/topics") is None


def test_large_bodies_are_not_kept(tmp_path) -> None:
    cache = EtagCache(tmp_path / "etags.json", "acct")
    assert not cache.put("/x", '"e"', "y" * (conditional_requests.MAX_BODY_CHARS + 10))
    assert cache.get("/x") is None


def test_the_store_keeps_only_the_newest_entries(tmp_path) -> None:
    cache = EtagCache(None, "acct")
    for index in range(conditional_requests.MAX_ENTRIES + 5):
        cache.put(f"/x/{index}", f'"{index}"', index)
    assert cache.get("/x/0") is None
    assert cache.get(f"/x/{conditional_requests.MAX_ENTRIES + 4}") is not None


def test_explore_pages_read_is_conditional(monkeypatch) -> None:
    seen: list[dict[str, str]] = []

    def fake(token, method, path, *, query=None, extra_headers=None, **_kw):
        seen.append(dict(extra_headers or {}))
        if len(seen) == 1:
            return RestResponse(200, {"etag": '"p1"'}, {"status": "built"})
        return RestResponse(304, {}, None)

    monkeypatch.setattr(conditional_requests, "request_json", fake)
    assert explore_extra_views.explore_api_get("tok", "/repos/o/r/pages") == {"status": "built"}
    assert explore_extra_views.explore_api_get("tok", "/repos/o/r/pages") == {"status": "built"}
    assert seen[1]["If-None-Match"] == '"p1"'


# -- Searches -----------------------------------------------------------------------


def test_code_search_rows_read_path_matching_line_and_matched_text(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    def fake(token, method, path, *, query=None, extra_headers=None, **_kw):
        captured.update(path=path, query=query, headers=extra_headers)
        return RestResponse(
            200,
            {},
            {
                "total_count": 3,
                "items": [
                    {
                        "path": "quill/core/paths.py",
                        "html_url": "https://github.com/o/r/blob/main/quill/core/paths.py",
                        "repository": {"full_name": "o/r"},
                        "text_matches": [
                            {
                                "fragment": "import os\ndef app_data_dir() -> Path:\n    pass",
                                "matches": [{"text": "app_data_dir", "indices": [14, 26]}],
                            }
                        ],
                    }
                ],
            },
        )

    monkeypatch.setattr(search_views, "request_json", fake)
    warnings: list[str] = []
    rows = search_views.run_search("tok", "code_search", "app_data_dir", limit=1, warnings=warnings)
    assert captured["path"] == "/search/code"
    assert captured["headers"] == {"Accept": "application/vnd.github.text-match+json"}
    assert rows[0].label == (
        "quill/core/paths.py: def app_data_dir() -> Path: (matched app_data_dir)"
    )
    assert "Excerpt:" in rows[0].detail and rows[0].repo == "o/r"
    assert warnings == ["showing the first 1 of 3 matches"]


def test_commit_and_repository_search_rows() -> None:
    commit = search_views.commit_row({
        "sha": "abcdef123456",
        "html_url": "https://github.com/o/r/commit/abcdef1",
        "repository": {"full_name": "o/r"},
        "author": {"login": "jeff"},
        "commit": {"message": "Fix the thing\n\nBody", "author": {"date": "2026-11-01T10:00:00Z"}},
    })
    assert commit.label == "o/r abcdef1: Fix the thing, by jeff, 2026-11-01"
    assert commit.kind == "commit"
    repo = search_views.repository_row({
        "full_name": "o/r",
        "description": "An editor",
        "stargazers_count": 1,
        "language": "Python",
        "archived": True,
    })
    assert repo.label == "o/r: An editor (1 star, Python, archived)"
    assert repo.kind == "repo" and repo.repo == "o/r"


def test_code_search_needs_an_account_and_a_query() -> None:
    with pytest.raises(GitHubExploreError, match="signed-in"):
        search_views.run_search(None, "code_search", "x", limit=5, warnings=[])
    with pytest.raises(GitHubExploreError, match="query"):
        search_views.run_search("tok", "repo_search", "  ", limit=5, warnings=[])


def test_an_invalid_query_says_what_github_said(monkeypatch) -> None:
    def fake(*_a, **_kw):
        raise GitHubRestError("x", status=422, data={"message": "Validation Failed"})

    monkeypatch.setattr(search_views, "request_json", fake)
    with pytest.raises(GitHubExploreError, match="could not run that commits search"):
        search_views.run_search("tok", "commit_search", "bad:", limit=5, warnings=[])
