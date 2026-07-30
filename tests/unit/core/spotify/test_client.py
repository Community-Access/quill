"""Spotify Web API client: request building, parsing, and lazy refresh."""

from __future__ import annotations

import json
from urllib.request import Request

import pytest

from quill.core.spotify.client import SpotifyClient, SpotifyClientError
from quill.core.spotify.token_store import TokenBundle

_NOW = 1000.0


def _fresh_tokens() -> TokenBundle:
    return TokenBundle(
        access_token="access-1",
        refresh_token="refresh-1",
        expires_at=_NOW + 3600,
        scope="streaming",
    )


def _json_opener(routes: dict[str, object]):
    """An opener that returns fixture JSON keyed by a URL substring."""
    calls: list[Request] = []

    def opener(request: Request) -> tuple[int, bytes]:
        calls.append(request)
        for needle, payload in routes.items():
            if needle in request.full_url:
                return 200, json.dumps(payload).encode("utf-8")
        return 404, b'{"error":{"status":404,"message":"not found"}}'

    opener.calls = calls  # type: ignore[attr-defined]
    return opener


def test_get_me_parses_profile_and_sends_bearer() -> None:
    opener = _json_opener({"/me": {"id": "u1", "product": "premium"}})
    client = SpotifyClient(_fresh_tokens(), "cid", opener=opener, time_fn=lambda: _NOW)
    me = client.get_me()
    assert me["product"] == "premium"
    # Token in the Authorization header, never in the URL.
    request = opener.calls[0]  # type: ignore[attr-defined]
    assert request.headers.get("Authorization") == "Bearer access-1"
    assert "access-1" not in request.full_url


def test_search_maps_all_types() -> None:
    opener = _json_opener({
        "/search": {
            "tracks": {"items": [{"id": "t", "uri": "spotify:track:t", "name": "Song"}]},
            "shows": {"items": [{"id": "s", "uri": "spotify:show:s", "name": "Show"}]},
            "episodes": {"items": [{"id": "e", "uri": "spotify:episode:e", "name": "Ep"}]},
        }
    })
    client = SpotifyClient(_fresh_tokens(), "cid", opener=opener, time_fn=lambda: _NOW)
    results = client.search("hello")
    assert [t.name for t in results.tracks] == ["Song"]
    assert [s.name for s in results.shows] == ["Show"]
    assert [e.name for e in results.episodes] == ["Ep"]
    # Query encodes the requested types.
    assert "type=track%2Cshow%2Cepisode" in opener.calls[0].full_url  # type: ignore[attr-defined]


def test_search_blank_query_makes_no_request() -> None:
    opener = _json_opener({})
    client = SpotifyClient(_fresh_tokens(), "cid", opener=opener, time_fn=lambda: _NOW)
    results = client.search("   ")
    assert results.tracks == [] and results.shows == [] and results.episodes == []
    assert opener.calls == []  # type: ignore[attr-defined]


def test_saved_shows_episodes_tracks_unwrap_containers() -> None:
    opener = _json_opener({
        "/me/shows": {"items": [{"show": {"id": "s", "uri": "spotify:show:s", "name": "S"}}]},
        "/me/episodes": {
            "items": [{"episode": {"id": "e", "uri": "spotify:episode:e", "name": "E"}}]
        },
        "/me/tracks": {"items": [{"track": {"id": "t", "uri": "spotify:track:t", "name": "T"}}]},
    })
    client = SpotifyClient(_fresh_tokens(), "cid", opener=opener, time_fn=lambda: _NOW)
    assert [s.name for s in client.saved_shows()] == ["S"]
    assert [e.name for e in client.saved_episodes()] == ["E"]
    assert [t.name for t in client.saved_tracks()] == ["T"]


def test_playlists_simplified() -> None:
    opener = _json_opener({
        "/me/playlists": {
            "items": [
                {
                    "id": "p1",
                    "uri": "spotify:playlist:p1",
                    "name": "Faves",
                    "owner": {"display_name": "Jeff"},
                    "tracks": {"total": 25},
                }
            ]
        }
    })
    client = SpotifyClient(_fresh_tokens(), "cid", opener=opener, time_fn=lambda: _NOW)
    playlists = client.playlists()
    assert playlists == [
        {"id": "p1", "name": "Faves", "uri": "spotify:playlist:p1", "total": 25, "owner": "Jeff"}
    ]


def test_error_status_raises() -> None:
    def opener(request: Request) -> tuple[int, bytes]:
        return 401, b'{"error":{"status":401,"message":"Invalid token"}}'

    client = SpotifyClient(_fresh_tokens(), "cid", opener=opener, time_fn=lambda: _NOW)
    with pytest.raises(SpotifyClientError) as excinfo:
        client.get_me()
    assert "Invalid token" in str(excinfo.value)


def test_lazy_refresh_before_expired_request() -> None:
    refreshed: list[TokenBundle] = []
    expired = TokenBundle(
        access_token="stale", refresh_token="refresh-1", expires_at=0.0, scope="streaming"
    )

    def opener(request: Request) -> tuple[int, bytes]:
        if "accounts.spotify.com/api/token" in request.full_url:
            assert b"grant_type=refresh_token" in (request.data or b"")
            return 200, b'{"access_token":"fresh","expires_in":3600,"scope":"streaming"}'
        # The API call must carry the freshly minted token.
        assert request.headers.get("Authorization") == "Bearer fresh"
        return 200, b'{"id":"u1"}'

    client = SpotifyClient(
        expired,
        "cid",
        opener=opener,
        on_tokens_refreshed=refreshed.append,
        time_fn=lambda: _NOW,
    )
    assert client.get_me()["id"] == "u1"
    assert refreshed and refreshed[-1].access_token == "fresh"
    assert client.tokens.access_token == "fresh"


def test_refresh_without_refresh_token_raises() -> None:
    empty = TokenBundle(access_token="", refresh_token="", expires_at=0.0)
    client = SpotifyClient(empty, "cid", opener=_json_opener({}), time_fn=lambda: _NOW)
    with pytest.raises(SpotifyClientError):
        client.get_me()
