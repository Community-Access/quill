"""Bounded repository access and deployment evidence rows for GitHub Explore."""

from __future__ import annotations

from typing import Any
from urllib.parse import parse_qsl, urlsplit

from quill.core.github.explore_models import ExploreRow, _date, _rows, _text


def _reported_count(collection: Any, *, label: str, limit: int, warnings: list[str]) -> str:
    try:
        total = getattr(collection, "totalCount", None)
        if isinstance(total, int) and not isinstance(total, bool) and total >= 0:
            return str(total)
        rows = _rows(collection, limit + 1, source=label, warnings=warnings)
    except Exception as exc:  # noqa: BLE001 - missing count data must stay explicit
        warnings.append(f"{label} count unavailable: {exc}")
        return "unavailable"
    if len(rows) > limit:
        warnings.append(f"{label}: count is at least {limit}; the preview cap was reached")
        return f"at least {limit}"
    return str(len(rows))


def fetch_repository_access(
    repo_object: Any,
    repository: str,
    *,
    limit: int,
    warnings: list[str],
) -> list[ExploreRow]:
    """Show reported direct-collaborator and team permissions without writes."""
    result: list[ExploreRow] = []
    for group, method_name in (
        ("Collaborator", "get_collaborators"),
        ("Team", "get_teams"),
    ):
        try:
            collection = getattr(repo_object, method_name)()
            members = _rows(collection, limit, source=f"{group} access", warnings=warnings)
        except Exception as exc:  # noqa: BLE001 - keep the other access group visible
            warnings.append(f"{group} access could not be read: {exc}")
            continue
        for member in members:
            name = _text(
                getattr(member, "login", "")
                if group == "Collaborator"
                else getattr(member, "name", "") or getattr(member, "slug", "")
            )
            permissions = getattr(member, "permissions", None)
            if group == "Collaborator" and isinstance(permissions, dict):
                access = next(
                    (
                        level
                        for level in ("admin", "maintain", "push", "triage", "pull")
                        if permissions.get(level)
                    ),
                    "permission not reported",
                )
            else:
                access = _text(getattr(member, "permission", "")) or "permission not reported"
            url = _text(getattr(member, "html_url", ""))
            role = "Team" if group == "Team" else "Collaborator"
            label = f"{role}: {name} — {access}"
            detail = f"{repository} {role.lower()}: {name}\nPermission: {access}\n{url}"
            result.append(ExploreRow(label, detail, url, repository, "access", name.casefold()))
    if len(result) > limit:
        warnings.append(f"Repository access: showing the first {limit} results; more may exist")
    return result[:limit]


def _safe_deployment_url(value: str) -> str:
    parsed = urlsplit(value)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        return ""
    sensitive = {"access_token", "authorization", "client_secret", "code", "oauth_token", "token"}
    if any(
        key.casefold().replace("-", "_") in sensitive or key.casefold().endswith("_token")
        for key, _value in parse_qsl(parsed.query, keep_blank_values=True)
    ):
        return ""
    return value[:2048]


def fetch_deployments(
    repo_object: Any,
    repository: str,
    *,
    limit: int,
    warnings: list[str],
) -> list[ExploreRow]:
    """Show bounded deployment environments, latest statuses, and target SHAs."""
    deployments = _rows(
        repo_object.get_deployments(),
        min(limit, 20),
        source="Deployments",
        warnings=warnings,
    )
    result: list[ExploreRow] = []
    for deployment in deployments:
        deployment_id = int(getattr(deployment, "id", 0) or 0)
        environment = _text(getattr(deployment, "environment", ""))
        sha = _text(getattr(deployment, "sha", ""))
        task = _text(getattr(deployment, "task", ""))
        creator = _text(getattr(getattr(deployment, "creator", None), "login", ""))
        try:
            statuses = _rows(
                deployment.get_statuses(),
                20,
                source=f"Deployment {deployment_id} statuses",
                warnings=warnings,
            )
        except Exception as exc:  # noqa: BLE001 - retain the deployment row
            warnings.append(f"Deployment {deployment_id} status unavailable: {exc}")
            statuses = []
        latest = max(
            statuses,
            key=lambda status: _date(
                getattr(status, "updated_at", None) or getattr(status, "created_at", None)
            ),
            default=None,
        )
        state = _text(getattr(latest, "state", "")) if latest else "status unavailable"
        status_date = (
            _date(getattr(latest, "updated_at", None) or getattr(latest, "created_at", None))
            if latest
            else ""
        )
        target_url = _text(getattr(latest, "target_url", "")) if latest else ""
        environment_url = _text(getattr(latest, "environment_url", "")) if latest else ""
        safe_target_url = _safe_deployment_url(target_url)
        safe_environment_url = _safe_deployment_url(environment_url)
        target_display = safe_target_url or (
            "hidden because it is not a safe HTTPS link" if target_url else "not reported"
        )
        environment_display = safe_environment_url or (
            "hidden because it is not a safe HTTPS link" if environment_url else "not reported"
        )
        label = f"{environment or task or 'Deployment'}: {state}"
        details = [
            f"Deployment #{deployment_id}",
            f"Environment: {environment or 'not reported'}",
            f"Task: {task or 'not reported'}",
            f"State: {state}",
            f"Commit: {sha[:12] if sha else 'not reported'}",
            f"Started: {_date(getattr(deployment, 'created_at', None))}",
            f"Latest status: {status_date or 'not reported'}",
            f"Creator: {creator or 'not reported'}",
            f"Description: {_text(getattr(latest, 'description', '')) if latest else ''}",
            f"Target URL: {target_display}",
            f"Environment URL: {environment_display}",
        ]
        result.append(
            ExploreRow(
                label,
                "\n".join(details),
                safe_target_url or safe_environment_url,
                repository,
                "deployment",
                str(deployment_id),
                status_date,
            )
        )
    return result


def fetch_repository_metrics(
    repo_object: Any,
    repository: str,
    *,
    limit: int,
    warnings: list[str],
    security_alerts: list[Any],
) -> ExploreRow:
    """Return a private, non-personal snapshot of repository health counts."""
    open_issues_and_prs = getattr(repo_object, "open_issues_count", None)
    if not isinstance(open_issues_and_prs, int) or isinstance(open_issues_and_prs, bool):
        open_issues_and_prs = "unavailable"
        warnings.append("Open issue and pull request count unavailable")
    else:
        open_issues_and_prs = str(max(0, open_issues_and_prs))

    try:
        open_prs = _reported_count(
            repo_object.get_pulls(state="open"),
            label="Open pull requests",
            limit=limit,
            warnings=warnings,
        )
    except Exception as exc:  # noqa: BLE001 - don't show a missing metric as zero
        warnings.append(f"Open pull request count unavailable: {exc}")
        open_prs = "unavailable"

    try:
        failed_runs = _reported_count(
            repo_object.get_workflow_runs(status="failure"),
            label="Failed workflow runs",
            limit=limit,
            warnings=warnings,
        )
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"Failed workflow run count unavailable: {exc}")
        failed_runs = "unavailable"

    try:
        deployments = _reported_count(
            repo_object.get_deployments(),
            label="Deployments",
            limit=limit,
            warnings=warnings,
        )
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"Deployment count unavailable: {exc}")
        deployments = "unavailable"

    open_alerts = sum(1 for alert in security_alerts if getattr(alert, "state", "") == "open")
    unavailable_types = sorted({
        str(getattr(alert, "alert_type", "Security"))
        for alert in security_alerts
        if getattr(alert, "state", "") == "unavailable"
    })
    available_types = {
        str(getattr(alert, "alert_type", "Security"))
        for alert in security_alerts
        if getattr(alert, "state", "") != "unavailable"
    }
    if unavailable_types:
        security_text = f"{open_alerts} open; unavailable: {', '.join(unavailable_types)}"
        warnings.append("Some security alert categories were unavailable")
    elif security_alerts:
        security_text = f"{open_alerts} open across {len(available_types)} alert categories"
    else:
        security_text = "unavailable"
        warnings.append("Security alert counts unavailable")

    details = [
        f"Repository health snapshot: {repository}",
        f"Open issues and pull requests: {open_issues_and_prs}",
        f"Open pull requests: {open_prs}",
        f"Failed workflow runs: {failed_runs}",
        f"Security alerts: {security_text}",
        f"Deployments: {deployments}",
        "This snapshot is local to this device and does not rank contributors.",
    ]
    url = _text(getattr(repo_object, "html_url", ""))
    return ExploreRow(
        f"Repository health snapshot: {repository}",
        "\n".join(details),
        url,
        repository,
        "metrics",
        repository.casefold(),
    )


__all__ = ["fetch_deployments", "fetch_repository_access", "fetch_repository_metrics"]
