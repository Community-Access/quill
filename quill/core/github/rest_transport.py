"""One small authenticated REST transport for GitHub workbench writes and reads.

PyGithub covers most of the workbench, but a few endpoints it either lacks
(``rerun-failed-jobs``, ``pending_deployments``, ``approve``, notification
``Done``) or hides the response headers of (``X-Poll-Interval`` on the
notifications inbox). Those calls come through :func:`request_json` instead:
one fixed host (``api.github.com``), verified TLS, a 20-second timeout, and no
redirect following, so the bearer token can never be forwarded to another
host. Failures raise :class:`GitHubRestError`, which carries the status,
headers and parsed body so :func:`rest_failure_message` can turn it into an
action a person can take.

No ``wx`` imports; strict-typed.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, HTTPSHandler, Request, build_opener

from quill.core.error_codes import CodedError
from quill.core.github.auth_diagnostics import github_exception_hint
from quill.core.net import verified_ssl_context

API_ROOT = "https://api.github.com"
_TIMEOUT_SECONDS = 20
_MAX_RESPONSE_BYTES = 8_000_000


class GitHubRestError(CodedError):
    """A GitHub REST request failed; ``status``/``headers``/``data`` describe how."""

    code = "QUILL-GITHUB-REST-REQUEST-FAILED"

    def __init__(
        self,
        message: str,
        *,
        status: int | None = None,
        headers: dict[str, str] | None = None,
        data: object = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.headers = headers or {}
        self.data = data


@dataclass(frozen=True, slots=True)
class RestResponse:
    """One GitHub REST reply: status code, headers (lower-cased names), JSON body."""

    status: int
    headers: dict[str, str] = field(default_factory=dict)
    data: Any = None

    def header(self, name: str) -> str:
        return self.headers.get(name.casefold(), "")


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *_args: object, **_kwargs: object) -> None:
        return None


class _Headers(dict[str, str]):
    """Header names stored lower-cased and looked up case-insensitively."""

    def get(self, key: str, default: str | None = None) -> str | None:  # type: ignore[override]
        return super().get(key.casefold(), default)


def _headers_of(raw: object) -> dict[str, str]:
    items = getattr(raw, "items", None)
    if not callable(items):
        return _Headers()
    try:
        return _Headers({str(key).casefold(): str(value) for key, value in items()})
    except Exception:  # noqa: BLE001 - header containers vary by client
        return _Headers()


def _decode(body: bytes) -> Any:
    if not body.strip():
        return None
    try:
        return json.loads(body.decode("utf-8", errors="replace"))
    except ValueError:
        return None


def request_json(
    token: str | None,
    method: str,
    path: str,
    *,
    body: dict[str, object] | None = None,
    query: dict[str, str] | None = None,
    extra_headers: dict[str, str] | None = None,
    opener: Any = None,
) -> RestResponse:
    """Send one request to ``api.github.com`` + *path* and return its reply.

    A 304 (Not Modified) is returned, not raised, so a caller polling with
    ``If-Modified-Since`` can keep what it already shows. Every other non-2xx
    status raises :class:`GitHubRestError`.
    """
    if not path.startswith("/") or "//" in path or "\\" in path:
        raise GitHubRestError("Refusing a GitHub API path that is not a plain absolute path.")
    url = API_ROOT + path + (f"?{urlencode(query)}" if query else "")
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "QUILL-GitHub-Workbench",
        **(extra_headers or {}),
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    payload = None
    if body is not None:
        payload = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = Request(url, data=payload, headers=headers, method=method.upper())
    if opener is None:
        opener = build_opener(_NoRedirect, HTTPSHandler(context=verified_ssl_context()))
    try:
        with opener.open(request, timeout=_TIMEOUT_SECONDS) as response:
            raw = response.read(_MAX_RESPONSE_BYTES + 1)
            status = int(getattr(response, "status", 200) or 200)
            response_headers = _headers_of(getattr(response, "headers", None))
    except HTTPError as exc:
        error_headers = _headers_of(exc.headers)
        if exc.code == 304:
            return RestResponse(304, error_headers, None)
        if exc.code in (301, 302, 303, 307, 308):
            raise GitHubRestError(
                "GitHub redirected the request; QUILL did not follow it, so your "
                "token stayed on api.github.com.",
                status=exc.code,
                headers=error_headers,
            ) from exc
        try:
            error_body = exc.read(_MAX_RESPONSE_BYTES)
        except Exception:  # noqa: BLE001 - a body is optional on errors
            error_body = b""
        data = _decode(error_body)
        message = data.get("message", "") if isinstance(data, dict) else ""
        raise GitHubRestError(
            str(message) or f"GitHub returned HTTP {exc.code}.",
            status=exc.code,
            headers=error_headers,
            data=data,
        ) from exc
    except GitHubRestError:
        raise
    except Exception as exc:  # noqa: BLE001 - network failures become visible
        raise GitHubRestError(f"Could not reach GitHub: {exc}") from exc
    if len(raw) > _MAX_RESPONSE_BYTES:
        raise GitHubRestError("GitHub's reply was larger than QUILL reads in one request.")
    return RestResponse(status, response_headers, _decode(raw))


def rest_failure_message(action: str, exc: GitHubRestError) -> str:
    """Say what failed and what to do next, without any credential text."""
    hint = github_exception_hint(exc)
    detail = str(exc.data.get("message", "")) if isinstance(exc.data, dict) else ""
    if hint:
        reason = hint + (f" GitHub said: {detail}" if detail and exc.status == 403 else "")
    elif exc.status == 404:
        reason = (
            "GitHub could not find it, or this account cannot see it. "
            "Refresh the list; it may already be gone."
        )
    elif exc.status == 409:
        reason = f"GitHub reported a conflict: {detail or 'the item changed'}. Refresh and retry."
    elif exc.status == 422:
        reason = f"GitHub refused the request: {detail or 'it is not allowed in this state'}."
    elif exc.status is not None and exc.status >= 500:
        reason = f"GitHub had a server error (HTTP {exc.status}). Wait a moment and retry."
    else:
        reason = detail or (str(exc.args[0]) if exc.args else "GitHub refused the request.")
    return f"Could not {action}. {reason}"


__all__ = [
    "API_ROOT",
    "GitHubRestError",
    "RestResponse",
    "request_json",
    "rest_failure_message",
]
