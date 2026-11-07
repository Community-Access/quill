"""One GraphQL call for the Wave 3 workbench features, over the REST transport.

Blame, Discussions writes and discussion threads go to ``api.github.com/graphql``
through :func:`~quill.core.github.rest_transport.request_json`, so they share its
fixed host, refused redirects, verified TLS and timeout. This module only adds
what GraphQL needs on top: the ``errors`` array (GitHub answers 200 with errors
for a refused mutation or a rate limit) becomes one actionable
:class:`~quill.core.github.items_errors.GitHubItemsError`.

No ``wx`` imports; strict-typed.
"""

from __future__ import annotations

from typing import Any

from quill.core.github.items_errors import GitHubItemsError
from quill.core.github.rest_transport import GitHubRestError, request_json, rest_failure_message

__all__ = ["as_dict", "graphql_data", "split_repo"]


def as_dict(value: object) -> dict[str, Any]:
    """*value* when it is a JSON object, else an empty one, so nested reads never fail."""
    return value if isinstance(value, dict) else {}


def split_repo(full_name: str) -> tuple[str, str]:
    """``("owner", "name")`` for ``owner/name``, or a clear error."""
    owner, _, name = full_name.strip().partition("/")
    if not owner or not name or "/" in name:
        raise GitHubItemsError("Enter a repository as owner/repo first.")
    return owner, name


def graphql_data(
    token: str | None, query: str, variables: dict[str, object], *, action: str
) -> dict[str, Any]:
    """Run one GraphQL query or mutation and return its ``data`` object.

    *action* completes "Could not ..." in every failure message.
    """
    if not token:
        raise GitHubItemsError(
            f"To {action} you need a signed-in GitHub account; GitHub's GraphQL API "
            "does not answer anonymous requests."
        )
    try:
        response = request_json(
            token, "POST", "/graphql", body={"query": query, "variables": variables}
        )
    except GitHubRestError as exc:
        raise GitHubItemsError(rest_failure_message(action, exc)) from exc
    payload = response.data
    if not isinstance(payload, dict):
        raise GitHubItemsError(f"Could not {action}. GitHub returned no data.")
    errors = payload.get("errors")
    if isinstance(errors, list) and errors:
        kinds = {str(row.get("type", "")) for row in errors if isinstance(row, dict)}
        if "RATE_LIMITED" in kinds:
            raise GitHubItemsError(
                f"Could not {action}. GitHub rate-limited this request. Wait before retrying."
            )
        messages = [str(row.get("message", "")) for row in errors if isinstance(row, dict)]
        detail = "; ".join(message for message in messages if message) or "the request was refused"
        raise GitHubItemsError(f"Could not {action}. GitHub said: {detail}")
    data = payload.get("data")
    if not isinstance(data, dict):
        raise GitHubItemsError(f"Could not {action}. GitHub returned no data.")
    return data
