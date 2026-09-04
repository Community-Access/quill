"""Connect YouTube Account: OAuth sign-in, listing, and the one-time import.

Pinned here: the parts that do not need a live Google account or a browser --
token-response parsing, the authorization URL's required parameters (PKCE,
``access_type=offline``, ``prompt=consent`` -- without which Google never
returns a refresh token), API response parsing via an injected opener, and the
import into :class:`ChannelStore`, which must behave exactly like the Takeout
importer beside it (first-seen wins, duplicates collapse) since both write to
the same store.
"""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from quill.core.radio.youtube_channels import ChannelStore
from quill.core.radio.youtube_oauth import TokenResponse, build_authorization
from quill.core.radio.youtube_oauth_api import (
    PlaylistEntry,
    SubscriptionEntry,
    YouTubeOAuthError,
    import_subscriptions_into_store,
    list_playlists,
    list_subscriptions,
)


def _json_opener(status: int, payload: object):
    def opener(_request: object) -> tuple[int, bytes]:
        return status, json.dumps(payload).encode("utf-8")

    return opener


def test_token_response_parses_the_documented_fields() -> None:
    response = TokenResponse.from_json({
        "access_token": "a-token",
        "refresh_token": "a-refresh",
        "expires_in": 3599,
        "scope": "https://www.googleapis.com/auth/youtube.readonly",
        "token_type": "Bearer",
    })
    assert response.access_token == "a-token"
    assert response.refresh_token == "a-refresh"
    assert response.expires_in == 3599


def test_a_missing_expires_in_defaults_to_zero_rather_than_raising() -> None:
    response = TokenResponse.from_json({"access_token": "a-token"})
    assert response.expires_in == 0
    assert response.refresh_token == ""


def test_the_authorization_request_asks_for_a_refresh_token() -> None:
    request = build_authorization("client-123")
    query = parse_qs(urlparse(request.url).query)
    assert query["client_id"] == ["client-123"]
    assert query["access_type"] == ["offline"]
    assert query["prompt"] == ["consent"]
    assert query["code_challenge_method"] == ["S256"]
    assert query["scope"] == ["https://www.googleapis.com/auth/youtube.readonly"]
    # The verifier/state travel back through the caller, never in the URL.
    assert request.code_verifier and request.state
    assert request.code_verifier not in request.url


def test_list_subscriptions_paginates_until_no_next_page_token() -> None:
    pages = [
        {
            "items": [
                {"snippet": {"title": "Show One", "resourceId": {"channelId": "UC1"}}},
            ],
            "nextPageToken": "page2",
        },
        {
            "items": [
                {"snippet": {"title": "Show Two", "resourceId": {"channelId": "UC2"}}},
            ]
        },
    ]
    calls = iter(pages)

    def opener(_request: object) -> tuple[int, bytes]:
        return 200, json.dumps(next(calls)).encode("utf-8")

    entries = list_subscriptions("a-token", opener=opener)
    assert entries == [
        SubscriptionEntry("UC1", "Show One"),
        SubscriptionEntry("UC2", "Show Two"),
    ]


def test_list_subscriptions_skips_a_malformed_row_rather_than_raising() -> None:
    payload = {
        "items": [
            {"snippet": {"title": "No channel id"}},
            {"snippet": {"title": "Good", "resourceId": {"channelId": "UC9"}}},
            "not-a-dict",
        ]
    }
    entries = list_subscriptions("a-token", opener=_json_opener(200, payload))
    assert entries == [SubscriptionEntry("UC9", "Good")]


def test_list_playlists_reads_the_item_count() -> None:
    payload = {
        "items": [
            {
                "id": "PL1",
                "snippet": {"title": "My Playlist"},
                "contentDetails": {"itemCount": 12},
            }
        ]
    }
    entries = list_playlists("a-token", opener=_json_opener(200, payload))
    assert entries == [PlaylistEntry("PL1", "My Playlist", 12)]


def test_an_expired_token_raises_a_speakable_error() -> None:
    payload = {"error": {"message": "The access token is expired."}}
    try:
        list_subscriptions("a-stale-token", opener=_json_opener(401, payload))
        raised = False
    except YouTubeOAuthError as error:
        raised = True
        assert "expired" in str(error)
    assert raised


def test_importing_adds_new_channels_and_counts_duplicates(tmp_path: Path) -> None:
    store = ChannelStore(data_dir=tmp_path)
    entries = [
        SubscriptionEntry("UC1", "Show One"),
        SubscriptionEntry("UC2", "Show Two"),
    ]
    added, already = import_subscriptions_into_store(entries, store)
    assert (added, already) == (2, 0)

    # Re-importing the same subscriptions must not duplicate the rows.
    added_again, already_again = import_subscriptions_into_store(entries, store)
    assert (added_again, already_again) == (0, 2)
    assert len(store.all()) == 2


def test_a_subscription_becomes_a_normal_channel_url(tmp_path: Path) -> None:
    store = ChannelStore(data_dir=tmp_path)
    import_subscriptions_into_store([SubscriptionEntry("UCabc123", "A Show")], store)
    channels = store.all()
    assert channels[0].url == "https://www.youtube.com/channel/UCabc123"
    assert channels[0].name == "A Show"
