"""Tests for server 'now playing' status endpoints -- the free #1111 fallback
(Icecast /status-json.xsl, SHOUTcast /stats and /7.html). Pure parsing + URL
derivation; no network."""

from __future__ import annotations

import quill.core.radio.station_status as ss


def test_candidates_derive_from_the_stream_host_and_port() -> None:
    cands = ss.status_endpoint_candidates("http://example.com:8000/mount")
    urls = [c[0] for c in cands]
    assert "http://example.com:8000/status-json.xsl" in urls
    assert "http://example.com:8000/stats?json=1" in urls
    assert "http://example.com:8000/7.html" in urls
    # Icecast candidate carries the mount for source matching.
    icecast = next(c for c in cands if c[1] == "icecast")
    assert icecast[2] == "/mount"


def test_candidates_empty_for_non_http() -> None:
    assert ss.status_endpoint_candidates("file:///x") == []
    assert ss.status_endpoint_candidates("") == []


def test_parse_icecast_matches_the_mount() -> None:
    body = """
    {"icestats": {"source": [
      {"listenurl": "http://h:8000/other", "title": "Other Show"},
      {"listenurl": "http://h:8000/mount", "title": "Elton John - Your Song"}
    ]}}
    """
    assert ss.parse_icecast_status(body, mount="/mount") == "Elton John - Your Song"


def test_parse_icecast_single_source_dict_and_yp_field() -> None:
    body = '{"icestats": {"source": {"yp_currently_playing": "Adele - Hello"}}}'
    assert ss.parse_icecast_status(body, mount="/anything") == "Adele - Hello"


def test_parse_icecast_bad_json_is_empty() -> None:
    assert ss.parse_icecast_status("not json", mount="/m") == ""
    assert ss.parse_icecast_status("{}", mount="/m") == ""


def test_parse_shoutcast_v2_songtitle() -> None:
    assert ss.parse_shoutcast_v2_status('{"songtitle": "Queen - Bohemian Rhapsody"}') == (
        "Queen - Bohemian Rhapsody"
    )
    assert ss.parse_shoutcast_v2_status('{"songtitle": ""}') == ""
    assert ss.parse_shoutcast_v2_status("nope") == ""


def test_parse_shoutcast_v1_seven_html() -> None:
    # <current>,<status>,<peak>,<max>,<unique>,<bitrate>,<songtitle...>
    body = "<HTML><body>12,1,30,100,12,128,The Beatles - Hey Jude</body></HTML>"
    assert ss.parse_shoutcast_v1_status(body) == "The Beatles - Hey Jude"


def test_parse_shoutcast_v1_songtitle_with_commas_is_preserved() -> None:
    body = "12,1,30,100,12,128,Earth, Wind & Fire - September"
    assert ss.parse_shoutcast_v1_status(body) == "Earth, Wind & Fire - September"


def test_parse_shoutcast_v1_no_valid_line_is_empty() -> None:
    assert ss.parse_shoutcast_v1_status("<html>nothing here</html>") == ""


def test_read_server_now_playing_tries_candidates_in_order(monkeypatch) -> None:
    # Icecast endpoint fails/empty, SHOUTcast v2 answers.
    responses = {
        "http://h:8000/status-json.xsl": "",
        "http://h:8000/stats?json=1": '{"songtitle": "A - B"}',
    }
    monkeypatch.setattr(ss, "_http_get_text", lambda url, timeout: responses.get(url, ""))
    assert ss.read_server_now_playing("http://h:8000/mount") == "A - B"


def test_read_server_now_playing_refused_in_safe_mode(monkeypatch) -> None:
    monkeypatch.setattr(
        ss, "_http_get_text", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no net"))
    )
    assert ss.read_server_now_playing("http://h:8000/mount", safe_mode=True) == ""


def test_read_server_now_playing_all_empty(monkeypatch) -> None:
    monkeypatch.setattr(ss, "_http_get_text", lambda url, timeout: "")
    assert ss.read_server_now_playing("http://h:8000/mount") == ""
