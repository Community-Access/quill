"""The station's own published playlist: matching, parsing, and the fetch loop.

The fixtures under ``fixtures/station_playlist`` were written by hand, cut down
from real answers each service gave on 2026-11-07. The source list and its edge
cases come from BlindRadio by serrebidev (MIT). No test reaches the network:
``station_playlist._fetch`` is the boundary, and it is replaced.
"""

from __future__ import annotations

import re
import urllib.error
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from quill.core.radio import radio_paradise
from quill.core.radio import station_playlist as sp

_FIXTURES = Path(__file__).parent / "fixtures" / "station_playlist"


def _fixture(name: str) -> str:
    return (_FIXTURES / name).read_text(encoding="utf-8")


# --- matching ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("url", "provider", "key"),
    [
        (
            "https://playerservices.streamtheworld.com/api/livestream-redirect/977_HITS_SC.mp3",
            sp.PROVIDER_TRITON,
            "977_HITS_SC",
        ),
        (
            "http://17883.live.streamtheworld.com:3690/RADIO538.mp3?x=1",
            sp.PROVIDER_TRITON,
            "RADIO538",
        ),
        ("https://streaming.live365.com/a62479", sp.PROVIDER_LIVE365, "a62479"),
        ("https://eins.stream.laut.fm/eins", sp.PROVIDER_LAUT_FM, "eins"),
        ("https://stream.laut.fm/teatime", sp.PROVIDER_LAUT_FM, "teatime"),
        (
            "https://demo.azuracast.com/listen/azuratest_radio/radio.mp3",
            sp.PROVIDER_AZURACAST,
            "azuratest_radio",
        ),
        (
            "http://as-hls-ww-live.akamaized.net/pool_74208725/live/ww/bbc_radio_two/"
            "bbc_radio_two.isml/bbc_radio_two-audio%3d128000.norewind.m3u8",
            sp.PROVIDER_BBC,
            "bbc_radio_two",
        ),
        (
            "https://a.files.bbci.co.uk/ms6/live/3441A116/audio/simulcast/hls/nonuk/"
            "pc_hd_abr_v2/ak/bbc_radio_one.m3u8",
            sp.PROVIDER_BBC,
            "bbc_radio_one",
        ),
        ("https://kexp.streamguys1.com/kexp160.aac", sp.PROVIDER_KEXP, "kexp"),
        ("http://live-mp3-128.kexp.org/kexp128.mp3", sp.PROVIDER_KEXP, "kexp"),
        ("https://stream.radioparadise.com/mellow-128", sp.PROVIDER_RADIO_PARADISE, "1"),
        ("https://stream.radioparadise.com/aac-320", sp.PROVIDER_RADIO_PARADISE, "0"),
        ("https://stream.radioparadise.com/radio2050-flacm", sp.PROVIDER_RADIO_PARADISE, "2050"),
    ],
)
def test_a_stream_address_names_its_source(url: str, provider: str, key: str) -> None:
    source = sp.match_source(url)
    assert source is not None
    assert (source.provider, source.key) == (provider, key)


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/stream.mp3",
        "https://example.com/listen/live",  # AzuraCast's route has three parts
        "https://stream.radioparadise.com/kfat-128",  # no playlist behind it
        "https://notstreamtheworld.com/KEXP.mp3",
        "https://streamtheworld.com.evil.example/977_HITS.mp3",
        "https://kexp.example.com/kexp160.aac",  # a name, not KEXP's host
        "https://streamguys1.com/kexp160.aac",
        "https://stream.laut.fm.example.org/eins",
        "https://streaming.live365.com/",
        "http://151.80.56.90:8090/bbc_radio_one_dance.aac",  # a relay, not the BBC
        "https://as-hls-ww-live.akamaized.net/pool_1/live/ww/radio_one/radio_one.m3u8",
        "ftp://stream.laut.fm/eins",
        "not a url",
        "",
    ],
)
def test_addresses_that_name_no_source_match_nothing(url: str) -> None:
    assert sp.match_source(url) is None


def test_the_station_name_never_decides_the_match() -> None:
    # Only the address is consulted; a KEXP-looking name changes nothing.
    assert sp.match_source("https://example.com/kexp/stream.mp3") is None


def test_azuracast_is_asked_over_https_and_keeps_only_an_https_port() -> None:
    plain = sp.match_source("http://radio.example.org:8000/listen/jazz/radio.mp3")
    secure = sp.match_source("https://radio.example.org:8443/listen/jazz/radio.mp3")
    assert plain is not None and secure is not None
    assert plain.api_urls() == ("https://radio.example.org/api/nowplaying/jazz",)
    assert secure.api_urls() == ("https://radio.example.org:8443/api/nowplaying/jazz",)


def test_every_api_url_is_https_and_the_kexp_and_bbc_quirks_are_kept() -> None:
    kexp = sp.match_source("https://kexp.streamguys1.com/kexp160.aac")
    bbc = sp.match_source("https://a.files.bbci.co.uk/x/bbc_6music.m3u8")
    assert kexp is not None and bbc is not None
    assert "ordering=-airdate" in kexp.api_urls()[0]
    assert bbc.api_urls()[0].endswith("/services/bbc_6music/segments/latest?limit=10")


def test_radio_paradise_channel_table_lives_with_radio_paradise() -> None:
    assert radio_paradise.playlist_channel("https://stream.radioparadise.com/serenity") == 42
    assert radio_paradise.playlist_channel("https://stream.radioparadise.com/rock-flacm") == 2
    assert radio_paradise.playlist_channel("https://radioparadise.example/rock-128") is None


# --- Triton mount names -----------------------------------------------------


def test_triton_tries_the_mount_then_without_sc_then_without_aac() -> None:
    assert sp.triton_mount_candidates("977_HITSAAC_SC") == (
        "977_HITSAAC_SC",
        "977_HITSAAC",
        "977_HITS",
    )
    assert sp.triton_mount_candidates("KNPRFMAAC") == ("KNPRFMAAC", "KNPRFM")
    assert sp.triton_mount_candidates("WABEFM_HD1_SC") == ("WABEFM_HD1_SC", "WABEFM_HD1")
    assert sp.triton_mount_candidates("RADIO538") == ("RADIO538",)
    assert sp.triton_mount_candidates("AAC") == ("AAC",)


def test_triton_source_asks_each_mount_in_turn() -> None:
    source = sp.match_source("https://x.live.streamtheworld.com/977_HITSAAC_SC.aac")
    assert source is not None
    urls = source.api_urls()
    assert [u.split("mountName=")[1].split("&")[0] for u in urls] == [
        "977_HITSAAC_SC",
        "977_HITSAAC",
        "977_HITS",
    ]
    assert all("eventType=track" in u and "numberToFetch=50" in u for u in urls)


# --- times ------------------------------------------------------------------


def test_times_read_every_published_form() -> None:
    want = datetime(2026, 11, 4, 8, 5, 16, tzinfo=UTC)
    assert sp.parse_time("2026-11-04 08:05:16.45+00:00") == want
    assert sp.parse_time("2026-11-04 09:05:16 +0100") == want
    assert sp.parse_time("2026-11-04T00:05:16-08:00") == want
    assert sp.parse_time("2026-11-04 08:05:16") == want
    assert sp.parse_time("2026-11-04T08:05:16Z") == want
    assert sp.parse_time("soon") is None
    assert sp.parse_time("") is None
    assert sp.parse_time(None) is None


# --- parsers ----------------------------------------------------------------


def test_azuracast_reads_now_playing_then_history_and_falls_back_to_text() -> None:
    songs = sp.parse_azuracast(_fixture("azuracast.json"), "azuratest_radio")
    assert [s.display() for s in songs] == [
        "One Of A Kind by SKALP & Ryan Konline",
        "Imagine by Internet Empire",
        "Station ID Only",
    ]
    assert songs[0].is_current and not songs[1].is_current
    assert songs[0].started_at == datetime.fromtimestamp(1794105811, tz=UTC)


def test_azuracast_answer_for_another_station_is_ignored() -> None:
    assert sp.parse_azuracast(_fixture("azuracast.json"), "some_other_station") == ()
    assert sp.parse_azuracast("<html>not azuracast</html>", "azuratest_radio") == ()


def test_kexp_skips_airbreaks() -> None:
    songs = sp.parse_kexp(_fixture("kexp.json"))
    assert [s.display() for s in songs] == ["Telegram by Eggshells", "BROWN BEANIE by Yaya Bey"]
    assert songs[0].started_at == datetime(2026, 11, 8, 2, 42, 15, tzinfo=UTC)


def test_bbc_keeps_music_and_its_own_words_for_when() -> None:
    now = datetime(2026, 11, 8, 3, 0, tzinfo=UTC)
    songs = sp.parse_bbc(_fixture("bbc.json"), now=now)
    assert [s.display() for s in songs] == [
        "Beautiful People <CJ Edit> by Barbara Tucker",
        "Can You Feel The Force? by The Real Thing",
        "I Will Survive by Gloria Gaynor",
    ]
    assert songs[0].is_current and songs[0].when_label == ""
    assert songs[1].when_label == "3 minutes ago"
    assert songs[1].started_at == now - timedelta(minutes=3)
    assert songs[2].started_at == now - timedelta(hours=2)


def test_radio_paradise_times_are_milliseconds() -> None:
    songs = sp.parse_radio_paradise(_fixture("radio_paradise.json"))
    assert songs[0].display() == "First Came the Thunder by Chuck Prophet"
    assert songs[0].started_at == datetime.fromtimestamp(1794105790.41, tz=UTC)


def test_live365_puts_the_current_track_first_and_drops_its_ad_breaks() -> None:
    songs = sp.parse_live365(_fixture("live365.json"))
    assert [s.display() for s in songs] == [
        "Tee Time featuring Blvd. East by Pat O'Donnell Group",
        "HDR Adamo 3 by Horn Driven Radio Promo",
        "Moanin' by Art Blakey",
    ]
    assert songs[0].is_current


def test_laut_fm_reads_the_nested_artist_and_tidies_the_title() -> None:
    songs = sp.parse_laut_fm(_fixture("laut_fm.json"))
    assert songs[0].display() == "Sidestep by World News"
    assert songs[0].started_at == datetime(2026, 11, 8, 2, 19, 26, tzinfo=UTC)


def test_triton_reads_properties_and_skips_a_row_with_no_title() -> None:
    songs = sp.parse_triton(_fixture("triton.xml"))
    assert [s.display() for s in songs] == ["Risk It All by Bruno Mars", "Trampoline by SHAED"]
    assert songs[0].started_at == datetime.fromtimestamp(1794105835.429, tz=UTC)
    assert sp.parse_triton("<nowplaying-info-list/>") == ()
    assert sp.parse_triton("not xml") == ()


def test_parsers_survive_junk() -> None:
    for parse in (sp.parse_kexp, sp.parse_radio_paradise, sp.parse_live365, sp.parse_laut_fm):
        assert parse("") == ()
        assert parse("[1, 2]") == ()
        assert parse("{}") == ()
    assert sp.parse_bbc('{"data": [{"segment_type": "music"}]}') == ()


def test_unsorted_rows_come_back_newest_first() -> None:
    payload = (
        '{"song": [{"title": "Old", "artist": "A", "play_time": 1000},'
        ' {"title": "New", "artist": "B", "play_time": 9000}]}'
    )
    assert [s.title for s in sp.parse_radio_paradise(payload)] == ["New", "Old"]


# --- the fetch loop ---------------------------------------------------------


def test_no_source_means_no_request(monkeypatch: pytest.MonkeyPatch) -> None:
    asked: list[str] = []
    monkeypatch.setattr(sp, "_fetch", asked.append)
    assert sp.fetch_station_playlist("https://example.com/stream.mp3") is None
    assert asked == []


def test_safe_mode_refuses_before_asking(monkeypatch: pytest.MonkeyPatch) -> None:
    asked: list[str] = []
    monkeypatch.setattr(sp, "_fetch", asked.append)
    with pytest.raises(sp.StationPlaylistError):
        sp.fetch_station_playlist("https://kexp.streamguys1.com/kexp160.aac", safe_mode=True)
    assert asked == []


def test_triton_falls_through_to_the_plain_mount(monkeypatch: pytest.MonkeyPatch) -> None:
    asked: list[str] = []
    empty = '<?xml version="1.0"?><nowplaying-info-list></nowplaying-info-list>'

    def fake(url: str) -> str:
        asked.append(url)
        return _fixture("triton.xml") if "mountName=977_HITS&" in url else empty

    monkeypatch.setattr(sp, "_fetch", fake)
    result = sp.fetch_station_playlist(
        "https://playerservices.streamtheworld.com/api/livestream-redirect/977_HITS_SC.mp3"
    )
    assert result is not None and len(result.songs) == 2
    assert len(asked) == 2


def test_an_empty_answer_is_a_playlist_with_no_songs(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sp, "_fetch", lambda _url: None)  # a 404
    result = sp.fetch_station_playlist("https://stream.laut.fm/eins")
    assert result is not None and result.songs == ()


def test_a_failure_everywhere_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(_url: str) -> str:
        raise sp.StationPlaylistError("offline")

    monkeypatch.setattr(sp, "_fetch", boom)
    with pytest.raises(sp.StationPlaylistError):
        sp.fetch_station_playlist("https://stream.laut.fm/eins")


def test_fetch_treats_404_as_no_list_and_refuses_plain_http(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def not_found(*_a: object, **_k: object) -> object:
        raise urllib.error.HTTPError("https://x", 404, "Not Found", None, None)  # type: ignore[arg-type]

    monkeypatch.setattr(sp.urllib.request, "urlopen", not_found)
    assert sp._fetch("https://api.laut.fm/station/x/last_songs") is None
    with pytest.raises(sp.StationPlaylistError):
        sp._fetch("http://api.laut.fm/station/x/last_songs")


def test_provenance_names_the_publisher_and_host() -> None:
    source = sp.match_source("https://kexp.streamguys1.com/kexp160.aac")
    assert source is not None
    line = source.provenance()
    assert "KEXP" in line and "not what Quill Radio heard" in line
    # Named as a word in the sentence, not checked as a URL.
    assert re.search(r"(?<![\w.-])api\.kexp\.org(?![\w-]|\.\w)", line)
