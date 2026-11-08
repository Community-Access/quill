"""ListenBrainz and last.fm/Libre.fm requests and answers, against hand-written fixtures.

No network: every call goes through a fake ``post``.
"""

from __future__ import annotations

import json
import urllib.parse

import pytest

from quill.core.radio import lastfm, listenbrainz
from quill.core.radio import scrobble_queue as sq
from quill.core.radio.scrobble_http import Reply, ScrobbleNetworkError
from quill.core.radio.scrobble_tracker import Listen

SONG = Listen("k.d. lang", "Constant Craving", 1_800_000_000, "Ingenue")


class _Post:
    def __init__(self, *replies: Reply | Exception) -> None:
        self.replies = list(replies)
        self.calls: list[dict[str, object]] = []

    def __call__(self, url: str, body: bytes, **kwargs: object) -> Reply:
        self.calls.append({"url": url, "body": body, **kwargs})
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply

    def form(self, index: int = -1) -> dict[str, str]:
        body = self.calls[index]["body"]
        assert isinstance(body, bytes)
        return dict(urllib.parse.parse_qsl(body.decode("utf-8")))


# -- ListenBrainz ---------------------------------------------------------------


def test_listenbrainz_single_listen_body() -> None:
    body = json.loads(listenbrainz.build_body([SONG]))
    assert body["listen_type"] == "single"
    listen = body["payload"][0]
    assert listen["listened_at"] == 1_800_000_000
    meta = listen["track_metadata"]
    assert meta["artist_name"] == "k.d. lang"
    assert meta["track_name"] == "Constant Craving"
    assert meta["release_name"] == "Ingenue"
    assert meta["additional_info"]["submission_client"] == "Quill Radio"


def test_listenbrainz_several_listens_are_an_import_and_playing_now_has_no_time() -> None:
    two = json.loads(listenbrainz.build_body([SONG, Listen("A", "B", 5)]))
    assert two["listen_type"] == "import" and len(two["payload"]) == 2
    assert "release_name" not in two["payload"][1]["track_metadata"]
    now = json.loads(listenbrainz.build_body([SONG], playing_now=True))
    assert now["listen_type"] == "playing_now"
    assert "listened_at" not in now["payload"][0]


def test_listenbrainz_sends_the_token_header() -> None:
    post = _Post(Reply(200, '{"status": "ok"}'))
    outcome = listenbrainz.submit(" TOKEN ", [SONG], post=post)
    assert outcome.kind == sq.SENT
    call = post.calls[0]
    assert call["url"] == "https://api.listenbrainz.org/1/submit-listens"
    assert call["headers"] == {"Authorization": "Token TOKEN"}
    assert call["content_type"] == "application/json"


@pytest.mark.parametrize(
    ("reply", "kind"),
    [
        (Reply(200, '{"status": "ok"}'), sq.SENT),
        (
            Reply(401, '{"code": 401, "error": "You need to provide an Authorization header."}'),
            sq.SIGN_IN,
        ),
        (Reply(429, ""), sq.RETRY),
        (Reply(503, "<html>"), sq.RETRY),
        (Reply(400, '{"code": 400, "error": "Invalid JSON document submitted."}'), sq.REJECTED),
    ],
)
def test_listenbrainz_answers(reply: Reply, kind: str) -> None:
    assert listenbrainz.parse_reply(reply).kind == kind


def test_listenbrainz_network_trouble_is_a_retry_and_no_token_sends_nothing() -> None:
    post = _Post(ScrobbleNetworkError("down"))
    assert listenbrainz.submit("T", [SONG], post=post).kind == sq.RETRY
    never = _Post()
    assert listenbrainz.submit("", [SONG], post=never).kind == sq.SIGN_IN
    assert never.calls == []


# -- last.fm and Libre.fm --------------------------------------------------------


def test_the_signature_matches_blindradios_reference() -> None:
    # md5("api_keykey" "methodauth.getSession" "tokentok" "secret"), the value
    # BlindRadio's own test computed independently.
    params = {"token": "tok", "api_key": "key", "method": "auth.getSession"}
    assert lastfm.sign(params, "secret") == "04e870be4bb79756721b7bc1937fe83d"
    assert lastfm.sign({**params, "format": "json"}, "secret") == lastfm.sign(params, "secret")


def test_a_signed_call_carries_method_key_signature_and_json() -> None:
    form = dict(
        urllib.parse.parse_qsl(
            lastfm.build_call("auth.getToken", {}, api_key="K", secret="S").decode()
        )
    )
    assert form["method"] == "auth.getToken" and form["api_key"] == "K"
    assert form["format"] == "json"
    assert form["api_sig"] == lastfm.sign({"method": "auth.getToken", "api_key": "K"}, "S")


def test_the_desktop_sign_in_flow() -> None:
    post = _Post(
        Reply(200, '{"token": "TOK123"}'),
        Reply(200, '{"session": {"name": "jeff", "key": "SESSION", "subscriber": 0}}'),
    )
    token = lastfm.get_token(lastfm.LASTFM, api_key="K", secret="S", post=post)
    assert token == "TOK123"
    assert post.calls[0]["url"] == "https://ws.audioscrobbler.com/2.0/"
    url = lastfm.auth_page_url(lastfm.LASTFM, api_key="K", token=token)
    assert url == "https://www.last.fm/api/auth/?api_key=K&token=TOK123"
    user, session = lastfm.get_session(
        lastfm.LASTFM, api_key="K", secret="S", token=token, post=post
    )
    assert (user, session) == ("jeff", "SESSION")
    assert post.form()["token"] == "TOK123"


def test_libre_fm_uses_its_own_addresses() -> None:
    post = _Post(Reply(200, '{"token": "T"}'))
    lastfm.get_token(lastfm.LIBREFM, api_key="K", secret="S", post=post)
    assert post.calls[0]["url"] == "https://libre.fm/2.0/"
    assert lastfm.auth_page_url(lastfm.LIBREFM, api_key="K", token="T").startswith(
        "https://libre.fm/api/auth/?"
    )


def test_an_unapproved_token_is_its_own_error() -> None:
    post = _Post(Reply(403, '{"error": 14, "message": "This token has not been authorized"}'))
    with pytest.raises(lastfm.LastFmError) as caught:
        lastfm.get_session(lastfm.LASTFM, api_key="K", secret="S", token="T", post=post)
    assert caught.value.error_code == lastfm.NOT_AUTHORISED_CODE


def test_no_app_key_says_where_to_get_one_and_sends_nothing() -> None:
    post = _Post()
    with pytest.raises(lastfm.LastFmError) as caught:
        lastfm.get_token(lastfm.LASTFM, api_key="", secret="", post=post)
    assert lastfm.API_ACCOUNT_URL in str(caught.value.args[0])
    assert post.calls == []


def test_the_listeners_own_pair_wins_over_the_builds(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(lastfm, "bundled_credentials", lambda: ("BUILD", "BUILDSECRET"))
    assert lastfm.app_credentials("MINE", "MYSECRET") == ("MINE", "MYSECRET")
    assert lastfm.app_credentials("MINE", "") == ("BUILD", "BUILDSECRET"), "half a pair is none"
    assert lastfm.app_credentials() == ("BUILD", "BUILDSECRET")


def test_a_scrobble_batch_is_indexed_and_marked_not_chosen_by_the_listener() -> None:
    post = _Post(Reply(200, '{"scrobbles": {"@attr": {"accepted": 2, "ignored": 0}}}'))
    other = Listen("A", "B", 1_800_000_100)
    outcome = lastfm.scrobble(
        lastfm.LASTFM, [SONG, other], api_key="K", secret="S", session_key="SK", post=post
    )
    assert outcome.kind == sq.SENT
    form = post.form()
    assert form["method"] == "track.scrobble" and form["sk"] == "SK"
    assert form["artist[0]"] == "k.d. lang" and form["track[0]"] == "Constant Craving"
    assert form["timestamp[0]"] == "1800000000" and form["album[0]"] == "Ingenue"
    assert form["artist[1]"] == "A" and "album[1]" not in form
    assert form["chosenByUser[0]"] == "0"
    signed = {k: v for k, v in form.items() if k not in ("api_sig", "format")}
    assert form["api_sig"] == lastfm.sign(signed, "S")


@pytest.mark.parametrize(
    ("text", "status", "kind"),
    [
        (
            '{"error": 9, "message": "Invalid session key - Please re-authenticate"}',
            403,
            sq.SIGN_IN,
        ),
        ('{"error": 11, "message": "Service Offline"}', 503, sq.RETRY),
        ('{"error": 16, "message": "Temporarily unavailable"}', 503, sq.RETRY),
        ('{"error": 29, "message": "Rate limit exceeded"}', 429, sq.RETRY),
        ('{"error": 6, "message": "Invalid parameters"}', 400, sq.REJECTED),
        ("", 502, sq.RETRY),
    ],
)
def test_lastfm_answers(text: str, status: int, kind: str) -> None:
    assert lastfm.outcome_for(lastfm.LASTFM, Reply(status, text)).kind == kind


def test_now_playing_is_sent_with_the_session() -> None:
    post = _Post(Reply(200, '{"nowplaying": {}}'))
    lastfm.update_now_playing(
        lastfm.LIBREFM, SONG, api_key="K", secret="S", session_key="SK", post=post
    )
    form = post.form()
    assert form["method"] == "track.updateNowPlaying" and form["artist"] == "k.d. lang"
    assert post.calls[0]["url"] == "https://libre.fm/2.0/"


def test_safe_mode_and_plain_http_are_refused_before_any_socket() -> None:
    from quill.core.radio import scrobble_http

    with pytest.raises(ScrobbleNetworkError):
        scrobble_http.post("https://example.invalid/", b"", content_type="x", safe_mode=True)
    with pytest.raises(ScrobbleNetworkError):
        scrobble_http.post("http://example.invalid/", b"", content_type="x")
