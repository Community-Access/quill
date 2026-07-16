"""Tests for the Triton Digital / StreamTheWorld resolver (no network)."""

from __future__ import annotations

import pytest

import quill.core.radio.triton as triton
from quill.core.radio.triton import (
    TritonResolverError,
    callsign_from_page,
    page_is_triton_player,
    parse_livestream_config,
    refuse_in_safe_mode,
    resolve_station_streams,
)

# The exact XML shape Triton returns (captured from a live KMGLFM response):
# a namespaced <live_stream_config> with one <mountpoint> per codec, each
# carrying its own <servers>, <mount>, and <media-format><audio codec=...>.
_LIVESTREAM_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<live_stream_config version="1.9"
    xmlns="http://provisioning.streamtheworld.com/player/livestream-1.9">
  <mountpoints>
    <mountpoint>
      <status><status-code>200</status-code><status-message>OK</status-message></status>
      <servers>
        <server sid="29306"><ip>29306.live.streamtheworld.com</ip>
          <ports><port type="https">443</port></ports></server>
        <server sid="14613"><ip>14613.live.streamtheworld.com</ip>
          <ports><port type="https">443</port></ports></server>
      </servers>
      <mount>KMGLFM</mount>
      <format>FLV</format>
      <bitrate>64000</bitrate>
      <media-format container="flv">
        <audio index="0" samplerate="22050" codec="mp3" bitrate="64000" channels="2"/>
      </media-format>
    </mountpoint>
    <mountpoint>
      <status><status-code>200</status-code><status-message>OK</status-message></status>
      <servers>
        <server sid="14623"><ip>14623.live.streamtheworld.com</ip>
          <ports><port type="https">443</port></ports></server>
      </servers>
      <mount>KMGLFMAAC</mount>
      <media-format container="flv">
        <audio index="0" samplerate="44100" codec="heaacv2" bitrate="32000" channels="2"/>
      </media-format>
    </mountpoint>
  </mountpoints>
</live_stream_config>"""


def test_refuse_in_safe_mode_raises() -> None:
    with pytest.raises(TritonResolverError):
        refuse_in_safe_mode(True)
    refuse_in_safe_mode(False)  # no raise


def test_parse_livestream_config_builds_playable_urls() -> None:
    streams = parse_livestream_config(_LIVESTREAM_XML)
    assert len(streams) == 2
    mp3, aac = streams
    # MP3 comes first (Triton's order; the widely-compatible mount ahead of AAC).
    assert mp3.url == "https://29306.live.streamtheworld.com/KMGLFM"
    assert mp3.mount == "KMGLFM"
    assert mp3.codec == "MP3"
    assert mp3.bitrate == 64000
    assert aac.url == "https://14623.live.streamtheworld.com/KMGLFMAAC"
    assert aac.codec == "AAC"
    assert aac.bitrate == 32000


def test_parse_skips_non_ok_mountpoint() -> None:
    xml = """<live_stream_config
        xmlns="http://provisioning.streamtheworld.com/player/livestream-1.9">
      <mountpoints><mountpoint>
        <status><status-code>404</status-code></status>
        <servers><server><ip>x.streamtheworld.com</ip></server></servers>
        <mount>NOPE</mount>
      </mountpoint></mountpoints>
    </live_stream_config>"""
    assert parse_livestream_config(xml) == []


def test_parse_skips_mountpoint_without_server_or_mount() -> None:
    xml = """<live_stream_config
        xmlns="http://provisioning.streamtheworld.com/player/livestream-1.9">
      <mountpoints>
        <mountpoint><status><status-code>200</status-code></status>
          <mount>NOSERVER</mount></mountpoint>
        <mountpoint><status><status-code>200</status-code></status>
          <servers><server><ip>host.streamtheworld.com</ip></server></servers></mountpoint>
      </mountpoints>
    </live_stream_config>"""
    assert parse_livestream_config(xml) == []


def test_parse_tolerates_malformed_xml() -> None:
    assert parse_livestream_config("<not-xml <<<") == []
    assert parse_livestream_config("") == []


def test_parse_refuses_entity_expansion_payload() -> None:
    # A billion-laughs-style DTD must be refused (via safe_xml), not expanded.
    xml = """<?xml version="1.0"?>
    <!DOCTYPE lolz [<!ENTITY lol "lol">]>
    <live_stream_config><mountpoints><mountpoint>
      <status><status-code>200</status-code></status>
      <servers><server><ip>&lol;</ip></server></servers><mount>X</mount>
    </mountpoint></mountpoints></live_stream_config>"""
    assert parse_livestream_config(xml) == []


@pytest.mark.parametrize(
    ("url", "html", "expected"),
    [
        ("https://player.listenlive.co/34461", "<html>Triton Digital</html>", True),
        ("https://example.com", '<script src="//x.streamtheworld.com/p.js">', True),
        ("https://example.com", "<html>a normal station site</html>", False),
    ],
)
def test_page_is_triton_player(url: str, html: str, expected: bool) -> None:
    assert page_is_triton_player(url, html) is expected


def test_callsign_from_logo_asset() -> None:
    html = (
        '<img src="//pwaimg.listenlive.co/KMGLFM_1115091_config_station_logo_image_1514560282.png">'
    )
    assert callsign_from_page("https://player.listenlive.co/34461", html) == "KMGLFM"


def test_callsign_from_station_query_fallback() -> None:
    html = '<script>var u="https://x/api/livestream?station=wabcfm&version=1.9";</script>'
    assert callsign_from_page("https://example.com", html) == "WABCFM"


def test_callsign_absent_returns_none() -> None:
    assert callsign_from_page("https://example.com", "<html>no callsign here</html>") is None


def test_resolve_station_streams_calls_api_and_parses(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def fake_fetch(callsign: str) -> str:
        calls.append(callsign)
        return _LIVESTREAM_XML

    monkeypatch.setattr(triton, "_fetch_api", fake_fetch)
    streams = resolve_station_streams("kmglfm")
    assert calls == ["KMGLFM"]  # normalized to upper-case for the API
    assert [s.url for s in streams] == [
        "https://29306.live.streamtheworld.com/KMGLFM",
        "https://14623.live.streamtheworld.com/KMGLFMAAC",
    ]


def test_resolve_station_streams_empty_callsign_makes_no_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        triton, "_fetch_api", lambda _c: pytest.fail("must not fetch for an empty callsign")
    )
    assert resolve_station_streams("   ") == []


def test_resolve_station_streams_refuses_in_safe_mode() -> None:
    with pytest.raises(TritonResolverError):
        resolve_station_streams("KMGLFM", safe_mode=True)


def test_api_url_shape() -> None:
    url = triton._api_url("KMGLFM")
    assert url.startswith("https://playerservices.streamtheworld.com/api/livestream?")
    assert "station=KMGLFM" in url
    assert "transports=http" in url
    assert "version=1.9" in url
