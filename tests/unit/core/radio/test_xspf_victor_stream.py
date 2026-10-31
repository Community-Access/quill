"""XSPF as real devices write it (#1691).

The fixture is cut from the list attached to the issue: a HumanWare Victor
Stream export of radio reading services, header extension and all. Two of its
tracks have a title tag whose name was lost (``< >Name</ >``), which no XML
parser accepts, and two point at ``ootunes`` rather than at a stream. Before
#1691 the whole file imported as zero stations.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.radio.favorites import FavoriteStation
from quill.core.radio.models import RadioStation
from quill.core.radio.playlist_export import export_xspf
from quill.core.radio.playlist_formats import PlaylistFormatError, parse_xspf, sniff
from quill.core.radio.playlist_import import IMPORT_WILDCARD, read_playlist_file
from quill.core.radio.xspf import XspfEntry, parse_xspf_entries, stations_from_entries

_FIXTURE = Path(__file__).parent / "fixtures" / "victor_stream_reading_services.xspf"


def _fixture_text() -> str:
    return _FIXTURE.read_text(encoding="utf-8")


def test_victor_export_is_sniffed_as_xspf() -> None:
    assert sniff(_fixture_text(), url="Radio Reading Services.xspf.txt") == "xspf"


def test_victor_export_keeps_every_playable_track_despite_malformed_lines() -> None:
    stations = parse_xspf(_fixture_text())
    assert [s.stream_url for s in stations] == [
        "http://tektite.streamguys1.com:5210/live",
        "https://kpbs-rrs.streamguys1.com/kpbs-rrs",
        "https://streaming.wkar.msu.edu/rrs-64-mp3",
        "http://peridot.streamguys.com:5360/live.m3u",
        "http://ice23.securenetsystems.net/AMIAUDIO",
    ]


def test_a_title_whose_tag_name_was_lost_still_names_the_station() -> None:
    names = {s.stream_url: s.name for s in parse_xspf(_fixture_text())}
    assert names["https://streaming.wkar.msu.edu/rrs-64-mp3"].startswith(
        "WKAR Radio Reading Service"
    )
    assert names["http://peridot.streamguys.com:5360/live.m3u"].startswith("Sight Into Sound")


def test_victor_creator_web_address_becomes_the_home_page() -> None:
    by_url = {s.stream_url: s for s in parse_xspf(_fixture_text())}
    assert by_url["https://kpbs-rrs.streamguys1.com/kpbs-rrs"].homepage == (
        "https://www.kpbsreadingservice.org"
    )
    # A track with no creator has no home page, rather than a made-up one.
    assert by_url["http://ice23.securenetsystems.net/AMIAUDIO"].homepage == ""


def test_vendor_extension_text_is_never_taken_for_a_field() -> None:
    entries = parse_xspf_entries(_fixture_text())
    assert all("ootunes" not in e.title for e in entries)
    assert "Radio Reading service stations" not in [e.title for e in entries]


def test_ootunes_locations_are_read_but_not_offered_as_stations() -> None:
    entries = parse_xspf_entries(_fixture_text())
    assert sum(1 for e in entries if e.location == "ootunes") == 2
    assert all(s.stream_url.startswith("http") for s in parse_xspf(_fixture_text()))


def test_well_formed_xspf_reads_info_and_image_per_the_spec() -> None:
    text = """<?xml version="1.0" encoding="UTF-8"?>
<playlist version="1" xmlns="http://xspf.org/ns/0/"><trackList><track>
  <location>https://example.org/live</location>
  <annotation>Example Reading Service</annotation>
  <info>https://example.org/about</info>
  <image>https://example.org/logo.png</image>
</track></trackList></playlist>"""
    [station] = parse_xspf(text)
    assert station.name == "Example Reading Service"  # annotation, as no title
    assert station.homepage == "https://example.org/about"
    assert station.favicon == "https://example.org/logo.png"


def test_info_that_is_not_a_url_is_not_a_home_page() -> None:
    entry = XspfEntry(location="https://x.example/s", title="X", info="Blind Reading")
    [station] = stations_from_entries([entry])
    assert station.homepage == ""


def test_malformed_document_with_escaped_text_is_unescaped() -> None:
    text = (
        '<playlist xmlns="http://xspf.org/ns/0/"><trackList>'
        "<track><location>https://a.example/s?x=1&amp;y=2</location>"
        "<title>Tom &amp; Jerry</title></track>"
        "<track><broken attr></track></trackList></playlist>"
    )
    [station] = parse_xspf(text)
    assert station.stream_url == "https://a.example/s?x=1&y=2"
    assert station.name == "Tom & Jerry"


def test_hostile_xspf_is_still_refused_not_swept_by_the_fallback() -> None:
    hostile = (
        '<?xml version="1.0"?><!DOCTYPE lolz [<!ENTITY lol "lol">]>'
        "<playlist><trackList><track><location>https://a.example/s</location>"
        "<title>&lol;</title></track></trackList></playlist>"
    )
    with pytest.raises(PlaylistFormatError):
        parse_xspf(hostile)


def test_export_carries_home_page_and_logo_and_reads_back() -> None:
    station = RadioStation(
        name="Example",
        stream_url="https://example.org/live",
        homepage="https://example.org/",
        favicon="https://example.org/logo.png",
    )
    text = export_xspf([FavoriteStation(station=station)])
    assert "<info>https://example.org/</info>" in text
    [back] = parse_xspf(text)
    assert (back.name, back.stream_url, back.homepage, back.favicon) == (
        "Example",
        "https://example.org/live",
        "https://example.org/",
        "https://example.org/logo.png",
    )


def test_import_file_dialog_offers_xspf_saved_as_txt() -> None:
    assert "*.xspf.txt" in IMPORT_WILDCARD.split("|")[1]


def test_read_playlist_file_imports_a_victor_export_saved_as_txt(tmp_path: Path) -> None:
    path = tmp_path / "Radio Reading Services.xspf.txt"
    path.write_text(_fixture_text(), encoding="utf-8")
    assert len(read_playlist_file(path)) == 5
