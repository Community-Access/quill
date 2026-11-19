"""Which GitHub a token belongs to: GitHub.com or a GitHub Enterprise Server host.

An account is saved with its host (``accounts.py``). GitHub.com answers REST
at ``https://api.github.com`` and GraphQL at ``https://api.github.com/graphql``;
a GitHub Enterprise Server at ``HOST`` answers REST at ``https://HOST/api/v3``
and GraphQL at ``https://HOST/api/graphql``. Every request the Workbench sends
goes through :func:`quill.core.github.rest_transport.request_json`, which asks
:func:`api_url` where a token's request goes, so a token is only ever sent to
the host its account was saved for: a GitHub.com token never reaches an
Enterprise server, and an Enterprise token never reaches GitHub.com.

The binding is kept by a hash of the token, never the token itself, and only
for this process: :func:`bind_token` is called wherever an account's token is
loaded (``accounts.load_github_account_token``) or about to be verified.

An older Enterprise Server lacks some endpoints GitHub.com has; it answers
404. :func:`missing_endpoint_sentence` says so plainly ("this server's GitHub
does not have ..."), and :func:`remember_server_version` keeps the version
``GET /meta`` reported, so :mod:`quill.core.github.api_coverage` can grey a
row before anyone tries it.

wx-free and strict-typed.
"""

from __future__ import annotations

import hashlib
import re
import threading

__all__ = [
    "API_VERSION",
    "DOTCOM",
    "api_url",
    "bind_token",
    "forget_bindings",
    "host_for_token",
    "is_enterprise",
    "missing_endpoint_sentence",
    "normalize_host",
    "pygithub_host",
    "remember_server_version",
    "rest_root",
    "server_version",
    "graphql_url",
    "web_root",
]

#: GitHub.com's host, as accounts store it.
DOTCOM = "github.com"

#: The REST API version every request asks for. GitHub.com and GitHub
#: Enterprise Server 3.9 and later honour it; an older server ignores it.
API_VERSION = "2022-11-28"

_HOST_RE = re.compile(
    r"^(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z][a-z0-9-]{0,62}(?::\d{1,5})?$"
)
#: Hosts that are GitHub.com under another name, and so never an Enterprise Server.
_DOTCOM_NAMES = frozenset({"github.com", "www.github.com", "api.github.com"})


class GitHubHostError(ValueError):
    """A host name that cannot be a GitHub server."""


def normalize_host(text: str) -> str:
    """``github.com`` or an Enterprise host name, lower-cased; raises for anything else.

    Accepts what people paste: ``ghe.example.com``, ``https://ghe.example.com/``
    or ``https://ghe.example.com/api/v3``. A path other than the API's own, a
    user name, a query or a non-HTTPS scheme is refused.
    """
    value = text.strip().casefold()
    if value.startswith("https://"):
        value = value.removeprefix("https://")
    elif "://" in value:
        raise GitHubHostError("A GitHub server is reached over HTTPS only.")
    value = value.rstrip("/")
    for suffix in ("/api/v3", "/api/graphql", "/api"):
        value = value.removesuffix(suffix)
    value = value.rstrip(".")
    if value in _DOTCOM_NAMES:
        return DOTCOM
    if not value or "/" in value or "@" in value or "?" in value or "#" in value:
        raise GitHubHostError(
            "Type the server's name only, such as github.example.com, without a path."
        )
    if not _HOST_RE.fullmatch(value):
        raise GitHubHostError(f"{text.strip()} is not a server name QUILL can reach.")
    return value


def is_enterprise(host: str) -> bool:
    return host != DOTCOM


def rest_root(host: str) -> str:
    """Where *host* answers REST: ``https://api.github.com`` or ``https://HOST/api/v3``."""
    return "https://api.github.com" if host == DOTCOM else f"https://{host}/api/v3"


def graphql_url(host: str) -> str:
    """Where *host* answers GraphQL."""
    return "https://api.github.com/graphql" if host == DOTCOM else f"https://{host}/api/graphql"


def web_root(host: str) -> str:
    return f"https://{host}"


_BOUND: dict[str, str] = {}
_VERSIONS: dict[str, str] = {}
_LOCK = threading.Lock()


def _key(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def bind_token(token: str | None, host: str) -> None:
    """Remember, for this process, that *token* belongs to *host*."""
    if not token:
        return
    normalized = normalize_host(host)
    with _LOCK:
        _BOUND[_key(token)] = normalized


def host_for_token(token: str | None) -> str:
    """The host *token* was bound to; GitHub.com for a token never bound (or none)."""
    if not token:
        return DOTCOM
    with _LOCK:
        return _BOUND.get(_key(token), DOTCOM)


def forget_bindings() -> None:
    """Forget every binding and server version (tests; sign-out)."""
    with _LOCK:
        _BOUND.clear()
        _VERSIONS.clear()


def api_url(token: str | None, path: str) -> str:
    """The full address for *path* with *token*'s host.

    ``/graphql`` is GraphQL's own address on either kind of server; every other
    path is under the host's REST root.
    """
    host = host_for_token(token)
    if path == "/graphql":
        return graphql_url(host)
    return rest_root(host) + path


def pygithub_host(token: str | None) -> dict[str, str]:
    """PyGithub's ``base_url`` for *token*'s host: nothing for GitHub.com, its default."""
    host = host_for_token(token)
    return {"base_url": rest_root(host)} if is_enterprise(host) else {}


def remember_server_version(host: str, version: str) -> None:
    """Keep the version an Enterprise server's ``GET /meta`` reported (``installed_version``)."""
    if not is_enterprise(host) or not re.fullmatch(r"\d+\.\d+(?:\.\d+)?", version.strip()):
        return
    with _LOCK:
        _VERSIONS[host] = version.strip()


def server_version(host: str) -> str | None:
    """The remembered Enterprise Server version; ``None`` for GitHub.com or when unknown."""
    if not is_enterprise(host):
        return None
    with _LOCK:
        return _VERSIONS.get(host)


def missing_endpoint_sentence(host: str, path: str) -> str:
    """What a 404 from an Enterprise server means, in one plain sentence.

    A 404 on GitHub.com means "not found, or you cannot see it". On an Enterprise
    Server it can also mean the server's version of GitHub has no such endpoint,
    and that is said first, because no change of access would fix it.
    """
    version = server_version(host)
    where = f"GitHub Enterprise Server at {host}" + (f", version {version}," if version else "")
    what = _what(path)
    return (
        f"This server's GitHub does not have {what}, or this account cannot see it: "
        f"{where} answered 'not found'. An older server lacks some of what GitHub.com has; "
        "its administrator can say which version it runs."
    )


def _what(path: str) -> str:
    """The feature a path asks for: ``/repos/o/r/rules/branches/main`` is "rules"."""
    bare = path.split("?")[0]
    parts = [part for part in bare.split("/") if part]
    skip = {"repos": 3, "orgs": 2, "users": 2, "enterprises": 2}.get(parts[0] if parts else "", 0)
    rest = parts[skip:] or parts[-1:]
    words = rest[0].replace("-", " ").replace("_", " ").strip() if rest else ""
    return f"{words} ({bare})" if words else bare
