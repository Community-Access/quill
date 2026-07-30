"""Spotify Web API wrapper -- one funnel, Bearer auth, lazy token refresh.

Every call the Radio/Cast browse surfaces make (search, the signed-in profile,
saved shows/episodes/tracks, and playlists) goes through the single private
:meth:`SpotifyClient._request`, which is the module's one reviewed
network-egress site (see ``quill/tools/network_egress_audit.py``). Modelled on
:mod:`quill.core.mastodon.client`: HTTPS-only over a verified TLS context, the
access token in the ``Authorization: Bearer`` header (never in the URL), and one
place that turns an HTTP/JSON error into a clean :class:`SpotifyClientError`.

The access token is refreshed lazily and under a lock: the first request that
finds an expired (or nearly expired) token refreshes it via
:func:`quill.core.spotify.auth.refresh`, and the double-checked lock keeps two
threads from refreshing at once. ``opener`` is injectable for both the API and
the refresh, so the request building, the refresh gate, and the response parsing
are all unit-tested offline with a fake opener.

wx-free, strict-typed.
"""

from __future__ import annotations

import json
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable

from quill import __version__
from quill.core.error_codes import CodedError
from quill.core.net import verified_ssl_context
from quill.core.spotify import auth
from quill.core.spotify.models import (
    SavedItems,
    SearchResults,
    SpotifyEpisode,
    SpotifyShow,
    SpotifyTrack,
)
from quill.core.spotify.token_store import TokenBundle

_API_ROOT = "https://api.spotify.com/v1"
_USER_AGENT = f"QUILL/{__version__} (https://github.com/Community-Access/quill)"
_TIMEOUT_SECONDS = 30.0
#: Refresh a little before the real expiry so an in-flight request never races
#: the token going stale on Spotify's side.
_EXPIRY_SKEW_SECONDS = 30.0
#: Spotify's page ceiling for the list endpoints used here.
_MAX_PAGE_LIMIT = 50

#: The search object types QUILL surfaces (Spotify's ``type`` query values).
SEARCH_TYPES: tuple[str, ...] = ("track", "show", "episode")


class SpotifyClientError(CodedError):
    """A Spotify Web API call failed (network, auth, or an API error status)."""

    code = "QUILL-SPOTIFY-API-REQUEST"


class SpotifyClient:
    """Authenticated Spotify Web API client for the browse surfaces.

    Construct with the stored :class:`TokenBundle` and the user's Client ID.
    ``on_tokens_refreshed`` (if given) is called with the new bundle whenever a
    lazy refresh mints one, so the caller can persist it. ``opener`` and
    ``time_fn`` are injectable for offline tests.
    """

    def __init__(
        self,
        tokens: TokenBundle,
        client_id: str,
        *,
        opener: auth.Opener | None = None,
        on_tokens_refreshed: Callable[[TokenBundle], None] | None = None,
        time_fn: Callable[[], float] = time.time,
    ) -> None:
        self._tokens = tokens
        self._client_id = client_id
        self._opener = opener
        self._on_tokens_refreshed = on_tokens_refreshed
        self._time = time_fn
        self._lock = threading.Lock()

    @property
    def tokens(self) -> TokenBundle:
        """The current session bundle (updated in place after a refresh)."""
        return self._tokens

    # -- library / browse -------------------------------------------------------

    def get_me(self) -> dict[str, object]:
        """The signed-in user's profile (``GET /me``); ``product`` reveals Premium."""
        result = self._request("GET", "/me")
        return result if isinstance(result, dict) else {}

    def search(
        self,
        query: str,
        *,
        types: tuple[str, ...] = SEARCH_TYPES,
        limit: int = 20,
    ) -> SearchResults:
        """Search Spotify for the given object *types* (``GET /search``)."""
        if not query.strip():
            return SearchResults()
        payload = self._request(
            "GET",
            "/search",
            query={
                "q": query,
                "type": ",".join(types),
                "limit": _bounded_limit(limit),
            },
        )
        data = payload if isinstance(payload, dict) else {}
        return SearchResults(
            tracks=[SpotifyTrack.from_json(x) for x in _items(data.get("tracks"))],
            shows=[SpotifyShow.from_json(x) for x in _items(data.get("shows"))],
            episodes=[SpotifyEpisode.from_json(x) for x in _items(data.get("episodes"))],
        )

    def saved_shows(self, *, limit: int = _MAX_PAGE_LIMIT) -> list[SpotifyShow]:
        """The user's saved podcast shows (``GET /me/shows``)."""
        payload = self._request("GET", "/me/shows", query={"limit": _bounded_limit(limit)})
        return [
            SpotifyShow.from_json(show)
            for entry in _items(payload)
            if isinstance(show := entry.get("show"), dict)
        ]

    def saved_episodes(self, *, limit: int = _MAX_PAGE_LIMIT) -> list[SpotifyEpisode]:
        """The user's saved podcast episodes (``GET /me/episodes``)."""
        payload = self._request("GET", "/me/episodes", query={"limit": _bounded_limit(limit)})
        return [
            SpotifyEpisode.from_json(episode)
            for entry in _items(payload)
            if isinstance(episode := entry.get("episode"), dict)
        ]

    def saved_tracks(self, *, limit: int = _MAX_PAGE_LIMIT) -> list[SpotifyTrack]:
        """The user's saved songs (``GET /me/tracks``)."""
        payload = self._request("GET", "/me/tracks", query={"limit": _bounded_limit(limit)})
        return [
            SpotifyTrack.from_json(track)
            for entry in _items(payload)
            if isinstance(track := entry.get("track"), dict)
        ]

    def playlists(self, *, limit: int = _MAX_PAGE_LIMIT) -> list[dict[str, object]]:
        """The user's playlists (``GET /me/playlists``), simplified for browse.

        Returns lightweight ``{id, name, uri, total, owner}`` dicts -- enough to
        list and drill into a playlist without a dedicated model class.
        """
        payload = self._request("GET", "/me/playlists", query={"limit": _bounded_limit(limit)})
        return [_simplify_playlist(item) for item in _items(payload)]

    def saved_library(self) -> SavedItems:
        """One convenience call gathering saved shows, episodes, and tracks."""
        return SavedItems(
            shows=self.saved_shows(),
            episodes=self.saved_episodes(),
            tracks=self.saved_tracks(),
        )

    # -- egress -----------------------------------------------------------------

    def _request(
        self,
        method: str,
        path: str,
        *,
        query: dict[str, object] | None = None,
        body: dict[str, object] | None = None,
        allow_empty: bool = False,
    ) -> object:
        """Perform one Web API call -- the module's single reviewed egress site.

        Refreshes the access token first if needed, then sends the request with
        the Bearer token in the header. HTTPS-only over a verified TLS context
        with a bounded timeout; a rejected call (HTTP >= 400) is read and raised
        as :class:`SpotifyClientError`. ``opener`` is used when injected (tests),
        otherwise the real ``urlopen`` runs.
        """
        self._refresh_if_needed()
        url = _API_ROOT + path
        if query:
            url += "?" + urllib.parse.urlencode(query)
        data = json.dumps(body).encode("utf-8") if body is not None else None
        headers = {
            "Authorization": f"Bearer {self._tokens.access_token}",
            "Accept": "application/json",
            "User-Agent": _USER_AGENT,
        }
        if data is not None:
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(url, data=data, method=method, headers=headers)
        if self._opener is not None:
            status, raw = self._opener(request)
        else:
            if not url.startswith("https://"):  # defensive; _API_ROOT is https
                raise SpotifyClientError("Refusing a non-HTTPS Spotify API request.")
            context = verified_ssl_context()
            try:
                with urllib.request.urlopen(
                    request, timeout=_TIMEOUT_SECONDS, context=context
                ) as resp:
                    status, raw = int(resp.status or 200), resp.read()
            except urllib.error.HTTPError as error:
                status, raw = int(error.code), error.read()
            except (urllib.error.URLError, TimeoutError, OSError) as error:
                raise SpotifyClientError(f"Could not reach Spotify: {error}") from error
        return _parse_api_response(status, raw, allow_empty=allow_empty)

    def _refresh_if_needed(self) -> None:
        """Refresh the access token when it is missing or about to expire."""
        if self._token_is_fresh():
            return
        with self._lock:
            if self._token_is_fresh():
                return
            if not self._tokens.refresh_token:
                raise SpotifyClientError("Not signed in to Spotify.")
            if not self._client_id:
                raise SpotifyClientError("The Spotify Client ID is not configured.")
            response = auth.refresh(
                self._tokens.refresh_token, self._client_id, opener=self._opener
            )
            self._tokens = TokenBundle.from_token_response(response, now=self._time())
            if self._on_tokens_refreshed is not None:
                self._on_tokens_refreshed(self._tokens)

    def _token_is_fresh(self) -> bool:
        return bool(
            self._tokens.access_token
            and self._tokens.expires_at > self._time() + _EXPIRY_SKEW_SECONDS
        )


def _parse_api_response(status: int, raw: bytes, *, allow_empty: bool) -> object:
    """Decode a Web API reply, raising :class:`SpotifyClientError` on error."""
    if status == 204 or (allow_empty and not raw):
        return {}
    text = raw.decode("utf-8", errors="replace").strip()
    parsed: object = {}
    if text:
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as error:
            raise SpotifyClientError("Spotify returned an unreadable response.") from error
    if status >= 400:
        raise SpotifyClientError(f"Spotify request failed: {_error_message(parsed, status)}")
    return parsed


def _error_message(parsed: object, status: int) -> str:
    if isinstance(parsed, dict):
        error = parsed.get("error")
        if isinstance(error, dict) and error.get("message"):
            return str(error["message"])
        if isinstance(error, str) and error:
            return error
    return f"HTTP {status}"


def _items(payload: object) -> list[dict[str, object]]:
    """The ``items`` list out of a paged payload (or a raw list), objects only."""
    container = payload.get("items") if isinstance(payload, dict) else payload
    if not isinstance(container, list):
        return []
    return [item for item in container if isinstance(item, dict)]


def _simplify_playlist(item: dict[str, object]) -> dict[str, object]:
    owner = item.get("owner")
    owner_name = ""
    if isinstance(owner, dict):
        owner_name = str(owner.get("display_name") or owner.get("id") or "")
    tracks = item.get("tracks")
    total = 0
    if isinstance(tracks, dict):
        try:
            total = int(tracks.get("total") or 0)
        except (TypeError, ValueError):
            total = 0
    return {
        "id": str(item.get("id", "")),
        "name": str(item.get("name", "")) or "Untitled",
        "uri": str(item.get("uri", "")),
        "total": total,
        "owner": owner_name,
    }


def _bounded_limit(limit: int) -> int:
    return max(1, min(int(limit), _MAX_PAGE_LIMIT))


__all__ = [
    "SEARCH_TYPES",
    "SpotifyClient",
    "SpotifyClientError",
]
