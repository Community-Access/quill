"""The one door to a WordPress site's REST API (wordpress.md 9.1).

Every WordPress feature in QUILL and QUILL Lite reaches the site through
:class:`WordPressApi`, so three things are decided once and cannot drift:

* **Where a request goes.** A self-hosted site is ``<site>/wp-json/<route>``;
  a WordPress.com site is ``https://public-api.wordpress.com/<route with the
  site inserted>`` (``wp/v2/posts`` becomes ``wp/v2/sites/<site>/posts``), which
  is the same ``wp/v2`` shape behind a different base. :func:`route_url` holds
  that rule.
* **How it is signed.** An application password is HTTP Basic; a
  WordPress.com token is a Bearer header. The secret never appears in an
  exception, a log line or a ``repr``.
* **What a failure says.** WordPress answers a refusal with a JSON body whose
  ``code`` is stable (``rest_cannot_publish``, ``rest_post_invalid_id``...).
  :func:`plain_error` turns each into one sentence a person can act on, so no
  feature ever surfaces "HTTP 403" or a raw error code (wordpress.md 9.2, 5.10).

Network calls go through an injected *opener* (``urllib.request.urlopen`` by
default), which is how every test runs without a network: it hands back
recorded responses.
"""

from __future__ import annotations

import json
import ssl
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass, field
from typing import Any, Literal
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlparse
from urllib.request import Request, urlopen

from quill.core.error_codes import CodedError

AuthKind = Literal["app_password", "bearer", "none"]

WPCOM_API_BASE = "https://public-api.wordpress.com"
DEFAULT_TIMEOUT = 15.0
#: WordPress caps ``per_page`` at 100.
MAX_PER_PAGE = 100


class WordPressApiError(CodedError):
    """A request the site refused, or one that never arrived.

    ``status`` is the HTTP status (0 when the site could not be reached),
    ``wp_code`` WordPress's own error code when it sent one, and the message is
    already the plain sentence from :func:`plain_error`.
    """

    code = "QUILL-WORDPRESS-API-REQUEST"

    def __init__(self, message: str, *, status: int = 0, wp_code: str = "") -> None:
        super().__init__(message)
        self.status = status
        self.wp_code = wp_code

    @property
    def plain(self) -> str:
        """The sentence alone, without the support code in front."""
        return str(self.args[0]) if self.args else ""


class WordPressPolicyError(CodedError):
    """A site address QUILL will not send a password to (not HTTPS)."""

    code = "QUILL-WORDPRESS-API-INSECURE"


@dataclass(frozen=True)
class SiteAuth:
    """How to sign requests to one site. The secret is never shown."""

    kind: AuthKind
    username: str = ""
    secret: str = field(default="", repr=False)

    def header(self) -> str:
        if self.kind == "none":
            return ""
        if self.kind == "bearer":
            return f"Bearer {self.secret}"
        import base64

        token = f"{self.username.strip()}:{self.secret.strip()}".encode()
        return "Basic " + base64.b64encode(token).decode("ascii")

    def __repr__(self) -> str:
        return f"SiteAuth(kind={self.kind!r}, username={self.username!r}, secret=<hidden>)"


@dataclass(frozen=True)
class SiteAddress:
    """Where a site's REST API lives.

    *site_url* is the address a person types (``https://example.org``). For a
    WordPress.com site *wpcom_site* is its id or domain
    (``example.wordpress.com``) and requests go to the public API instead.
    """

    site_url: str
    wpcom_site: str = ""

    @property
    def is_wpcom(self) -> bool:
        return bool(self.wpcom_site)


@dataclass(frozen=True)
class ApiResponse:
    payload: Any
    status: int
    headers: Mapping[str, str]

    @property
    def total(self) -> int | None:
        return _int_header(self.headers, "X-WP-Total")

    @property
    def total_pages(self) -> int | None:
        return _int_header(self.headers, "X-WP-TotalPages")


Opener = Callable[..., Any]


def route_url(address: SiteAddress, route: str, params: Mapping[str, object] | None = None) -> str:
    """The full URL for *route* (``wp/v2/posts``, ``wp-site-health/v1/...``).

    WordPress.com inserts ``sites/<site>`` after the namespace's version:
    ``wp/v2/posts`` -> ``wp/v2/sites/<site>/posts``. The REST index (an empty
    route) is ``wp/v2/sites/<site>`` there and ``/wp-json/`` on a self-hosted
    site.
    """
    clean = route.strip("/")
    if address.is_wpcom:
        site = quote(address.wpcom_site, safe="")
        parts = clean.split("/")
        if len(parts) >= 2:
            namespaced = "/".join([*parts[:2], "sites", site, *parts[2:]])
        else:
            namespaced = f"wp/v2/sites/{site}"
        url = f"{WPCOM_API_BASE}/{namespaced}"
    else:
        url = address.site_url.rstrip("/") + "/wp-json/" + clean
    query = _query(params)
    return f"{url}?{query}" if query else url


def check_address(site_url: str) -> None:
    """Refuse to send a password anywhere but HTTPS (or a loopback test site)."""
    parsed = urlparse(site_url.strip())
    scheme = parsed.scheme.lower()
    host = (parsed.hostname or "").lower()
    if scheme == "https" and host:
        return
    if scheme == "http" and _is_loopback(host):
        return
    raise WordPressPolicyError(
        "QUILL only connects to WordPress sites over HTTPS, so your password is "
        "never sent in the clear. Check that the address starts with https://."
    )


def send_to_site(request: Request, timeout: float | None = None, context: Any = None) -> Any:
    """The one place a WordPress site is reached (the egress audit's marker).

    Every REST call, upload and batch from :class:`WordPressApi` lands here
    unless a test injects its own opener.
    """
    return urlopen(request, timeout=timeout, context=context)


class WordPressApi:
    """Signed JSON requests to one site, with plain-sentence failures."""

    def __init__(
        self,
        address: SiteAddress,
        auth: SiteAuth,
        *,
        opener: Opener | None = None,
        timeout: float = DEFAULT_TIMEOUT,
        site_name: str = "",
    ) -> None:
        if not address.is_wpcom:
            check_address(address.site_url)
        self.address = address
        self.auth = auth
        self._opener = opener or send_to_site
        self.timeout = timeout
        self.site_name = site_name or _host(address.site_url)

    def __repr__(self) -> str:
        return f"WordPressApi({self.address!r}, {self.auth!r})"

    # -- the one request path ------------------------------------------- #

    def request(
        self,
        method: str,
        route: str,
        *,
        params: Mapping[str, object] | None = None,
        json_body: object | None = None,
        data: bytes | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> ApiResponse:
        url = route_url(self.address, route, params)
        send_headers = {"Accept": "application/json"}
        signature = self.auth.header()
        if signature:
            send_headers["Authorization"] = signature
        body = data
        if json_body is not None:
            body = json.dumps(json_body).encode("utf-8")
            send_headers["Content-Type"] = "application/json"
        send_headers.update(headers or {})
        request = Request(url, data=body, headers=send_headers, method=method.upper())
        try:
            with self._opener(request, timeout=self.timeout, context=_context(url)) as response:
                raw = response.read()
                status = int(getattr(response, "status", 200) or 200)
                response_headers = _headers(response)
        except HTTPError as exc:
            raise _error_from_http(exc, method=method, site_name=self.site_name) from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise WordPressApiError(_network_sentence(exc, self.site_name)) from exc
        payload = _decode(raw, self.site_name)
        return ApiResponse(payload, status, response_headers)

    def get(self, route: str, **params: object) -> Any:
        return self.request("GET", route, params=params).payload

    def post(self, route: str, body: object | None = None, **params: object) -> Any:
        return self.request("POST", route, params=params, json_body=body or {}).payload

    def delete(self, route: str, **params: object) -> Any:
        return self.request("DELETE", route, params=params).payload

    def iter_collection(
        self,
        route: str,
        params: Mapping[str, object] | None = None,
        *,
        per_page: int = MAX_PER_PAGE,
        max_pages: int = 1000,
    ) -> Iterator[dict[str, Any]]:
        """Every item of a collection, page after page, with no More button.

        Stops on the last page by ``X-WP-TotalPages``, or on a short page when a
        site strips that header.
        """
        page = 1
        while page <= max_pages:
            merged: dict[str, object] = {**(params or {}), "per_page": per_page, "page": page}
            try:
                response = self.request("GET", route, params=merged)
            except WordPressApiError as exc:
                # Asking past the end is a 400 rest_post_invalid_page_number.
                if exc.wp_code == "rest_post_invalid_page_number" and page > 1:
                    return
                raise
            items = response.payload if isinstance(response.payload, list) else []
            yield from (item for item in items if isinstance(item, dict))
            total_pages = response.total_pages
            if total_pages is not None and page >= total_pages:
                return
            if total_pages is None and len(items) < per_page:
                return
            page += 1

    def upload(
        self,
        route: str,
        filename: str,
        content: bytes,
        content_type: str,
        *,
        fields: Mapping[str, object] | None = None,
    ) -> Any:
        """Send a file as the raw body, the way ``wp/v2/media`` expects."""
        safe_name = filename.replace('"', "").replace("\r", "").replace("\n", "")
        response = self.request(
            "POST",
            route,
            params=fields,
            data=content,
            headers={
                "Content-Type": content_type,
                "Content-Disposition": f'attachment; filename="{safe_name}"',
            },
        )
        return response.payload

    def batch(self, requests: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Several writes as one ``batch/v1`` request (WordPress 5.6+).

        Each entry is ``{"method": "POST", "path": "/wp/v2/posts/12", "body": {...}}``.
        WordPress takes at most 25 at a time, so larger sets go in chunks; the
        answers come back in order.
        """
        answers: list[dict[str, Any]] = []
        for start in range(0, len(requests), 25):
            chunk = requests[start : start + 25]
            payload = self.post(
                "batch/v1", {"validation": "require-all-validate", "requests": chunk}
            )
            responses = payload.get("responses", []) if isinstance(payload, dict) else []
            answers.extend(item for item in responses if isinstance(item, dict))
        return answers


# --------------------------------------------------------------------------- #
# Failures, in words


#: WordPress error codes -> what a person should be told. Kept as whole
#: sentences rather than templates so each reads naturally aloud.
_WP_CODE_SENTENCES: dict[str, str] = {
    "rest_cannot_publish": (
        "Your account on {site} cannot publish this. You can save it as a draft, or submit it "
        "for review."
    ),
    "rest_cannot_edit": "Your account on {site} is not allowed to change this item.",
    "rest_cannot_create": "Your account on {site} is not allowed to create this kind of item.",
    "rest_cannot_delete": "Your account on {site} is not allowed to delete this item.",
    "rest_cannot_edit_others": "Your account on {site} can only change items you wrote yourself.",
    "rest_cannot_assign_term": "Your account on {site} cannot choose that category or tag.",
    "rest_cannot_create_user": "Your account on {site} cannot add users.",
    "rest_cannot_manage_plugins": "Your account on {site} cannot manage plugins.",
    "rest_cannot_manage_options": "Only an administrator on {site} can change site settings.",
    "rest_forbidden": "Your account on {site} is not allowed to do that.",
    "rest_forbidden_context": "Your account on {site} cannot see that in editing mode.",
    "rest_upload_user_quota_exceeded": "{site} has no room left for uploads.",
    "rest_upload_file_too_big": "That file is bigger than {site} accepts.",
    "rest_upload_sideload_error": "{site} could not accept that file.",
    "rest_post_invalid_id": "That page or post is no longer on {site}. It may have been deleted.",
    "rest_term_invalid": "That category or tag is no longer on {site}.",
    "rest_post_incorrect_password": "That item is password protected.",
    "rest_already_trashed": "That item is already in the Trash on {site}.",
    "rest_trash_not_supported": (
        "{site} does not keep this kind of item in a Trash, so it can only be deleted for good."
    ),
    "rest_no_route": (
        "{site} does not offer this. It may be turned off, or the site may need a newer WordPress."
    ),
    "rest_not_logged_in": (
        "{site} did not accept the sign-in. Check the username and application password, then "
        "reconnect."
    ),
    "incorrect_password": (
        "{site} did not accept the application password. Check it belongs to this account, "
        "then reconnect."
    ),
    "invalid_username": "{site} does not know that username. Check it and reconnect.",
    "invalid_email": "{site} does not know that email address. Check it and reconnect.",
    "application_passwords_disabled": (
        "Application passwords are turned off on {site}. Ask the site's administrator to turn "
        "them on."
    ),
    "rest_cookie_invalid_nonce": "{site} refused the request. Reconnect and try again.",
    "rest_user_cannot_delete_self": "You cannot delete your own account from here.",
    "existing_user_login": "That username is already taken on {site}.",
    "existing_user_email": "That email address is already used by another account on {site}.",
    "term_exists": "A category or tag with that name already exists on {site}.",
    "rest_batch_not_allowed": "{site} would not run that change as one batch.",
    "rest_plugin_not_found": "That plugin is not on {site}.",
    "folder_exists": "That plugin is already installed on {site}.",
}


def plain_error(
    *,
    status: int,
    wp_code: str = "",
    wp_message: str = "",
    site_name: str = "the site",
    method: str = "GET",
) -> str:
    """One sentence for a refused request; never a bare code or status."""
    site = site_name or "the site"
    if wp_code in _WP_CODE_SENTENCES:
        return _WP_CODE_SENTENCES[wp_code].format(site=site)
    if status == 401:
        return (
            f"{site} did not accept the sign-in. Check the username and application password, "
            f"then reconnect."
        )
    if status == 403:
        if wp_message and "security" in wp_message.lower():
            return (
                f"A security setting on {site} blocked QUILL. Ask the site's "
                "administrator to allow the WordPress REST API and application passwords."
            )
        return f"Your account on {site} is not allowed to do that."
    if status == 404:
        return f"{site} could not find that. It may have been moved or deleted."
    if status == 413:
        return f"That is too big for {site} to accept."
    if status == 429:
        return f"{site} is asking QUILL to slow down. Wait a minute and try again."
    if status >= 500:
        return f"{site} had a problem of its own (error {status}). Try again in a moment."
    if wp_message:
        clean = wp_message.strip().rstrip(".")
        return f"{site} said: {clean}."
    verb = "loading" if method.upper() == "GET" else "saving"
    return f"{site} refused the request while {verb} (error {status})."


def _error_from_http(exc: HTTPError, *, method: str, site_name: str) -> WordPressApiError:
    wp_code = ""
    wp_message = ""
    try:
        body = json.loads(exc.read().decode("utf-8", errors="replace") or "{}")
        if isinstance(body, dict):
            wp_code = str(body.get("code", "") or "")
            wp_message = _strip_tags(str(body.get("message", "") or ""))
    except (ValueError, OSError, AttributeError):
        pass
    sentence = plain_error(
        status=exc.code, wp_code=wp_code, wp_message=wp_message, site_name=site_name, method=method
    )
    return WordPressApiError(sentence, status=exc.code, wp_code=wp_code)


def _network_sentence(exc: BaseException, site_name: str) -> str:
    reason = str(getattr(exc, "reason", "") or exc).lower()
    if "timed out" in reason or isinstance(exc, TimeoutError):
        return f"{site_name} took too long to answer. Check your connection and try again."
    if "certificate" in reason or "ssl" in reason:
        return f"{site_name}'s security certificate could not be checked, so QUILL did not connect."
    if "getaddrinfo" in reason or "name or service" in reason or "nodename" in reason:
        return f"QUILL could not find {site_name}. Check the address, and that you are online."
    return f"QUILL could not reach {site_name}. Check your connection and try again."


# --------------------------------------------------------------------------- #
# Small helpers


def _decode(raw: bytes, site_name: str) -> Any:
    if not raw:
        return None
    text = raw.decode("utf-8", errors="replace").lstrip("﻿")
    try:
        return json.loads(text)
    except ValueError as exc:
        # A PHP notice printed before the JSON is common on shared hosts.
        start = min((i for i in (text.find("{"), text.find("[")) if i >= 0), default=-1)
        if start > 0:
            try:
                return json.loads(text[start:])
            except ValueError:
                pass
        raise WordPressApiError(
            f"{site_name} sent back something that is not WordPress data. A plugin or "
            "the host may be getting in the way."
        ) from exc


def _query(params: Mapping[str, object] | None) -> str:
    if not params:
        return ""
    flat: list[tuple[str, str]] = []
    for key, value in params.items():
        if value is None:
            continue
        if isinstance(value, bool):
            flat.append((key, "true" if value else "false"))
        elif isinstance(value, (list, tuple, set, frozenset)):
            flat.append((key, ",".join(str(v) for v in value)))
        else:
            flat.append((key, str(value)))
    return urlencode(flat)


def _headers(response: Any) -> dict[str, str]:
    raw = getattr(response, "headers", None)
    if raw is None:
        return {}
    try:
        return {str(k): str(v) for k, v in raw.items()}
    except AttributeError:
        return {}


def _int_header(headers: Mapping[str, str], name: str) -> int | None:
    for key, value in headers.items():
        if key.lower() == name.lower():
            try:
                return int(value)
            except ValueError:
                return None
    return None


def _context(url: str) -> ssl.SSLContext | None:
    if urlparse(url).scheme == "https":
        from quill.core.net import verified_ssl_context

        return verified_ssl_context()
    return None


def _is_loopback(host: str) -> bool:
    return (
        host in {"127.0.0.1", "::1", "[::1]", "localhost"}
        or host.endswith(".localhost")
        or host.endswith(".test")
    )


def _host(site_url: str) -> str:
    return (urlparse(site_url).netloc or site_url).strip().rstrip("/") or "the site"


def _strip_tags(text: str) -> str:
    import re

    return re.sub(r"<[^>]+>", "", text).strip()
