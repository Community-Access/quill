"""Per-show credentials for private (HTTP Basic auth) podcast feeds.

The username lives on the ``PodcastShow`` record (it is not a secret); the
password lives in the platform secret store via
``quill.platform.windows.credential_store`` (Windows Credential Manager on
installed copies, the DPAPI ``keys.enc`` file in portable mode, the macOS
login Keychain upstream) under ``quill-podcast-feed:<show_id>``.

:func:`auth_for_url` is the one same-host gate every network call site uses:
credentials are returned only for requests to the feed URL's own host, so a
password is never sent to a third-party CDN. wx-free, strict-typed.
"""

from __future__ import annotations

import base64
import urllib.parse
import urllib.request
from typing import Any

from quill.core.podcasts.models import PodcastEpisode, PodcastShow

_CRED_PREFIX = "quill-podcast-feed:"


def _same_origin(url_a: str, url_b: str) -> bool:
    """True when scheme, host, and port all match (case-insensitive)."""
    a = urllib.parse.urlsplit(url_a)
    b = urllib.parse.urlsplit(url_b)
    return (
        a.scheme.lower() == b.scheme.lower()
        and (a.hostname or "").lower() == (b.hostname or "").lower()
        and a.port == b.port
    )


class _AuthStrippingRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Redirect handler that drops the ``Authorization`` header whenever a
    redirect crosses origin (scheme/host/port).

    CPython's default handler re-sends every non-``Content-*`` header —
    including ``Authorization`` — to the redirect target regardless of
    host, so a ``302`` to a third party would leak private-feed
    credentials. This restores the guarantee that a feed password is
    never sent anywhere but the feed's own origin.
    """

    def redirect_request(
        self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str
    ) -> Any:
        new = super().redirect_request(req, fp, code, msg, headers, newurl)
        if new is not None and not _same_origin(req.full_url, newurl):
            new.headers = {
                key: value for key, value in new.headers.items() if key.lower() != "authorization"
            }
        return new


def urlopen_auth_safe(request: Any, *, timeout: float, context: Any = None) -> Any:
    """``urlopen`` for authenticated feed requests that strips credentials on
    cross-origin redirects. Use this at every private-feed fetch site
    instead of the default opener."""
    handlers: list[Any] = [_AuthStrippingRedirectHandler()]
    if context is not None:
        handlers.append(urllib.request.HTTPSHandler(context=context))
    opener = urllib.request.build_opener(*handlers)
    return opener.open(request, timeout=timeout)


def _cred_name(show_id: str) -> str:
    return f"{_CRED_PREFIX}{show_id}"


def save_feed_password(show_id: str, password: str) -> None:
    """Persist *password* for *show_id* (empty password deletes the entry)."""
    from quill.platform.windows import credential_store

    credential_store.save_secret(_cred_name(show_id), password)


def load_feed_password(show_id: str) -> str:
    """The stored password for *show_id*, or ``""``."""
    from quill.platform.windows import credential_store

    return credential_store.load_secret(_cred_name(show_id))


def delete_feed_password(show_id: str) -> None:
    """Remove *show_id*'s stored password (no-op when absent)."""
    from quill.platform.windows import credential_store

    credential_store.delete_secret(_cred_name(show_id))


def basic_auth_header(username: str, password: str) -> str:
    """``Authorization`` header value for HTTP Basic auth."""
    token = base64.b64encode(f"{username}:{password}".encode()).decode("ascii")
    return f"Basic {token}"


def _hosts_match(feed_url: str, url: str) -> bool:
    """True only when *url* shares the feed's scheme AND host.

    Requiring the scheme to match prevents credentials stored for an
    ``https`` feed from being attached to an ``http`` request to the same
    host (a downgrade that would put HTTP Basic on the wire in cleartext).
    The port is intentionally not compared here: a feed legitimately
    serves enclosures on a different port of the same host. Cross-origin
    *redirects* are the attacker-influenced case and are guarded
    separately, strictly (scheme+host+port), by
    :class:`_AuthStrippingRedirectHandler`.
    """
    feed = urllib.parse.urlsplit(feed_url)
    target = urllib.parse.urlsplit(url)
    feed_host = (feed.hostname or "").lower()
    target_host = (target.hostname or "").lower()
    return (
        bool(feed_host)
        and feed_host == target_host
        and feed.scheme.lower() == target.scheme.lower()
    )


def auth_for_url(show: PodcastShow, url: str) -> tuple[str, str]:
    """``(username, password)`` for *url*, or ``("", "")``.

    The same-host gate: non-empty only when the show has a username, the
    request host equals the feed's host exactly (case-insensitive; a
    subdomain is a different host), and a password is actually stored.
    """
    if show.is_local or not show.feed_username or not show.feed_url:
        return ("", "")
    if not _hosts_match(show.feed_url, url):
        return ("", "")
    password = load_feed_password(show.id)
    if not password:
        return ("", "")
    return (show.feed_username, password)


def auth_header_for_url(show: PodcastShow, url: str) -> str:
    """A ready ``Authorization`` header value for *url*, or ``""``.

    A Quillin-contributed feed-auth provider (Quill Cast, ``podcast.feed.auth``)
    is consulted first: when one matches *url*'s host and returns a header, it
    wins. Otherwise the built-in per-show HTTP Basic path is used, so existing
    private feeds behave exactly as before. The provider returns a header the
    host attaches -- it makes no network call of its own.
    """
    from quill.core.podcasts import feed_auth_registry

    provider_header = feed_auth_registry.auth_header_from_providers(show.feed_url, url)
    if provider_header:
        return provider_header
    username, password = auth_for_url(show, url)
    return basic_auth_header(username, password) if username else ""


def url_with_auth(show: PodcastShow, url: str) -> str:
    """*url* with percent-encoded userinfo embedded, for playback engines
    (mpv, the ffmpeg enhancement relay) that accept only a URL string.
    Unchanged when :func:`auth_for_url` yields nothing."""
    username, password = auth_for_url(show, url)
    if not username:
        return url
    parts = urllib.parse.urlsplit(url)
    user = urllib.parse.quote(username, safe="")
    secret = urllib.parse.quote(password, safe="")
    host = parts.hostname or ""
    if parts.port:
        host = f"{host}:{parts.port}"
    netloc = f"{user}:{secret}@{host}"
    return urllib.parse.urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))


def playback_source(show: PodcastShow, episode: PodcastEpisode) -> str:
    """What to hand the playback engine: the downloaded file when there is
    one, otherwise the stream URL -- with userinfo embedded when the
    same-host gate yields credentials (mpv and the ffmpeg relay accept
    userinfo URLs; QUILL's own log lines are scrubbed by
    ``quill.stability.redaction.redact_url_userinfo``)."""
    if episode.downloaded_path:
        return episode.downloaded_path
    return url_with_auth(show, episode.audio_url)
