"""Security Overview reads every page of the organization's alert lists, and can be stopped (GX11).

Recorded answers only: a fake GitHub that hands out pages with a ``Link``
header, as the organization alert lists do (a cursor in ``after=``).
"""

from __future__ import annotations

from typing import Any

import pytest

from quill.core.github.every_page import Paging, PagingStopped, next_page, read_every_page
from quill.core.github.quick_table_security import SECURITY_QUICK, security_overview
from quill.core.github.rest_transport import GitHubRestError, RestResponse

_API = "https://api.github.com"


class PagedApi:
    """Each list in pages of *size*; the next page named in ``Link`` with a cursor."""

    def __init__(self, lists: dict[str, list[Any]], size: int = 100, refuse: str = "") -> None:
        self.lists, self.size, self.refuse = lists, size, refuse
        self.sent: list[tuple[str, dict[str, str]]] = []

    def rest(self, method: str, path: str, *, body: Any = None, query: Any = None) -> RestResponse:
        assert method == "GET"
        asked = dict(query or {})
        self.sent.append((path, asked))
        if self.refuse and self.refuse in path:
            raise GitHubRestError("Resource not accessible by integration", status=403)
        rows = self.lists.get(path, [])
        start = int(asked.get("after", "0"))
        page = rows[start : start + self.size]
        headers = {}
        if start + self.size < len(rows):
            headers["link"] = (
                f'<{_API}{path}?per_page={self.size}&after={start + self.size}>; rel="next", '
                f'<{_API}{path}?per_page={self.size}&before=0>; rel="prev"'
            )
        return RestResponse(200, headers, page)


def _alerts(repo: str, count: int, severity: str) -> list[dict[str, Any]]:
    return [
        {"repository": {"full_name": repo}, "security_advisory": {"severity": severity}}
        for _ in range(count)
    ]


def test_the_overview_counts_past_the_first_hundred_of_each_kind() -> None:
    api = PagedApi({
        "/orgs/acme/dependabot/alerts": _alerts("acme/web", 230, "high")
        + _alerts("acme/api", 20, "critical"),
        "/orgs/acme/code-scanning/alerts": [
            {"repository": {"full_name": "acme/web"}, "rule": {"security_severity_level": "low"}}
        ]
        * 101,
    })
    said = security_overview(api, {"org": "acme"})
    assert said.splitlines() == [
        "Open security alerts in acme, by repository, worst first.",
        "acme/api: 20 Dependabot (20 critical).",
        "acme/web: 230 Dependabot (230 high); 101 code scanning (101 low).",
        "Totals: 250 Dependabot, 101 code scanning, 0 secret scanning, in 2 repositories.",
        "Read every page: 351 alerts in 6 pages.",
    ]
    dependabot = [q for p, q in api.sent if p.endswith("dependabot/alerts")]
    assert [q.get("after") for q in dependabot] == [None, "100", "200"]
    assert dependabot[0] == {"state": "open", "per_page": "100"}
    secret = next(q for p, q in api.sent if "secret-scanning" in p)
    assert secret["hide_secret"] == "true"


def test_a_refused_kind_on_a_later_page_is_still_never_a_zero() -> None:
    api = PagedApi({"/orgs/acme/dependabot/alerts": _alerts("acme/web", 3, "low")}, size=2,
                   refuse="code-scanning")  # fmt: skip
    said = security_overview(api, {"org": "acme"})
    assert "Totals: 3 Dependabot, 0 secret scanning, in 1 repository." in said
    assert "Code scanning: GitHub would not show these to you, so this is not a zero." in said


def test_stopping_reads_no_further_page_and_says_how_far_it_got() -> None:
    api = PagedApi({"/orgs/acme/dependabot/alerts": _alerts("acme/web", 500, "high")})
    pages: list[int] = []
    paging = Paging(should_cancel=lambda: len(pages) >= 2, progress=pages.append)
    with pytest.raises(PagingStopped) as stopped:
        security_overview(api, {"org": "acme"}, paging)
    assert len(api.sent) == 2  # asked before each page; the third was never sent
    assert (stopped.value.rows, stopped.value.pages) == (200, 2)
    assert pages == [100, 200]  # the gauge's numbers; nothing here is spoken


def test_the_quick_command_reads_with_paging_behind_cancel() -> None:
    quick = next(q for q in SECURITY_QUICK if q.verb == "security_overview")
    assert quick.paged is security_overview and quick.report and not quick.writes


def test_only_githubs_own_host_is_followed() -> None:
    assert next_page(f'<{_API}/orgs/a/x?after=Y2&per_page=100>; rel="next"') == (
        "/orgs/a/x",
        {"after": "Y2", "per_page": "100"},
    )
    assert next_page('<https://evil.example/orgs/a/x?page=2>; rel="next"') is None
    assert next_page('<http://api.github.com/orgs/a/x?page=2>; rel="next"') is None
    assert next_page(f'<{_API}/orgs/a/x?page=1>; rel="prev"') is None
    assert next_page("") is None


def test_an_empty_page_ends_the_read_even_if_github_names_another() -> None:
    class Looping:
        calls = 0

        def rest(self, *_a: Any, **_k: Any) -> RestResponse:
            self.calls += 1
            return RestResponse(200, {"link": f'<{_API}/x?page=9>; rel="next"'}, [])

    api = Looping()
    assert read_every_page(api, "/x", {}) == []
    assert api.calls == 1
