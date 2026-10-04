"""Acting on YouTube: every write's request body, quota handling, incremental scope.

No network: a fake opener records each prepared request and answers it.
"""

from __future__ import annotations

import json
import urllib.parse

import pytest

from quill.core.auth.token_bundle import TokenBundle
from quill.core.radio import youtube_account_api as api
from quill.core.radio import youtube_oauth as oauth
from quill.core.radio import youtube_write_scope as ws


class _Opener:
    def __init__(self, *answers: tuple[int, object]) -> None:
        self.answers = list(answers) or [(200, {})]
        self.requests: list = []

    def __call__(self, request):
        self.requests.append(request)
        status, body = self.answers.pop(0) if len(self.answers) > 1 else self.answers[0]
        raw = json.dumps(body).encode() if body is not None else b""
        return status, raw

    @property
    def last(self):
        return self.requests[-1]

    def body(self, index: int = -1) -> dict:
        return json.loads(self.requests[index].data.decode())

    def query(self, index: int = -1) -> dict:
        url = self.requests[index].full_url
        return dict(urllib.parse.parse_qsl(urllib.parse.urlparse(url).query))

    def path(self, index: int = -1) -> str:
        return urllib.parse.urlparse(self.requests[index].full_url).path


def test_add_comment_body() -> None:
    opener = _Opener((200, {"id": "T1", "snippet": {"topLevelComment": {"id": "C1"}}}))
    posted = api.add_comment("tok", "vid12345678", "  Lovely  ", opener=opener)
    assert opener.last.get_method() == "POST"
    assert opener.path().endswith("/youtube/v3/commentThreads")
    assert opener.query() == {"part": "snippet"}
    assert opener.body() == {
        "snippet": {
            "videoId": "vid12345678",
            "topLevelComment": {"snippet": {"textOriginal": "Lovely"}},
        }
    }
    assert opener.last.get_header("Authorization") == "Bearer tok"
    assert posted.comment_id == "C1"


def test_reply_to_a_reply_joins_its_thread() -> None:
    opener = _Opener((200, {"id": "R9"}))
    api.reply("tok", "Ugx123.abc", "Agreed", opener=opener)
    assert opener.path().endswith("/comments")
    assert opener.body() == {"snippet": {"parentId": "Ugx123", "textOriginal": "Agreed"}}


def test_delete_comment_is_a_delete_with_the_id() -> None:
    opener = _Opener((204, None))
    api.delete_comment("tok", "Ugx1", opener=opener)
    assert opener.last.get_method() == "DELETE"
    assert opener.query() == {"id": "Ugx1"}


def test_is_mine_compares_author_with_own_channel() -> None:
    opener = _Opener(
        (200, {"items": [{"id": "UCme"}]}),
        (200, {"items": [{"snippet": {"authorChannelId": {"value": "UCme"}}}]}),
    )
    assert api.is_mine("tok", "Ugx1", opener=opener)
    assert opener.query(0) == {"part": "id", "mine": "true"}


def test_send_chat_message_body_and_chat_id_lookup() -> None:
    opener = _Opener(
        (200, {"items": [{"liveStreamingDetails": {"activeLiveChatId": "CHAT"}}]}),
        (200, {"id": "M1"}),
    )
    chat = api.live_chat_id("tok", "vid", opener=opener)
    assert opener.query(0) == {"part": "liveStreamingDetails", "id": "vid"}
    api.send_chat_message("tok", chat, "hello", opener=opener)
    assert opener.path().endswith("/liveChat/messages")
    assert opener.body() == {
        "snippet": {
            "liveChatId": "CHAT",
            "type": "textMessageEvent",
            "textMessageDetails": {"messageText": "hello"},
        }
    }


def test_too_long_chat_message_is_refused_before_sending() -> None:
    opener = _Opener()
    with pytest.raises(oauth.YouTubeOAuthError):
        api.send_chat_message("tok", "CHAT", "x" * 201, opener=opener)
    assert opener.requests == []


def test_subscribe_and_unsubscribe() -> None:
    opener = _Opener((200, {"id": "S1"}), (204, None))
    assert api.subscribe("tok", "UCabc", opener=opener) == "S1"
    assert opener.body(0) == {
        "snippet": {"resourceId": {"kind": "youtube#channel", "channelId": "UCabc"}}
    }
    api.unsubscribe("tok", "S1", opener=opener)
    assert opener.last.get_method() == "DELETE" and opener.query() == {"id": "S1"}


def test_channel_id_from_address_or_handle() -> None:
    opener = _Opener((200, {"items": [{"id": "UChandle"}]}))
    direct = "https://www.youtube.com/channel/UC" + "a" * 22
    assert api.channel_id_for("tok", direct, opener=opener) == "UC" + "a" * 22
    assert opener.requests == []
    assert api.channel_id_for("tok", "https://www.youtube.com/@ricksteves", opener=opener) == (
        "UChandle"
    )
    assert opener.query() == {"part": "id", "forHandle": "@ricksteves"}


def test_rate_and_get_rating() -> None:
    opener = _Opener((204, None), (200, {"items": [{"rating": "like"}]}))
    api.rate("tok", "vid", api.LIKE, opener=opener)
    assert opener.path(0).endswith("/videos/rate")
    assert opener.query(0) == {"id": "vid", "rating": "like"}
    assert opener.requests[0].get_method() == "POST"
    assert api.get_rating("tok", "vid", opener=opener) == "like"


def test_add_to_playlist_and_create_playlist_bodies() -> None:
    opener = _Opener((200, {"id": "PL1"}), (200, {"id": "I1"}))
    assert api.create_playlist("tok", "Walks", privacy="unlisted", opener=opener) == "PL1"
    assert opener.body(0) == {
        "snippet": {"title": "Walks"},
        "status": {"privacyStatus": "unlisted"},
    }
    assert opener.query(0) == {"part": "snippet,status"}
    api.add_to_playlist("tok", "PL1", "vid", opener=opener)
    assert opener.body(1) == {
        "snippet": {"playlistId": "PL1", "resourceId": {"kind": "youtube#video", "videoId": "vid"}}
    }


def test_my_playlists_pages_and_sorts() -> None:
    opener = _Opener(
        (200, {"items": [{"id": "b", "snippet": {"title": "Zed"}}], "nextPageToken": "p2"}),
        (200, {"items": [{"id": "a", "snippet": {"title": "apple"}}]}),
    )
    assert api.my_playlists("tok", opener=opener) == [("a", "apple"), ("b", "Zed")]
    assert opener.query(1)["pageToken"] == "p2"


def test_quota_exceeded_is_one_sentence_and_never_retried() -> None:
    body = {"error": {"code": 403, "message": "quota", "errors": [{"reason": "quotaExceeded"}]}}
    opener = _Opener((403, body))
    with pytest.raises(api.QuotaExceeded) as caught:
        api.subscribe("tok", "UCabc", opener=opener)
    assert api.plain(caught.value) == (
        "YouTube's daily limit for QUILL has been reached; try again tomorrow."
    )
    assert len(opener.requests) == 1


def test_other_errors_are_plain_sentences() -> None:
    body = {"error": {"message": "<b>x</b>", "errors": [{"reason": "commentsDisabled"}]}}
    with pytest.raises(oauth.YouTubeOAuthError) as caught:
        api.add_comment("tok", "vid", "hi", opener=_Opener((403, body)))
    assert api.plain(caught.value) == "Comments are turned off for this video."


# -- incremental authorization ----------------------------------------------------


def test_write_authorization_asks_for_both_scopes_and_keeps_granted() -> None:
    request = ws.build_write_authorization("client-id")
    query = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(request.url).query))
    assert query["scope"].split() == [oauth.SCOPE, ws.WRITE_SCOPE]
    assert query["include_granted_scopes"] == "true"
    assert query["code_challenge_method"] == "S256"


def test_read_only_session_has_no_write_scope() -> None:
    assert not ws.has_write_scope(TokenBundle(access_token="a", scope=oauth.SCOPE))
    both = TokenBundle(access_token="a", scope=f"{oauth.SCOPE} {ws.WRITE_SCOPE}")
    assert ws.has_write_scope(both)


def test_grant_write_access_stores_the_wider_token(monkeypatch) -> None:
    saved: list[TokenBundle] = []
    monkeypatch.setattr(oauth, "bundled_client", lambda: ("id", "secret"))
    monkeypatch.setattr(oauth, "save_tokens", saved.append)
    opened: list[str] = []
    token_reply = {
        "access_token": "AT",
        "refresh_token": "RT",
        "expires_in": 3600,
        "scope": f"{oauth.SCOPE} {ws.WRITE_SCOPE}",
    }
    opener = _Opener((200, token_reply))

    def waiter(state, redirect, *, timeout, on_ready):
        on_ready()
        return "CODE"

    ws.grant_write_access(opener=opener, browser_opener=opened.append, wait_for_redirect=waiter)
    assert ws.WRITE_SCOPE in urllib.parse.unquote(opened[0])
    assert saved and ws.has_write_scope(saved[-1])


def test_grant_refused_scope_keeps_reading_and_says_so(monkeypatch) -> None:
    saved: list[TokenBundle] = []
    monkeypatch.setattr(oauth, "bundled_client", lambda: ("id", "secret"))
    monkeypatch.setattr(oauth, "save_tokens", saved.append)
    opener = _Opener((200, {"access_token": "AT", "scope": oauth.SCOPE, "expires_in": 60}))
    with pytest.raises(oauth.YouTubeOAuthError):
        ws.grant_write_access(
            opener=opener,
            browser_opener=lambda _u: None,
            wait_for_redirect=lambda *a, **k: "CODE",
        )
    assert saved and not ws.has_write_scope(saved[-1])


def test_write_token_is_none_without_the_permission(monkeypatch) -> None:
    monkeypatch.setattr(
        oauth, "load_tokens", lambda: TokenBundle(access_token="a", scope=oauth.SCOPE)
    )
    assert ws.write_token() is None
