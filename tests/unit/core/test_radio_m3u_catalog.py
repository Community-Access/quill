from __future__ import annotations

import json

import pytest

import quill.core.radio.m3u_catalog as m3u
from quill.core.radio.m3u_catalog import (
    CATEGORY_LABEL,
    M3uCatalogError,
    fetch_genre_stations,
    fetch_genres,
    genre_display,
    genre_raw_url,
    parse_genre_list,
    refuse_in_safe_mode,
    stations_from_m3u,
)

_SAMPLE_M3U = """#EXTM3U
#EXTINF:-1 group-title="JAZZ Radio", Smooth Jazz Florida - 128 kbit/s
http://144.217.158.59:5120/stream/1/
#EXTINF:-1 group-title="JAZZ Radio", Jazz Cafe - 128 kbit/s
http://radio.wanderingsheep.tv:8000/jazzcafe
"""


def _tree(paths_types: list[tuple[str, str]]) -> str:
    return json.dumps({"tree": [{"path": p, "type": t} for p, t in paths_types]})


def test_parse_genre_list_keeps_root_genre_m3u_only() -> None:
    tree = _tree([
        ("jazz.m3u", "blob"),
        ("acid_jazz.m3u", "blob"),
        ("---everything-full.m3u", "blob"),   # aggregate: starts with '-'
        ("---sorted.m3u", "blob"),            # aggregate
        ("+checked+", "tree"),                # a directory
        ("deso.fm/something.m3u", "blob"),    # inside a subdir
        ("README.md", "blob"),                # not an .m3u
    ])
    assert parse_genre_list(tree) == ["acid_jazz", "jazz"]  # sorted, aggregates/subdirs dropped


def test_parse_genre_list_tolerates_junk() -> None:
    assert parse_genre_list("not json") == []
    assert parse_genre_list(json.dumps({"nope": 1})) == []
    assert parse_genre_list(json.dumps({"tree": "bad"})) == []


def test_genre_display_humanizes_slug() -> None:
    assert genre_display("acid_jazz") == "Acid Jazz"
    assert genre_display("80s") == "80s"
    assert genre_display("hip-hop") == "Hip Hop"


def test_genre_raw_url_points_at_raw_github() -> None:
    assert genre_raw_url("jazz") == (
        "https://raw.githubusercontent.com/junguler/m3u-radio-music-playlists/main/jazz.m3u"
    )


def test_stations_from_m3u_tags_source_and_genre() -> None:
    stations = stations_from_m3u(_SAMPLE_M3U, "jazz")
    assert [s.name for s in stations] == [
        "Smooth Jazz Florida - 128 kbit/s",
        "Jazz Cafe - 128 kbit/s",
    ]
    assert all(s.source == CATEGORY_LABEL for s in stations)
    assert all("Jazz" in s.tags for s in stations)
    assert stations[0].stream_url == "http://144.217.158.59:5120/stream/1/"


def test_fetch_genre_stations_uses_fetch(monkeypatch) -> None:
    monkeypatch.setattr(m3u, "_fetch", lambda url: _SAMPLE_M3U)
    stations = fetch_genre_stations("jazz")
    assert len(stations) == 2
    assert stations[0].source == CATEGORY_LABEL


def test_fetch_genre_stations_empty_slug_returns_nothing() -> None:
    assert fetch_genre_stations("   ") == []


def test_fetch_genres_parses_live_then_falls_back(monkeypatch) -> None:
    monkeypatch.setattr(
        m3u, "_fetch", lambda url: _tree([("jazz.m3u", "blob"), ("rock.m3u", "blob")])
    )
    assert fetch_genres() == ["jazz", "rock"]

    def boom(url):
        raise M3uCatalogError("offline")

    monkeypatch.setattr(m3u, "_fetch", boom)
    fallback = fetch_genres()
    assert "jazz" in fallback and len(fallback) > 5  # bundled fallback list


def test_safe_mode_refuses() -> None:
    with pytest.raises(M3uCatalogError):
        refuse_in_safe_mode(True)
    with pytest.raises(M3uCatalogError):
        fetch_genres(safe_mode=True)
    with pytest.raises(M3uCatalogError):
        fetch_genre_stations("jazz", safe_mode=True)
