"""Minimal Mastodon API calls for posting (no third-party dependency).

Implements just the four endpoints the "post to Mastodon" feature needs, using
``urllib`` over a verified TLS context (HTTPS only). All network egress funnels
through the single private :func:`_http_json` so there is exactly one reviewed
egress site (see ``quill/tools/network_egress_audit.py``).

The OAuth flow registers an app named **QUILL** on the user's instance, so
published posts are attributed "via QUILL":

    1. register_app(instance) -> (client_id, client_secret)   [POST /api/v1/apps]
    2. authorize_url(instance, client_id)                     [browser GET]
    3. exchange_code(instance, ids, code) -> access_token     [POST /oauth/token]
    4. post_status(instance, token, text, visibility) -> url  [POST /api/v1/statuses]

verify_credentials() is used after sign-in to fetch the @handle for display.

No ``wx`` imports: pure model code.
"""

from __future__ import annotations

import json
import ssl
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

from quill import __version__
from quill.core.error_codes import CodedError

#: The app QUILL registers on the user's instance; shown as the post's source.
CLIENT_NAME = "QUILL"
CLIENT_WEBSITE = "https://github.com/Community-Access/quill"
#: Out-of-band redirect: the instance shows the user a code to paste back.
REDIRECT_OOB = "urn:ietf:wg:oauth:2.0:oob"
#: Scopes QUILL requests: publish statuses, plus read:accounts so
#: verify_credentials can fetch the signed-in @handle for display. The GET
#: /api/v1/accounts/verify_credentials endpoint rejects a write-only token
#: with 403, so read:accounts is required for sign-in to complete.
SCOPES = "read:accounts write:statuses"

#: Mastodon's status visibilities, with human labels (stored value, label).
VISIBILITIES: tuple[tuple[str, str], ...] = (
    ("public", "Public"),
    ("unlisted", "Unlisted"),
    ("private", "Followers only"),
    ("direct", "Direct (mentioned only)"),
)
_VISIBILITY_VALUES = frozenset(value for value, _ in VISIBILITIES)

#: Mastodon's classic per-post character ceiling (instances may allow more).
DEFAULT_CHARACTER_LIMIT = 500

#: Per-instance fetched character limits, keyed by normalized base URL, so the
#: compose dialog's live counter can reflect an instance like poliversity.it
#: that allows 9999 characters instead of the classic 500 (#922). Fetched once
#: per instance per process and reused; cleared only by a fresh process.
_CHARACTER_LIMIT_CACHE: dict[str, int] = {}

_USER_AGENT = f"{CLIENT_NAME}/{__version__}"
_TIMEOUT_SECONDS = 30


class MastodonError(CodedError):
    """A Mastodon request failed (network, auth, or API error)."""

    code = "QUILL-PUBLISH-MASTODON-REQUEST"


@dataclass(frozen=True, slots=True)
class AppCredentials:
    client_id: str
    client_secret: str


def normalize_instance_url(raw: str) -> str:
    """Return a clean ``https://host`` base URL, or raise for an invalid one.

    Accepts ``mastodon.social`` or ``https://mastodon.social/``. Plain ``http``
    is rejected: tokens must never travel in clear text.
    """
    value = (raw or "").strip().rstrip("/")
    if not value:
        raise MastodonError("Enter your Mastodon instance, e.g. mastodon.social")
    if value.startswith("http://"):
        raise MastodonError("Insecure http:// is not allowed; use https://")
    if not value.startswith("https://"):
        value = "https://" + value
    parsed = urllib.parse.urlparse(value)
    if not parsed.netloc or "." not in parsed.netloc:
        raise MastodonError(f"That does not look like a server address: {raw!r}")
    return f"https://{parsed.netloc}"


def _http_json(
    method: str,
    url: str,
    *,
    data: dict[str, str] | None = None,
    token: str | None = None,
) -> dict[str, object]:
    """Perform one HTTPS request and return the decoded JSON object.

    The single network-egress site for Mastodon support. HTTPS-only, verified
    TLS context, short timeout; raises :class:`MastodonError` on any failure so
    callers never leak a raw traceback to the user.
    """
    if not url.startswith("https://"):
        raise MastodonError("Refusing a non-HTTPS Mastodon request.")
    body = urllib.parse.urlencode(data).encode("utf-8") if data is not None else None
    headers = {"User-Agent": _USER_AGENT, "Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    context = ssl.create_default_context()
    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS, context=context) as resp:
            payload = resp.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        raise MastodonError(_describe_http_error(error)) from error
    except (urllib.error.URLError, TimeoutError, ssl.SSLError) as error:
        raise MastodonError(f"Could not reach the server: {error}") from error
    try:
        parsed = json.loads(payload) if payload else {}
    except ValueError as error:
        raise MastodonError("The server returned an unexpected response.") from error
    if not isinstance(parsed, dict):
        raise MastodonError("The server returned an unexpected response.")
    return parsed


def _describe_http_error(error: urllib.error.HTTPError) -> str:
    detail = ""
    try:
        body = error.read().decode("utf-8")
        parsed = json.loads(body)
        if isinstance(parsed, dict):
            detail = str(parsed.get("error_description") or parsed.get("error") or "")
    except Exception:  # noqa: BLE001 - best-effort detail extraction
        detail = ""
    base = f"Server error {error.code}"
    return f"{base}: {detail}" if detail else base


def register_app(instance_url: str) -> AppCredentials:
    """Register the QUILL app on *instance_url*; return its OAuth credentials."""
    base = normalize_instance_url(instance_url)
    result = _http_json(
        "POST",
        f"{base}/api/v1/apps",
        data={
            "client_name": CLIENT_NAME,
            "redirect_uris": REDIRECT_OOB,
            "scopes": SCOPES,
            "website": CLIENT_WEBSITE,
        },
    )
    client_id = str(result.get("client_id", ""))
    client_secret = str(result.get("client_secret", ""))
    if not client_id or not client_secret:
        raise MastodonError("The server did not return app credentials.")
    return AppCredentials(client_id=client_id, client_secret=client_secret)


def authorize_url(instance_url: str, client_id: str) -> str:
    """Return the browser URL where the user authorizes QUILL and gets a code."""
    base = normalize_instance_url(instance_url)
    query = urllib.parse.urlencode({
        "client_id": client_id,
        "scope": SCOPES,
        "redirect_uri": REDIRECT_OOB,
        "response_type": "code",
    })
    return f"{base}/oauth/authorize?{query}"


def exchange_code(instance_url: str, credentials: AppCredentials, code: str) -> str:
    """Exchange the pasted authorization *code* for an access token."""
    base = normalize_instance_url(instance_url)
    result = _http_json(
        "POST",
        f"{base}/oauth/token",
        data={
            "grant_type": "authorization_code",
            "code": code.strip(),
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
            "redirect_uri": REDIRECT_OOB,
            "scope": SCOPES,
        },
    )
    token = str(result.get("access_token", ""))
    if not token:
        raise MastodonError("Authorization failed: no access token was returned.")
    return token


def verify_credentials(instance_url: str, token: str) -> str:
    """Return the account's full ``@handle@instance`` for *token*, for display."""
    base = normalize_instance_url(instance_url)
    result = _http_json("GET", f"{base}/api/v1/accounts/verify_credentials", token=token)
    username = str(result.get("username", "")).strip()
    host = urllib.parse.urlparse(base).netloc
    if not username:
        return ""
    return f"@{username}@{host}"


def post_status(
    instance_url: str,
    token: str,
    text: str,
    visibility: str = "public",
    language: str | None = None,
) -> str:
    """Publish *text* and return the new post's URL.

    Raises :class:`MastodonError` for empty text, an unknown visibility, or any
    API failure.

    *language*, when given, is sent as the post's ``language`` (an ISO 639-1 code
    such as ``"en"`` or ``"it"``) so the instance files the post under the right
    language preset instead of the account's default (#922). ``None`` omits the
    field and lets the instance choose.
    """
    if not text.strip():
        raise MastodonError("Nothing to post: the text is empty.")
    if visibility not in _VISIBILITY_VALUES:
        raise MastodonError(f"Unknown visibility: {visibility!r}")
    base = normalize_instance_url(instance_url)
    data: dict[str, str] = {"status": text, "visibility": visibility}
    if language:
        data["language"] = language
    result = _http_json(
        "POST",
        f"{base}/api/v1/statuses",
        data=data,
        token=token,
    )
    return str(result.get("url") or result.get("uri") or "")


def instance_character_limit(instance_url: str) -> int:
    """Return the per-instance max post length, falling back to the default.

    Fetches ``GET /api/v2/instance`` and reads
    ``configuration.statuses.max_characters`` (#922). The result is cached per
    normalized base URL for the process lifetime, so the compose dialog's live
    counter reflects an instance like poliversity.it (9999) without re-querying
    on every keystroke. Any network/API/parse failure falls back to
    :data:`DEFAULT_CHARACTER_LIMIT` so posting never breaks because the limit
    lookup failed.
    """
    base = normalize_instance_url(instance_url)
    cached = _CHARACTER_LIMIT_CACHE.get(base)
    if cached is not None:
        return cached
    try:
        result = _http_json("GET", f"{base}/api/v2/instance")
    except MastodonError:
        _CHARACTER_LIMIT_CACHE[base] = DEFAULT_CHARACTER_LIMIT
        return DEFAULT_CHARACTER_LIMIT
    limit = DEFAULT_CHARACTER_LIMIT
    configuration = result.get("configuration")
    if isinstance(configuration, dict):
        statuses = configuration.get("statuses")
        if isinstance(statuses, dict):
            try:
                limit = int(statuses.get("max_characters") or DEFAULT_CHARACTER_LIMIT)
            except (TypeError, ValueError):
                limit = DEFAULT_CHARACTER_LIMIT
    _CHARACTER_LIMIT_CACHE[base] = limit
    return limit


def clear_character_limit_cache() -> None:
    """Clear the in-memory per-instance character-limit cache (test hook)."""
    _CHARACTER_LIMIT_CACHE.clear()


__all__ = [
    "DEFAULT_CHARACTER_LIMIT",
    "VISIBILITIES",
    "AppCredentials",
    "MastodonError",
    "authorize_url",
    "clear_character_limit_cache",
    "exchange_code",
    "instance_character_limit",
    "normalize_instance_url",
    "post_status",
    "register_app",
    "verify_credentials",
]
