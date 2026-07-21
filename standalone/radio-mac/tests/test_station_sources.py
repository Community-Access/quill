"""Tests for the station-source and metadata modules ported in Task 4:
safe_xml, radio_browser, soma_fm, acb_media, triton, and icy.

All tests are pure or use canned documents / monkeypatched egress
functions -- no real network calls anywhere.
"""

from __future__ import annotations

import io
import urllib.request

import pytest

from quill_radio_mac import __version__
from quill_radio_mac.core import acb_media, icy, radio_browser, safe_xml, soma_fm, triton
from quill_radio_mac.core.models import RadioStation
from quill_radio_mac.core.triton import TritonResolverError, TritonStream

# --- safe_xml -----------------------------------------------------------

_PLAIN_XML = "<root><child>value</child></root>"
_DOCTYPE_XML = '<!DOCTYPE root [<!ENTITY xxe "boom">]><root>&xxe;</root>'


def test_safe_xml_parses_plain_document():
    root = safe_xml.fromstring(_PLAIN_XML)
    assert root.find("child").text == "value"


def test_safe_xml_refuses_doctype_without_defusedxml():
    if safe_xml._HAVE_DEFUSED:
        pytest.skip("defusedxml installed: this fallback path is inactive")
    with pytest.raises(safe_xml.UnsafeXMLError):
        safe_xml.fromstring(_DOCTYPE_XML)


def test_safe_xml_raises_parse_error_for_malformed_xml():
    with pytest.raises(safe_xml.ParseError):
        safe_xml.fromstring("<root><unclosed></root>")


# --- triton ---------------------------------------------------------------

_TRITON_PROVISIONING_XML = """<?xml version="1.0" encoding="UTF-8"?>
<live_stream_config>
  <mountpoints>
    <mountpoint>
      <status-code>200</status-code>
      <mount>KMGLFM</mount>
      <format>MP3</format>
      <bitrate>128</bitrate>
      <audio codec="MP3" bitrate="128000"/>
      <servers>
        <server><ip>12.34.56.78</ip></server>
      </servers>
    </mountpoint>
    <mountpoint>
      <status-code>200</status-code>
      <mount>KMGLFMAAC</mount>
      <audio codec="HE-AACv2" bitrate="48000"/>
      <servers>
        <server><ip>12.34.56.79</ip></server>
      </servers>
    </mountpoint>
    <mountpoint>
      <status-code>404</status-code>
      <mount>DEADMOUNT</mount>
      <servers>
        <server><ip>0.0.0.0</ip></server>
      </servers>
    </mountpoint>
    <mountpoint>
      <status-code>200</status-code>
      <mount>NOSERVERMOUNT</mount>
      <audio codec="MP3" bitrate="128000"/>
      <servers></servers>
    </mountpoint>
  </mountpoints>
</live_stream_config>
"""

_LISTENLIVE_PLAYER_HTML = """
<html><head>
<link rel="apple-touch-icon" href="https://pwaimg.listenlive.co/KMGLFM_1115091_config_station_logo_image_1514560282.png">
</head><body>Player for player.listenlive.co</body></html>
"""

_STATION_PARAM_HTML = """
<html><body><script>var src = "https://playerservices.streamtheworld.com/api/livestream?station=WXYZFM";</script></body></html>
"""

_NON_TRITON_HTML = "<html><body><p>Just a plain station homepage.</p></body></html>"


def test_triton_parse_livestream_config_orders_mp3_first_and_skips_dead_mounts():
    streams = triton.parse_livestream_config(_TRITON_PROVISIONING_XML)
    assert [s.mount for s in streams] == ["KMGLFM", "KMGLFMAAC"]
    mp3 = streams[0]
    assert mp3.url == "https://12.34.56.78/KMGLFM"
    assert mp3.codec == "MP3"
    assert mp3.bitrate == 128000
    aac = streams[1]
    assert aac.codec == "AAC"
    assert aac.bitrate == 48000


def test_triton_parse_livestream_config_empty_for_malformed_xml():
    assert triton.parse_livestream_config("not xml at all <<<") == []


def test_triton_page_is_triton_player_matches_known_hosts():
    assert triton.page_is_triton_player("https://player.listenlive.co/x", _LISTENLIVE_PLAYER_HTML)
    assert not triton.page_is_triton_player("https://example.com", _NON_TRITON_HTML)


def test_triton_callsign_from_page_prefers_logo_asset_name():
    callsign = triton.callsign_from_page("https://player.listenlive.co/x", _LISTENLIVE_PLAYER_HTML)
    assert callsign == "KMGLFM"


def test_triton_callsign_from_page_falls_back_to_station_param():
    callsign = triton.callsign_from_page("https://example.com", _STATION_PARAM_HTML)
    assert callsign == "WXYZFM"


def test_triton_callsign_from_page_none_when_absent():
    assert triton.callsign_from_page("https://example.com", _NON_TRITON_HTML) is None


def test_triton_resolve_station_streams_refuses_in_safe_mode():
    with pytest.raises(TritonResolverError):
        triton.resolve_station_streams("KMGLFM", safe_mode=True)


def test_triton_resolve_station_streams_uses_fetch_api(monkeypatch):
    monkeypatch.setattr(triton, "_fetch_api", lambda callsign: _TRITON_PROVISIONING_XML)
    streams = triton.resolve_station_streams("kmglfm")
    assert streams[0] == TritonStream(
        url="https://12.34.56.78/KMGLFM", mount="KMGLFM", codec="MP3", bitrate=128000
    )


def test_triton_resolve_station_streams_blank_callsign_short_circuits(monkeypatch):
    monkeypatch.setattr(
        triton, "_fetch_api", lambda callsign: (_ for _ in ()).throw(AssertionError("no fetch"))
    )
    assert triton.resolve_station_streams("   ") == []


def test_triton_user_agent_uses_app_version():
    assert triton._USER_AGENT == f"QuillRadioMac/{__version__}"


# --- icy --------------------------------------------------------------------


def test_icy_parse_stream_title_extracts_value():
    metadata = b"StreamTitle='Elton John - Your Song';StreamUrl='';"
    assert icy.parse_stream_title(metadata) == "Elton John - Your Song"


def test_icy_parse_stream_title_empty_when_absent():
    assert icy.parse_stream_title(b"NotStreamTitle stuff") == ""


class _FakeIcyResponse:
    """A minimal stand-in for the object urlopen()'s context manager yields,
    simulating one audio chunk followed by one ICY metadata block."""

    def __init__(self, metaint: int, title: str) -> None:
        title_block = f"StreamTitle='{title}';".encode("utf-8")
        # ICY metadata blocks are padded to a multiple of 16 bytes; the first
        # byte read is the block length in 16-byte units.
        pad = (-len(title_block)) % 16
        block = title_block + b"\x00" * pad
        length_byte = bytes([len(block) // 16])
        audio_chunk = b"\x00" * metaint
        self._buffer = io.BytesIO(audio_chunk + length_byte + block)
        self.headers = {"icy-metaint": str(metaint)}

    def read(self, size: int = -1) -> bytes:
        return self._buffer.read(size) if size >= 0 else self._buffer.read()

    def __enter__(self) -> "_FakeIcyResponse":
        return self

    def __exit__(self, *exc_info: object) -> None:
        return None


def test_icy_read_stream_title_happy_path(monkeypatch):
    fake_response = _FakeIcyResponse(metaint=64, title="Elton John - Your Song")
    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: fake_response)
    title = icy.read_stream_title("https://example.com/stream")
    assert title == "Elton John - Your Song"


def test_icy_read_stream_title_rejects_non_http_scheme():
    assert icy.read_stream_title("ftp://example.com/stream") == ""


def test_icy_read_stream_title_swallows_network_errors(monkeypatch):
    def _raise(*args: object, **kwargs: object):
        raise OSError("boom")

    monkeypatch.setattr(urllib.request, "urlopen", _raise)
    assert icy.read_stream_title("https://example.com/stream") == ""


def test_icy_user_agent_uses_app_version():
    assert icy._USER_AGENT == f"QuillRadioMac/{__version__}"


# --- acb_media ----------------------------------------------------------


def test_acb_media_stations_has_ten_entries_with_https_urls():
    stations = acb_media.acb_media_stations()
    assert len(stations) == 10
    assert all(isinstance(s, RadioStation) for s in stations)
    assert all(s.stream_url.startswith("https://streaming.live365.com/") for s in stations)
    assert all(s.tags == (acb_media.CATEGORY_LABEL,) for s in stations)
    assert [s.name for s in stations] == [f"ACB Media {n}" for n in range(1, 11)]


def test_acb_media_stations_are_all_unique_urls():
    stations = acb_media.acb_media_stations()
    urls = {s.stream_url for s in stations}
    assert len(urls) == 10


# --- radio_browser --------------------------------------------------------


def test_radio_browser_refuses_in_safe_mode():
    with pytest.raises(radio_browser.RadioBrowserError):
        radio_browser.search_stations("jazz", safe_mode=True)


def test_radio_browser_search_stations_builds_expected_params(monkeypatch):
    captured: dict[str, str] = {}

    def _fake_http_json(url_path: str) -> object:
        captured["path"] = url_path
        return []

    monkeypatch.setattr(radio_browser, "_http_json", _fake_http_json)
    radio_browser.search_stations("jazz", tag="chill", country="US", limit=500, offset=10)
    path = captured["path"]
    assert path.startswith("/json/stations/search?")
    assert "name=jazz" in path
    assert "tag=chill" in path
    assert "country=US" in path
    assert "limit=200" in path  # clamped to RadioBrowser's 200 cap
    assert "offset=10" in path
    assert "hidebroken=true" in path
    assert "order=clickcount" in path


def test_radio_browser_lookup_station_blank_uuid_short_circuits(monkeypatch):
    monkeypatch.setattr(
        radio_browser, "_http_json", lambda p: (_ for _ in ()).throw(AssertionError("no fetch"))
    )
    assert radio_browser.lookup_station("   ") is None


def test_radio_browser_stations_from_json_skips_incomplete_entries():
    data = [
        {"name": "Good Station", "url_resolved": "https://example.com/stream", "bitrate": "128"},
        {"name": "", "url_resolved": "https://example.com/missing-name"},
        {"name": "No URL Station"},
        "not a dict",
    ]
    stations = radio_browser.stations_from_json(data)
    assert len(stations) == 1
    assert stations[0].name == "Good Station"
    assert stations[0].bitrate_kbps == 128


def test_radio_browser_user_agent_uses_app_version():
    assert radio_browser._USER_AGENT == f"QuillRadioMac/{__version__}"


def test_radio_browser_register_click_skips_blank_uuid(monkeypatch):
    monkeypatch.setattr(
        radio_browser, "_http_json", lambda p: (_ for _ in ()).throw(AssertionError("no fetch"))
    )
    radio_browser.register_click("")  # must not raise / must not fetch


# --- soma_fm (pure helpers only; no network) -------------------------------


def test_soma_fm_first_stream_url_from_pls():
    pls_text = "[playlist]\nFile1=https://ice1.somafm.com/groovesalad-128-mp3\nTitle1=SomaFM\n"
    assert soma_fm.first_stream_url_from_pls(pls_text) == "https://ice1.somafm.com/groovesalad-128-mp3"


def test_soma_fm_first_stream_url_from_pls_none_when_absent():
    assert soma_fm.first_stream_url_from_pls("[playlist]\nTitle1=Nope\n") is None


def test_soma_fm_best_playlist_prefers_mp3_then_quality():
    playlists = [
        {"url": "https://a", "format": "aac", "quality": "highest"},
        {"url": "https://b", "format": "mp3", "quality": "low"},
        {"url": "https://c", "format": "mp3", "quality": "highest"},
    ]
    best = soma_fm._best_playlist(playlists)
    assert best["url"] == "https://c"


def test_soma_fm_channels_from_json_filters_non_dict_entries():
    data = {"channels": [{"title": "Groove Salad"}, "junk", 42]}
    channels = soma_fm.channels_from_json(data)
    assert channels == [{"title": "Groove Salad"}]


def test_soma_fm_channel_matches_query_across_fields():
    channel = {"title": "Groove Salad", "description": "Chill", "genre": "ambient|downtempo"}
    assert soma_fm._channel_matches(channel, "")
    assert soma_fm._channel_matches(channel, "ambient")
    assert not soma_fm._channel_matches(channel, "heavy metal")


def test_soma_fm_refuses_in_safe_mode():
    with pytest.raises(soma_fm.SomaFmError):
        soma_fm.search_stations("jazz", safe_mode=True)


def test_soma_fm_user_agent_uses_app_version():
    assert soma_fm._USER_AGENT == f"QuillRadioMac/{__version__}"
