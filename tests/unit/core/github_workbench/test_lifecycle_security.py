"""Security, end to end over recorded answers (complete.md 1.3, "Verify ... security").

The lifecycle the Workbench offers for each security object, and its refusals:

* alerts (Dependabot, code scanning, secret scanning): listed with a kind that
  cannot be read kept visible, opened on the Security Alert sheet from their
  row, dismissed or resolved there with the kind's own reason, reopened, and
  refused before anything is sent when the choice does not fit the kind;
* repository security advisories: listed, drafted, published, closed, a CVE
  asked for, each refusal said plainly;
* Dependabot: its secrets listed, added sealed and deleted; the repository
  sheet's Dependabot alerts and security updates switched on and off.

Read Only (the account's Workbench level) and GitHub's own refusals (no
permission, not found) are proved for every one. What is already proved
elsewhere is not repeated: dismissing through Dismiss or Reopen Alert...
(test_github_alert_triage.py), the advisory windows
(test_github_workbench_advisories.py), sealing (test_secrets_write_only.py),
the security quick tables (test_security_quick.py).
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from quill.core.github import resource_engine
from quill.core.github.alert_triage import alert_row
from quill.core.github.explore_models import ExploreRow
from quill.core.github.notifications import GitHubSecurityAlert
from quill.core.github.permissions import AccessLevel, ViewerContext
from quill.core.github.resource_engine import ResourceError
from quill.core.github.resource_specs import RESOURCE_SPECS
from quill.core.github.rest_transport import GitHubRestError
from quill.core.github.security_advisories import (
    AdvisoryError,
    draft_advisory,
    fetch_advisories,
    request_cve,
    set_state,
)
from quill.core.github.sheet_catalog import SHEETS, target_for
from quill.core.github.sheet_engine import SheetSaveError, load, locked_fields, plan, save
from quill.core.github.write_gate import command_refusal
from quill.core.workbench.properties import FieldChange
from tests.github_api_fake import FakeGitHubApi

REPO = "owner/repo"
ALERT = SHEETS["security_alert"]

_SECURITY_COMMANDS = (
    "dismiss_alert",
    "autofix_alert",
    "upload_sarif",
    "new_advisory",
    "advisory_state",
    "request_cve",
    "advisory_comment",
    "advisory_comment_edit",
    "advisory_fork",
    "dependabot_add_repo",
    "dependabot_remove_repo",
    "dependabot_default",
    "allow_blocked_secret",
)


def _refused(status: int, message: str = "Forbidden") -> GitHubRestError:
    return GitHubRestError(message, status=status)


# -- alerts: open and Properties ----------------------------------------------------

_RAW = {
    "dependabot": {
        "number": 7,
        "state": "open",
        "security_advisory": {"severity": "high"},
        "dependency": {"package": {"name": "lodash"}, "manifest_path": "package.json"},
        "created_at": "2026-11-01T10:00:00Z",
        "html_url": "https://github.com/owner/repo/security/dependabot/7",
    },
    "code-scanning": {
        "number": 3,
        "state": "open",
        "rule": {"description": "SQL injection", "security_severity_level": "critical"},
        "tool": {"name": "CodeQL"},
        "most_recent_instance": {"location": {"path": "app/db.py"}},
        "html_url": "https://github.com/owner/repo/security/code-scanning/3",
    },
    "secret-scanning": {
        "number": 2,
        "state": "open",
        "secret_type_display_name": "GitHub Personal Access Token",
        "html_url": "https://github.com/owner/repo/security/secret-scanning/2",
    },
}


def _alert_api(kind: str, **changes: Any) -> FakeGitHubApi:
    """GitHub with one alert of *kind*; a PATCH changes what the next read finds."""
    fake = FakeGitHubApi()
    path = f"/repos/{REPO}/{kind}/alerts/{_RAW[kind]['number']}"
    state = {"alert": {**_RAW[kind], **changes}}

    def on_write(method: str, at: str, body: Any) -> None:
        if method == "PATCH" and at == path and body:
            state["alert"] = {**state["alert"], **body}

    fake.on_write = on_write
    fake.answer("GET", path, lambda: state["alert"])
    return fake


def _opened(kind: str, api: FakeGitHubApi) -> tuple[dict[str, str], Any]:
    """The alert's row, then Alt+Enter: the target the row opens, and the sheet loaded."""
    row = _row(kind, int(_RAW[kind]["number"]))
    target = target_for(row, REPO)
    assert target is not None and target.kind == "security_alert"
    return dict(target.ident), load(api, ALERT, target.ident)


def _row(kind: str, number: int) -> ExploreRow:
    """The row the alerts list shows for an open alert of *kind*."""
    label = {"dependabot": "Dependabot", "code-scanning": "Code scanning"}.get(
        kind, "Secret scanning"
    )
    alert = GitHubSecurityAlert(
        number=number,
        state="open",
        severity="high",
        package="lodash",
        summary="A finding",
        html_url=f"https://github.com/{REPO}/security/{number}",
        alert_type=label,
    )
    return alert_row(alert, REPO)


def _change(key: str, before: Any, after: Any) -> FieldChange:
    return FieldChange(key, key.capitalize(), before, after)


@pytest.mark.parametrize(
    ("kind", "said"),
    [
        ("dependabot", {"package": "lodash", "manifest": "package.json", "severity": "high"}),
        ("code-scanning", {"rule": "SQL injection", "tool": "CodeQL", "location": "app/db.py"}),
        ("secret-scanning", {"rule": "GitHub Personal Access Token"}),
    ],
)
def test_each_kind_of_alert_opens_on_its_sheet_from_its_row(kind: str, said: dict) -> None:
    ident, loaded = _opened(kind, _alert_api(kind))
    assert ident["alert_path"] == f"{kind}/alerts"
    assert loaded.values["state"] == "open"
    for key, value in said.items():
        assert loaded.values[key] == value


@pytest.mark.parametrize(
    ("kind", "state", "reason", "sent"),
    [
        (
            "dependabot",
            "dismissed",
            "tolerable_risk",
            {"state": "dismissed", "dismissed_reason": "tolerable_risk", "dismissed_comment": "ok"},
        ),
        (
            "code-scanning",
            "dismissed",
            "won't fix",
            {"state": "dismissed", "dismissed_reason": "won't fix", "dismissed_comment": "ok"},
        ),
        (
            "secret-scanning",
            "resolved",
            "won't fix",
            {"state": "resolved", "resolution": "wont_fix", "resolution_comment": "ok"},
        ),
    ],
)
def test_the_sheet_closes_each_kind_its_own_way_and_the_re_read_proves_it(
    kind: str, state: str, reason: str, sent: dict
) -> None:
    api = _alert_api(kind)
    ident, loaded = _opened(kind, api)
    changes = [
        _change("state", "open", state),
        _change("reason", "", reason),
        _change("comment", "", "ok"),
    ]
    outcome = save(api, ALERT, ident, changes, loaded=loaded.values)
    assert api.writes() == [("PATCH", f"/repos/{REPO}/{kind}/alerts/{_RAW[kind]['number']}", sent)]
    assert [c.key for c in outcome.done] == ["state", "reason", "comment"]
    assert outcome.not_taken == [] and outcome.failed == []


def test_github_spells_a_secrets_reasons_its_own_way_and_the_sheet_says_one() -> None:
    api = _alert_api("secret-scanning", state="resolved", resolution="used_in_tests")
    _ident, loaded = _opened("secret-scanning", api)
    assert loaded.values["reason"] == "used in tests"
    assert "used in tests" in ALERT.sheet.pages[0].fields[2].choices
    assert "used_in_tests" not in ALERT.sheet.pages[0].fields[2].choices


def test_reopening_sends_only_the_state() -> None:
    api = _alert_api("dependabot", state="dismissed", dismissed_reason="no_bandwidth")
    ident, loaded = _opened("dependabot", api)
    outcome = save(api, ALERT, ident, [_change("state", "dismissed", "open")], loaded=loaded.values)
    assert api.writes() == [("PATCH", f"/repos/{REPO}/dependabot/alerts/7", {"state": "open"})]
    assert outcome.ok


def test_a_new_comment_on_a_dismissed_alert_keeps_its_reason() -> None:
    api = _alert_api("code-scanning", state="dismissed", dismissed_reason="false positive")
    ident, loaded = _opened("code-scanning", api)
    save(api, ALERT, ident, [_change("comment", "", "Checked again")], loaded=loaded.values)
    assert api.writes()[0][2] == {
        "state": "dismissed",
        "dismissed_reason": "false positive",
        "dismissed_comment": "Checked again",
    }


@pytest.mark.parametrize(
    ("kind", "raw", "changes", "words"),
    [
        # A code scanning alert takes none of Dependabot's reasons; GitHub would 422.
        (
            "code-scanning",
            {},
            [("state", "open", "dismissed"), ("reason", "", "tolerable_risk")],
            "Choose one of GitHub's reasons for a code scanning alert: false positive",
        ),
        # Dismissing without a reason used to send Dependabot's tolerable_risk to code scanning.
        (
            "code-scanning",
            {},
            [("state", "open", "dismissed")],
            "Choose one of GitHub's reasons for a code scanning alert",
        ),
        # A secret is resolved, never dismissed: this used to reopen it instead.
        (
            "secret-scanning",
            {"state": "resolved", "resolution": "revoked"},
            [("state", "resolved", "dismissed")],
            "A secret scanning alert is resolved, not dismissed: choose open or resolved.",
        ),
        (
            "dependabot",
            {},
            [("state", "open", "resolved")],
            "A dependabot alert is dismissed, not resolved",
        ),
        # GitHub fixed it; a new comment used to send state open and try to reopen it.
        (
            "dependabot",
            {"state": "fixed"},
            [("comment", "", "thanks")],
            "never set to fixed from here; GitHub marks an alert fixed itself.",
        ),
        (
            "dependabot",
            {},
            [("reason", "", "not_used")],
            "A reason and a comment go with dismissed alerts: set State to dismissed too.",
        ),
    ],
)
def test_a_choice_that_does_not_fit_the_kind_is_refused_before_anything_is_sent(
    kind: str, raw: dict, changes: list, words: str
) -> None:
    api = _alert_api(kind, **raw)
    ident, loaded = _opened(kind, api)
    with pytest.raises(SheetSaveError, match=words.replace("(", r"\(").replace(".", r"\.")):
        save(api, ALERT, ident, [_change(*c) for c in changes], loaded=loaded.values)
    assert api.writes() == []


def test_github_refusing_the_dismissal_is_said_for_the_fields_and_nothing_is_claimed() -> None:
    api = _alert_api("dependabot")
    api.answer(
        "PATCH",
        f"/repos/{REPO}/dependabot/alerts/7",
        _refused(403, "Resource not accessible by integration"),
    )
    ident, loaded = _opened("dependabot", api)
    changes = [_change("state", "open", "dismissed"), _change("reason", "", "inaccurate")]
    outcome = save(api, ALERT, ident, changes, loaded=loaded.values)
    assert outcome.done == []
    assert {c.key for c, _why in outcome.failed} == {"state", "reason"}
    assert all("Resource not accessible" in why for _c, why in outcome.failed)


def test_an_alert_that_is_gone_or_hidden_fails_to_open() -> None:
    api = FakeGitHubApi()  # nothing recorded: every read is GitHub's 404
    target = target_for(_row("dependabot", 99), REPO)
    assert target is not None
    with pytest.raises(GitHubRestError) as raised:
        load(api, ALERT, target.ident)
    assert raised.value.status == 404


def test_read_only_and_a_read_role_lock_every_alert_field_with_the_reason() -> None:
    read_only = locked_fields(ALERT, ViewerContext(repo_role="admin", level=AccessLevel.READ_ONLY))
    assert set(read_only) == {"state", "reason", "comment"}
    assert all("read only in the Workbench" in why for why in read_only.values())
    reader = locked_fields(ALERT, ViewerContext(repo_role="read", where=REPO))
    assert set(reader) == {"state", "reason", "comment"}
    assert all("write access" in why for why in reader.values())
    assert locked_fields(ALERT, ViewerContext(repo_role="write", where=REPO)) == {}


@pytest.mark.parametrize("verb", _SECURITY_COMMANDS)
def test_every_security_write_is_refused_at_read_only(verb: str) -> None:
    said = command_refusal(f"github.workbench.{verb}", lambda: AccessLevel.READ_ONLY)
    assert said.startswith("Cannot run ") and "this account is Read Only" in said
    assert command_refusal(f"github.workbench.{verb}", lambda: AccessLevel.FULL) == ""


def test_publishing_or_closing_an_advisory_needs_full_and_dismissing_needs_organize() -> None:
    def at(verb: str, level: AccessLevel) -> str:
        return command_refusal(f"github.workbench.{verb}", lambda: level)

    assert "it needs Full" in at("advisory_state", AccessLevel.ORGANIZE)
    assert "it needs Full" in at("dependabot_default", AccessLevel.ORGANIZE)
    assert at("dismiss_alert", AccessLevel.ORGANIZE) == ""


# -- alerts: the list ---------------------------------------------------------------


def test_the_alerts_list_keeps_a_kind_it_cannot_read_visible_with_githubs_reason() -> None:
    from quill.core.github.notifications import list_security_alerts

    def turned_off(**_kw: Any) -> Any:
        raise RuntimeError("Advanced Security must be enabled for this repository")

    advisory = SimpleNamespace(severity="high", summary="Prototype pollution")
    dependency = SimpleNamespace(package=SimpleNamespace(name="lodash"))
    repo = SimpleNamespace(
        get_dependabot_alerts=lambda **_kw: [
            SimpleNamespace(
                number=7,
                state="open",
                security_advisory=advisory,
                dependency=dependency,
                html_url="https://github.com/owner/repo/security/dependabot/7",
                created_at=None,
            )
        ],
        get_codescan_alerts=turned_off,
        get_secret_scanning_alerts=turned_off,
    )
    alerts = list_security_alerts(repo, limit=30, take=lambda rows, limit: list(rows)[:limit])
    rows = [alert_row(alert, REPO) for alert in alerts]
    assert rows[0].key == "dependabot:7" and "lodash" in rows[0].label
    unavailable = [row for row in rows if "unavailable" in row.label]
    assert [row.label for row in unavailable] == [
        "Code scanning alerts unavailable",
        "Secret scanning alerts unavailable",
    ]
    assert all("Advanced Security must be enabled" in row.detail for row in unavailable)
    assert all(row.key == "" for row in unavailable)  # nothing there to open or dismiss


# -- repository security advisories -------------------------------------------------


def test_an_advisory_is_drafted_published_and_closed_one_request_each() -> None:
    api = FakeGitHubApi()
    api.answer("POST", f"/repos/{REPO}/security-advisories", {"ghsa_id": "GHSA-abcd-efgh-ijkl"})
    said = draft_advisory(api, REPO, "XSS", "Escapes nothing.", "High", package="quill")
    assert said.startswith("Drafted advisory GHSA-abcd-efgh-ijkl.")
    assert api.writes()[0][2]["severity"] == "high"
    assert set_state(api, REPO, "GHSA-abcd-efgh-ijkl", "published").startswith("Published")
    assert set_state(api, REPO, "GHSA-abcd-efgh-ijkl", "closed") == "Closed GHSA-abcd-efgh-ijkl."
    assert [(m, p) for m, p, _b in api.writes()[1:]] == [
        ("PATCH", f"/repos/{REPO}/security-advisories/GHSA-abcd-efgh-ijkl"),
        ("PATCH", f"/repos/{REPO}/security-advisories/GHSA-abcd-efgh-ijkl"),
    ]


def test_an_advisory_state_github_does_not_have_is_refused_before_sending() -> None:
    api = FakeGitHubApi()
    with pytest.raises(AdvisoryError, match="is not an advisory state"):
        set_state(api, REPO, "GHSA-abcd-efgh-ijkl", "withdrawn")
    with pytest.raises(AdvisoryError, match="not a severity GitHub knows"):
        draft_advisory(api, REPO, "XSS", "Body", "severe")
    with pytest.raises(AdvisoryError, match="needs a summary and a description"):
        draft_advisory(api, REPO, " ", "Body", "low")
    assert api.writes() == []


@pytest.mark.parametrize("status", [403, 404])
def test_advisories_github_will_not_show_or_change_are_said_plainly(status: int) -> None:
    api = FakeGitHubApi()
    api.answer("GET", f"/repos/{REPO}/security-advisories", _refused(status))
    api.answer("PATCH", f"/repos/{REPO}/security-advisories/GHSA-abcd-efgh-ijkl", _refused(status))
    with pytest.raises(AdvisoryError, match="GitHub refused to list owner/repo's security"):
        fetch_advisories(api, REPO)
    with pytest.raises(AdvisoryError, match="administrators and security managers"):
        set_state(api, REPO, "GHSA-abcd-efgh-ijkl", "published")


def test_a_cve_github_will_not_request_says_githubs_reason() -> None:
    api = FakeGitHubApi()
    cve = f"/repos/{REPO}/security-advisories/GHSA-abcd-efgh-ijkl/cve"
    api.answer("POST", cve, _refused(422, "A CVE has already been requested"))
    with pytest.raises(AdvisoryError, match="GitHub could not request a CVE .*already been"):
        request_cve(api, REPO, "GHSA-abcd-efgh-ijkl")
    api.answer("POST", cve, {})
    assert "GitHub reviews the request first" in request_cve(api, REPO, "GHSA-abcd-efgh-ijkl")


# -- Dependabot: secrets and the repository's switches ------------------------------

_DEPENDABOT_SECRETS = next(spec for spec in RESOURCE_SPECS if spec.key == "dependabot_secrets")


def test_dependabot_secrets_are_listed_by_name_and_deleted_one_at_a_time() -> None:
    api = FakeGitHubApi()
    listed = {"total_count": 1, "secrets": [{"name": "NPM_TOKEN", "updated_at": "2026-11-01"}]}
    api.answer("GET", f"/repos/{REPO}/dependabot/secrets", listed)
    rows = resource_engine.fetch(api, _DEPENDABOT_SECRETS, REPO)
    assert [row.key for row in rows] == ["dependabot_secrets:NPM_TOKEN"]
    assert "NPM_TOKEN" in rows[0].label
    resource_engine.delete(api, _DEPENDABOT_SECRETS, REPO, "NPM_TOKEN")
    assert api.writes() == [("DELETE", f"/repos/{REPO}/dependabot/secrets/NPM_TOKEN", None)]


def test_dependabot_secrets_github_refuses_or_cannot_find_are_said() -> None:
    api = FakeGitHubApi()
    api.answer("GET", f"/repos/{REPO}/dependabot/secrets", _refused(403))
    with pytest.raises(ResourceError, match="GitHub refused to list the"):
        resource_engine.fetch(api, _DEPENDABOT_SECRETS, REPO)
    api.answer("DELETE", f"/repos/{REPO}/dependabot/secrets/GONE", _refused(404))
    with pytest.raises(ResourceError, match="GitHub found nothing to"):
        resource_engine.delete(api, _DEPENDABOT_SECRETS, REPO, "GONE")


@pytest.mark.parametrize(
    ("key", "path"),
    [
        ("vulnerability_alerts", "vulnerability-alerts"),
        ("security_fixes", "automated-security-fixes"),
        ("private_reporting", "private-vulnerability-reporting"),
    ],
)
def test_the_repository_sheets_dependabot_switches_put_on_and_delete_off(
    key: str, path: str
) -> None:
    repository = SHEETS["repository"]
    ident = {"repo": REPO}
    on = plan(repository, ident, [FieldChange(key, key, False, True)])
    off = plan(repository, ident, [FieldChange(key, key, True, False)])
    assert [(r.method, r.path) for r in on] == [("PUT", f"/repos/{REPO}/{path}")]
    assert [(r.method, r.path) for r in off] == [("DELETE", f"/repos/{REPO}/{path}")]
    locked = locked_fields(repository, ViewerContext(repo_role="write", where=REPO))
    assert "needs admin access" in locked[key]
