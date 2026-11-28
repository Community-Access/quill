"""Find Streams: server listings, Global Player, the soundmap and IPRD.

Ideas from Andre Louis's StreamSift (https://github.com/OnjLouis/StreamSift),
written in QUILL's own code. Tested against pages recorded on 2026-11-22
(Global's ``media-ssl.musicradio.com`` catalogue and a Global Player station
page, both trimmed; the Locus Sonus active list, its first three entries) and
synthetic SHOUTcast statistics and IPRD rows, in ``fixtures/more_sources``.
No network: every fetch and probe is answered from a dictionary.
"""

from __future__ import annotations

import urllib.error
from pathlib import Path

import pytest

import quill.core.radio.link_finder as lf
from quill.core.radio import (
    browse_flat,
    browse_visibility,
    global_player,
    iprd,
    locus_sonus,
    securenet,
    server_listings,
    triton,
)
from quill.core.radio.find_streams_text import row_status
from quill.core.radio.live_check import HttpReply
from quill.core.radio.page_links import PageStreamCandidate

_FIXTURES = Path(__file__).parent / "fixtures" / "more_sources"
_MP3 = (Path(__file__).parent / "fixtures" / "live_check" / "mp3_prefix.bin").read_bytes()


def _text(name: str) -> str:
    return (_FIXTURES / name).read_text(encoding="utf-8")


def _serve(monkeypatch: pytest.MonkeyPatch, pages: dict[str, str]) -> list[str]:
    fetched: list[str] = []

    def fetch(url: str) -> str:
        fetched.append(url)
        if url not in pages:
            raise lf.LinkFinderError(f"not recorded: {url}")
        return pages[url]

    monkeypatch.setattr(lf, "_fetch_html", fetch)
    return fetched


@pytest.fixture(autouse=True)
def _no_iprd(monkeypatch: pytest.MonkeyPatch) -> None:
    """No catalogue in memory or on disk unless a test puts one there."""
    monkeypatch.setattr(iprd, "_memo", None)
    monkeypatch.setattr(iprd.directory_cache, "load", lambda key: None)
    monkeypatch.setattr(iprd, "_fetch", lambda: pytest.fail("a scan downloaded IPRD"))


# -- server listings (pure) ---------------------------------------------------


def test_shoutcast_statistics_list_every_stream_on_air() -> None:
    mounts = server_listings.parse_shoutcast_json(
        _text("shoutcast_statistics.json"), "http://sc.example.org:8000"
    )
    assert [(m.url, m.name, m.bitrate_kbps, m.listeners) for m in mounts] == [
        ("http://sc.example.org:8000/stream", "WABC Community Radio", 128, 12),
        ("http://sc.example.org:8000/talk", "WABC Talk", 64, 3),
    ]  # "/spare" is off air (streamstatus 0), so it is not offered


def test_icecast_json_mounts_stay_on_the_server_that_answered() -> None:
    text = (
        '{"icestats":{"source":{"listenurl":"http://10.0.0.5:9000/live",'
        '"server_name":"Live","server_type":"audio/mpeg","bitrate":96,"listeners":7}}}'
    )
    mounts = server_listings.parse_icecast_json(text, "https://ice.example.org")
    assert [(m.url, m.listeners, m.bitrate_kbps) for m in mounts] == [
        ("https://ice.example.org/live", 7, 96)
    ]
    video = text.replace("audio/mpeg", "video/webm")
    assert server_listings.parse_icecast_json(video, "https://ice.example.org") == []


def test_global_catalogue_lists_its_audio_mounts_on_its_own_https_host() -> None:
    mounts = server_listings.parse_icecast_html(
        _text("global_catalogue.html"), "https://media-ssl.musicradio.com/"
    )
    assert [m.url for m in mounts] == [
        "https://media-ssl.musicradio.com/BigTop40",
        "https://media-ssl.musicradio.com/BigTop40MP3",
        "https://media-ssl.musicradio.com/BigTop40V1",
    ]  # the crafted video card is left out
    assert mounts[0].name == "The Big Top 40 Show"


def test_a_card_that_names_no_content_type_is_not_offered() -> None:
    legacy = _text("../live_check/icecast_status.html")
    assert server_listings.parse_icecast_html(legacy, "https://ice.example.org/status.xsl") == []


@pytest.mark.parametrize(
    "path", ["/admin/stats", "/a/../b", "//evil.example/x", "/status-json.xsl"]
)
def test_status_and_admin_routes_never_become_mounts(path: str) -> None:
    text = f'{{"icestats":{{"source":{{"mount":"{path}","server_type":"audio/mpeg"}}}}}}'
    assert server_listings.parse_icecast_json(text, "https://ice.example.org") == []


def test_status_addresses_are_recognised_by_kind() -> None:
    assert server_listings.status_kind("http://h:8000/status.xsl") == "icecast"
    assert server_listings.status_kind("http://h:8000/index.html?sid=1") == "shoutcast"
    assert server_listings.status_kind("http://h:8000/statistics") == "shoutcast"
    assert server_listings.status_kind("https://station.example/stats") == ""
    assert server_listings.server_kind("http://h:8000/", "SHOUTcast Server") == "shoutcast"
    assert server_listings.server_kind("https://k.example/about", "Icecast fans") == ""


# -- server listings in a scan ------------------------------------------------


def test_a_shoutcast_server_front_page_lists_every_stream_with_listeners(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = "https://sc.example.org:8443"
    _serve(
        monkeypatch,
        {
            f"{root}/": "<html><head><title>SHOUTcast Server</title></head><body></body></html>",
            f"{root}/statistics?json=1": _text("shoutcast_statistics.json"),
        },
    )
    live = HttpReply(200, {"Content-Type": "audio/mpeg"}, _MP3)
    monkeypatch.setattr(lf, "_probe", lambda url, timeout: live)
    result = lf.scan_page_for_streams(f"{root}/", check_live=True)
    by_url = {c.url: c for c in result.candidates}
    stream = by_url[f"{root}/stream"]
    assert (stream.check, stream.label, stream.bitrate_kbps, stream.listeners) == (
        "live",
        "WABC Community Radio",
        128,
        12,
    )
    assert f"{root}/spare" not in by_url
    # The listener count comes last, after name, codec and bitrate.
    assert row_status(stream) == "Live: WABC Community Radio, MP3, 128 kbps, 12 listeners"


def test_a_page_linking_to_a_shoutcast_status_page_reads_its_statistics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fetched = _serve(
        monkeypatch,
        {
            "https://wabc.example.org": '<a href="http://sc.example.org:8000/index.html?sid=1">Stats</a>',
            "http://sc.example.org:8000/statistics?json=1": _text("shoutcast_statistics.json"),
        },
    )
    urls = [c.url for c in lf.scan_page_for_streams("wabc.example.org").candidates]
    assert urls[:2] == ["http://sc.example.org:8000/stream", "http://sc.example.org:8000/talk"]
    assert "http://sc.example.org:8000/status-json.xsl" not in fetched


def test_globals_catalogue_is_read_from_the_page_already_fetched(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    page = "https://media-ssl.musicradio.com/"
    fetched = _serve(monkeypatch, {page: _text("global_catalogue.html")})
    result = lf.scan_page_for_streams(page)
    urls = [c.url for c in result.candidates]
    assert urls[:3] == [
        "https://media-ssl.musicradio.com/BigTop40",
        "https://media-ssl.musicradio.com/BigTop40MP3",
        "https://media-ssl.musicradio.com/BigTop40V1",
    ]
    assert result.candidates[0].reason == "mount listed on the server's Icecast status page"
    assert fetched.count(page) == 1  # no second read of the catalogue


def test_a_server_listing_raises_the_check_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    page = "https://media-ssl.musicradio.com/"
    _serve(monkeypatch, {page: _text("global_catalogue.html")})
    seen: list[int] = []

    def check(
        urls: list[str], get: object, *, limit: int, on_verdict: object = None
    ) -> dict[str, object]:
        seen.append(limit)
        return {}

    monkeypatch.setattr(lf.live_check, "check_urls", check)
    lf.scan_page_for_streams(page, check_live=True)
    monkeypatch.setattr(lf, "_fetch_html", lambda url: '<audio src="https://k.example/live">')
    lf.scan_page_for_streams("k.example", check_live=True)
    assert seen == [lf._LISTING_CHECKS, lf.live_check.MAX_CHECKS]


# -- Global Player ------------------------------------------------------------


def test_a_global_player_page_offers_only_the_stream_anyone_may_play() -> None:
    html = _text("globalplayer_capital_uk.html")
    assert global_player.is_station_page("https://www.globalplayer.com/live/capital/uk/")
    assert not global_player.is_station_page("https://www.globalplayer.com/podcasts/x/")
    assert global_player.station_title(html) == "Capital UK"
    # The HLS, Alexa and HD entries need a licence or a sign-in; they are not offered.
    assert global_player.stream_urls_from_page(html) == [
        "https://media-ssl.musicradio.com/CapitalUK"
    ]


def test_a_station_site_linking_to_global_player_is_followed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gp = "https://www.globalplayer.com/live/capital/uk/"
    _serve(
        monkeypatch,
        {
            "https://capital.example": f'<a href="{gp}">Listen on Global Player</a>',
            gp: _text("globalplayer_capital_uk.html"),
        },
    )
    result = lf.scan_page_for_streams("capital.example")
    assert [c.url for c in result.candidates] == ["https://media-ssl.musicradio.com/CapitalUK"]
    assert "Global Player" in result.candidates[0].reason


# -- Locus Sonus Soundmap -----------------------------------------------------


def test_the_soundmap_list_becomes_named_stations_a_to_z() -> None:
    stations = locus_sonus.parse_active_list(_text("locus_active.json"))
    # The country is said once, by the row itself, after the cleaned name.
    assert [s.display_name for s in stations] == [
        "acra, wave farm (United States)",
        "amsterdam, hydrophile 1 (Netherlands)",
        "amsterdam, hydrophile 5 (Netherlands)",
    ]
    assert stations[0].stream_url == "https://locus.creacast.com:9443/acra_wave_farm.mp3"
    assert stations[0].source == "Locus Sonus" and stations[0].codec == "MP3"
    assert locus_sonus.parse_active_list("not json") == []
    said_twice = (
        '[{"name": "lisbon \u2014  rooftop, portugal", "url": "https://m.example/a.mp3",'
        ' "country": "portugal"}]'
    )
    (one,) = locus_sonus.parse_active_list(said_twice)
    assert one.display_name == "lisbon, rooftop, portugal"


def test_an_unreachable_soundmap_is_not_an_empty_one(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(locus_sonus.directory_cache, "resolve", lambda *a, **k: ("", None))
    with pytest.raises(locus_sonus.LocusSonusError) as raised:
        locus_sonus.fetch_stations()
    from quill.core.radio.browse_failure import last_error_was_network

    assert last_error_was_network(raised.value)
    monkeypatch.setattr(locus_sonus.directory_cache, "resolve", lambda *a, **k: ("[]", None))
    assert locus_sonus.fetch_stations() == []
    assert browse_flat.empty_note("locussonus") == (
        "No open microphones are on air right now. Refresh to look again."
    )
    assert browse_flat.empty_note("radioparadise") == ""


def test_the_soundmap_is_refused_in_safe_mode() -> None:
    with pytest.raises(locus_sonus.LocusSonusError):
        locus_sonus.fetch_stations(safe_mode=True)
    assert locus_sonus.LocusSonusError.code == "QUILL-RADIO-LOCUSSONUS-REQUEST"


def test_the_soundmap_page_lists_its_open_microphones(monkeypatch: pytest.MonkeyPatch) -> None:
    page = "https://locusonus.org/soundmap/"
    _serve(monkeypatch, {page: "<html><title>Locus Sonus soundmap</title></html>"})
    stations = locus_sonus.parse_active_list(_text("locus_active.json"))
    monkeypatch.setattr(locus_sonus, "fetch_stations", lambda safe_mode: stations)
    result = lf.scan_page_for_streams(page)
    assert [c.url for c in result.candidates] == [s.stream_url for s in stations]
    assert result.candidates[0].label == "acra, wave farm (United States)"
    assert row_status(result.candidates[0]) == "Not checked: acra, wave farm (United States)"


def test_the_soundmap_is_checked_like_a_listing(monkeypatch: pytest.MonkeyPatch) -> None:
    page = "https://locusonus.org/soundmap/"
    _serve(monkeypatch, {page: "<html><title>Locus Sonus soundmap</title></html>"})
    stations = locus_sonus.parse_active_list(_text("locus_active.json"))
    monkeypatch.setattr(locus_sonus, "fetch_stations", lambda safe_mode: stations)
    seen: list[int] = []

    def check(
        urls: list[str], get: object, *, limit: int, on_verdict: object = None
    ) -> dict[str, object]:
        seen.append(limit)
        return {}

    monkeypatch.setattr(lf.live_check, "check_urls", check)
    result = lf.scan_page_for_streams(page, check_live=True)
    assert seen == [lf._LISTING_CHECKS] and result.check_limit == lf._LISTING_CHECKS


def test_the_soundmap_is_a_browse_branch_shown_to_existing_profiles() -> None:
    assert "locussonus" in browse_flat.FLAT
    assert "locussonus" in browse_visibility.introduced_since(6)
    ids = [info.id for info in browse_visibility.BROWSE_SOURCES]
    assert "locussonus" in ids


# -- IPRD, matched by website -------------------------------------------------

_ROWS: list[iprd.Row] = [
    (
        "WXYZ Community",
        "https://ice.wxyz.example/live",
        "US",
        ("community",),
        "MP3",
        128,
        "http://www.wxyz.example/",
    ),
    ("Other", "https://other.example/live", "US", (), "MP3", 64, "https://other.example"),
    (
        "Network Station",
        "https://net.example/one",
        "US",
        (),
        "AAC",
        48,
        "https://network.example/stations/one",
    ),
]


def test_iprd_matches_a_website_by_host_either_side_of_www(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(iprd, "_memo", (0.0, _ROWS))
    assert [s.name for s in iprd.stations_for_website("https://wxyz.example")] == ["WXYZ Community"]
    one = iprd.stations_for_website("https://network.example/stations/one/")
    assert [s.name for s in one] == ["Network Station"]
    assert iprd.stations_for_website("https://network.example/stations/two") == []


def test_iprd_matching_never_downloads_and_respects_safe_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert iprd.stations_for_website("https://wxyz.example") == []  # nothing cached
    monkeypatch.setattr(iprd, "_memo", (0.0, _ROWS))
    assert iprd.stations_for_website("https://wxyz.example", safe_mode=True) == []


def test_a_website_scan_adds_what_iprd_lists_for_it(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(iprd, "_memo", (0.0, _ROWS))
    _serve(monkeypatch, {"https://wxyz.example": "<html><title>WXYZ</title></html>"})
    candidates = lf.scan_page_for_streams("wxyz.example").candidates
    assert [(c.url, c.label) for c in candidates] == [
        ("https://ice.wxyz.example/live", "WXYZ Community")
    ]
    assert "IPRD" in candidates[0].reason


def test_an_iprd_match_is_checked_like_any_other_link(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(iprd, "_memo", (0.0, _ROWS))
    _serve(monkeypatch, {"https://wxyz.example": "<html><title>WXYZ</title></html>"})
    gone = urllib.error.HTTPError("https://ice.wxyz.example/live", 404, "gone", {}, None)  # type: ignore[arg-type]

    def probe(url: str, timeout: float) -> HttpReply:
        raise gone

    monkeypatch.setattr(lf, "_probe", probe)
    result = lf.scan_page_for_streams("wxyz.example", check_live=True)
    assert result.candidates == [] and result.left_out == 1


# -- Triton and SecureNet page forms --------------------------------------------


def test_a_listenlive_player_names_its_mount_in_its_app_name() -> None:
    page = '<html><head><meta name="application-name" content="KKSEFM"></head></html>'
    assert triton.callsign_from_page("https://player.listenlive.co/20551", page) == "KKSEFM"
    # Off the player's own host, an app name is only a site's name.
    assert triton.callsign_from_page("https://example.com/", page) is None


def test_a_cirruscontent_page_names_its_callsign() -> None:
    url = "https://streamdb9web.securenetsystems.net/cirruscontent/WWOJ"
    assert securenet.callsign_from_page(url) == "WWOJ"


def test_a_row_without_a_listener_count_is_unchanged() -> None:
    row = PageStreamCandidate(url="https://k.example/", reason="r", check="live", codec="MP3")
    assert row_status(row) == "Live: k.example, MP3"
    one = PageStreamCandidate(url="https://k.example/", reason="r", check="live", listeners=1)
    assert row_status(one) == "Live: k.example, 1 listener"


def test_a_scan_counts_the_links_it_never_contacted(monkeypatch: pytest.MonkeyPatch) -> None:
    page = "https://media-ssl.musicradio.com/"
    _serve(monkeypatch, {page: _text("global_catalogue.html")})
    live = HttpReply(200, {"Content-Type": "audio/mpeg"}, _MP3)
    monkeypatch.setattr(lf, "_LISTING_CHECKS", 1)
    monkeypatch.setattr(lf, "_probe", lambda url, timeout: live)
    result = lf.scan_page_for_streams(page, check_live=True)
    assert result.check_limit == 1 and result.skipped == 2
    unchecked = [c for c in result.candidates if c.check == "not checked"]
    # Named from the listing, not "BigTop40MP3 on media-ssl.musicradio.com".
    assert row_status(unchecked[0]) == (
        "Not checked: The Big Top 40 Show, there were too many links to check them all"
    )
