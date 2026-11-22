"""The Find Streams live check: verdicts from canned replies (no network).

Every reply here is built from the recorded fixtures in
``fixtures/live_check``; the "network" is a dictionary.
"""

from __future__ import annotations

import http.client
import threading
import urllib.error
from pathlib import Path

import pytest

from quill.core.radio import live_check
from quill.core.radio.live_check import (
    FILE,
    LIVE,
    NOT_AUDIO,
    UNCHECKED,
    HttpReply,
    check_urls,
    clean_header_text,
    verdict_from_reply,
)

_FIXTURES = Path(__file__).parent / "fixtures" / "live_check"


def _bytes(name: str) -> bytes:
    return (_FIXTURES / name).read_bytes()


def _reply(name: str, status: int = 200, **headers: str) -> HttpReply:
    return HttpReply(status, {k.replace("_", "-"): v for k, v in headers.items()}, _bytes(name))


def test_mp3_with_no_length_is_live_and_reads_the_icy_headers() -> None:
    reply = _reply(
        "mp3_prefix.bin",
        content_type="audio/mpeg",
        icy_name="KXYZ 88.1",
        icy_br="128",
        icy_genre="Community",
    )
    verdict, follow = verdict_from_reply(reply, "https://stream.example.org/live")
    assert (verdict.state, verdict.codec, verdict.bitrate_kbps) == (LIVE, "MP3", 128)
    assert (verdict.name, verdict.genre, follow) == ("KXYZ 88.1", "Community", "")


@pytest.mark.parametrize(
    ("fixture", "codec"), [("aac_prefix.bin", "AAC"), ("ogg_prefix.bin", "Ogg Opus")]
)
def test_aac_and_ogg_are_live(fixture: str, codec: str) -> None:
    verdict, _ = verdict_from_reply(_reply(fixture), "https://s.example/x")
    assert (verdict.state, verdict.codec) == (LIVE, codec)


def test_audio_with_a_content_length_is_a_file_not_a_station() -> None:
    reply = _reply("mp3_prefix.bin", content_type="audio/mpeg", content_length="48211330")
    assert verdict_from_reply(reply, "https://pod.example/ep12.mp3")[0].state == FILE


def test_a_web_page_answering_200_is_not_audio() -> None:
    reply = _reply("html_200.html", content_type="text/html; charset=utf-8")
    assert verdict_from_reply(reply, "https://site.example/stream")[0].state == NOT_AUDIO


def test_a_404_is_not_audio_but_a_403_is_only_not_checked() -> None:
    assert verdict_from_reply(HttpReply(404, {}, b""), "u")[0].state == NOT_AUDIO
    refused = verdict_from_reply(HttpReply(403, {}, b""), "u")[0]
    assert refused.state == UNCHECKED and "403" in refused.note


def test_a_playlist_is_judged_by_its_first_entry() -> None:
    reply = _reply("station.pls", content_type="audio/x-scpls")
    verdict, follow = verdict_from_reply(reply, "https://kxyz.example.org/listen.pls")
    assert verdict.state == UNCHECKED and follow == "https://stream.kxyz.example.org/live"


def test_hls_rules() -> None:
    live, _ = verdict_from_reply(_reply("hls_live.m3u8"), "https://c.example/live.m3u8")
    assert (live.state, live.codec) == (LIVE, "HLS")
    assert verdict_from_reply(_reply("hls_vod.m3u8"), "u")[0].state == FILE
    assert verdict_from_reply(_reply("hls_encrypted.m3u8"), "u")[0].state == NOT_AUDIO
    assert verdict_from_reply(_reply("hls_video_only.m3u8"), "u")[0].state == NOT_AUDIO
    _master, follow = verdict_from_reply(_reply("hls_master.m3u8"), "https://c.example/m.m3u8")
    assert follow == "https://c.example/audio/96k.m3u8"


def test_unrecognised_audio_is_not_checked_rather_than_dropped() -> None:
    reply = _reply("noise_prefix.bin", content_type="audio/mpeg")
    assert verdict_from_reply(reply, "u")[0].state == UNCHECKED


def test_server_names_are_cleaned_before_they_are_shown_or_spoken() -> None:
    assert clean_header_text("  KXYZ\x07  88.1\r\n ") == "KXYZ 88.1"
    # UTF-8 bytes that http.client decoded as Latin-1.
    assert clean_header_text("Radio FranÃ§ais") == "Radio Français"
    assert len(clean_header_text("x" * 200)) == 60


# -- check_urls: the bounded, deadline-capped pool ------------------------------


def _network(replies: dict[str, HttpReply | BaseException]) -> live_check.Getter:
    def get(url: str, _timeout: float) -> HttpReply:
        answer = replies[url]
        if isinstance(answer, BaseException):
            raise answer
        return answer

    return get


def test_check_urls_follows_a_playlist_and_reports_every_address() -> None:
    get = _network({
        "https://k.example/listen.pls": _reply("station.pls"),
        "https://stream.kxyz.example.org/live": _reply("mp3_prefix.bin", icy_name="KXYZ"),
        "https://k.example/gone": HttpReply(404, {}, b""),
        "https://k.example/slow": urllib.error.URLError(TimeoutError("timed out")),
        "https://k.example/refused": urllib.error.URLError(ConnectionRefusedError()),
    })
    urls = [
        "https://k.example/listen.pls",
        "https://k.example/gone",
        "https://k.example/slow",
        "https://k.example/refused",
    ]
    verdicts = check_urls(urls, get)
    assert set(verdicts) == set(urls)
    assert verdicts["https://k.example/listen.pls"].state == LIVE
    assert verdicts["https://k.example/listen.pls"].name == "KXYZ"
    assert verdicts["https://k.example/gone"].state == NOT_AUDIO
    assert verdicts["https://k.example/slow"].note == "it took too long to answer"
    assert verdicts["https://k.example/refused"].note == "the server refused the connection"


def test_an_http_error_is_read_for_its_status() -> None:
    error = urllib.error.HTTPError("https://k.example/x", 404, "Not Found", {}, None)  # type: ignore[arg-type]
    assert (
        check_urls(["https://k.example/x"], _network({"https://k.example/x": error}))[
            "https://k.example/x"
        ].state
        == NOT_AUDIO
    )


def test_a_shoutcast_icy_status_line_counts_as_live() -> None:
    error = http.client.BadStatusLine("ICY 200 OK\r\n")
    verdict = check_urls(["u"], _network({"u": error}))["u"]
    assert verdict.state == LIVE


def test_addresses_past_the_limit_are_listed_as_not_checked() -> None:
    urls = [f"https://k.example/{n}" for n in range(5)]
    get = _network({u: _reply("mp3_prefix.bin") for u in urls})
    verdicts = check_urls(urls, get, limit=2)
    assert [verdicts[u].state for u in urls] == [LIVE, LIVE, UNCHECKED, UNCHECKED, UNCHECKED]


def test_the_overall_deadline_leaves_slow_ones_not_checked() -> None:
    release = threading.Event()

    def get(url: str, _timeout: float) -> HttpReply:
        if url.endswith("slow"):
            release.wait(5)
        return _reply("mp3_prefix.bin")

    try:
        verdicts = check_urls(
            ["https://k.example/fast", "https://k.example/slow"], get, total_seconds=1.0
        )
    finally:
        release.set()
    assert verdicts["https://k.example/fast"].state == LIVE
    assert verdicts["https://k.example/slow"].state == UNCHECKED


def test_concurrency_is_bounded() -> None:
    lock = threading.Lock()
    running = 0
    peak = 0

    def get(_url: str, _timeout: float) -> HttpReply:
        nonlocal running, peak
        with lock:
            running += 1
            peak = max(peak, running)
        threading.Event().wait(0.05)
        with lock:
            running -= 1
        return _reply("mp3_prefix.bin")

    check_urls([f"https://k.example/{n}" for n in range(10)], get, workers=3)
    assert peak <= 3
