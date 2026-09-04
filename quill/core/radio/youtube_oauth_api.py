"""YouTube Data API v3 listing: what Connect YouTube Account actually reads.

Split from :mod:`quill.core.radio.youtube_oauth` (GATE-11 -- extract, never
rebaseline): that module is the OAuth session (sign-in, sign-out, token
refresh); this is what an authenticated session is used *for* -- listing the
account's subscriptions and playlists, and the one-time import into
:class:`~quill.core.radio.youtube_channels.ChannelStore` that the Connect
YouTube Account command drives.

Read-only, and deliberately narrow: ``subscriptions.list`` and
``playlists.list`` are the whole surface. Nothing here resolves a video
stream or plays anything -- playback of an imported channel goes through the
same yt-dlp path a pasted channel link already does (``youtube_channels.py``).
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

from quill.core.radio.youtube_channels import ChannelStore
from quill.core.radio.youtube_oauth import (
    _TIMEOUT_SECONDS,
    _USER_AGENT,
    Opener,
    YouTubeOAuthError,
    _context_for,
    get_access_token,
)

__all__ = [
    "PlaylistEntry",
    "SubscriptionEntry",
    "fetch_and_import_subscriptions",
    "import_subscriptions_into_store",
    "list_playlists",
    "list_subscriptions",
]

API_ROOT = "https://www.googleapis.com/youtube/v3"
_PAGE_SIZE = 50


@dataclass(frozen=True, slots=True)
class SubscriptionEntry:
    channel_id: str
    title: str = ""


@dataclass(frozen=True, slots=True)
class PlaylistEntry:
    playlist_id: str
    title: str = ""
    item_count: int = 0


def _authed_get(
    path: str, access_token: str, params: dict[str, str], *, opener: Opener | None = None
) -> dict[str, object]:
    """One authenticated GET against the YouTube Data API v3 -- the reviewed egress site."""
    url = f"{API_ROOT}/{path}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "User-Agent": _USER_AGENT,
        },
    )
    try:
        if opener is not None:
            status, raw = opener(request)
        else:
            with urllib.request.urlopen(
                request, timeout=_TIMEOUT_SECONDS, context=_context_for(url)
            ) as resp:
                status, raw = int(resp.status or 200), resp.read()
    except urllib.error.HTTPError as error:
        status, raw = int(error.code), error.read()
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        raise YouTubeOAuthError(f"Could not reach YouTube: {error}") from error
    text = raw.decode("utf-8", errors="replace")
    try:
        payload = json.loads(text) if text else {}
    except json.JSONDecodeError as error:
        raise YouTubeOAuthError("YouTube returned an unreadable reply.") from error
    if status >= 400:
        message = ""
        if isinstance(payload, dict):
            error_obj = payload.get("error")
            if isinstance(error_obj, dict):
                message = str(error_obj.get("message", ""))
        raise YouTubeOAuthError(message or f"YouTube API request failed (HTTP {status}).")
    return payload if isinstance(payload, dict) else {}


def list_subscriptions(
    access_token: str, *, opener: Opener | None = None, limit: int = 0
) -> list[SubscriptionEntry]:
    """Every channel this account subscribes to, newest-added first.

    Paginated at 50 per request (the API's maximum) until exhausted or
    ``limit`` is reached (``0`` = no limit).
    """
    entries: list[SubscriptionEntry] = []
    page_token = ""
    while True:
        params = {"part": "snippet", "mine": "true", "maxResults": str(_PAGE_SIZE)}
        if page_token:
            params["pageToken"] = page_token
        payload = _authed_get("subscriptions", access_token, params, opener=opener)
        raw_items = payload.get("items")
        for item in raw_items if isinstance(raw_items, list) else []:
            if not isinstance(item, dict):
                continue
            snippet = item.get("snippet")
            if not isinstance(snippet, dict):
                continue
            resource = snippet.get("resourceId")
            channel_id = str(resource.get("channelId", "")) if isinstance(resource, dict) else ""
            if channel_id:
                entries.append(SubscriptionEntry(channel_id, str(snippet.get("title", ""))))
            if limit and len(entries) >= limit:
                return entries
        page_token = str(payload.get("nextPageToken", ""))
        if not page_token:
            return entries


def list_playlists(
    access_token: str, *, opener: Opener | None = None, limit: int = 0
) -> list[PlaylistEntry]:
    """Every playlist this account owns (not liked/saved playlists -- its own)."""
    entries: list[PlaylistEntry] = []
    page_token = ""
    while True:
        params = {
            "part": "snippet,contentDetails",
            "mine": "true",
            "maxResults": str(_PAGE_SIZE),
        }
        if page_token:
            params["pageToken"] = page_token
        payload = _authed_get("playlists", access_token, params, opener=opener)
        raw_items = payload.get("items")
        for item in raw_items if isinstance(raw_items, list) else []:
            if not isinstance(item, dict):
                continue
            snippet = item.get("snippet")
            content = item.get("contentDetails")
            playlist_id = str(item.get("id", ""))
            if not playlist_id:
                continue
            title = str(snippet.get("title", "")) if isinstance(snippet, dict) else ""
            item_count = int(content.get("itemCount") or 0) if isinstance(content, dict) else 0
            entries.append(PlaylistEntry(playlist_id, title, item_count))
            if limit and len(entries) >= limit:
                return entries
        page_token = str(payload.get("nextPageToken", ""))
        if not page_token:
            return entries


def import_subscriptions_into_store(
    entries: list[SubscriptionEntry], store: ChannelStore | None = None
) -> tuple[int, int]:
    """Add every subscription to :class:`ChannelStore`; ``(added, already_following)``.

    Pure with respect to the network -- takes the already-fetched list, same
    split as :mod:`quill.core.radio.youtube_takeout`'s importer.
    """
    channel_store = store or ChannelStore()
    already = {channel.url for channel in channel_store.all()}
    added = 0
    for entry in entries:
        url = f"https://www.youtube.com/channel/{entry.channel_id}"
        saved = channel_store.add(url, entry.title)
        if saved is not None and saved.url not in already:
            already.add(saved.url)
            added += 1
    return added, len(entries) - added


def fetch_and_import_subscriptions(
    *, opener: Opener | None = None, store: ChannelStore | None = None
) -> tuple[int, int]:
    """Sign-in must already be complete. Lists subscriptions and imports them.

    Raises :class:`YouTubeOAuthError` when there is no valid session.
    """
    access_token = get_access_token(opener=opener)
    if not access_token:
        raise YouTubeOAuthError("Not signed in to YouTube. Use Connect YouTube Account first.")
    entries = list_subscriptions(access_token, opener=opener)
    return import_subscriptions_into_store(entries, store)
