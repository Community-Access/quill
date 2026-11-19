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

import threading
from collections.abc import Mapping
from typing import Any, Protocol

from quill.core.github.rest_transport import RestResponse, request_json

__all__ = ["GitHubApi", "TokenApi", "fill_path", "forget_remembered_reads"]


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
        """One request. A GET sends the last ETag, and a 304 hands back what GitHub sent then.

        GH-R-131: every repeated read is conditional, so reopening a sheet, F5
        and a verify-after-save that found nothing new cost no rate limit. The
        bodies are kept in memory only, per account, never on disk.
        """
        if method != "GET":
            return request_json(
                self._token,
                method,
                path,
                body=dict(body) if body is not None else None,
                query=dict(query) if query is not None else None,
            )
        from quill.core.github.conditional_requests import request_key

        cache = _memory_cache(self._token)
        asked = dict(query) if query is not None else None
        key = request_key(path, asked)
        previous = cache.get(key)
        headers = {"If-None-Match": previous[0]} if previous is not None else None
        response = request_json(self._token, "GET", path, query=asked, extra_headers=headers)
        if response.status == 304:
            if previous is not None:
                return RestResponse(200, response.headers, previous[1])
            response = request_json(self._token, "GET", path, query=asked)
        etag = response.header("ETag")
        if etag:
            cache.put(key, etag, response.data)
        return response

    def graphql(self, query: str, variables: Mapping[str, object]) -> dict[str, Any]:
        from quill.core.github.github_graphql import graphql_data

        return graphql_data(self._token, query, dict(variables), action="read from GitHub")


_MEMORY: dict[str, Any] = {}
_MEMORY_LOCK = threading.Lock()


def _memory_cache(token: str | None) -> Any:
    """This process's in-memory ETag cache for the account behind *token*."""
    from quill.core.github.conditional_requests import EtagCache
    from quill.core.github.navigation_state import account_key_for_token

    key = account_key_for_token(token)
    with _MEMORY_LOCK:
        cache = _MEMORY.get(key)
        if cache is None:
            cache = EtagCache(None, key)
            _MEMORY[key] = cache
        return cache


def forget_remembered_reads() -> None:
    """Drop every remembered ETag and body (sign-out; tests)."""
    with _MEMORY_LOCK:
        _MEMORY.clear()


def fill_path(template: str, ident: Mapping[str, str]) -> str:
    """``/repos/{repo}/issues/{number}`` with *ident*'s values put in.

    Values are percent-encoded except for ``/``: a repository's ``owner/name``
    and a branch's ``feature/x`` keep their slashes, which is what GitHub's
    paths want, and a label called "good first issue" travels as
    ``good%20first%20issue``. A value with ``..`` or a backslash is refused,
    so no field can steer a request to another path. Only values the
    template names are checked: a secret's base64 ``public_key`` rides in
    *ident* too and may start with ``/``, which refused one save in 64.
    """
    from urllib.parse import quote

    path = template
    for key, value in ident.items():
        if "{" + key + "}" not in path:
            continue
        text = str(value)
        if ".." in text or "\\" in text or text.startswith("/") or text.endswith("/"):
            raise ValueError(f"Refusing a {key} with characters a GitHub path cannot hold.")
        path = path.replace("{" + key + "}", quote(text, safe="/"))
    if "{" in path:
        raise ValueError(f"The path {template} needs a value it was not given.")
    return path
