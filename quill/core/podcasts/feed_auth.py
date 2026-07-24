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

from quill.core.podcasts.models import PodcastEpisode, PodcastShow

_CRED_PREFIX = "quill-podcast-feed:"


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
    feed_host = (urllib.parse.urlsplit(feed_url).hostname or "").lower()
    host = (urllib.parse.urlsplit(url).hostname or "").lower()
    return bool(feed_host) and feed_host == host


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
    """A ready ``Authorization`` header value for *url*, or ``""``."""
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
