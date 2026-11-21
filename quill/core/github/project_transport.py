"""Authenticated, redirect-refusing transport for GitHub Projects GraphQL."""

from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, HTTPSHandler, Request, build_opener

from quill.core.github.auth_diagnostics import github_auth_hint
from quill.core.github.project_models import GitHubProjectsError
from quill.core.net import verified_ssl_context


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *_args: object, **_kwargs: object) -> None:
        return None


_NOT_FOUND = "GitHub found no such Project or item, or will not show it to this account."
_FORBIDDEN = (
    "GitHub refused: this account may not change this Project. It needs write access to "
    "the Project, and a sign-in with the project scope."
)
_SCOPES = (
    "GitHub refused: your sign-in lacks the project scope. Sign in with GitHub again, from "
    "Manage GitHub Accounts, to grant it."
)

_REFUSALS = (("INSUFFICIENT_SCOPES", _SCOPES), ("FORBIDDEN", _FORBIDDEN), ("NOT_FOUND", _NOT_FOUND))


def refusal_words(errors: object) -> str:
    """GraphQL *errors* as one plain sentence, GitHub's own words after it."""
    rows = [row for row in errors if isinstance(row, dict)] if isinstance(errors, list) else []
    kinds = {str(row.get("type", "")) for row in rows}
    said = "; ".join(str(row.get("message", "")) for row in rows if row.get("message"))
    lead = next(
        (words for kind, words in _REFUSALS if kind in kinds),
        "",
    )
    if not lead:
        return said or "GitHub rejected the request."
    return f"{lead} GitHub said: {said}" if said else lead


def request_graphql(token: str, query: str, variables: dict[str, object]) -> dict[str, Any]:
    if not token.strip():
        raise GitHubProjectsError("Sign in to GitHub to view or update Projects.")
    request = Request(
        _graphql_address(token),
        data=json.dumps({"query": query, "variables": variables}).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "User-Agent": "QUILL-GitHub-Workbench",
        },
        method="POST",
    )
    try:
        opener = build_opener(_NoRedirect, HTTPSHandler(context=verified_ssl_context()))
        with opener.open(request, timeout=20) as response:
            payload = json.load(response)
    except HTTPError as exc:
        if exc.code in (301, 302, 303, 307, 308):
            raise GitHubProjectsError(
                "GitHub redirected the Projects request; credentials were not forwarded."
            ) from exc
        if exc.code in (401, 403):
            hint = github_auth_hint(
                exc.code,
                headers=exc.headers,
                message=str(exc.reason or ""),
            )
            raise GitHubProjectsError(
                hint or "GitHub denied the Projects request. Check token and organization access."
            ) from exc
        if exc.code == 404:
            raise GitHubProjectsError(_NOT_FOUND) from exc
        raise GitHubProjectsError(f"GitHub returned HTTP {exc.code} for Projects.") from exc
    except Exception as exc:  # noqa: BLE001 - response/network failures are user-visible
        raise GitHubProjectsError(f"GitHub Projects request failed: {exc}") from exc
    if not isinstance(payload, dict):
        raise GitHubProjectsError("GitHub returned an invalid Projects response.")
    errors = payload.get("errors")
    if errors:
        raise GitHubProjectsError(refusal_words(errors))
    data = payload.get("data")
    if not isinstance(data, dict):
        raise GitHubProjectsError("GitHub returned no Projects data.")
    return data


__all__ = ["refusal_words", "request_graphql"]


def _graphql_address(token: str | None) -> str:
    """GraphQL's address for *token*'s host: GitHub.com or its Enterprise Server."""
    from quill.core.github.hosts import api_url

    return api_url(token, "/graphql")
