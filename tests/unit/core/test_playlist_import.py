"""Tests for M3U/M3U8 playlist parsing and duplicate partitioning (station import)."""

from __future__ import annotations

import pytest

from quill.core.radio.models import RadioStation
from quill.core.radio.playlist_import import (
    dedup_key,
    parse_m3u,
    split_new_and_duplicates,
)

_EXTENDED = """#EXTM3U
#EXTINF:-1,Jazz FM
https://stream.example.com/jazz
#EXTINF:-1, Classic Rock
http://cdn.example.net/rock.mp3
"""


def test_parse_extended_m3u_uses_extinf_names() -> None:
    stations = parse_m3u(_EXTENDED)
    assert [(s.name, s.stream_url) for s in stations] == [
        ("Jazz FM", "https://stream.example.com/jazz"),
        ("Classic Rock", "http://cdn.example.net/rock.mp3"),
    ]


def test_parse_plain_m3u_names_from_host() -> None:
    stations = parse_m3u("https://www.wjib.example.org/stream\nhttps://ice.example.com:8000/x")
    assert [s.name for s in stations] == ["wjib.example.org", "ice.example.com"]


def test_parse_ignores_comments_blanks_and_non_http() -> None:
    text = "#EXTM3U\n\n# a note\nfile:///local/path.mp3\nrtsp://x/y\nhttps://ok.example.com/s\n"
    stations = parse_m3u(text)
    assert [s.stream_url for s in stations] == ["https://ok.example.com/s"]


def test_parse_collapses_duplicate_urls_first_name_wins() -> None:
    text = "#EXTINF:-1,First\nhttps://a.example.com/s\n#EXTINF:-1,Second\nhttps://a.example.com/s\n"
    stations = parse_m3u(text)
    assert len(stations) == 1
    assert stations[0].name == "First"


def test_split_new_and_duplicates_against_existing_keys() -> None:
    parsed = [
        RadioStation(name="New", stream_url="https://new.example.com/s"),
        RadioStation(name="Dup", stream_url="https://have.example.com/s"),
    ]
    existing = {"https://have.example.com/s"}
    new, dup = split_new_and_duplicates(parsed, existing)
    assert [s.name for s in new] == ["New"]
    assert [s.name for s in dup] == ["Dup"]


def test_dedup_key_prefers_uuid_then_url() -> None:
    assert dedup_key(RadioStation(name="x", stream_url="u", station_uuid="uuid-1")) == "uuid-1"
    assert dedup_key(RadioStation(name="x", stream_url="u")) == "u"


# --- Import Stations reads every supported format (2026-09-25) ---------------
#
# The importer read only M3U while PLS, XSPF and ASX parsers sat unused in
# playlist_formats. These drive the import entry point with each format.

_PLS = "[playlist]\nFile1=http://pls.example.com/a\nTitle1=PLS One\nNumberOfEntries=1\n"
_XSPF = (
    '<?xml version="1.0"?><playlist version="1" xmlns="http://xspf.org/ns/0/">'
    "<trackList><track><location>https://xspf.example.com/b</location>"
    "<title>XSPF Two</title></track></trackList></playlist>"
)
_ASX = '<asx version="3.0"><entry><title>ASX Three</title><ref href="http://asx.example.com/c"/></entry></asx>'


@pytest.mark.parametrize(
    ("text", "filename", "expected"),
    [
        (_EXTENDED, "list.m3u", ("Jazz FM", "https://stream.example.com/jazz")),
        (_PLS, "listen.pls", ("PLS One", "http://pls.example.com/a")),
        (_XSPF, "xiph.xspf", ("XSPF Two", "https://xspf.example.com/b")),
        (_ASX, "reading.asx", ("ASX Three", "http://asx.example.com/c")),
        # Body outranks a wrong extension: a PLS saved as .m3u still imports.
        (_PLS, "misnamed.m3u", ("PLS One", "http://pls.example.com/a")),
        # A headerless plain M3U with an unfamiliar name is still a playlist.
        (
            "https://a.example.com/s\nhttps://b.example.com/t\n",
            "stations.txt",
            ("a.example.com", "https://a.example.com/s"),
        ),
    ],
)
def test_parse_playlist_file_reads_every_import_format(text, filename, expected) -> None:
    from quill.core.radio.playlist_import import parse_playlist_file

    stations = parse_playlist_file(text, filename)
    assert stations and (stations[0].name, stations[0].stream_url) == expected


def test_parse_playlist_file_never_imports_an_hls_manifest() -> None:
    from quill.core.radio.playlist_import import parse_playlist_file

    hls = "#EXTM3U\n#EXT-X-TARGETDURATION:6\n#EXTINF:6,\nhttps://cdn.example.com/seg1.ts\n"
    assert parse_playlist_file(hls, "live.m3u8") == []


def test_read_playlist_file_refuses_hostile_xml(tmp_path) -> None:
    from quill.core.radio.playlist_import import PlaylistFormatError, read_playlist_file

    bomb = tmp_path / "bomb.xspf"
    bomb.write_bytes(
        b'<?xml version="1.0"?><!DOCTYPE p [<!ENTITY a "aaaa">]>'
        b"<playlist><trackList><track><location>&a;</location></track></trackList></playlist>"
    )
    with pytest.raises(PlaylistFormatError):
        read_playlist_file(bomb)


def test_read_playlist_file_reads_a_pls_from_disk(tmp_path) -> None:
    from quill.core.radio.playlist_import import read_playlist_file

    path = tmp_path / "Listen Live.pls"
    path.write_bytes(_PLS.encode("utf-8"))
    assert [s.stream_url for s in read_playlist_file(path)] == ["http://pls.example.com/a"]


def test_import_wildcard_offers_all_four_formats() -> None:
    from quill.core.radio.playlist_import import IMPORT_WILDCARD

    first_filter = IMPORT_WILDCARD.split("|")[1]
    for pattern in ("*.m3u", "*.m3u8", "*.pls", "*.xspf", "*.asx"):
        assert pattern in first_filter
