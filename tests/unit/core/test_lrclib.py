"""The LRCLIB lyrics client: pure parsing, and the network half with _fetch faked."""

from __future__ import annotations

import io
import json
import urllib.error
from email.message import Message

import pytest

from quill.core.error_codes import CodedError
from quill.core.lyrics import lrclib
from quill.core.lyrics.lrclib import Lyrics, LyricsError, line_at, parse_lrc, parse_response

_SYNCED = (
    "[ar:Elton John]\n"
    "[00:09.06] It's a little bit funny, this feelin' inside\n"
    "[00:16.79] I'm not one of those who can easily hide\n"
    "[00:24.5]\n"
    "[01:02.125][02:40.00] And you can tell everybody this is your song\n"
)

_RECORD = {
    "id": 1,
    "trackName": "Your Song",
    "artistName": "Elton John",
    "albumName": "Elton John",
    "duration": 241.0,
    "instrumental": False,
    "plainLyrics": "It's a little bit funny\nthis feelin' inside",
    "syncedLyrics": _SYNCED,
}


@pytest.fixture(autouse=True)
def _fresh(monkeypatch: pytest.MonkeyPatch) -> None:
    lrclib.clear_cache()
    monkeypatch.setattr(lrclib, "MIN_INTERVAL_SECONDS", 0.0)


# -- parse_lrc / line_at ---------------------------------------------------------


def test_parse_lrc_reads_offsets_fractions_blank_lines_and_repeats() -> None:
    lines = parse_lrc(_SYNCED)

    assert [line.start_ms for line in lines] == [9060, 16790, 24500, 62125, 160000]
    assert lines[2].text == ""  # the instrumental break is kept
    assert lines[3].text == lines[4].text == "And you can tell everybody this is your song"


@pytest.mark.parametrize("junk", ["", "no timestamps here\nat all", "[ar:Someone]", "[xx:yy] no"])
def test_parse_lrc_on_junk_is_empty_and_never_raises(junk: str) -> None:
    assert parse_lrc(junk) == ()


def test_line_at_before_on_between_and_after() -> None:
    lines = parse_lrc(_SYNCED)

    assert line_at(lines, 0) == -1
    assert line_at(lines, 9060) == 0
    assert line_at(lines, 20_000) == 1
    assert line_at(lines, 10_000_000) == len(lines) - 1
    assert line_at((), 5000) == -1


# -- parse_response --------------------------------------------------------------


def test_a_full_match() -> None:
    lyrics = parse_response(json.dumps(_RECORD))

    assert lyrics.track == "Your Song" and lyrics.artist == "Elton John"
    assert lyrics.has_synced and not lyrics.is_empty
    assert lyrics.text.startswith("It's a little bit funny")


def test_an_instrumental_is_an_answer_not_an_absence() -> None:
    record = {**_RECORD, "instrumental": True, "plainLyrics": None, "syncedLyrics": None}

    lyrics = parse_response(json.dumps(record))

    assert lyrics.instrumental
    assert not lyrics.is_empty
    assert lyrics.text == ""


def test_plain_words_without_timings() -> None:
    lyrics = parse_response(json.dumps({**_RECORD, "syncedLyrics": None}))

    assert not lyrics.has_synced
    assert lyrics.text == "It's a little bit funny\nthis feelin' inside"


def test_a_404_body_is_empty_not_an_error() -> None:
    body = '{"message":"Failed to find specified track","name":"TrackNotFound","statusCode":404}'
    assert parse_response(body) == Lyrics()
    assert parse_response("") == Lyrics()
    assert parse_response("[]") == Lyrics()


def test_a_search_list_prefers_timed_words_when_asked() -> None:
    plain_only = {**_RECORD, "syncedLyrics": None, "trackName": "Live"}
    body = json.dumps([plain_only, _RECORD])

    assert parse_response(body).track == "Live"
    assert parse_response(body, prefer_synced=True).track == "Your Song"


# -- the network half, faked -----------------------------------------------------


def test_safe_mode_refuses_and_is_a_coded_error() -> None:
    with pytest.raises(LyricsError):
        lrclib.refuse_in_safe_mode(True)
    lrclib.refuse_in_safe_mode(False)
    assert issubclass(LyricsError, CodedError)
    assert LyricsError.code == "QUILL-LYRICS-LRCLIB-LOOKUP"
    with pytest.raises(LyricsError):
        lrclib.search("Elton John", "Your Song", safe_mode=True)


def test_two_identical_searches_make_one_request(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def fake(url: str) -> str:
        calls.append(url)
        return json.dumps([_RECORD])

    monkeypatch.setattr(lrclib, "_fetch", fake)

    first = lrclib.search("Elton John", "Your Song")
    second = lrclib.search("elton john", "YOUR SONG")

    assert first == second and first.track == "Your Song"
    assert len(calls) == 1
    assert calls[0].startswith("https://lrclib.net/api/search?")
    assert "artist_name=Elton+John" in calls[0]


def test_the_cache_is_memory_only_by_default() -> None:
    # A default awaiting Jeff: nothing about what somebody listened to on disk.
    assert lrclib.CACHE_ON_DISK is False


def test_get_exact_asks_for_the_exact_cut_then_falls_back(monkeypatch) -> None:
    calls: list[str] = []

    def fake(url: str) -> str:
        calls.append(url)
        return "" if "/get?" in url else json.dumps([_RECORD])

    monkeypatch.setattr(lrclib, "_fetch", fake)

    lyrics = lrclib.get_exact("Elton John", "Your Song", "Elton John", 241.4)

    assert lyrics.has_synced
    assert "/get?" in calls[0] and "duration=241" in calls[0]
    assert "/search?" in calls[1]


def test_get_exact_without_an_album_goes_straight_to_search(monkeypatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(lrclib, "_fetch", lambda url: calls.append(url) or "")

    assert lrclib.get_exact("Elton John", "Your Song", "", 0).is_empty
    assert len(calls) == 1 and "/search?" in calls[0]


def test_a_blank_title_asks_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(lrclib, "_fetch", lambda url: pytest.fail("no request expected"))
    assert lrclib.search("Elton John", "  ").is_empty


def _http_error(code: int, retry_after: str | None = None) -> urllib.error.HTTPError:
    headers = Message()
    if retry_after is not None:
        headers["Retry-After"] = retry_after
    return urllib.error.HTTPError("https://lrclib.net/api", code, "x", headers, io.BytesIO(b""))


class _Response(io.BytesIO):
    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_exc: object) -> None:
        return None


def test_fetch_404_is_empty_and_429_honours_retry_after_once(monkeypatch) -> None:
    slept: list[float] = []
    monkeypatch.setattr(lrclib.time, "sleep", slept.append)
    answers: list[object] = [_http_error(429, "1"), _Response(b"[]")]

    def urlopen(request, timeout, context):
        assert request.get_header("User-agent")  # LRCLIB asks for one
        answer = answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer

    monkeypatch.setattr(lrclib.urllib.request, "urlopen", urlopen)
    assert lrclib._fetch("https://lrclib.net/api/search?q=x") == "[]"
    assert slept == [1.0]

    monkeypatch.setattr(
        lrclib.urllib.request,
        "urlopen",
        lambda *a, **k: (_ for _ in ()).throw(_http_error(404)),
    )
    assert lrclib._fetch("https://lrclib.net/api/get?x") == ""


def test_fetch_gives_up_on_a_long_retry_after_without_looping(monkeypatch) -> None:
    calls: list[int] = []
    monkeypatch.setattr(lrclib.time, "sleep", lambda s: None)

    def urlopen(*_a, **_k):
        calls.append(1)
        raise _http_error(429, "120")

    monkeypatch.setattr(lrclib.urllib.request, "urlopen", urlopen)
    assert lrclib._fetch("https://lrclib.net/api/search?q=x") == ""
    assert len(calls) == 1


def test_an_unreachable_network_is_a_lyrics_error(monkeypatch) -> None:
    def urlopen(*_a, **_k):
        raise urllib.error.URLError("offline")

    monkeypatch.setattr(lrclib.urllib.request, "urlopen", urlopen)
    with pytest.raises(LyricsError):
        lrclib._fetch("https://lrclib.net/api/search?q=x")
