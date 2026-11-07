"""Security alert triage: dismiss or reopen Dependabot, code-scanning and
secret-scanning alerts (Wave 3).

Each kind has its own REST endpoint and its own list of reasons, and QUILL uses
GitHub's values exactly (``tolerable_risk``, ``"won't fix"``, ``used_in_tests``)
with plain words beside them for the chooser. A dismissal is only reported when
GitHub's reply shows the new state. Explore's two security views build their
rows here too, so every row carries the kind and number the triage needs.

No ``wx`` imports; strict-typed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from quill.core.github.explore_models import ExploreRow
from quill.core.github.items_errors import GitHubItemsError
from quill.core.github.notifications import GitHubSecurityAlert
from quill.core.github.rest_transport import GitHubRestError, request_json, rest_failure_message
from quill.core.github.run_actions import repo_path

__all__ = [
    "ALERT_KINDS",
    "DISMISS_REASONS",
    "AlertKind",
    "GitHubAlertTriageMixin",
    "alert_kind_for",
    "alert_row",
    "parse_alert_key",
]

_MAX_COMMENT = 280


@dataclass(frozen=True, slots=True)
class AlertKind:
    """How one kind of alert is addressed, listed and dismissed on GitHub."""

    key: str  # the REST path segment
    label: str  # as GitHubSecurityAlert.alert_type says it
    closed_state: str  # "dismissed", or "resolved" for secret scanning
    reason_field: str
    comment_field: str


ALERT_KINDS: tuple[AlertKind, ...] = (
    AlertKind("dependabot", "Dependabot", "dismissed", "dismissed_reason", "dismissed_comment"),
    AlertKind(
        "code-scanning", "Code scanning", "dismissed", "dismissed_reason", "dismissed_comment"
    ),
    AlertKind("secret-scanning", "Secret scanning", "resolved", "resolution", "resolution_comment"),
)

#: GitHub's own reason values per kind, each with the words QUILL shows for it.
DISMISS_REASONS: dict[str, tuple[tuple[str, str], ...]] = {
    "dependabot": (
        ("fix_started", "A fix has already been started"),
        ("inaccurate", "This alert is inaccurate or incorrect"),
        ("no_bandwidth", "No bandwidth to fix this"),
        ("not_used", "Vulnerable code is not actually used"),
        ("tolerable_risk", "Risk is tolerable to this project"),
    ),
    "code-scanning": (
        ("false positive", "False positive"),
        ("won't fix", "Won't fix"),
        ("used in tests", "Used in tests"),
    ),
    "secret-scanning": (
        ("false_positive", "False positive"),
        ("wont_fix", "Won't fix"),
        ("revoked", "Revoked"),
        ("used_in_tests", "Used in tests"),
    ),
}


def alert_kind_for(name: str) -> AlertKind:
    """The kind for a REST key (``dependabot``) or a label (``Code scanning``)."""
    folded = name.strip().casefold()
    for kind in ALERT_KINDS:
        if folded in (kind.key, kind.label.casefold()):
            return kind
    raise GitHubItemsError(f"QUILL does not know the {name!r} alert kind.")


def parse_alert_key(key: str) -> tuple[AlertKind, int] | None:
    """``("dependabot", 7)`` from an Explore row key such as ``dependabot:7``."""
    name, _, number = key.partition(":")
    if not number.isdecimal() or int(number) <= 0:
        return None
    try:
        return alert_kind_for(name), int(number)
    except GitHubItemsError:
        return None


def alert_row(alert: GitHubSecurityAlert, repo: str) -> ExploreRow:
    """One Explore row for an alert, keyed ``kind:number`` for triage."""
    alert_type = str(getattr(alert, "alert_type", "") or "Dependabot")
    if alert.state == "unavailable":
        label = f"{alert_type} alerts unavailable"
        return ExploreRow(
            label, f"{label}\n{alert.summary}\n{alert.html_url}", alert.html_url, repo, "security"
        )
    severity = alert.severity or "severity not reported"
    state = f" ({alert.state})" if alert.state and alert.state != "open" else ""
    label = f"{alert_type}: {severity}: {alert.package} — {alert.summary}{state}"
    details = [
        f"Security alert #{alert.number}",
        label,
        f"State: {alert.state}",
        f"Created: {alert.created_at}",
    ]
    for name, attribute in (("Location", "location"), ("Tool", "tool"), ("Rule", "rule_id")):
        value = str(getattr(alert, attribute, "") or "")
        if value:
            details.append(f"{name}: {value}")
    details.append(alert.html_url)
    try:
        key = f"{alert_kind_for(alert_type).key}:{alert.number}" if alert.number else ""
    except GitHubItemsError:
        key = ""
    return ExploreRow(label, "\n".join(details), alert.html_url, repo, "security", key)


def _closed_alert(kind: AlertKind, row: dict[str, object]) -> GitHubSecurityAlert:
    def text(value: object) -> str:
        return str(value) if value is not None else ""

    def nested(name: str) -> dict[str, object]:
        value = row.get(name)
        return value if isinstance(value, dict) else {}

    who = nested("dismissed_by") or nested("resolved_by")
    reason = text(row.get(kind.reason_field)).replace("_", " ")
    note = f"{kind.closed_state.capitalize()}" + (f" as {reason}" if reason else "")
    note += f" by {text(who.get('login'))}" if who.get("login") else ""
    if kind.key == "dependabot":
        advisory = nested("security_advisory")
        package = nested("dependency").get("package")
        severity = text(advisory.get("severity"))
        name = text(package.get("name")) if isinstance(package, dict) else ""
        summary = text(advisory.get("summary"))
    elif kind.key == "code-scanning":
        rule = nested("rule")
        severity = text(rule.get("severity"))
        name = text(rule.get("name") or rule.get("id"))
        summary = text(rule.get("description"))
    else:
        severity = "unclassified"
        name = text(row.get("secret_type_display_name") or row.get("secret_type"))
        summary = "A potential secret. The secret value is withheld."
    try:
        number = int(str(row.get("number") or 0))
    except ValueError:
        number = 0
    return GitHubSecurityAlert(
        number=number,
        state=text(row.get("state")),
        severity=severity,
        package=name,
        summary=f"{summary} {note}.".strip(),
        html_url=text(row.get("html_url")),
        created_at=text(row.get("created_at")),
        alert_type=kind.label,
    )


class _AlertAccess(Protocol):
    _token: str | None

    def _require_write_access(self, action: str) -> None: ...


class GitHubAlertTriageMixin:
    """Dismiss, reopen and list closed security alerts for ``GitHubItemsProvider``."""

    def fetch_closed_security_alerts(
        self: _AlertAccess, full_name: str, *, limit: int = 30
    ) -> list[GitHubSecurityAlert]:
        """Dismissed and resolved alerts, so they can be reopened.

        A kind this account cannot read becomes a visible unavailable row, as in
        the open-alerts view, never an empty list.
        """
        out: list[GitHubSecurityAlert] = []
        for kind in ALERT_KINDS:
            query = {"state": kind.closed_state, "per_page": str(max(1, min(limit, 100)))}
            if kind.key == "secret-scanning":
                query["hide_secret"] = "true"
            try:
                response = request_json(
                    self._token, "GET", f"{repo_path(full_name)}/{kind.key}/alerts", query=query
                )
            except GitHubRestError as exc:
                out.append(
                    GitHubSecurityAlert(
                        number=0,
                        state="unavailable",
                        severity="",
                        package="",
                        summary=rest_failure_message(f"list {kind.label} alerts", exc),
                        alert_type=kind.label,
                    )
                )
                continue
            rows = response.data if isinstance(response.data, list) else []
            out.extend(_closed_alert(kind, row) for row in rows[:limit] if isinstance(row, dict))
        return out

    def set_security_alert_state(
        self: _AlertAccess,
        full_name: str,
        kind_name: str,
        number: int,
        *,
        dismiss: bool,
        reason: str = "",
        comment: str = "",
    ) -> str:
        """Dismiss (with one of GitHub's reasons) or reopen an alert; returns its new state."""
        kind = alert_kind_for(kind_name)
        if number <= 0:
            raise GitHubItemsError("This alert has no number.")
        verb = "dismiss" if dismiss else "reopen"
        if dismiss and reason not in {value for value, _words in DISMISS_REASONS[kind.key]}:
            raise GitHubItemsError("Choose one of GitHub's reasons for dismissing this alert.")
        if len(comment) > _MAX_COMMENT:
            raise GitHubItemsError(f"GitHub takes a comment of up to {_MAX_COMMENT} characters.")
        self._require_write_access(f"{verb} a security alert")
        want = kind.closed_state if dismiss else "open"
        body: dict[str, object] = {"state": want}
        if dismiss:
            body[kind.reason_field] = reason
            if comment.strip():
                body[kind.comment_field] = comment.strip()
        action = f"{verb} {kind.label} alert #{number}"
        try:
            response = request_json(
                self._token,
                "PATCH",
                f"{repo_path(full_name)}/{kind.key}/alerts/{int(number)}",
                body=body,
            )
        except GitHubRestError as exc:
            raise GitHubItemsError(rest_failure_message(action, exc)) from exc
        data = response.data if isinstance(response.data, dict) else {}
        state = str(data.get("state") or "")
        if response.status != 200 or state != want:
            raise GitHubItemsError(
                f"Could not {action}. GitHub did not confirm it"
                + (f"; the alert is still {state}." if state else ".")
            )
        return state
