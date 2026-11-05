"""Sign-in flows for WordPress sites and WordPress.com (wordpress.md 4.2, 4.3).

Two flows live here, both pure Python and free of ``wx``:

- **Self-hosted sites** use the Authorize Application screen
  (``/wp-admin/authorize-application.php``). On approval WordPress redirects
  to our ``success_url`` with ``site_url``, ``user_login`` and ``password``;
  on rejection it redirects to ``reject_url`` with ``success=false``. A
  one-time ``state`` rides on both URLs and is checked on the way back.
- **WordPress.com** uses OAuth 2.1, authorization code with PKCE (S256), as
  a public client with token auth ``none``. No client secret exists.

The reply arrives on a one-time :class:`LoopbackListener` bound to
``127.0.0.1`` (never ``localhost``, which WordPress refuses on purpose and
RFC 8252 section 8.3 warns about).

**Not yet confirmed:** which WordPress release ships core changeset r62096
(March 2026, ticket #57809), the change that accepts a plain-http loopback
``success_url`` on every site. :func:`supports_loopback_success_url` treats
7.0 and later as having it. Confirm against the WordPress 7.0 field guide
and move the threshold if it shipped elsewhere; a wrong guess only costs the
tier-two fallback (paste the password), never a broken connection.

Secrets never appear in an exception message, a log line or a ``repr``:
they are held in :class:`Secret`, whose ``repr`` is redacted.

The errors, :class:`Secret` and the loopback constants live in
:mod:`.signin_base` and :class:`LoopbackListener` in :mod:`.signin_loopback`
(split for GATE-11); all are re-exported here, so import from this module. The only
network call is :func:`exchange_code` / :func:`refresh_tokens`, through an
injected ``opener``.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import secrets
import time
import urllib.error
import urllib.request
import uuid
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

from quill.core.wordpress.signin_base import (
    LOOPBACK_HOST,
    LOOPBACK_PATH,
    AuthorizationDeniedError,
    ListenerError,
    MalformedRedirectError,
    Secret,
    SignInError,
    StateMismatchError,
    TokenResponseError,
)
from quill.core.wordpress.signin_base import query_params as _query
from quill.core.wordpress.signin_loopback import LoopbackListener

__all__ = [
    "LOOPBACK_HOST",
    "LOOPBACK_PATH",
    "WPCOM_AUTHORIZE_ENDPOINT",
    "WPCOM_SCOPES",
    "WPCOM_TOKEN_ENDPOINT",
    "AppPasswordResult",
    "AuthorizationDeniedError",
    "ListenerError",
    "LoopbackListener",
    "MalformedRedirectError",
    "PkcePair",
    "Rejected",
    "Secret",
    "SignInError",
    "StateMismatchError",
    "TokenResponseError",
    "WpcomTokens",
    "authorize_url_from_index",
    "build_authorize_application_url",
    "build_wpcom_authorize_url",
    "exchange_code",
    "looks_like_application_password",
    "new_state",
    "parse_authorize_application_redirect",
    "parse_token_response",
    "parse_wpcom_redirect",
    "refresh_request",
    "refresh_tokens",
    "supports_loopback_success_url",
    "token_request",
]

WPCOM_AUTHORIZE_ENDPOINT = "https://public-api.wordpress.com/oauth2-1/authorize"
WPCOM_TOKEN_ENDPOINT = "https://public-api.wordpress.com/oauth2-1/token"
#: The narrowest scopes that cover the PRD; ``global`` is deliberately absent.
WPCOM_SCOPES: tuple[str, ...] = ("sites", "posts", "media", "taxonomy", "comments")

#: The first WordPress release assumed to carry r62096 (see module docstring).
_LOOPBACK_MIN_VERSION = (7, 0)


# --------------------------------------------------------------------------
# Results
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class AppPasswordResult:
    """An approved Authorize Application handback."""

    site_url: str
    user_login: str
    password: Secret


@dataclass(frozen=True)
class Rejected:
    """The user pressed "No thanks" on the Authorize Application screen."""

    reason: str = "rejected"


# --------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------


def new_state() -> str:
    """A fresh one-time ``state`` value (URL-safe, 256 bits)."""
    return secrets.token_urlsafe(32)


def _with_query(url: str, params: Mapping[str, str]) -> str:
    """Return ``url`` with ``params`` added to (or replacing in) its query."""
    parts = urlsplit(url)
    existing = [
        (key, value)
        for key, values in parse_qs(parts.query, keep_blank_values=True).items()
        for value in values
        if key not in params
    ]
    query = urlencode([*existing, *params.items()])
    return urlunsplit((parts.scheme, parts.netloc, parts.path, query, parts.fragment))


def _check_state(params: Mapping[str, str], expected_state: str) -> None:
    got = params.get("state", "")
    if not expected_state or not got:
        raise StateMismatchError("The sign-in reply carried no state.")
    if not hmac.compare_digest(got.encode(), expected_state.encode()):
        raise StateMismatchError("The sign-in reply was not the one QUILL asked for.")


# --------------------------------------------------------------------------
# Self-hosted: Authorize Application
# --------------------------------------------------------------------------


def authorize_url_from_index(index_json: Mapping[str, Any] | str | bytes) -> str | None:
    """The Authorize Application URL from a REST index (``GET /wp-json/``).

    Returns ``None`` when the index does not advertise it, which means
    application passwords are unavailable on that site (tier three).
    """
    data: Any = index_json
    if isinstance(data, (str, bytes)):
        try:
            data = json.loads(data)
        except ValueError:
            return None
    try:
        url = data["authentication"]["application-passwords"]["endpoints"]["authorization"]
    except (KeyError, TypeError, IndexError):
        return None
    if isinstance(url, str) and url.strip():
        return url.strip()
    return None


def build_authorize_application_url(
    authorize_url: str,
    *,
    app_name: str,
    app_id: str,
    success_url: str | None,
    reject_url: str | None,
    state: str,
) -> str:
    """The URL to open in the browser for the Authorize Application screen.

    ``state`` is added as a query parameter to ``success_url`` and
    ``reject_url`` so the reply can be matched to this request. Pass
    ``success_url=None`` for tier two: WordPress then shows the password on
    its own page for the user to copy.
    """
    if not state:
        raise ValueError("state must not be empty")
    try:
        uuid.UUID(app_id)
    except ValueError as exc:
        raise ValueError("app_id must be a UUID") from exc
    params: dict[str, str] = {"app_name": app_name, "app_id": app_id}
    if success_url:
        params["success_url"] = _with_query(success_url, {"state": state})
    if reject_url:
        params["reject_url"] = _with_query(reject_url, {"state": state})
    return _with_query(authorize_url, params)


_VERSION_RE = re.compile(r"^\s*(\d+)(?:\.(\d+))?")


def supports_loopback_success_url(wp_version: str) -> bool:
    """Whether a site of this version accepts ``http://127.0.0.1`` success URLs.

    7.0 and later are assumed to carry r62096 (unconfirmed; see the module
    docstring). Pre-release suffixes count as their release. An unreadable
    version answers ``False``, which falls back to the paste flow.
    """
    match = _VERSION_RE.match(wp_version or "")
    if match is None:
        return False
    major = int(match.group(1))
    minor = int(match.group(2) or 0)
    return (major, minor) >= _LOOPBACK_MIN_VERSION


def parse_authorize_application_redirect(
    url: str, expected_state: str
) -> AppPasswordResult | Rejected:
    """Read the Authorize Application handback that reached the listener."""
    params = _query(url)
    _check_state(params, expected_state)
    if params.get("success", "").lower() == "false":
        return Rejected()
    missing = [name for name in ("site_url", "user_login", "password") if not params.get(name)]
    if missing:
        raise MalformedRedirectError("WordPress's reply is missing " + ", ".join(missing) + ".")
    return AppPasswordResult(
        site_url=params["site_url"],
        user_login=params["user_login"],
        password=Secret(params["password"]),
    )


_APP_PASSWORD_RE = re.compile(r"[A-Za-z0-9]{24}|(?:[A-Za-z0-9]{4} ){5}[A-Za-z0-9]{4}")


def looks_like_application_password(text: str) -> bool:
    """Whether ``text`` has the shape of a WordPress application password.

    Twenty-four letters and digits, either run together or in six groups of
    four separated by single spaces. Surrounding whitespace is ignored.
    """
    if not isinstance(text, str):
        return False
    return _APP_PASSWORD_RE.fullmatch(text.strip()) is not None


# --------------------------------------------------------------------------
# WordPress.com: OAuth 2.1 with PKCE
# --------------------------------------------------------------------------

_UNRESERVED_RE = re.compile(r"[A-Za-z0-9\-._~]{43,128}")


def _s256(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


@dataclass(frozen=True)
class PkcePair:
    """A PKCE code verifier and its S256 challenge (RFC 7636)."""

    verifier: str = field(repr=False)
    challenge: str
    method: str = "S256"

    @classmethod
    def generate(cls, nbytes: int = 64) -> PkcePair:
        """A fresh pair. 64 random bytes give an 86-character verifier."""
        verifier = secrets.token_urlsafe(nbytes)
        return cls.from_verifier(verifier)

    @classmethod
    def from_verifier(cls, verifier: str) -> PkcePair:
        if _UNRESERVED_RE.fullmatch(verifier) is None:
            raise ValueError("A PKCE verifier is 43 to 128 characters from A-Z, a-z, 0-9 and -._~")
        return cls(verifier=verifier, challenge=_s256(verifier))


def _scope_text(scopes: Iterable[str] | str) -> str:
    if isinstance(scopes, str):
        return " ".join(scopes.split())
    return " ".join(s for s in scopes if s)


def build_wpcom_authorize_url(
    client_id: str,
    redirect_uri: str,
    scopes: Iterable[str] | str,
    state: str,
    challenge: str,
) -> str:
    """The WordPress.com authorization URL for the code flow with PKCE."""
    if not state:
        raise ValueError("state must not be empty")
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": _scope_text(scopes),
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    return f"{WPCOM_AUTHORIZE_ENDPOINT}?{urlencode(params)}"


def parse_wpcom_redirect(url: str, expected_state: str) -> str:
    """The authorization code from a WordPress.com redirect.

    Raises :class:`AuthorizationDeniedError` when the user declined, and
    :class:`StateMismatchError` when the reply is not ours.
    """
    params = _query(url)
    _check_state(params, expected_state)
    error = params.get("error")
    if error:
        if error == "access_denied":
            raise AuthorizationDeniedError("WordPress.com sign-in was declined.")
        raise AuthorizationDeniedError(f"WordPress.com refused the sign-in ({error}).")
    code = params.get("code", "")
    if not code:
        raise MalformedRedirectError("WordPress.com's reply carried no code.")
    return code


TokenRequest = tuple[str, bytes, dict[str, str]]

_FORM_HEADERS = {
    "Content-Type": "application/x-www-form-urlencoded",
    "Accept": "application/json",
}


def token_request(code: str, verifier: str, client_id: str, redirect_uri: str) -> TokenRequest:
    """``(url, form body, headers)`` for exchanging a code for tokens."""
    body = urlencode({
        "grant_type": "authorization_code",
        "code": code,
        "code_verifier": verifier,
        "client_id": client_id,
        "redirect_uri": redirect_uri,
    }).encode("ascii")
    return WPCOM_TOKEN_ENDPOINT, body, dict(_FORM_HEADERS)


def refresh_request(refresh_token: Secret | str, client_id: str) -> TokenRequest:
    """``(url, form body, headers)`` for renewing tokens with a refresh token."""
    token = refresh_token.reveal() if isinstance(refresh_token, Secret) else refresh_token
    body = urlencode({
        "grant_type": "refresh_token",
        "refresh_token": token,
        "client_id": client_id,
    }).encode("ascii")
    return WPCOM_TOKEN_ENDPOINT, body, dict(_FORM_HEADERS)


@dataclass(frozen=True)
class WpcomTokens:
    """Tokens from the WordPress.com token endpoint. ``repr`` is redacted."""

    access_token: Secret
    refresh_token: Secret | None
    expires_at: float | None
    scope: tuple[str, ...]
    blog_id: str | None = None
    token_type: str = "bearer"

    def expired(self, *, now: float | None = None, leeway: float = 60.0) -> bool:
        if self.expires_at is None:
            return False
        current = time.time() if now is None else now
        return current >= self.expires_at - leeway


def parse_token_response(
    data: Mapping[str, Any] | str | bytes, *, now: float | None = None
) -> WpcomTokens:
    """Read a token endpoint body into :class:`WpcomTokens`."""
    body: Any = data
    if isinstance(body, (str, bytes)):
        try:
            body = json.loads(body)
        except ValueError:
            raise TokenResponseError("WordPress.com's token reply was not JSON.") from None
    if not isinstance(body, Mapping):
        raise TokenResponseError("WordPress.com's token reply was not an object.")
    error = body.get("error")
    if error:
        raise TokenResponseError(f"WordPress.com refused the token request ({error}).")
    access = body.get("access_token")
    if not isinstance(access, str) or not access:
        raise TokenResponseError("WordPress.com's token reply had no access token.")
    refresh = body.get("refresh_token")
    expires_at: float | None = None
    expires_in = body.get("expires_in")
    if isinstance(expires_in, (int, float, str)) and not isinstance(expires_in, bool):
        try:
            seconds = float(expires_in)
        except ValueError:
            seconds = -1.0
        if seconds >= 0:
            expires_at = (time.time() if now is None else now) + seconds
    blog_id = body.get("blog_id")
    blog_text = str(blog_id) if blog_id not in (None, "", 0, "0") else None
    token_type = body.get("token_type")
    return WpcomTokens(
        access_token=Secret(access),
        refresh_token=Secret(refresh) if isinstance(refresh, str) and refresh else None,
        expires_at=expires_at,
        scope=tuple(_scope_text(str(body.get("scope") or "")).split()),
        blog_id=blog_text,
        token_type=str(token_type).lower() if token_type else "bearer",
    )


Opener = Callable[..., Any]


def _error_field(raw: bytes) -> str | None:
    try:
        body = json.loads(raw)
    except ValueError:
        return None
    if isinstance(body, Mapping) and isinstance(body.get("error"), str):
        return str(body["error"])
    return None


def _post(request: TokenRequest, opener: Opener, timeout: float, now: float | None) -> WpcomTokens:
    url, body, headers = request
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with opener(req, timeout=timeout) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        # OAuth errors come back as 400 with a JSON body naming the error.
        try:
            raw = exc.read()
        except OSError:
            raw = b""
        finally:
            exc.close()
        error = _error_field(raw)
        detail = f"({error})" if error else f"(HTTP {exc.code})"
        raise TokenResponseError(f"WordPress.com refused the token request {detail}.") from None
    except (urllib.error.URLError, OSError) as exc:
        reason = getattr(exc, "reason", exc)
        raise TokenResponseError(f"Could not reach WordPress.com ({reason}).") from None
    return parse_token_response(raw, now=now)


def _token_urlopen(request: urllib.request.Request, timeout: float | None = None) -> Any:
    """WordPress.com's token endpoint, the one network call in sign-in (egress marker)."""
    from quill.core.net import verified_ssl_context

    return urllib.request.urlopen(request, timeout=timeout, context=verified_ssl_context())


def exchange_code(
    code: str,
    verifier: str,
    client_id: str,
    redirect_uri: str,
    *,
    opener: Opener | None = None,
    timeout: float = 30.0,
    now: float | None = None,
) -> WpcomTokens:
    """Exchange an authorization code for tokens (the one network call)."""
    request = token_request(code, verifier, client_id, redirect_uri)
    return _post(request, opener or _token_urlopen, timeout, now)


def refresh_tokens(
    refresh_token: Secret | str,
    client_id: str,
    *,
    opener: Opener | None = None,
    timeout: float = 30.0,
    now: float | None = None,
) -> WpcomTokens:
    """Renew tokens silently with a refresh token."""
    return _post(refresh_request(refresh_token, client_id), opener or _token_urlopen, timeout, now)
