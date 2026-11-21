"""Signing in to Scribe for Documents (PRD 7.2), on QUILL's OAuth pieces.

* **PKCE** from :mod:`quill.core.auth.pkce` (S256 only); QUILL is a public
  client, so there is no secret.
* **The authorize URL** is Pneuma's shape: ``/oauth/authorize?...`` wrapped in
  ``/auth/logout?next=...``, so a browser session left from an earlier
  account is dropped before the sign-in page (SCR-POL-2: QUILL opens Scribe's
  own page in the person's browser and never sees what is typed).
* **The redirect** lands on a one-shot loopback listener bound *before* the
  browser opens, on a free port of ``127.0.0.1`` (or ``[::1]``), at
  ``/scribe/callback`` -- the two registered redirect URIs, any port.
* **Tokens** are a :class:`~quill.core.auth.token_bundle.TokenBundle` in the
  :class:`~quill.core.secrets.SecretsManager` under namespace ``scribe``, the
  same entry :class:`~quill.core.auth.token_manager.TokenManager` would use, so
  one sign-in covers every app in the family. Refresh is five minutes before
  expiry (Pneuma's skew) and once more on a 401; ``invalid_grant`` wipes the
  namespace. The token exchange, refresh and revoke go through the reviewed
  :func:`quill.core.ai.oauth_poster.post_form` (an injected poster).

Nothing here logs a token, a code or a verifier. wx-free.
"""

from __future__ import annotations

import http.server
import logging
import socket
import threading
import time
from collections.abc import Callable
from typing import Any
from urllib.parse import parse_qs, urlencode, urlsplit

from quill.core.auth.flows import AuthRedirect
from quill.core.auth.pkce import PkcePair, generate_pkce_pair
from quill.core.auth.token_bundle import TokenBundle
from quill.core.scribe.errors import ScribeError, ScribeSignInError, ScribeSignInLocalError
from quill.core.secrets import SecretRef, SecretsManager, default_secrets_manager

logger = logging.getLogger(__name__)

NAMESPACE = "scribe"
_TOKENS = SecretRef(NAMESPACE, "tokens")
CALLBACK_PATH = "/scribe/callback"
REFRESH_SKEW_S = 300.0
SIGN_IN_TIMEOUT_S = 300.0

#: The page the browser shows after the redirect (7.2).
SIGNED_IN_PAGE = "Signed in. You can close this tab and return to {app}."
REFUSED_PAGE = "Sign-in did not complete. Return to {app} and try again."

Poster = Callable[[str, "dict[str, str]"], "dict[str, Any]"]


def _default_poster(url: str, fields: dict[str, str]) -> dict[str, Any]:
    from quill.core.ai.oauth_poster import post_form

    return post_form(url, fields)


def authorization_url(
    base_url: str, client_id: str, redirect_uri: str, challenge: str, *, locale: str = ""
) -> str:
    """Pneuma's sign-in address: ``/auth/logout?next=/oauth/authorize?...``.

    ``next`` is a path and query only (the server refuses absolute targets).
    """
    authorize_query = urlencode({
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    })
    outer: dict[str, str] = {"next": f"/oauth/authorize?{authorize_query}"}
    if locale:
        outer["locale"] = locale
    return f"{base_url.rstrip('/')}/auth/logout?{urlencode(outer)}"


class LoopbackListener:
    """A one-shot HTTP listener on a free loopback port for the redirect.

    Bound in the constructor, so the redirect URI (with its port) is known
    before the browser opens and a fast redirect cannot arrive to nothing.
    """

    def __init__(self, *, app_name: str = "QUILL") -> None:
        self._app_name = app_name
        self.captured: AuthRedirect | None = None
        self._done = threading.Event()
        listener = self

        class _Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802 - http.server API
                request = urlsplit(self.path)
                if request.path != CALLBACK_PATH:
                    self.send_error(404)
                    return
                query = parse_qs(request.query)
                code = (query.get("code") or [""])[0]
                error = (query.get("error") or [""])[0] or ("" if code else "no_code")
                listener.captured = AuthRedirect(code=code, error=error)
                text = (SIGNED_IN_PAGE if code else REFUSED_PAGE).format(app=listener._app_name)
                body = (
                    "<!doctype html><html lang=en><meta charset=utf-8>"
                    f"<title>Scribe for Documents</title><h1>{text}</h1></html>"
                ).encode()
                self.send_response(200 if code else 400)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                listener._done.set()

            def log_message(self, *_args: object) -> None:  # the query holds the code
                pass

        self._server = self._bind(_Handler)
        host, port = self._server.server_address[:2]
        name = host.decode() if isinstance(host, bytes) else str(host)
        shown = f"[{name}]" if ":" in name else name
        self.redirect_uri = f"http://{shown}:{port}{CALLBACK_PATH}"

    @staticmethod
    def _bind(handler: type[http.server.BaseHTTPRequestHandler]) -> http.server.HTTPServer:
        try:
            return http.server.HTTPServer(("127.0.0.1", 0), handler)
        except OSError:
            pass

        class _V6(http.server.HTTPServer):
            address_family = socket.AF_INET6

        try:
            return _V6(("::1", 0), handler)
        except OSError as error:
            raise ScribeSignInLocalError(
                "QUILL could not open a port on this computer to receive the sign-in. "
                "Check that security software allows QUILL to listen on 127.0.0.1."
            ) from error

    def wait(self, timeout: float, cancelled: Callable[[], bool]) -> AuthRedirect | None:
        """Serve until the redirect arrives, *timeout* passes or *cancelled*."""
        deadline = time.monotonic() + timeout
        self._server.timeout = 0.5
        try:
            while not self._done.is_set():
                if cancelled() or time.monotonic() >= deadline:
                    return None
                self._server.handle_request()
            return self.captured
        finally:
            self.close()

    def close(self) -> None:
        try:
            self._server.server_close()
        except OSError:
            pass


class ScribeSession:
    """The signed-in session: tokens on demand, sign-in, sign-out.

    Implements :class:`quill.core.scribe.client.TokenSource`.
    """

    def __init__(
        self,
        *,
        secrets: SecretsManager | None = None,
        poster: Poster | None = None,
        client_id: str | None = None,
        base_url: str | None = None,
        now: Callable[[], float] = time.time,
    ) -> None:
        from quill.core import scribe

        self._secrets = secrets or default_secrets_manager()
        self._poster = poster or _default_poster
        self._client_id = client_id if client_id is not None else scribe.client_id()
        self.base_url = (base_url or scribe.base_url()).rstrip("/")
        self._now = now
        self._lock = threading.Lock()

    # -------------------------------------------------------------- storage

    def bundle(self) -> TokenBundle:
        raw = self._secrets.get(_TOKENS)
        return TokenBundle.from_json(raw) if raw else TokenBundle()

    def is_signed_in(self) -> bool:
        return not self.bundle().is_empty

    def _store(self, bundle: TokenBundle) -> None:
        self._secrets.set(_TOKENS, bundle.to_json())
        _remember(bundle)

    # ------------------------------------------------------------- sign in

    def begin_sign_in(self, *, app_name: str = "QUILL", locale: str = "") -> SignInAttempt:
        """Bind the listener and build the URL; the caller opens the browser."""
        if not self._client_id:
            raise ScribeError("Scribe for Documents is not available in this build yet.")
        listener = LoopbackListener(app_name=app_name)
        pkce = generate_pkce_pair()
        url = authorization_url(
            self.base_url, self._client_id, listener.redirect_uri, pkce.challenge, locale=locale
        )
        return SignInAttempt(self, listener, pkce, url)

    def exchange(self, code: str, redirect_uri: str, verifier: str) -> TokenBundle:
        response = self._post(
            "/oauth/token",
            {
                "grant_type": "authorization_code",
                "client_id": self._client_id,
                "redirect_uri": redirect_uri,
                "code": code,
                "code_verifier": verifier,
            },
        )
        bundle = TokenBundle.from_mapping(response, now=self._now())
        if bundle.is_empty:
            raise ScribeSignInError(
                _message(response, "We couldn't sign you in. Please try again.")
            )
        self._store(bundle)
        logger.info("Scribe signed in")
        return bundle

    # --------------------------------------------------------------- tokens

    def access_token(self) -> str:
        """A valid access token, refreshed five minutes before expiry."""
        bundle = self.bundle()
        if bundle.is_empty:
            raise ScribeSignInError(
                "You are not signed in to Scribe for Documents.", reason="unauthenticated"
            )
        if (
            bundle.refresh_token
            and bundle.expires_at
            and bundle.is_expired(self._now(), skew=REFRESH_SKEW_S)
        ):
            return self._refresh(bundle.access_token)
        _remember(bundle)
        return bundle.access_token

    def force_refresh(self) -> str:
        """Refresh now (after a 401). Raises :class:`ScribeSignInError` if it cannot."""
        return self._refresh(None)

    def _refresh(self, stale: str | None) -> str:
        with self._lock:
            current = self.bundle()
            if stale is not None and current.access_token != stale:
                return current.access_token  # another thread refreshed meanwhile
            if not current.refresh_token:
                self.wipe()
                raise ScribeSignInError(
                    "Your Scribe for Documents sign-in has ended.", reason="invalid_grant"
                )
            try:
                response = self._post(
                    "/oauth/token",
                    {
                        "grant_type": "refresh_token",
                        "client_id": self._client_id,
                        "refresh_token": current.refresh_token,
                    },
                )
            except OSError:
                from quill.core.scribe.errors import ScribeOfflineError

                raise ScribeOfflineError(
                    "Couldn't connect to Scribe. Check your connection and try again."
                ) from None
            if response.get("error"):
                if str(response.get("error")) == "invalid_grant":
                    self.wipe()
                raise ScribeSignInError(
                    _message(response, "Your session has expired. Please sign in again."),
                    reason=str(response.get("error")),
                )
            fresh = TokenBundle.from_mapping(response, now=self._now())
            if not fresh.access_token:
                raise ScribeSignInError("Your session has expired. Please sign in again.")
            merged = TokenBundle(
                access_token=fresh.access_token,
                refresh_token=fresh.refresh_token or current.refresh_token,
                expires_at=fresh.expires_at,
                scope=fresh.scope or current.scope,
                token_type=fresh.token_type,
            )
            self._store(merged)
            logger.info("Scribe token refreshed")
            return merged.access_token

    # ------------------------------------------------------------- sign out

    def sign_out(self) -> None:
        """Revoke (best effort; the refresh token takes its access tokens with it),
        then wipe the namespace."""
        bundle = self.bundle()
        token = bundle.refresh_token or bundle.access_token
        if token and self._client_id:
            try:
                self._post("/oauth/revoke", {"client_id": self._client_id, "token": token})
            except (OSError, ValueError):
                pass
        self.wipe()
        logger.info("Scribe signed out")

    def wipe(self) -> None:
        self._secrets.wipe_namespace(NAMESPACE)

    def _post(self, path: str, fields: dict[str, str]) -> dict[str, Any]:
        from quill.core.scribe.client import require_secure

        url = f"{self.base_url}{path}"
        require_secure(url)
        return self._poster(url, fields)


class SignInAttempt:
    """One sign-in in progress: open :attr:`url` in the browser, then :meth:`wait`."""

    def __init__(
        self, session: ScribeSession, listener: LoopbackListener, pkce: PkcePair, url: str
    ) -> None:
        self._session = session
        self._listener = listener
        self._pkce = pkce
        self.url = url
        self._cancelled = threading.Event()

    def cancel(self) -> None:
        self._cancelled.set()

    def wait(self, timeout: float = SIGN_IN_TIMEOUT_S) -> TokenBundle | None:
        """Block until signed in (the bundle), or ``None`` on timeout or cancel."""
        redirect = self._listener.wait(timeout, self._cancelled.is_set)
        if redirect is None:
            return None
        if redirect.error or not redirect.code:
            raise ScribeSignInError(
                "Scribe for Documents did not sign you in. Try again.", reason=redirect.error
            )
        return self._session.exchange(
            redirect.code, self._listener.redirect_uri, self._pkce.verifier
        )

    def close(self) -> None:
        self._cancelled.set()
        self._listener.close()


def _message(response: dict[str, Any], fallback: str) -> str:
    return str(response.get("message") or "") or fallback


def _remember(bundle: TokenBundle) -> None:
    """Scrub the tokens from every redacted log line in this process."""
    from quill.stability.redaction import remember_secret

    remember_secret(bundle.access_token)
    remember_secret(bundle.refresh_token)


__all__ = [
    "CALLBACK_PATH",
    "NAMESPACE",
    "REFRESH_SKEW_S",
    "SIGNED_IN_PAGE",
    "LoopbackListener",
    "ScribeSession",
    "SignInAttempt",
    "authorization_url",
]
