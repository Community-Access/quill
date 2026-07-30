"""Spotify OAuth 2.0 Authorization-Code-with-PKCE sign-in (no client secret).

A native desktop app cannot keep a client secret, so Spotify's PKCE flow is
the right one: QUILL generates a high-entropy ``code_verifier``, sends only its
SHA-256 ``code_challenge`` to the authorize endpoint, and proves possession of
the verifier when it redeems the code. The user's browser lands on a loopback
``http://127.0.0.1`` redirect that :mod:`quill.core.spotify.auth_callback`
receives; a random ``state`` guards against a cross-site redirect.

Modelled on :mod:`quill.core.ai.oauth_poster` and
:mod:`quill.core.mastodon.client`: the two token exchanges (authorization-code
redemption and refresh) POST an ``application/x-www-form-urlencoded`` body to
Spotify's token endpoint through a single private funnel,
:func:`_token_request`, which is the module's one reviewed network-egress site
(see ``quill/tools/network_egress_audit.py``). The funnel takes an injectable
``opener`` -- defaulting to a real, TLS-verified ``urlopen`` -- so the request
encoding and the JSON/error parsing are unit-tested offline with a fake opener,
never a live endpoint.

wx-free, strict-typed.
"""

from __future__ import annotations

import base64
import hashlib
import json
import secrets
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, replace

from quill import __version__
from quill.core.error_codes import CodedError
from quill.core.net import verified_ssl_context

#: Spotify's public OAuth endpoints (accounts service is HTTPS-only).
AUTHORIZE_URL = "https://accounts.spotify.com/authorize"
TOKEN_URL = "https://accounts.spotify.com/api/token"

#: The loopback redirect the browser returns to. A fixed high port keeps the
#: value the user registers on their Spotify app dashboard stable; the
#: :class:`~quill.core.spotify.auth_callback.CallbackServer` binds it before the
#: browser opens so the port is already held when Spotify redirects back.
DEFAULT_REDIRECT_URI = "http://127.0.0.1:43217/callback"

#: Scopes QUILL requests. ``streaming`` + ``user-read-email`` +
#: ``user-read-private`` are the Web Playback SDK's hard requirements (and
#: Premium-only); the library/playback-state read scopes back the Radio/Cast
#: browse surfaces. Kept as a tuple so the set is explicit and diff-able.
DEFAULT_SCOPES: tuple[str, ...] = (
    "streaming",
    "user-read-email",
    "user-read-private",
    "user-read-playback-state",
    "user-modify-playback-state",
    "user-library-read",
    "playlist-read-private",
)

_USER_AGENT = f"QUILL/{__version__} (https://github.com/Community-Access/quill)"
_TIMEOUT_SECONDS = 30.0

#: An opener performs one prepared request and returns ``(status, body_bytes)``.
#: Identical in spirit to :data:`quill.core.ai.oauth_poster.Opener`, so a test
#: can hand either module the same fake.
Opener = Callable[[urllib.request.Request], "tuple[int, bytes]"]


class SpotifyAuthError(CodedError):
    """A Spotify sign-in / token exchange failed (network, OAuth, or Safe Mode)."""

    code = "QUILL-SPOTIFY-AUTH-FAILED"


def refuse_in_safe_mode(safe_mode: bool) -> None:
    """Raise :class:`SpotifyAuthError` when Safe Mode is active.

    Safe Mode (``QUILL_SAFE_MODE=1``) disables every network service. Signing in
    to Spotify is a network service, so the UI calls this before building an
    authorization request. Kept in core (with the flag passed in) so the refusal
    is unit-testable without wx.
    """
    if safe_mode:
        raise SpotifyAuthError(
            "Spotify sign-in is disabled in Safe Mode. Restart QUILL normally to connect Spotify."
        )


@dataclass(frozen=True, slots=True)
class AuthorizationRequest:
    """The browser URL to open plus the secrets that redeem the returned code.

    ``code_verifier`` and ``state`` are held by the caller for the length of the
    sign-in and never leave the machine: the verifier is sent only to the token
    endpoint, and the state is compared against the value Spotify echoes back to
    the loopback redirect.
    """

    url: str
    code_verifier: str
    state: str


@dataclass(frozen=True, slots=True)
class TokenResponse:
    """A parsed token endpoint reply.

    ``expires_in`` is Spotify's seconds-until-expiry; callers convert it to an
    absolute ``expires_at`` when persisting (see
    :class:`quill.core.spotify.token_store.TokenBundle`).
    """

    access_token: str
    refresh_token: str
    expires_in: int
    scope: str
    token_type: str = "Bearer"

    @classmethod
    def from_json(cls, data: dict[str, object]) -> TokenResponse:
        return cls(
            access_token=str(data.get("access_token", "")),
            refresh_token=str(data.get("refresh_token", "")),
            expires_in=_coerce_int(data.get("expires_in"), 3600),
            scope=str(data.get("scope", "")),
            token_type=str(data.get("token_type", "Bearer")) or "Bearer",
        )


def build_pkce_pair() -> tuple[str, str]:
    """Return ``(code_verifier, code_challenge)`` for a fresh PKCE exchange.

    The verifier is 43-128 characters of URL-safe entropy (RFC 7636);
    ``token_urlsafe(64)`` lands comfortably inside that range. The challenge is
    the base64url-encoded SHA-256 of the verifier with padding stripped, exactly
    what Spotify expects for ``code_challenge_method=S256``.
    """
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return verifier, challenge


def build_authorization(
    client_id: str,
    redirect_uri: str = DEFAULT_REDIRECT_URI,
    scopes: tuple[str, ...] = DEFAULT_SCOPES,
    *,
    show_dialog: bool = False,
) -> AuthorizationRequest:
    """Build the authorize URL and the PKCE/state secrets that redeem its code.

    ``show_dialog=True`` forces Spotify to re-prompt even for an already-approved
    account (used by an explicit "sign in as a different user" action).
    """
    if not client_id.strip():
        raise SpotifyAuthError("A Spotify Client ID is required to sign in.")
    verifier, challenge = build_pkce_pair()
    state = secrets.token_urlsafe(24)
    query = urllib.parse.urlencode({
        "client_id": client_id.strip(),
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "scope": " ".join(scopes),
        "code_challenge_method": "S256",
        "code_challenge": challenge,
        "state": state,
        "show_dialog": "true" if show_dialog else "false",
    })
    return AuthorizationRequest(f"{AUTHORIZE_URL}?{query}", verifier, state)


def exchange_code(
    code: str,
    verifier: str,
    client_id: str,
    redirect_uri: str = DEFAULT_REDIRECT_URI,
    *,
    opener: Opener | None = None,
) -> TokenResponse:
    """Redeem an authorization *code* for an access + refresh token pair."""
    return _token_request(
        {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": client_id.strip(),
            "code_verifier": verifier,
        },
        opener=opener,
    )


def refresh(
    refresh_token: str,
    client_id: str,
    *,
    opener: Opener | None = None,
) -> TokenResponse:
    """Exchange a *refresh_token* for a fresh access token.

    Spotify may omit ``refresh_token`` from a refresh reply (the existing one
    stays valid), so a blank one is backfilled with the token we sent -- callers
    can persist the result unconditionally without losing the ability to refresh
    again.
    """
    result = _token_request(
        {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": client_id.strip(),
        },
        opener=opener,
    )
    if not result.refresh_token:
        return replace(result, refresh_token=refresh_token)
    return result


def _token_request(fields: dict[str, str], *, opener: Opener | None = None) -> TokenResponse:
    """POST *fields* to Spotify's token endpoint -- the one reviewed egress site.

    HTTPS-only over a verified TLS context with a bounded timeout. Spotify
    signals a rejected grant with an HTTP error *status* and a JSON ``error`` /
    ``error_description`` body, so the body is read on both success and
    ``HTTPError`` and the OAuth error is surfaced as a clean
    :class:`SpotifyAuthError`. ``opener`` is injectable so this whole path is
    exercised offline; the default performs the real request.
    """
    body = urllib.parse.urlencode(fields).encode("utf-8")
    request = urllib.request.Request(
        TOKEN_URL,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "User-Agent": _USER_AGENT,
        },
    )
    if opener is not None:
        status, raw = opener(request)
    else:
        if not TOKEN_URL.startswith("https://"):  # defensive; the constant is https
            raise SpotifyAuthError("Refusing a non-HTTPS Spotify token request.")
        context = verified_ssl_context()
        try:
            with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS, context=context) as resp:
                status, raw = int(resp.status or 200), resp.read()
        except urllib.error.HTTPError as error:
            status, raw = int(error.code), error.read()
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            raise SpotifyAuthError(f"Could not reach Spotify to sign in: {error}") from error
    return _parse_token_response(status, raw)


def _parse_token_response(status: int, raw: bytes) -> TokenResponse:
    """Parse a token endpoint reply, raising :class:`SpotifyAuthError` on error."""
    text = raw.decode("utf-8", errors="replace").strip()
    try:
        parsed = json.loads(text) if text else {}
    except json.JSONDecodeError as error:
        raise SpotifyAuthError("Spotify returned an unreadable sign-in response.") from error
    if not isinstance(parsed, dict):
        raise SpotifyAuthError("Spotify returned an unexpected sign-in response.")
    if status >= 400 or parsed.get("error"):
        detail = str(parsed.get("error_description") or parsed.get("error") or f"HTTP {status}")
        raise SpotifyAuthError(f"Spotify sign-in failed: {detail}")
    response = TokenResponse.from_json(parsed)
    if not response.access_token:
        raise SpotifyAuthError("Spotify did not return an access token.")
    return response


def _coerce_int(value: object, default: int) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str) and value.strip():
        try:
            return int(float(value))
        except ValueError:
            return default
    return default


__all__ = [
    "AUTHORIZE_URL",
    "DEFAULT_REDIRECT_URI",
    "DEFAULT_SCOPES",
    "TOKEN_URL",
    "AuthorizationRequest",
    "Opener",
    "SpotifyAuthError",
    "TokenResponse",
    "build_authorization",
    "build_pkce_pair",
    "exchange_code",
    "refresh",
    "refuse_in_safe_mode",
]
