"""Push protection, dependency review, the security overview and private reports (complete.md 1.3).

Recorded answers only: Allow a Blocked Secret..., Dependency Review on a pull
request, Security Overview on an organization, a private vulnerability report
accepted or closed, and an organization's secret alerts read without the secret.
"""

from __future__ import annotations

from typing import Any

import pytest

from quill.core.github import resource_engine as engine
from quill.core.github.quick_actions import QuickError
from quill.core.github.quick_table_security import (
    BYPASS_REASONS,
    SECURITY_QUICK,
    dependency_changes,
    security_overview,
)
from quill.core.github.quick_tables import QUICK_ENDPOINTS, QUICK_LIVE, QUICK_REQUIREMENTS
from quill.core.github.resource_specs import spec_for
from quill.core.github.rest_transport import GitHubRestError, RestResponse

_BY_VERB = {q.verb: q for q in SECURITY_QUICK}


class Api:
    """Answers by path (the query ignored); a status instead raises GitHub's refusal."""

    def __init__(self, answers: dict[str, Any], refuse: dict[str, int] | None = None) -> None:
        self.answers, self.refuse = answers, refuse or {}
        self.sent: list[tuple[str, str, Any, Any]] = []

    def rest(self, method: str, path: str, *, body: Any = None, query: Any = None) -> Any:
        self.sent.append((method, path, body, query))
        for part, status in self.refuse.items():
            if part in path:
                raise GitHubRestError("Resource not accessible by integration", status=status)
        return RestResponse(200, {}, self.answers.get(path, {}))


# -- push protection -------------------------------------------------------------------------


def test_allow_a_blocked_secret_sends_the_placeholder_and_reason_and_says_how_long() -> None:
    quick = _BY_VERB["allow_blocked_secret"]
    api = Api({
        "/repos/o/r/secret-scanning/push-protection-bypasses": {
            "reason": "used_in_tests",
            "expire_at": "2026-11-19T18:00:00Z",
            "token_type": "GitHub personal access token",
        }
    })
    ctx = {"repo": "o/r", "placeholder": " 2xyzPlaceholder ", "reason": "used_in_tests"}
    said = quick.said(quick.run(api, ctx), ctx)
    assert api.sent == [
        (
            "POST",
            "/repos/o/r/secret-scanning/push-protection-bypasses",
            {"reason": "used_in_tests", "placeholder_id": "2xyzPlaceholder"},
            None,
        )
    ]
    assert said == (
        "GitHub will let GitHub personal access token through until 2026-11-19 at 18:00 UTC. "
        "Push again now; GitHub keeps an alert for it."
    )


def test_allow_a_blocked_secret_asks_first_and_offers_only_githubs_reasons() -> None:
    quick = _BY_VERB["allow_blocked_secret"]
    assert [v for v, _w in BYPASS_REASONS] == ["false_positive", "used_in_tests", "will_fix_later"]
    assert quick.asks[1].values == tuple(v for v, _w in BYPASS_REASONS)
    assert "{repo}" in quick.confirm and "history" in quick.confirm
    assert quick.writes and QUICK_REQUIREMENTS["github.workbench.allow_blocked_secret"][0] == (
        "repo:write"
    )
    assert QUICK_LIVE["allow_blocked_secret"].startswith("needs Jeff:")
    assert QUICK_ENDPOINTS[
        "POST /repos/{owner}/{repo}/secret-scanning/push-protection-bypasses"
    ] == ("command:github.workbench.allow_blocked_secret")
    with pytest.raises(QuickError, match="reasons"):
        quick.run(Api({}), {"repo": "o/r", "placeholder": "p", "reason": "because"})


def test_a_refused_bypass_is_said_plainly() -> None:
    quick = _BY_VERB["allow_blocked_secret"]
    api = Api({}, refuse={"push-protection-bypasses": 404})
    with pytest.raises(QuickError, match="does not show that to you"):
        quick.run(api, {"repo": "o/r", "placeholder": "p", "reason": "false_positive"})


# -- dependency review -------------------------------------------------------------------------

CHANGES = [
    {
        "change_type": "removed",
        "manifest": "package.json",
        "ecosystem": "npm",
        "name": "left-pad",
        "version": "1.0.0",
        "license": "WTFPL",
        "vulnerabilities": [],
    },
    {
        "change_type": "added",
        "manifest": "package.json",
        "ecosystem": "npm",
        "name": "lodash",
        "version": "4.17.20",
        "license": "MIT",
        "vulnerabilities": [
            {
                "severity": "high",
                "advisory_ghsa_id": "GHSA-p6mc-m468-83gw",
                "advisory_summary": "Prototype Pollution in lodash",
                "advisory_url": "https://github.com/advisories/GHSA-p6mc-m468-83gw",
            }
        ],
    },
    {
        "change_type": "added",
        "manifest": "requirements.txt",
        "ecosystem": "pip",
        "name": "requests",
        "version": "2.32.0",
        "license": None,
        "vulnerabilities": [],
    },
]


def test_dependency_review_compares_the_pull_requests_base_and_head_commits() -> None:
    quick = _BY_VERB["dependency_review"]
    api = Api({
        "/repos/o/r/pulls/7": {"base": {"sha": "aaa111"}, "head": {"sha": "bbb222"}},
        "/repos/o/r/dependency-graph/compare/aaa111...bbb222": CHANGES,
    })
    said = quick.said(quick.run(api, {"repo": "o/r", "number": "7"}), {})
    assert [p for _m, p, _b, _q in api.sent] == [
        "/repos/o/r/pulls/7",
        "/repos/o/r/dependency-graph/compare/aaa111...bbb222",
    ]
    assert said.splitlines() == [
        "Added 2, removed 1. 1 added dependency has known vulnerabilities.",
        "Added: lodash 4.17.20 (npm, package.json), licence MIT. Vulnerable: high, "
        "GHSA-p6mc-m468-83gw, Prototype Pollution in lodash.",
        "Removed: left-pad 1.0.0 (npm, package.json), licence WTFPL.",
        "Added: requests 2.32.0 (pip, requirements.txt), licence unknown.",
    ]
    assert quick.report and quick.menu == ("pull_request",) and not quick.writes


def test_no_dependency_change_and_a_turned_off_graph_are_said() -> None:
    assert dependency_changes([]) == "No dependency changed between those two."
    quick = _BY_VERB["dependency_review"]
    api = Api(
        {"/repos/o/r/pulls/7": {"base": {"sha": "a"}, "head": {"sha": "b"}}},
        refuse={"dependency-graph": 403},
    )
    with pytest.raises(QuickError, match="GitHub refused"):
        quick.run(api, {"repo": "o/r", "number": "7"})
    with pytest.raises(QuickError, match="which commits"):
        quick.run(Api({"/repos/o/r/pulls/7": {}}), {"repo": "o/r", "number": "7"})


def test_compare_dependencies_on_a_repository_says_licences_too() -> None:
    from quill.core.github.quick_table_repo import REPO_QUICK

    compare = next(q for q in REPO_QUICK if q.verb == "compare_dependencies")
    assert "licence MIT" in compare.said(CHANGES, {})


# -- the organization's security overview ------------------------------------------------------


def _alert(repo: str, **extra: Any) -> dict[str, Any]:
    return {"repository": {"full_name": repo}, "state": "open", **extra}


def test_the_overview_counts_by_repository_and_severity_worst_first() -> None:
    api = Api({
        "/orgs/acme/dependabot/alerts": [
            _alert("acme/api", security_advisory={"severity": "medium"}),
            _alert("acme/web", security_advisory={"severity": "critical"}),
            _alert("acme/web", security_advisory={"severity": "high"}),
            _alert("acme/web", security_advisory={"severity": "high"}),
        ],
        "/orgs/acme/code-scanning/alerts": [
            _alert("acme/web", rule={"security_severity_level": "high"})
        ],
        "/orgs/acme/secret-scanning/alerts": [_alert("acme/api"), _alert("acme/api")],
    })
    said = security_overview(api, {"org": "acme"})
    assert said.splitlines() == [
        "Open security alerts in acme, by repository, worst first.",
        "acme/web: 3 Dependabot (1 critical, 2 high); 1 code scanning (1 high).",
        "acme/api: 1 Dependabot (1 medium); 2 secret scanning.",
        "Totals: 4 Dependabot, 1 code scanning, 2 secret scanning, in 2 repositories.",
        "Read every page: 7 alerts in 3 pages.",
    ]
    queries = {p: q for _m, p, _b, q in api.sent}
    assert queries["/orgs/acme/secret-scanning/alerts"] == {
        "state": "open",
        "per_page": "100",
        "hide_secret": "true",
    }
    assert queries["/orgs/acme/dependabot/alerts"] == {"state": "open", "per_page": "100"}


def test_a_kind_github_will_not_show_is_said_never_counted_as_none() -> None:
    api = Api(
        {"/orgs/acme/dependabot/alerts": [_alert("acme/web", security_advisory={})]},
        refuse={"secret-scanning": 403, "code-scanning": 404},
    )
    said = security_overview(api, {"org": "acme"})
    assert "Totals: 1 Dependabot, in 1 repository." in said
    assert "0 secret scanning" not in said and "0 code scanning" not in said
    assert "Secret scanning: GitHub would not show these to you, so this is not a zero." in said
    assert "Code scanning: GitHub would not show these to you, so this is not a zero." in said


def test_an_organization_with_nothing_open_says_so_and_how_much_it_read() -> None:
    empty = Api({})
    assert security_overview(empty, {"org": "acme"}) == (
        "No open security alerts in acme's repositories. Read every page: 0 alerts in 3 pages."
    )
    many = Api({"/orgs/acme/dependabot/alerts": [_alert("acme/web")] * 100})
    said = security_overview(many, {"org": "acme"})
    assert "at least" not in said  # no next link: the hundred are all of them
    assert "Read every page: 100 alerts in 3 pages." in said


# -- an organization's secret alerts, and private reports ---------------------------------------


def test_the_organizations_secret_alerts_list_never_asks_for_the_secret() -> None:
    api = Api({"/orgs/acme/secret-scanning/alerts": [{"number": 1, "state": "open"}]})
    engine.fetch(api, spec_for("org_secret_alerts"), "acme")
    assert api.sent[-1][3] == {"per_page": "100", "hide_secret": "true"}
    assert "GET /orgs/{org}/secret-scanning/alerts" in spec_for("org_secret_alerts").endpoints()


def test_a_private_report_reads_as_one_to_review_and_can_be_accepted_or_closed() -> None:
    from quill.core.github import security_advisories as sa

    row = sa.advisory_row("o/r", {"ghsa_id": "GHSA-a", "severity": "high", "state": "triage"})
    assert row.label == "GHSA-a: high severity, private report to review: ."
    assert sa.is_private_report(row)
    draft = sa.advisory_row("o/r", {"ghsa_id": "GHSA-b", "severity": "low", "state": "draft"})
    assert not sa.is_private_report(draft)

    class Fake:
        def __init__(self) -> None:
            self.sent: list[tuple[str, str, Any]] = []

        def rest(self, method: str, path: str, *, body: Any = None, query: Any = None) -> Any:
            self.sent.append((method, path, body))
            return RestResponse(200, {}, {})

    api = Fake()
    accepted = sa.set_state(api, "o/r", "GHSA-a", "draft", report=True)  # type: ignore[arg-type]
    assert api.sent[-1] == ("PATCH", "/repos/o/r/security-advisories/GHSA-a", {"state": "draft"})
    assert accepted.startswith("Accepted the report; GHSA-a is a draft advisory now")
    closed = sa.set_state(api, "o/r", "GHSA-a", "closed", report=True)  # type: ignore[arg-type]
    assert closed == "Closed the report GHSA-a. The reporter can still read it."
    assert (
        spec_for("org_advisories").sentence({
            "ghsa_id": "GHSA-a",
            "summary": "Bug",
            "severity": "high",
            "state": "triage",
        })
        == "GHSA-a: Bug, high, private report to review."
    )
