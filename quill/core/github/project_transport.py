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


def request_graphql(token: str, query: str, variables: dict[str, object]) -> dict[str, Any]:
    if not token.strip():
        raise GitHubProjectsError("Sign in to GitHub to view or update Projects.")
    request = Request(
        "https://api.github.com/graphql",
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
        raise GitHubProjectsError(f"GitHub returned HTTP {exc.code} for Projects.") from exc
    except Exception as exc:  # noqa: BLE001 - response/network failures are user-visible
        raise GitHubProjectsError(f"GitHub Projects request failed: {exc}") from exc
    if not isinstance(payload, dict):
        raise GitHubProjectsError("GitHub returned an invalid Projects response.")
    errors = payload.get("errors")
    if errors:
        messages = [row.get("message", "error") for row in errors if isinstance(row, dict)]
        raise GitHubProjectsError(
            "; ".join(str(message) for message in messages) or "GitHub rejected the request."
        )
    data = payload.get("data")
    if not isinstance(data, dict):
        raise GitHubProjectsError("GitHub returned no Projects data.")
    return data


__all__ = ["request_graphql"]
