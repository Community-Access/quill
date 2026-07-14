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


@dataclass(frozen=True, slots=True)
class GitHubSecurityAlert:
    """One Dependabot security alert for a repository."""

    number: int
    state: str
    severity: str
    package: str
    summary: str
    html_url: str = ""
    created_at: str = ""


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
            )
        )
    return out


def mark_notification_read(gh_client: Any, notification_id: str) -> None:
    notification = gh_client.get_user().get_notification(notification_id)
    notification.mark_as_read()


def list_security_alerts(
    repo: Any, *, limit: int, take: Callable[[Any, int], list[Any]]
) -> list[GitHubSecurityAlert]:
    """Open Dependabot security alerts for *repo* (an already-resolved
    PyGithub ``Repository``)."""
    rows = take(repo.get_dependabot_alerts(state="open"), limit)
    out: list[GitHubSecurityAlert] = []
    for row in rows:
        advisory = getattr(row, "security_advisory", None)
        dependency = getattr(row, "dependency", None)
        package = getattr(dependency, "package", None) if dependency else None
        out.append(
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
    return out


__all__ = [
    "GitHubNotification",
    "GitHubSecurityAlert",
    "list_notifications",
    "list_security_alerts",
    "mark_notification_read",
]
