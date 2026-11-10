"""The one door the Workbench's sheets use to reach GitHub: REST and GraphQL.

Properties sheets, batches, permissions and access pages (GitHub PRD sections
15 to 18) read and write through :class:`GitHubApi`, a two-method protocol,
so every one of them can be tested against recorded answers and none of them
ever reaches GitHub from a test. :class:`TokenApi` is the real one: it sends
through :func:`quill.core.github.rest_transport.request_json` (one fixed host,
``api.github.com``, verified TLS, no redirects) and
:func:`quill.core.github.github_graphql.graphql_data`, which the rest of the
GitHub code already uses, so the network egress audit's existing rows cover
the transport and the new rows name the endpoint families.

wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

from quill.core.github.rest_transport import RestResponse, request_json

__all__ = ["GitHubApi", "TokenApi", "fill_path"]


class GitHubApi(Protocol):
    """REST and GraphQL, nothing else. A test passes a recorded fake."""

    def rest(
        self,
        method: str,
        path: str,
        *,
        body: Mapping[str, object] | None = None,
        query: Mapping[str, str] | None = None,
    ) -> RestResponse: ...

    def graphql(self, query: str, variables: Mapping[str, object]) -> dict[str, Any]: ...


class TokenApi:
    """:class:`GitHubApi` for one signed-in token."""

    def __init__(self, token: str | None) -> None:
        self._token = token

    @property
    def signed_in(self) -> bool:
        return bool(self._token)

    def rest(
        self,
        method: str,
        path: str,
        *,
        body: Mapping[str, object] | None = None,
        query: Mapping[str, str] | None = None,
    ) -> RestResponse:
        return request_json(
            self._token,
            method,
            path,
            body=dict(body) if body is not None else None,
            query=dict(query) if query is not None else None,
        )

    def graphql(self, query: str, variables: Mapping[str, object]) -> dict[str, Any]:
        from quill.core.github.github_graphql import graphql_data

        return graphql_data(self._token, query, dict(variables), action="read from GitHub")


def fill_path(template: str, ident: Mapping[str, str]) -> str:
    """``/repos/{repo}/issues/{number}`` with *ident*'s values put in.

    Values are percent-encoded except for ``/``: a repository's ``owner/name``
    and a branch's ``feature/x`` keep their slashes, which is what GitHub's
    paths want, and a label called "good first issue" travels as
    ``good%20first%20issue``. A value with ``..`` or a backslash is refused,
    so no field can steer a request to another path.
    """
    from urllib.parse import quote

    path = template
    for key, value in ident.items():
        text = str(value)
        if ".." in text or "\\" in text or text.startswith("/") or text.endswith("/"):
            raise ValueError(f"Refusing a {key} with characters a GitHub path cannot hold.")
        path = path.replace("{" + key + "}", quote(text, safe="/"))
    if "{" in path:
        raise ValueError(f"The path {template} needs a value it was not given.")
    return path
