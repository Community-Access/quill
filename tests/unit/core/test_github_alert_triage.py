"""Security alert triage: GitHub's own reasons per kind, confirmed state changes."""

from __future__ import annotations

from typing import Any

import pytest

from quill.core.github import alert_triage
from quill.core.github.alert_triage import (
    DISMISS_REASONS,
    GitHubAlertTriageMixin,
    alert_row,
    parse_alert_key,
)
from quill.core.github.items_errors import GitHubItemsError
from quill.core.github.notifications import GitHubSecurityAlert
from quill.core.github.rest_transport import GitHubRestError, RestResponse


class _Provider(GitHubAlertTriageMixin):
    def __init__(self, token: str | None = "tok") -> None:
        self._token = token

    def _require_write_access(self, action: str) -> None:
        if not self._token:
            raise GitHubItemsError(f"To {action} you need a signed-in GitHub account.")


class _Api:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, Any, Any]] = []
        self.replies: dict[tuple[str, str], Any] = {}

    def __call__(self, token, method, path, *, body=None, query=None, **_kw):
        self.calls.append((method, path, query, body))
        reply = self.replies.get((method, path), RestResponse(200, {}, []))
        if isinstance(reply, Exception):
            raise reply
        return reply


@pytest.fixture
def api(monkeypatch: pytest.MonkeyPatch) -> _Api:
    fake = _Api()
    monkeypatch.setattr(alert_triage, "request_json", fake)
    return fake


def test_reason_values_are_githubs_own() -> None:
    assert [value for value, _ in DISMISS_REASONS["dependabot"]] == [
        "fix_started",
        "inaccurate",
        "no_bandwidth",
        "not_used",
        "tolerable_risk",
    ]
    assert [value for value, _ in DISMISS_REASONS["code-scanning"]] == [
        "false positive",
        "won't fix",
        "used in tests",
    ]
    assert [value for value, _ in DISMISS_REASONS["secret-scanning"]] == [
        "false_positive",
        "wont_fix",
        "revoked",
        "used_in_tests",
    ]


@pytest.mark.parametrize(
    ("kind", "reason", "body"),
    [
        (
            "dependabot",
            "tolerable_risk",
            {"state": "dismissed", "dismissed_reason": "tolerable_risk", "dismissed_comment": "ok"},
        ),
        (
            "code-scanning",
            "won't fix",
            {"state": "dismissed", "dismissed_reason": "won't fix", "dismissed_comment": "ok"},
        ),
        (
            "secret-scanning",
            "revoked",
            {"state": "resolved", "resolution": "revoked", "resolution_comment": "ok"},
        ),
    ],
)
def test_dismiss_patches_the_kind_endpoint_and_checks_the_state(
    api: _Api, kind: str, reason: str, body: dict[str, object]
) -> None:
    path = f"/repos/o/r/{kind}/alerts/7"
    api.replies[("PATCH", path)] = RestResponse(200, {}, {"state": body["state"]})
    state = _Provider().set_security_alert_state(
        "o/r", kind, 7, dismiss=True, reason=reason, comment=" ok "
    )
    assert state == body["state"]
    assert api.calls == [("PATCH", path, None, body)]


def test_reopen_and_an_unconfirmed_change(api: _Api) -> None:
    path = "/repos/o/r/dependabot/alerts/7"
    api.replies[("PATCH", path)] = RestResponse(200, {}, {"state": "open"})
    assert _Provider().set_security_alert_state("o/r", "Dependabot", 7, dismiss=False) == "open"
    assert api.calls[-1][3] == {"state": "open"}
    api.replies[("PATCH", path)] = RestResponse(200, {}, {"state": "dismissed"})
    with pytest.raises(GitHubItemsError, match="still dismissed"):
        _Provider().set_security_alert_state("o/r", "dependabot", 7, dismiss=False)


def test_a_reason_from_another_kind_is_refused(api: _Api) -> None:
    with pytest.raises(GitHubItemsError, match="GitHub's reasons"):
        _Provider().set_security_alert_state(
            "o/r", "code-scanning", 7, dismiss=True, reason="tolerable_risk"
        )
    with pytest.raises(GitHubItemsError, match="280"):
        _Provider().set_security_alert_state(
            "o/r", "dependabot", 7, dismiss=True, reason="not_used", comment="x" * 281
        )
    assert api.calls == []


def test_forbidden_dismissal_says_what_to_do(api: _Api) -> None:
    api.replies[("PATCH", "/repos/o/r/dependabot/alerts/7")] = GitHubRestError(
        "Resource not accessible", status=403, data={"message": "Resource not accessible"}
    )
    with pytest.raises(GitHubItemsError, match="Access denied"):
        _Provider().set_security_alert_state(
            "o/r", "dependabot", 7, dismiss=True, reason="not_used"
        )


def test_closed_alerts_list_each_kind_and_keep_unreadable_kinds_visible(api: _Api) -> None:
    api.replies[("GET", "/repos/o/r/dependabot/alerts")] = RestResponse(
        200,
        {},
        [
            {
                "number": 3,
                "state": "dismissed",
                "dismissed_reason": "tolerable_risk",
                "dismissed_by": {"login": "jeff"},
                "security_advisory": {"severity": "high", "summary": "Bad regex"},
                "dependency": {"package": {"name": "lodash"}},
            }
        ],
    )
    api.replies[("GET", "/repos/o/r/code-scanning/alerts")] = GitHubRestError(
        "no", status=403, data={"message": "no"}
    )
    alerts = _Provider().fetch_closed_security_alerts("o/r")
    assert alerts[0].summary == "Bad regex Dismissed as tolerable risk by jeff."
    assert alerts[1].state == "unavailable"
    queries = {path: query for _m, path, query, _b in api.calls}
    assert queries["/repos/o/r/secret-scanning/alerts"]["state"] == "resolved"
    assert queries["/repos/o/r/secret-scanning/alerts"]["hide_secret"] == "true"


def test_rows_carry_the_kind_and_number() -> None:
    alert = GitHubSecurityAlert(5, "open", "high", "lodash", "Bad", alert_type="Code scanning")
    row = alert_row(alert, "o/r")
    assert row.key == "code-scanning:5"
    kind, number = parse_alert_key(row.key)
    assert (kind.label, number) == ("Code scanning", 5)
    assert parse_alert_key("") is None
    unavailable = GitHubSecurityAlert(0, "unavailable", "", "", "no access")
    assert alert_row(unavailable, "o/r").key == ""
