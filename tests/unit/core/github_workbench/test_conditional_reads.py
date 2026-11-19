"""GH-R-131: every repeated GitHub read is conditional.

Sheets, pickers and reloads go through ``TokenApi``, whose GETs now send the
last ETag; the issue and pull request lists, which come through PyGithub, are
checked first with one conditional read of the same window. A 304 costs no
rate limit and hands back what was shown before.
"""

from __future__ import annotations

from typing import Any

import pytest

from quill.core.github import workbench_api
from quill.core.github.list_probe import forget_lists, probe_token, rows_or_fetch
from quill.core.github.rest_transport import GitHubRestError, RestResponse
from quill.core.github.workbench_api import TokenApi, forget_remembered_reads

TOKEN = "test-token-not-real"


@pytest.fixture(autouse=True)
def _fresh() -> Any:
    forget_lists()
    forget_remembered_reads()
    yield
    forget_lists()
    forget_remembered_reads()


class _GitHub:
    """Answers a GET with ETag "v<version>", and 304 when that is the ETag sent."""

    def __init__(self) -> None:
        self.version = 1
        self.sent: list[tuple[str, str, dict[str, str] | None]] = []
        self.fail = False

    def __call__(
        self,
        _token: Any,
        method: str,
        path: str,
        *,
        query: Any = None,
        extra_headers: dict[str, str] | None = None,
        body: Any = None,
        **_kw: Any,
    ) -> RestResponse:
        self.sent.append((method, path, extra_headers))
        if self.fail:
            raise GitHubRestError("Server Error", status=500)
        etag = f'"v{self.version}"'
        if method == "GET" and (extra_headers or {}).get("If-None-Match") == etag:
            return RestResponse(304, {"etag": etag}, None)
        return RestResponse(200, {"etag": etag}, {"path": path, "version": self.version})


# -- the lists -----------------------------------------------------------------


def _list(github: _GitHub, fetched: list[int], token: str | None = TOKEN, page: int = 30):
    def fetch() -> list[str]:
        fetched.append(1)
        return [f"row {github.version}"]

    return rows_or_fetch(
        token,
        "/repos/owner/repo/issues",
        {"state": "open", "per_page": str(page)},
        fetch,
        request=github,
    )


def test_an_unchanged_list_is_not_read_again() -> None:
    github, fetched = _GitHub(), []
    assert _list(github, fetched) == (["row 1"], True)
    assert _list(github, fetched) == (["row 1"], False)
    assert len(fetched) == 1
    assert github.sent[0][2] is None
    assert github.sent[1][2] == {"If-None-Match": '"v1"'}


def test_a_changed_list_is_read_again() -> None:
    github, fetched = _GitHub(), []
    _list(github, fetched)
    github.version = 2
    assert _list(github, fetched) == (["row 2"], True)
    assert len(fetched) == 2
    assert _list(github, fetched) == (["row 2"], False)


def test_a_failed_probe_falls_through_to_the_real_read() -> None:
    github, fetched = _GitHub(), []
    github.fail = True
    assert _list(github, fetched) == (["row 1"], True)
    assert len(fetched) == 1


def test_a_window_longer_than_one_page_or_no_token_is_never_probed() -> None:
    github, fetched = _GitHub(), []
    assert _list(github, fetched, page=150)[1] is True
    assert _list(github, fetched, token=None)[1] is True
    assert github.sent == []
    assert len(fetched) == 2


def test_each_account_keeps_its_own_lists() -> None:
    github, fetched = _GitHub(), []
    _list(github, fetched, token="token-a")
    assert _list(github, fetched, token="token-b")[1] is True
    assert github.sent[-1][2] is None


def test_only_the_real_provider_is_probed() -> None:
    class Fake:
        token = TOKEN

    assert probe_token(Fake()) is None


# -- sheets, pickers and reloads ----------------------------------------------------


def test_a_repeated_sheet_read_sends_the_etag_and_keeps_the_body(monkeypatch) -> None:
    github = _GitHub()
    monkeypatch.setattr(workbench_api, "request_json", github)
    api = TokenApi(TOKEN)
    first = api.rest("GET", "/repos/owner/repo/issues/1")
    again = api.rest("GET", "/repos/owner/repo/issues/1")
    assert again.status == 200
    assert again.data == first.data == {"path": "/repos/owner/repo/issues/1", "version": 1}
    assert github.sent[1][2] == {"If-None-Match": '"v1"'}


def test_a_write_is_never_conditional(monkeypatch) -> None:
    github = _GitHub()
    monkeypatch.setattr(workbench_api, "request_json", github)
    api = TokenApi(TOKEN)
    api.rest("GET", "/repos/owner/repo/issues/1")
    api.rest("PATCH", "/repos/owner/repo/issues/1", body={"title": "x"})
    assert github.sent[-1] == ("PATCH", "/repos/owner/repo/issues/1", None)


def test_a_304_with_nothing_remembered_asks_again_plainly(monkeypatch) -> None:
    calls: list[dict[str, str] | None] = []

    def answer(_t: Any, _m: str, _p: str, *, query: Any = None, extra_headers: Any = None):
        calls.append(extra_headers)
        if len(calls) == 1:
            return RestResponse(304, {}, None)
        return RestResponse(200, {}, ["fresh"])

    monkeypatch.setattr(workbench_api, "request_json", answer)
    assert TokenApi(TOKEN).rest("GET", "/user/repos").data == ["fresh"]
    assert len(calls) == 2


def test_different_queries_are_different_reads(monkeypatch) -> None:
    github = _GitHub()
    monkeypatch.setattr(workbench_api, "request_json", github)
    api = TokenApi(TOKEN)
    api.rest("GET", "/repos/owner/repo/branches", query={"page": "1"})
    api.rest("GET", "/repos/owner/repo/branches", query={"page": "2"})
    assert [headers for _m, _p, headers in github.sent] == [None, None]


def test_every_repository_list_view_names_the_endpoint_it_shows() -> None:
    from quill.core.github.list_probe import VIEW_PATHS, view_rows

    assert set(VIEW_PATHS) == {"branches", "commits", "tags", "releases", "workflows", "runs"}
    # A fake provider is never probed: the fetch alone answers.
    assert view_rows(object(), "owner/repo", "tags", 30, lambda: ["v1"]) == ["v1"]
    assert view_rows(object(), "owner/repo", "unknown", 30, lambda: ["x"]) == ["x"]
