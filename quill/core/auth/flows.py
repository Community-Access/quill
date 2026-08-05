"""Interactive sign-in flow drivers: Authorization Code + PKCE, and device code.

The network-independent parts -- building the authorization URL, validating the
returned ``state``, exchanging a code or polling for a device token -- are pure
functions that take an injected ``poster`` (and, for the loopback flow, an
injected ``waiter``/``opener``), so the whole flow logic is unit-testable with
fakes and no sockets. The default ``waiter``/``opener`` (a loopback HTTP
listener and the system browser) are the only I/O edges and are kept thin.

No new network egress lives here: the token exchange goes through the injected
``poster`` (by default the reviewed :func:`quill.core.ai.oauth_poster.post_form`).
"""

from __future__ import annotations

import secrets
import time
import webbrowser
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

from quill.core.auth.errors import AuthError, FlowStateMismatchError, FlowTimeoutError
from quill.core.auth.pkce import PkcePair, generate_pkce_pair
from quill.core.auth.provider import OAuthProvider
from quill.core.auth.token_bundle import TokenBundle

Poster = Callable[[str, "dict[str, str]"], "dict[str, Any]"]


@dataclass(frozen=True, slots=True)
class AuthRedirect:
    """What the loopback listener captured from the authorization redirect."""

    code: str = ""
    state: str = ""
    error: str = ""


#: Opens a listener on the redirect URI, drives the browser, and blocks until the
#: authorization server redirects back -- returning the captured code/state, or
#: raising :class:`FlowTimeoutError`. Injected for tests.
RedirectWaiter = Callable[[str, str, float], AuthRedirect]
#: Opens a URL in the system browser. Injected for tests.
BrowserOpener = Callable[[str], None]


def build_authorization_url(
    provider: OAuthProvider, *, challenge: str, state: str, method: str = "S256"
) -> str:
    """Build the provider's authorization URL for an Authorization Code + PKCE request."""
    params = {
        "response_type": "code",
        "client_id": provider.client_id,
        "redirect_uri": provider.redirect_uri,
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": method,
    }
    if provider.scopes:
        params["scope"] = provider.scope_str
    separator = "&" if "?" in provider.authorize_url else "?"
    return f"{provider.authorize_url}{separator}{urlencode(params)}"


def exchange_code(
    provider: OAuthProvider,
    poster: Poster,
    *,
    code: str,
    code_verifier: str,
    now: float,
) -> TokenBundle:
    """Exchange an authorization code for a token bundle via ``poster``."""
    url = provider.broker_url or provider.token_url
    response = poster(
        url,
        {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": provider.redirect_uri,
            "client_id": provider.client_id,
            "code_verifier": code_verifier,
        },
    )
    error = str(response.get("error", ""))
    if error:
        raise AuthError(f"{provider.name} token exchange failed: {error}")
    bundle = TokenBundle.from_mapping(response, now=now)
    if bundle.is_empty:
        raise AuthError(f"{provider.name} token exchange returned no tokens")
    return bundle


def run_authorization_code_flow(
    provider: OAuthProvider,
    poster: Poster,
    *,
    waiter: RedirectWaiter | None = None,
    opener: BrowserOpener | None = None,
    now: Callable[[], float] = time.time,
    timeout: float = 300.0,
    pkce: PkcePair | None = None,
    state: str | None = None,
) -> TokenBundle:
    """Drive the full loopback PKCE flow and return the resulting token bundle."""
    pair = pkce or generate_pkce_pair()
    expected_state = state or secrets.token_urlsafe(24)
    auth_url = build_authorization_url(provider, challenge=pair.challenge, state=expected_state)

    (opener or webbrowser.open)(auth_url)
    redirect = (waiter or _loopback_waiter)(auth_url, provider.redirect_uri, timeout)

    if redirect.error:
        raise AuthError(f"{provider.name} sign-in was refused: {redirect.error}")
    if not redirect.code:
        raise FlowTimeoutError(f"{provider.name} sign-in did not complete")
    if redirect.state != expected_state:
        raise FlowStateMismatchError(f"{provider.name} sign-in state did not match")
    return exchange_code(
        provider, poster, code=redirect.code, code_verifier=pair.verifier, now=now()
    )


def run_device_code_flow(
    provider: OAuthProvider,
    poster: Poster,
    on_code: Callable[[str, str], None],
    *,
    now: Callable[[], float] = time.time,
    sleep: Callable[[float], None] | None = None,
    max_seconds: float = 900.0,
) -> TokenBundle:
    """Drive the device-code flow: show the user code, then poll to completion."""
    if not provider.device_code_url:
        raise AuthError(f"{provider.name} has no device_code_url")
    do_sleep = sleep or time.sleep

    start = poster(
        provider.device_code_url,
        {
            "client_id": provider.client_id,
            **({"scope": provider.scope_str} if provider.scopes else {}),
        },
    )
    device_code = str(start.get("device_code", ""))
    user_code = str(start.get("user_code", ""))
    verification_uri = str(start.get("verification_uri", "") or start.get("verification_url", ""))
    if not device_code or not user_code:
        raise AuthError(f"{provider.name} device authorization failed")
    interval = max(_coerce_float(start.get("interval", 5)), 1.0)
    on_code(user_code, verification_uri)

    deadline = now() + max_seconds
    while now() < deadline:
        do_sleep(interval)
        response = poster(
            provider.token_url,
            {
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                "device_code": device_code,
                "client_id": provider.client_id,
            },
        )
        error = str(response.get("error", ""))
        if not error:
            bundle = TokenBundle.from_mapping(response, now=now())
            if bundle.is_empty:
                raise AuthError(f"{provider.name} device flow returned no tokens")
            return bundle
        if error == "authorization_pending":
            continue
        if error == "slow_down":
            interval += 5.0
            continue
        if error == "expired_token":
            raise FlowTimeoutError(f"{provider.name} device code expired before authorization")
        raise AuthError(f"{provider.name} device flow failed: {error}")
    raise FlowTimeoutError(f"{provider.name} device sign-in timed out")


def _coerce_float(value: object) -> float:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0.0


def _loopback_waiter(auth_url: str, redirect_uri: str, timeout: float) -> AuthRedirect:
    """Default waiter: a one-shot loopback HTTP listener for the redirect.

    Kept deliberately small -- it is the flow's only socket I/O and is not unit
    tested; the flow *logic* is covered through an injected fake waiter. Parses
    ``code``/``state``/``error`` from the query string of the single redirect
    request, replies with a short human-readable page, and returns.
    """
    import http.server
    from urllib.parse import parse_qs, urlparse

    parsed = urlparse(redirect_uri)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 0
    captured: dict[str, str] = {}

    class _Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802 - http.server API
            query = parse_qs(urlparse(self.path).query)
            captured["code"] = (query.get("code") or [""])[0]
            captured["state"] = (query.get("state") or [""])[0]
            captured["error"] = (query.get("error") or [""])[0]
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"QUILL sign-in complete. You can return to the app.")

        def log_message(self, *args: object) -> None:  # silence default stderr logging
            pass

    server = http.server.HTTPServer((host, port), _Handler)
    server.timeout = timeout
    try:
        server.handle_request()  # blocks until one request or the timeout
    finally:
        server.server_close()
    if not captured:
        raise FlowTimeoutError("no authorization redirect was received")
    return AuthRedirect(
        code=captured.get("code", ""),
        state=captured.get("state", ""),
        error=captured.get("error", ""),
    )


__all__ = [
    "AuthRedirect",
    "BrowserOpener",
    "Poster",
    "RedirectWaiter",
    "build_authorization_url",
    "exchange_code",
    "run_authorization_code_flow",
    "run_device_code_flow",
]
