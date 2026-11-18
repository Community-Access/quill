"""Security policy, advisories and the Advisory Database (GitHub PRD 14.1, GX11)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from quill.core.github import security_advisories as sa
from quill.core.github.rest_transport import GitHubRestError, RestResponse

ADVISORY = {
    "ghsa_id": "GHSA-abcd-2345-wxyz",
    "severity": "high",
    "state": "draft",
    "summary": "Path traversal in the importer",
    "cve_id": None,
    "html_url": "https://github.com/o/r/security/advisories/GHSA-abcd-2345-wxyz",
    "description": "A crafted file name escapes the folder.",
    "vulnerabilities": [
        {
            "package": {"ecosystem": "pip", "name": "quill-io"},
            "vulnerable_version_range": "< 2.1.0",
            "patched_versions": "2.1.0",
        }
    ],
    "credits": [{"login": "sam"}],
}


class FakeApi:
    def __init__(self, status: dict[str, int] | None = None, policy: str = "SECURITY.md") -> None:
        self.status, self.policy = status or {}, policy
        self.sent: list[tuple[str, str, Any, Any]] = []

    def rest(self, method: str, path: str, *, body: Any = None, query: Any = None) -> Any:
        self.sent.append((method, path, body, query))
        for part, code in self.status.items():
            if part in f"{method} {path}":
                raise GitHubRestError("no", status=code)
        if "/contents/" in path:
            if path.endswith("/" + self.policy):
                return RestResponse(
                    200, {}, {"html_url": f"https://github.com/o/r/blob/main/{self.policy}"}
                )
            raise GitHubRestError("Not Found", status=404)
        if path.endswith("/private-vulnerability-reporting"):
            return RestResponse(200, {}, {"enabled": True})
        if path == "/advisories" or (method == "GET" and path.endswith("/security-advisories")):
            return RestResponse(
                200, {}, [{**ADVISORY, "source_code_location": "https://github.com/o/r"}]
            )
        return RestResponse(201, {}, {"ghsa_id": "GHSA-new0-2345-wxyz"})

    def graphql(self, *_a: Any) -> Any:
        raise AssertionError


def test_an_advisory_reads_as_a_sentence_with_its_packages_in_the_details() -> None:
    rows = sa.fetch_advisories(FakeApi(), "o/r")
    assert rows[0].label == (
        "GHSA-abcd-2345-wxyz: high severity, draft: Path traversal in the importer."
    )
    assert "Affects: pip quill-io, affected < 2.1.0, fixed in 2.1.0." in rows[0].detail
    assert "Credited: sam." in rows[0].detail
    assert rows[0].kind == "advisory" and rows[0].key == "GHSA-abcd-2345-wxyz"
    with pytest.raises(sa.AdvisoryError, match="administrators and security managers"):
        sa.fetch_advisories(FakeApi({"GET /repos": 403}), "o/r")


def test_the_policy_is_found_and_private_reporting_is_said() -> None:
    rows = sa.fetch_policy(FakeApi(policy=".github/SECURITY.md"), "o/r")
    assert rows[0].label == "Security policy: .github/SECURITY.md. Enter opens it."
    assert rows[0].kind == "file"
    assert rows[1].label.startswith("Private vulnerability reporting is on")
    rows = sa.fetch_policy(FakeApi(policy="nowhere"), "o/r")
    assert rows[0].label == "o/r has no security policy file (SECURITY.md)."


def test_reporting_drafting_publishing_and_a_cve() -> None:
    api = FakeApi()
    assert sa.report_vulnerability(api, "o/r", "Crash", "Steps", "High") == (
        "Reported privately to o/r's maintainers as GHSA-new0-2345-wxyz."
    )
    assert api.sent[-1][2] == {"summary": "Crash", "description": "Steps", "severity": "high"}
    said = sa.draft_advisory(api, "o/r", "Crash", "Steps", "", ecosystem="npm", package="x")
    assert said.startswith("Drafted advisory GHSA-new0-2345-wxyz.")
    assert api.sent[-1][2]["vulnerabilities"] == [{"package": {"ecosystem": "npm", "name": "x"}}]
    assert sa.set_state(api, "o/r", "GHSA-a", "published").startswith("Published GHSA-a.")
    assert api.sent[-1][:3] == (
        "PATCH",
        "/repos/o/r/security-advisories/GHSA-a",
        {"state": "published"},
    )
    assert "CVE number" in sa.request_cve(api, "o/r", "GHSA-a")
    with pytest.raises(sa.AdvisoryError, match="not a severity"):
        sa.report_vulnerability(api, "o/r", "a", "b", "huge")
    with pytest.raises(sa.AdvisoryError, match="does not take private vulnerability reports"):
        sa.report_vulnerability(FakeApi({"POST": 404}), "o/r", "a", "b")
    assert sa.AdvisoryError.code == "QUILL-GITHUB-ADVISORIES"


def test_the_advisory_database_is_searched_by_what_was_typed() -> None:
    for typed, param in (
        ("GHSA-abcd-2345-wxyz", "ghsa_id"),
        ("cve-2026-12345", "cve_id"),
        ("lodash", "affects"),
    ):
        api = FakeApi()
        rows = sa.search_advisories(api, typed)
        assert param in api.sent[-1][3] and rows[0].repo == "o/r"
    with pytest.raises(sa.AdvisoryError, match="Type a package name"):
        sa.search_advisories(FakeApi(), " ")


def test_the_three_views_reach_their_loader(monkeypatch: Any) -> None:
    from quill.core.github.explore_extra_views import fetch_extra_view

    monkeypatch.setattr(sa, "fetch_advisories", lambda _a, repo, limit: [repo])
    monkeypatch.setattr(sa, "fetch_policy", lambda _a, repo: ["policy"])
    monkeypatch.setattr(sa, "search_advisories", lambda _a, query, limit: [query])
    provider = SimpleNamespace(token="t", is_authenticated=True)
    ask = {"repo": "o/r", "query": "lodash", "limit": 5, "warnings": []}
    assert fetch_extra_view(provider, "advisories", **ask) == ["o/r"]
    assert fetch_extra_view(provider, "security_policy", **ask) == ["policy"]
    assert fetch_extra_view(provider, "advisory_search", **ask) == ["lodash"]
