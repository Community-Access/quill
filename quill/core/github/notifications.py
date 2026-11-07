"""GitHub notifications inbox and Dependabot security alerts.

Split out of :mod:`quill.core.github.items_provider` to keep that module
under its GATE-11 size budget --
:meth:`~quill.core.github.items_provider.GitHubItemsProvider.fetch_notifications`,
``mark_notification_read``, and ``fetch_security_alerts`` are thin wrappers
around the free functions here. No import of ``items_provider`` at all (this
module needs nothing from it beyond the plain PyGithub objects its caller
already resolved), so there is no load-order concern either direction.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse


@dataclass(frozen=True, slots=True)
class GitHubNotification:
    """One entry in the authenticated account's GitHub notifications inbox."""

    id: str
    repository: str
    reason: str
    subject_title: str
    subject_type: str
    unread: bool
    updated_at: str = ""
    url: str = ""
    subject_url: str = ""


@dataclass(frozen=True, slots=True)
class GitHubSecurityAlert:
    """One repository security finding or explicit unavailable-data notice."""

    number: int
    state: str
    severity: str
    package: str
    summary: str
    html_url: str = ""
    created_at: str = ""
    alert_type: str = "Dependabot"
    location: str = ""
    tool: str = ""
    rule_id: str = ""


def _str(value: object) -> str:
    try:
        return str(value) if value is not None else ""
    except Exception:  # noqa: BLE001 - PyGithub attribute access can raise
        return ""


def _iso(value: object) -> str:
    if value is None:
        return ""
    isoformat = getattr(value, "isoformat", None)
    if callable(isoformat):
        try:
            return str(isoformat())
        except Exception:  # noqa: BLE001
            return ""
    return _str(value)


def _subject_web_url(value: object) -> str:
    """Convert a GitHub subject API URL to its browser issue/PR address."""
    raw = _str(value)
    parsed = urlparse(raw)
    if parsed.scheme != "https" or parsed.netloc != "api.github.com":
        return ""
    path = parsed.path.removeprefix("/repos/")
    parts = path.split("/")
    if len(parts) == 4 and parts[2] in ("issues", "pulls") and parts[3].isdigit():
        kind = "pull" if parts[2] == "pulls" else "issues"
        return f"https://github.com/{parts[0]}/{parts[1]}/{kind}/{parts[3]}"
    return ""


def list_notifications(
    gh_client: Any, *, limit: int, take: Callable[[Any, int], list[Any]]
) -> list[GitHubNotification]:
    """The authenticated account's notifications inbox, across every
    repository -- a real inbox, not scoped to one repo."""
    rows = take(gh_client.get_user().get_notifications(), limit)
    out: list[GitHubNotification] = []
    for row in rows:
        subject = getattr(row, "subject", None)
        repository = getattr(row, "repository", None)
        out.append(
            GitHubNotification(
                id=_str(getattr(row, "id", "")),
                repository=_str(getattr(repository, "full_name", "")),
                reason=_str(getattr(row, "reason", "")),
                subject_title=_str(getattr(subject, "title", "")) if subject else "",
                subject_type=_str(getattr(subject, "type", "")) if subject else "",
                unread=bool(getattr(row, "unread", False)),
                updated_at=_iso(getattr(row, "updated_at", None)),
                url=_str(getattr(row, "url", "")),
                subject_url=_subject_web_url(getattr(subject, "url", "")) if subject else "",
            )
        )
    return out


def mark_notification_read(gh_client: Any, notification_id: str) -> None:
    notification = gh_client.get_user().get_notification(notification_id)
    notification.mark_as_read()


def list_security_alerts(
    repo: Any, *, limit: int, take: Callable[[Any, int], list[Any]]
) -> list[GitHubSecurityAlert]:
    """Open Dependabot, code-scanning, and secret-scanning alerts for a repo.

    A category whose feature is disabled or whose permission is missing yields
    a visible unavailable row. It never silently becomes an empty result.
    Secret values are excluded at the API request and are never mapped.
    """
    out: list[GitHubSecurityAlert] = []
    for alert_type, load in (
        ("Dependabot", lambda: _dependabot_alerts(repo, limit=limit, take=take)),
        ("Code scanning", lambda: _code_scanning_alerts(repo, limit=limit, take=take)),
        ("Secret scanning", lambda: _secret_scanning_alerts(repo, limit=limit, take=take)),
    ):
        try:
            out.extend(load())
        except Exception as exc:  # noqa: BLE001 - permission/feature errors stay visible
            out.append(
                GitHubSecurityAlert(
                    number=0,
                    state="unavailable",
                    severity="",
                    package="",
                    summary=f"{alert_type} alerts unavailable: {_str(exc)}",
                    alert_type=alert_type,
                )
            )
    return out


def _dependabot_alerts(
    repo: Any, *, limit: int, take: Callable[[Any, int], list[Any]]
) -> list[GitHubSecurityAlert]:
    rows = take(repo.get_dependabot_alerts(state="open"), limit)
    alerts = []
    for row in rows:
        advisory = getattr(row, "security_advisory", None)
        dependency = getattr(row, "dependency", None)
        package = getattr(dependency, "package", None) if dependency else None
        alerts.append(
            GitHubSecurityAlert(
                number=int(getattr(row, "number", 0) or 0),
                state=_str(getattr(row, "state", "")),
                severity=_str(getattr(advisory, "severity", "")) if advisory else "",
                package=_str(getattr(package, "name", "")) if package else "",
                summary=_str(getattr(advisory, "summary", "")) if advisory else "",
                html_url=_str(getattr(row, "html_url", "")),
                created_at=_iso(getattr(row, "created_at", None)),
            )
        )
    return alerts


def _code_scanning_alerts(
    repo: Any, *, limit: int, take: Callable[[Any, int], list[Any]]
) -> list[GitHubSecurityAlert]:
    rows = take(repo.get_codescan_alerts(state="open"), limit)
    alerts = []
    for row in rows:
        rule = getattr(row, "rule", None)
        tool = getattr(row, "tool", None)
        instance = getattr(row, "most_recent_instance", None)
        message = getattr(instance, "message", None) if instance else None
        location = getattr(instance, "location", None) if instance else None
        path = _str(getattr(location, "path", "")) if location else ""
        start_line = int(getattr(location, "start_line", 0) or 0) if location else 0
        end_line = int(getattr(location, "end_line", 0) or 0) if location else 0
        location_text = f"{path}:{start_line}-{end_line}" if path else ""
        alerts.append(
            GitHubSecurityAlert(
                number=int(getattr(row, "number", 0) or 0),
                state=_str(getattr(row, "state", "")),
                severity=_str(getattr(rule, "severity", "")) if rule else "",
                package=_str(getattr(rule, "name", "") or getattr(rule, "id", "")) if rule else "",
                summary=(
                    _str(getattr(rule, "description", "")) or _str(getattr(message, "text", ""))
                ),
                html_url=_str(getattr(row, "html_url", "")),
                created_at=_iso(getattr(row, "created_at", None)),
                alert_type="Code scanning",
                location=location_text,
                tool=_str(getattr(tool, "name", "")) if tool else "",
                rule_id=_str(getattr(rule, "id", "")) if rule else "",
            )
        )
    return alerts


def _secret_scanning_alerts(
    repo: Any, *, limit: int, take: Callable[[Any, int], list[Any]]
) -> list[GitHubSecurityAlert]:
    rows = take(repo.get_secret_scanning_alerts(state="open", hide_secret=True), limit)
    return [
        GitHubSecurityAlert(
            number=int(getattr(row, "number", 0) or 0),
            state=_str(getattr(row, "state", "")),
            severity="unclassified",
            package=_str(
                getattr(row, "secret_type_display_name", "") or getattr(row, "secret_type", "")
            ),
            summary="A potential secret was detected. The secret value is withheld.",
            html_url=_str(getattr(row, "html_url", "")),
            created_at=_iso(getattr(row, "created_at", None)),
            alert_type="Secret scanning",
        )
        for row in rows
    ]


__all__ = [
    "GitHubNotification",
    "GitHubSecurityAlert",
    "list_notifications",
    "list_security_alerts",
    "mark_notification_read",
]
