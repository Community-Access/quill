"""last.fm and Libre.fm: sign in through the browser, then scrobble.

Libre.fm speaks last.fm's own API at its own address, so one module serves
both (:data:`LASTFM`, :data:`LIBREFM`).

**Signing in is the desktop flow last.fm documents.** Quill Radio asks for a
token (``auth.getToken``), opens the listener's browser at the service's own
"allow this application?" page, and once the listener has said yes there,
trades the token for a session key (``auth.getSession``). The listener's
password never passes through Quill Radio. The session key is kept in the
Windows credential store and does not expire until the listener removes
access on the service's website.

**The application key.** last.fm gives every application an API key and a
shared secret. Quill Radio never invents one. A build can carry one baked in
at build time by ``tools/generate_lastfm_api_key.py`` (into the gitignored
``quill._lastfm_api_key`` module, the way the Podcast Index credential ships);
a listener can always paste their own pair into Preferences, and their own
pair wins. With neither, signing in says what is missing and where to get it.

**Every call is signed**: an MD5 of the parameters sorted by name, each name
followed by its value, then the shared secret (:func:`sign`).

Scrobbles go in batches of up to 50 with ``chosenByUser=0``, which is what
last.fm asks a radio player to send. Error 9 (the session was removed) means
sign in again; 11, 16 and 29 mean try later; anything else means the request
will never be accepted as written. The signature and the call shapes follow
BlindRadio by serrebidev (MIT), ``crates/blindradio-core/src/scrobble.rs``;
the sign-in flow is from https://www.last.fm/api/desktopauth. wx-free,
strict-typed; the one network call is :func:`quill.core.radio.scrobble_http.post`.
"""

from __future__ import annotations

import hashlib
import json
import urllib.parse
from collections.abc import Callable
from dataclasses import dataclass

from quill.core.error_codes import CodedError
from quill.core.radio import radio_credentials, scrobble_http
from quill.core.radio.scrobble_queue import REJECTED, RETRY, SENT, SIGN_IN, Outcome
from quill.core.radio.scrobble_tracker import Listen

#: Where a listener gets their own API key and shared secret, free.
API_ACCOUNT_URL = "https://www.last.fm/api/account/create"

_FORM = "application/x-www-form-urlencoded"

Poster = Callable[..., scrobble_http.Reply]


@dataclass(frozen=True, slots=True)
class Service:
    """One last.fm-compatible service."""

    id: str
    name: str
    api_url: str
    auth_url: str
    session_target: str


LASTFM = Service(
    "lastfm",
    "last.fm",
    "https://ws.audioscrobbler.com/2.0/",
    "https://www.last.fm/api/auth/",
    radio_credentials.LASTFM_SESSION,
)
LIBREFM = Service(
    "librefm",
    "Libre.fm",
    "https://libre.fm/2.0/",
    "https://libre.fm/api/auth/",
    radio_credentials.LIBREFM_SESSION,
)

#: last.fm's error codes, by what they mean for the songs waiting.
_SIGN_IN_CODES = frozenset({4, 9, 10, 14, 15, 26})
_RETRY_CODES = frozenset({8, 11, 16, 29})
NOT_AUTHORISED_CODE = 14

NO_APP_KEY = (
    "Signing in to last.fm or Libre.fm needs a last.fm API key and shared "
    "secret, and this copy of Quill Radio has none. Make a free API account at "
    f"{API_ACCOUNT_URL}, then paste the API key and shared secret into "
    "Preferences, in the Scrobbling group."
)


class LastFmError(CodedError):
    """A last.fm or Libre.fm call failed."""

    code = "QUILL-RADIO-LASTFM-CALL"
    listener_facing = True

    def __init__(self, message: str, *, error_code: int = 0) -> None:
        super().__init__(message)
        self.error_code = error_code


def bundled_credentials() -> tuple[str, str]:
    """The API key and secret baked in at build time, or ``("", "")``."""
    try:
        from quill._lastfm_api_key import (  # type: ignore[import-untyped,import-not-found,unused-ignore]
            BUNDLED_LASTFM_API_KEY,
            BUNDLED_LASTFM_SHARED_SECRET,
        )
    except ImportError:
        return "", ""
    return (
        str(BUNDLED_LASTFM_API_KEY or "").strip(),
        str(BUNDLED_LASTFM_SHARED_SECRET or "").strip(),
    )


def app_credentials(own_key: str = "", own_secret: str = "") -> tuple[str, str]:
    """The pair to use: the listener's own when both are given, else the build's."""
    if own_key.strip() and own_secret.strip():
        return own_key.strip(), own_secret.strip()
    return bundled_credentials()


def stored_app_credentials() -> tuple[str, str]:
    """The listener's own pair from the credential store, else the build's."""
    return app_credentials(
        radio_credentials.load(radio_credentials.LASTFM_API_KEY).secret,
        radio_credentials.load(radio_credentials.LASTFM_SECRET).secret,
    )


def sign(params: dict[str, str], secret: str) -> str:
    """last.fm's ``api_sig`` for *params* (pure). ``format`` is never signed.

    MD5 is not our choice: last.fm's API defines ``api_sig`` as the MD5 of the
    sorted parameters followed by the shared secret
    (https://www.last.fm/api/authspec, section 8), and Libre.fm copies it.
    Nothing here stores or compares a password; the listener's password is
    typed on the service's own page and never reaches Quill Radio.
    """
    plain = "".join(
        f"{name}{value}"
        for name, value in sorted(params.items())
        if name not in ("format", "callback")
    )
    return hashlib.md5((plain + secret).encode("utf-8"), usedforsecurity=False).hexdigest()


def build_call(method: str, params: dict[str, str], *, api_key: str, secret: str) -> bytes:
    """The signed form body for one call (pure)."""
    full = {**params, "method": method, "api_key": api_key}
    full["api_sig"] = sign(full, secret)
    full["format"] = "json"
    return urllib.parse.urlencode(sorted(full.items())).encode("utf-8")


def parse_error(text: str) -> tuple[int, str] | None:
    """``(code, message)`` when an answer is an error, else None (pure)."""
    try:
        data = json.loads(text) if text else None
    except ValueError:
        return None
    if not isinstance(data, dict) or "error" not in data:
        return None
    try:
        code = int(data.get("error") or 0)
    except (TypeError, ValueError):
        code = 0
    return code, str(data.get("message", "") or "").strip()


def _call(
    service: Service,
    method: str,
    params: dict[str, str],
    *,
    api_key: str,
    secret: str,
    safe_mode: bool,
    post: Poster | None,
) -> scrobble_http.Reply:
    sender = post if post is not None else scrobble_http.post
    return sender(
        service.api_url,
        build_call(method, params, api_key=api_key, secret=secret),
        content_type=_FORM,
        safe_mode=safe_mode,
    )


def _answer(service: Service, reply: scrobble_http.Reply) -> dict[str, object]:
    problem = parse_error(reply.text)
    if problem is not None:
        code, message = problem
        raise LastFmError(
            f"{service.name} said: {message or 'error ' + str(code)}.", error_code=code
        )
    try:
        data = json.loads(reply.text)
    except ValueError as error:
        raise LastFmError(f"{service.name}'s answer could not be read.") from error
    if reply.status != 200 or not isinstance(data, dict):
        raise LastFmError(f"{service.name} could not do that ({reply.status}).")
    return data


def get_token(
    service: Service,
    *,
    api_key: str,
    secret: str,
    safe_mode: bool = False,
    post: Poster | None = None,
) -> str:
    """Step one of signing in: a token for the listener to approve."""
    if not (api_key and secret):
        raise LastFmError(NO_APP_KEY)
    try:
        reply = _call(
            service,
            "auth.getToken",
            {},
            api_key=api_key,
            secret=secret,
            safe_mode=safe_mode,
            post=post,
        )
    except scrobble_http.ScrobbleNetworkError as error:
        raise LastFmError(
            f"Could not reach {service.name}. Check the internet connection."
        ) from error
    token = str(_answer(service, reply).get("token", "") or "").strip()
    if not token:
        raise LastFmError(f"{service.name} did not give a sign-in token.")
    return token


def auth_page_url(service: Service, *, api_key: str, token: str) -> str:
    """The page where the listener says yes to Quill Radio (pure)."""
    return f"{service.auth_url}?{urllib.parse.urlencode({'api_key': api_key, 'token': token})}"


def get_session(
    service: Service,
    *,
    api_key: str,
    secret: str,
    token: str,
    safe_mode: bool = False,
    post: Poster | None = None,
) -> tuple[str, str]:
    """Step two: ``(user name, session key)`` once the listener has said yes.

    Raises :class:`LastFmError` with ``error_code == NOT_AUTHORISED_CODE`` when
    the listener has not approved the token yet.
    """
    try:
        reply = _call(
            service,
            "auth.getSession",
            {"token": token},
            api_key=api_key,
            secret=secret,
            safe_mode=safe_mode,
            post=post,
        )
    except scrobble_http.ScrobbleNetworkError as error:
        raise LastFmError(
            f"Could not reach {service.name}. Check the internet connection."
        ) from error
    session = _answer(service, reply).get("session")
    if not isinstance(session, dict) or not str(session.get("key", "") or "").strip():
        raise LastFmError(f"{service.name} did not give a session key.")
    return str(session.get("name", "") or "").strip(), str(session.get("key", "")).strip()


def outcome_for(service: Service, reply: scrobble_http.Reply) -> Outcome:
    """What a ``track.scrobble`` answer means for the songs sent (pure)."""
    problem = parse_error(reply.text)
    if problem is not None:
        code, message = problem
        if code in _SIGN_IN_CODES:
            return Outcome(
                SIGN_IN,
                f"{service.name} no longer accepts Quill Radio's sign-in. Choose "
                f"Sign In to {service.name} in Preferences to sign in again.",
            )
        if code in _RETRY_CODES:
            return Outcome(RETRY, message)
        return Outcome(REJECTED, message or f"error {code}")
    if reply.status == 200:
        return Outcome(SENT)
    if reply.status == 429 or reply.status >= 500:
        return Outcome(RETRY, f"{service.name} is busy ({reply.status}).")
    return Outcome(REJECTED, f"{service.name} refused the scrobbles ({reply.status}).")


def scrobble_params(listens: list[Listen], session_key: str) -> dict[str, str]:
    """The ``track.scrobble`` parameters for a batch (pure, before signing)."""
    params = {"sk": session_key}
    for index, listen in enumerate(listens[:50]):
        params[f"artist[{index}]"] = listen.artist
        params[f"track[{index}]"] = listen.title
        params[f"timestamp[{index}]"] = str(listen.listened_at)
        params[f"chosenByUser[{index}]"] = "0"
        if listen.album:
            params[f"album[{index}]"] = listen.album
    return params


def scrobble(
    service: Service,
    listens: list[Listen],
    *,
    api_key: str,
    secret: str,
    session_key: str,
    safe_mode: bool = False,
    post: Poster | None = None,
) -> Outcome:
    """Send a batch. Network trouble is a RETRY, never an exception."""
    if not session_key:
        return Outcome(SIGN_IN, f"Sign in to {service.name} in Preferences first.")
    if not (api_key and secret):
        return Outcome(SIGN_IN, NO_APP_KEY)
    if not listens:
        return Outcome(SENT)
    try:
        reply = _call(
            service,
            "track.scrobble",
            scrobble_params(listens, session_key),
            api_key=api_key,
            secret=secret,
            safe_mode=safe_mode,
            post=post,
        )
    except scrobble_http.ScrobbleNetworkError as error:
        return Outcome(RETRY, str(error.args[0]) if error.args else "")
    return outcome_for(service, reply)


def update_now_playing(
    service: Service,
    listen: Listen,
    *,
    api_key: str,
    secret: str,
    session_key: str,
    safe_mode: bool = False,
    post: Poster | None = None,
) -> Outcome:
    """Tell the service what is playing now. Never retried, so never queued."""
    if not (session_key and api_key and secret):
        return Outcome(SIGN_IN)
    params = {"sk": session_key, "artist": listen.artist, "track": listen.title}
    if listen.album:
        params["album"] = listen.album
    try:
        reply = _call(
            service,
            "track.updateNowPlaying",
            params,
            api_key=api_key,
            secret=secret,
            safe_mode=safe_mode,
            post=post,
        )
    except scrobble_http.ScrobbleNetworkError:
        return Outcome(RETRY)
    return outcome_for(service, reply)


__all__ = [
    "API_ACCOUNT_URL",
    "LASTFM",
    "LIBREFM",
    "NOT_AUTHORISED_CODE",
    "NO_APP_KEY",
    "LastFmError",
    "Service",
    "app_credentials",
    "auth_page_url",
    "build_call",
    "bundled_credentials",
    "get_session",
    "get_token",
    "outcome_for",
    "parse_error",
    "scrobble",
    "scrobble_params",
    "sign",
    "stored_app_credentials",
    "update_now_playing",
]
