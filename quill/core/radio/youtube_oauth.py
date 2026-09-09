"""Connect YouTube Account: the OAuth session behind real-time subscriptions.

The Takeout import (:mod:`quill.core.radio.youtube_takeout`) answers "I follow
forty channels; do not make me paste forty addresses" with no account and no
network call at all. This module answers a different, narrower question --
*I want that list kept live, and I am willing to sign in for it* -- with
Google's own sanctioned Authorization-Code-with-PKCE flow.

**What this is.** Sign-in, sign-out, and token refresh only: building the
Google authorize URL, running the loopback redirect, exchanging a code (or a
refresh token) for an access token, and persisting the resulting session. What
an authenticated session is used *for* -- listing subscriptions/playlists via
the YouTube Data API v3 and importing them into
:class:`~quill.core.radio.youtube_channels.ChannelStore` -- lives in
:mod:`quill.core.radio.youtube_oauth_api` (GATE-11 -- extract, never
rebaseline).

**What this is not.** It never touches yt-dlp, never resolves a stream, and
never plays anything. Playback of anything added through this path goes
through the exact same yt-dlp path a pasted channel link already does --
nothing about *how a video plays* changes. Keeping those two paths apart is
the whole reason this is safe to ship alongside yt-dlp playback: an
API-authenticated "what do I follow" is not mixed with a scraped stream in the
same request the way a terms-of-service violation would require.

**The client is QUILL's, not the listener's.** A per-listener Google Cloud
project would repeat the "seven steps of console work" Takeout was built to
avoid. So, like the Podcast Index credential, one OAuth client is baked in at
build time by ``tools/generate_youtube_oauth_client.py`` into the gitignored
``quill._youtube_oauth_client`` module -- never committed, and reported as
unavailable rather than broken when absent (a dev checkout with nothing baked
in simply cannot offer this feature). Unlike the Podcast Index key, this
credential grants real per-user access, so the OAuth consent screen for the
``youtube.readonly`` scope must be a verified Google app (or the signer added
as a test user) before sign-in will work for anyone but a developer -- an
external Cloud Console step, not a code path.

Tokens are the listener's own and never baked in: they live only in the OS
secret vault via :class:`~quill.core.secrets.SecretsManager`, namespaced
``youtube``, exactly like every other OAuth session in QUILL.

Locked off in a public build (``released=False`` on the ``future.youtube_oauth``
feature) until the Cloud Console verification above is complete; reachable in a
developer build (``QUILL_DEV_BUILD=1``) for testing against Google's own
"test users" allowance. Refused outright in Safe Mode. wx-free, strict-typed.
"""

from __future__ import annotations

import http.server
import json
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from collections.abc import Callable
from dataclasses import dataclass, replace

from quill import __version__
from quill.core.auth.token_bundle import TokenBundle
from quill.core.error_codes import CodedError
from quill.core.net import verified_ssl_context
from quill.core.secrets import SecretRef, default_secrets_manager

__all__ = [
    "AUTHORIZE_URL",
    "DEFAULT_REDIRECT_URI",
    "REVOKE_URL",
    "SCOPE",
    "TOKEN_URL",
    "AuthorizationRequest",
    "TokenResponse",
    "YouTubeOAuthError",
    "available",
    "bundled_client",
    "build_authorization",
    "clear_tokens",
    "exchange_code",
    "get_access_token",
    "is_signed_in",
    "load_tokens",
    "refresh",
    "refuse_in_safe_mode",
    "save_tokens",
    "sign_in",
    "sign_out",
]

AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
REVOKE_URL = "https://oauth2.googleapis.com/revoke"

#: Read-only: lists what the account follows, nothing more. Deliberately not
#: ``youtube`` (read/write) or ``youtube.force-ssl`` -- this feature only ever
#: reads.
SCOPE = "https://www.googleapis.com/auth/youtube.readonly"

#: A fixed loopback port, distinct from Spotify's 43217 (core/spotify/auth.py)
#: so the two features can be connected in the same run. Google's "Desktop app"
#: OAuth client type accepts any 127.0.0.1 redirect without pre-registering the
#: port (RFC 8252), so a fixed value here is a convenience, not a requirement.
DEFAULT_REDIRECT_URI = "http://127.0.0.1:8912/callback"

_USER_AGENT = f"QUILL/{__version__} (https://github.com/Community-Access/quill)"
_TIMEOUT_SECONDS = 30.0
_CALLBACK_TIMEOUT_SECONDS = 600.0

#: An opener performs one prepared request and returns ``(status, body_bytes)``.
Opener = Callable[[urllib.request.Request], "tuple[int, bytes]"]

_SECRETS = default_secrets_manager()
_TOKENS_REF = SecretRef("youtube", "tokens")


class YouTubeOAuthError(CodedError):
    """A YouTube sign-in, token refresh, or API call failed, or was refused."""

    code = "QUILL-RADIO-YTOAUTH-FAILED"


def refuse_in_safe_mode(safe_mode: bool) -> None:
    """Raise :class:`YouTubeOAuthError` when Safe Mode is active."""
    if safe_mode:
        raise YouTubeOAuthError(
            "Connecting a YouTube account is disabled in Safe Mode. Restart QUILL "
            "normally to sign in."
        )


def bundled_client() -> tuple[str, str]:
    """The application OAuth client baked in at build time, or ``("", "")``.

    Written by ``tools/generate_youtube_oauth_client.py`` into the gitignored
    ``quill._youtube_oauth_client`` module, so the credential is never in the
    repository. See the module docstring for what this credential is and is
    not.
    """
    try:
        from quill._youtube_oauth_client import (  # type: ignore[import-untyped]
            BUNDLED_YOUTUBE_OAUTH_CLIENT_ID,
            BUNDLED_YOUTUBE_OAUTH_CLIENT_SECRET,
        )
    except ImportError:
        return "", ""
    return (
        (BUNDLED_YOUTUBE_OAUTH_CLIENT_ID or "").strip(),
        (BUNDLED_YOUTUBE_OAUTH_CLIENT_SECRET or "").strip(),
    )


def available() -> bool:
    """Whether Connect YouTube Account can be offered at all in this build."""
    client_id, client_secret = bundled_client()
    return bool(client_id and client_secret)


# --- token bundle persistence --------------------------------------------------


def load_tokens() -> TokenBundle:
    """The listener's stored YouTube session, or an empty bundle when none."""
    raw = _SECRETS.get(_TOKENS_REF)
    return TokenBundle.from_json(raw) if raw else TokenBundle()


def save_tokens(bundle: TokenBundle) -> None:
    _SECRETS.set(_TOKENS_REF, bundle.to_json())


def clear_tokens() -> None:
    _SECRETS.delete(_TOKENS_REF)


def is_signed_in() -> bool:
    return not load_tokens().is_empty


# --- OAuth: authorization request, loopback redirect, token exchange ----------


@dataclass(frozen=True, slots=True)
class AuthorizationRequest:
    """The browser URL to open plus the secrets that redeem the returned code."""

    url: str
    code_verifier: str
    state: str


@dataclass(frozen=True, slots=True)
class TokenResponse:
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
            expires_in=_coerce_int(data.get("expires_in")),
            scope=str(data.get("scope", "")),
            token_type=str(data.get("token_type", "Bearer")) or "Bearer",
        )


def _coerce_int(value: object) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str) and value.strip():
        try:
            return int(float(value))
        except ValueError:
            return 0
    return 0


def _pkce_pair() -> tuple[str, str]:
    """``(code_verifier, code_challenge)`` for a fresh PKCE exchange (RFC 7636)."""
    import base64
    import hashlib
    import secrets as _secrets_module

    verifier = _secrets_module.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return verifier, challenge


def build_authorization(
    client_id: str, redirect_uri: str = DEFAULT_REDIRECT_URI
) -> AuthorizationRequest:
    """Build Google's authorize URL and the PKCE/state secrets that redeem its code.

    ``access_type=offline`` plus ``prompt=consent`` are what makes Google
    return a ``refresh_token`` at all -- without them a second consent from the
    same account returns an access token only, and this feature is built
    around not asking the listener to re-authorize every hour.
    """
    import secrets as _secrets_module

    verifier, challenge = _pkce_pair()
    state = _secrets_module.token_urlsafe(24)
    query = urllib.parse.urlencode({
        "client_id": client_id.strip(),
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "scope": SCOPE,
        "code_challenge_method": "S256",
        "code_challenge": challenge,
        "state": state,
        "access_type": "offline",
        "prompt": "consent",
    })
    return AuthorizationRequest(f"{AUTHORIZE_URL}?{query}", verifier, state)


def _wait_for_redirect(
    expected_state: str,
    redirect_uri: str,
    *,
    timeout: float,
    on_ready: Callable[[], None] | None = None,
) -> str:
    """Block for the single OAuth redirect on the loopback address; return its code.

    Deliberately small, mirroring ``core/spotify/auth_callback.py`` and
    ``core/auth/flows.py``'s ``_loopback_waiter`` -- this is the only socket I/O
    in the module. Binds before ``on_ready`` fires, so the browser can never
    race an unbound port.
    """
    parsed = urllib.parse.urlparse(redirect_uri)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 0
    captured: dict[str, str] = {}

    class _Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802 - http.server API
            query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            captured["code"] = (query.get("code") or [""])[0]
            captured["state"] = (query.get("state") or [""])[0]
            captured["error"] = (query.get("error") or [""])[0]
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(
                b"QUILL is connected to YouTube. You can close this tab and return to QUILL."
            )

        def log_message(self, *args: object) -> None:  # silence default stderr logging
            pass

    server = http.server.HTTPServer((host, port), _Handler)
    try:
        if on_ready is not None:
            on_ready()
        server.timeout = timeout
        server.handle_request()
    finally:
        server.server_close()
    if not captured:
        raise YouTubeOAuthError("Timed out waiting for the YouTube sign-in to complete.")
    if captured.get("error"):
        raise YouTubeOAuthError(f"YouTube sign-in was refused: {captured['error']}")
    if captured.get("state") != expected_state:
        raise YouTubeOAuthError("YouTube sign-in state did not match; sign-in was not completed.")
    code = captured.get("code", "")
    if not code:
        raise YouTubeOAuthError("YouTube did not return an authorization code.")
    return code


def _context_for(url: str) -> ssl.SSLContext | None:
    return verified_ssl_context() if url.startswith("https://") else None


def _token_request(fields: dict[str, str], *, opener: Opener | None = None) -> TokenResponse:
    """POST *fields* to Google's token endpoint -- the reviewed egress site.

    HTTPS-only over a verified TLS context with a bounded timeout. ``opener``
    is injectable so the whole exchange is unit-tested offline.
    """
    if not TOKEN_URL.startswith("https://"):  # defensive; the constant is https
        raise YouTubeOAuthError("Refusing a non-HTTPS YouTube token request.")
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
        try:
            with urllib.request.urlopen(
                request, timeout=_TIMEOUT_SECONDS, context=_context_for(TOKEN_URL)
            ) as resp:
                status, raw = int(resp.status or 200), resp.read()
        except urllib.error.HTTPError as error:
            status, raw = int(error.code), error.read()
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            raise YouTubeOAuthError(f"Could not reach Google to sign in: {error}") from error
    return _parse_token_response(status, raw)


def _parse_token_response(status: int, raw: bytes) -> TokenResponse:
    text = raw.decode("utf-8", errors="replace").strip()
    try:
        parsed = json.loads(text) if text else {}
    except json.JSONDecodeError as error:
        raise YouTubeOAuthError("Google returned an unreadable sign-in response.") from error
    if not isinstance(parsed, dict):
        raise YouTubeOAuthError("Google returned an unexpected sign-in response.")
    if status >= 400 or parsed.get("error"):
        detail = str(parsed.get("error_description") or parsed.get("error") or f"HTTP {status}")
        raise YouTubeOAuthError(f"YouTube sign-in failed: {detail}")
    response = TokenResponse.from_json(parsed)
    if not response.access_token:
        raise YouTubeOAuthError("Google did not return an access token.")
    return response


def exchange_code(
    code: str,
    verifier: str,
    client_id: str,
    client_secret: str,
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
            "client_secret": client_secret.strip(),
            "code_verifier": verifier,
        },
        opener=opener,
    )


def refresh(
    refresh_token: str, client_id: str, client_secret: str, *, opener: Opener | None = None
) -> TokenResponse:
    """Exchange a *refresh_token* for a fresh access token.

    Google omits ``refresh_token`` from a refresh reply (the existing one
    stays valid), so a blank one is backfilled with the token sent -- callers
    can persist the result unconditionally without losing the ability to
    refresh again.
    """
    result = _token_request(
        {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": client_id.strip(),
            "client_secret": client_secret.strip(),
        },
        opener=opener,
    )
    if not result.refresh_token:
        return replace(result, refresh_token=refresh_token)
    return result


def sign_in(
    *,
    safe_mode: bool = False,
    opener: Opener | None = None,
    browser_opener: Callable[[str], None] | None = None,
    callback_timeout: float = _CALLBACK_TIMEOUT_SECONDS,
) -> None:
    """Run the full loopback sign-in flow and persist the resulting session.

    Blocks until the listener completes (or abandons) the browser consent
    screen, so callers run this off the UI thread. Raises
    :class:`YouTubeOAuthError` when this build has no bundled client, in Safe
    Mode, on a state mismatch, a refused consent, a timeout, or a token
    exchange failure.
    """
    refuse_in_safe_mode(safe_mode)
    client_id, client_secret = bundled_client()
    if not (client_id and client_secret):
        raise YouTubeOAuthError(
            "This build has no YouTube sign-in credential configured. See "
            "tools/generate_youtube_oauth_client.py."
        )
    request = build_authorization(client_id)
    open_browser = browser_opener or webbrowser.open

    def _on_ready() -> None:
        open_browser(request.url)

    code = _wait_for_redirect(
        request.state, DEFAULT_REDIRECT_URI, timeout=callback_timeout, on_ready=_on_ready
    )
    response = exchange_code(code, request.code_verifier, client_id, client_secret, opener=opener)
    save_tokens(TokenBundle.from_token_response(response, now=time.time()))


def sign_out(*, opener: Opener | None = None) -> None:
    """Forget the YouTube session, best-effort revoking it at Google first.

    A revoke failure (offline, already revoked, transient error) never blocks
    clearing the local session -- an unreachable revoke call must not leave a
    listener unable to disconnect.
    """
    bundle = load_tokens()
    token = bundle.refresh_token or bundle.access_token
    if token:
        try:
            _revoke(token, opener=opener)
        except Exception:  # noqa: BLE001 - local sign-out must always succeed
            pass
    clear_tokens()


def _revoke(token: str, *, opener: Opener | None = None) -> None:
    body = urllib.parse.urlencode({"token": token}).encode("utf-8")
    request = urllib.request.Request(
        REVOKE_URL,
        data=body,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded", "User-Agent": _USER_AGENT},
    )
    if opener is not None:
        opener(request)
        return
    with urllib.request.urlopen(
        request, timeout=_TIMEOUT_SECONDS, context=_context_for(REVOKE_URL)
    ):
        pass


def get_access_token(*, opener: Opener | None = None, now: float | None = None) -> str | None:
    """A currently-valid access token, refreshing if needed, or ``None``.

    ``None`` means no session is stored, or the refresh token was rejected
    (the caller must sign in again).
    """
    bundle = load_tokens()
    if bundle.is_empty:
        return None
    clock = now if now is not None else time.time()
    if not bundle.needs_refresh(clock):
        return bundle.access_token or None
    if not bundle.refresh_token:
        return bundle.access_token or None
    client_id, client_secret = bundled_client()
    if not (client_id and client_secret):
        return None
    try:
        response = refresh(bundle.refresh_token, client_id, client_secret, opener=opener)
    except YouTubeOAuthError:
        return None
    refreshed = TokenBundle.from_token_response(response, now=clock)
    save_tokens(refreshed)
    return refreshed.access_token or None
