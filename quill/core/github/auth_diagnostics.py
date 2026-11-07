"""Plain-language GitHub authentication and organization-access diagnostics."""

from __future__ import annotations

from typing import Any


def _header(headers: object, name: str) -> str:
    getter = getattr(headers, "get", None)
    if not callable(getter):
        return ""
    try:
        return str(getter(name, "") or "")
    except Exception:  # noqa: BLE001 - header containers vary by client
        return ""


def github_auth_hint(
    status: int | None,
    *,
    headers: object = None,
    message: str = "",
) -> str | None:
    """Return a credential-safe action for GitHub 401/403/rate-limit errors."""
    if status == 401:
        return "The GitHub token is invalid or expired. Add a valid token or switch accounts."
    if status == 429 or (
        status == 403
        and (
            _header(headers, "Retry-After")
            or _header(headers, "X-RateLimit-Remaining") == "0"
            or "rate limit" in message.casefold()
        )
    ):
        return "GitHub rate-limited this request. Wait before retrying."
    if status == 403:
        sso = _header(headers, "X-GitHub-SSO")
        normalized_message = message.casefold()
        if (
            "required" in sso.casefold()
            or "saml" in normalized_message
            or "single sign-on" in normalized_message
        ):
            return (
                "GitHub requires organization SSO authorization for this token. "
                "In your GitHub token settings, authorize it for the organization, "
                "then try again."
            )
        return (
            "Access denied. GitHub refused this request: check the token permissions "
            "and its organization SSO authorization."
        )
    return None


def github_exception_hint(exc: Any) -> str | None:
    """Classify a PyGithub or HTTP exception without including credential text."""
    status_value = getattr(exc, "status", None)
    if status_value is None:
        status_value = getattr(exc, "code", None)
    status = status_value if isinstance(status_value, int) else None
    data = getattr(exc, "data", None)
    message = data.get("message", "") if isinstance(data, dict) else ""
    return github_auth_hint(status, headers=getattr(exc, "headers", None), message=str(message))


__all__ = ["github_auth_hint", "github_exception_hint"]
