"""Tests for M3U/M3U8 playlist parsing and duplicate partitioning (station import)."""

from __future__ import annotations

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
