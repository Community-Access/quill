"""#36: Altitude Sports Radio (KKSE 92.5 FM / 950 AM, Denver) from recorded pages.

John Gassman added https://www.altitudesportsradio.com/ to Quill Radio and was
told the stream was not supported. What the site really plays: two Triton
Digital web players, ``player.listenlive.co/20551`` (92.5 FM, mount ``KKSEFM``)
and ``/48751`` (950 AM, ``KKSEAM``), each an ordinary StreamTheWorld MP3 and
HE-AAC stream with no token and no DRM. Three things stood in the way, and each
has a test here:

* the FM player has no station logo, and the logo was the only place the
  resolver looked for a callsign, so FM resolved to nothing;
* the player links Triton's own help article, whose URL contains ``/stream``,
  and that article was the FIRST candidate a scan offered;
* MP3 and AAC mounts of one station counted as two choices, so neither stream
  recovery nor anything else would call a Triton player unambiguous.

Every page and provisioning answer is a recorded fixture (2026-10-15); nothing
here touches the network.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import quill.core.radio.link_finder as lf
import quill.core.radio.triton as triton
from quill.core.radio import address_kind, recovery
from quill.core.radio.link_finder import PageStreamCandidate, scan_page_for_streams
from quill.core.radio.stream_pick import durable_url, pick_stream, station_key

_FIXTURES = Path(__file__).parent / "fixtures" / "altitude"
_PAGES = {
    "www.altitudesportsradio.com": "home.html",
    "player.listenlive.co/20551": "listenlive_20551.html",
    "player.listenlive.co/48751": "listenlive_48751.html",
}


def _read(name: str) -> str:
    return (_FIXTURES / name).read_text(encoding="utf-8")


@pytest.fixture
def recorded(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Serve the recorded pages and provisioning answers; return what was fetched."""
    fetched: list[str] = []

    def fetch_html(url: str) -> str:
        fetched.append(url)
        key = url.split("://", 1)[-1].rstrip("/")
        if key.endswith("/en"):
            key = key[:-3]
        if key not in _PAGES:
            raise lf.LinkFinderError(f"not recorded: {url}")
        return _read(_PAGES[key])

    monkeypatch.setattr(lf, "_fetch_html", fetch_html)
    monkeypatch.setattr(triton, "_fetch_api", lambda callsign: _read(f"triton_{callsign}.xml"))
    return fetched


def test_the_fm_player_has_no_logo_and_still_names_its_mount() -> None:
    fm = _read("listenlive_20551.html")
    assert "config_station_logo" not in fm
    assert triton.callsign_from_page("https://player.listenlive.co/20551", fm) == "KKSEFM"
    am = _read("listenlive_48751.html")
    assert triton.callsign_from_page("https://player.listenlive.co/48751", am) == "KKSEAM"


def test_a_listenlive_player_address_is_a_page_not_a_stream() -> None:
    assert triton.is_player_page_url("http://player.listenlive.co/20551")
    assert triton.is_player_page_url("https://player.listenlive.co/20551/en")
    # A file the player page happens to host is not the page.
    assert not triton.is_player_page_url("https://player.listenlive.co/live/kmgl.mp3")
    assert not triton.is_player_page_url("https://18233.live.streamtheworld.com/KKSEFM")


def test_the_station_home_page_finds_both_stations_and_nothing_else(recorded) -> None:
    result = scan_page_for_streams("https://www.altitudesportsradio.com/")

    keys = {station_key(c.url) for c in result.candidates}
    assert keys == {"stw:KKSEFM", "stw:KKSEAM"}
    urls = " ".join(c.url for c in result.candidates)
    assert "force.com" not in urls  # Triton's help article is not a stream
    assert "listenlive.co" not in urls  # nor is a player page
    # Each player is fetched once, though the home page links it twice.
    assert sorted(u for u in recorded if "listenlive" in u) == [
        "http://player.listenlive.co/20551",
        "http://player.listenlive.co/48751",
    ]


def test_the_fm_player_page_resolves_without_fetching_itself_again(recorded) -> None:
    result = scan_page_for_streams("http://player.listenlive.co/20551")

    assert [c.label for c in result.candidates] == ["KKSEFMAAC", "KKSEFM"]
    assert recorded == ["https://player.listenlive.co/20551"]


def test_one_stations_mp3_and_aac_mounts_are_one_answer_and_mp3_wins(recorded) -> None:
    result = scan_page_for_streams("http://player.listenlive.co/20551")

    pick = pick_stream(result.candidates)

    assert pick.found
    assert pick.url.endswith("/KKSEFM")
    assert durable_url(pick.url) == (
        "https://playerservices.streamtheworld.com/api/livestream-redirect/KKSEFM.mp3"
    )


def test_the_home_page_is_a_choice_between_two_stations(recorded) -> None:
    result = scan_page_for_streams("https://www.altitudesportsradio.com/")

    pick = pick_stream(result.candidates)

    assert not pick.found
    assert pick.stations == ("KKSEFM", "KKSEAM")


def test_recovery_now_trusts_a_triton_players_two_mounts() -> None:
    candidates = [
        PageStreamCandidate("https://16613.live.streamtheworld.com/KKSEFMAAC", "AAC"),
        PageStreamCandidate("https://18373.live.streamtheworld.com/KKSEFM", "MP3"),
    ]
    confident = recovery._confident_candidate(candidates)
    assert confident is not None and confident.url.endswith("/KKSEFM")


def test_durable_url_leaves_everything_but_a_stw_mp3_server_alone() -> None:
    aac = "https://16613.live.streamtheworld.com/KKSEFMAAC"
    other = "https://ice1.securenetsystems.net/WWOJ"
    assert durable_url(aac) == aac
    assert durable_url(other) == other


@pytest.mark.parametrize(
    ("url", "page"),
    [
        ("https://www.altitudesportsradio.com/", True),
        ("https://www.altitudesportsradio.com", True),
        ("http://player.listenlive.co/20551", True),
        ("https://example.com/listen.html", True),
        ("https://www.iheart.com/live/kkse-1234/", True),
        # Shoutcast streams from its root, on a port of its own.
        ("http://203.0.113.5:8000/", False),
        ("https://stream.example.com/live.mp3", False),
        ("https://ice1.example.com/stream", False),
        ("https://playerservices.streamtheworld.com/api/livestream-redirect/KKSEFM.mp3", False),
        ("not a url", False),
    ],
)
def test_what_add_custom_station_treats_as_a_web_page(url: str, page: bool) -> None:
    assert address_kind.is_web_page_address(url) is page
