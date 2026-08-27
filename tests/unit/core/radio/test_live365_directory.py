"""Tests for the Live365 directory (the sitemap half) -- pure, no network.

The transform half of ``live365.py`` has its own tests in
``tests/unit/core/test_live365.py`` and is untouched by this; what is asserted
here is that a published sitemap becomes a browsable, playable station list, and
that the odd entries in a real sitemap (the blog, a trailing slash, a slug that
contains its own ``a1234`` token) do not become stations.
"""

from __future__ import annotations

import pytest

from quill.core.radio import browse_sources as bs
from quill.core.radio import live365

_SITEMAP = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://live365.com/</loc></url>
  <url><loc>https://live365.com/blog/some-post</loc></url>
  <url><loc>https://live365.com/station/AIFM-Pop-a43216</loc></url>
  <url><loc>https://live365.com/station/24-7-Christmas-Music-Radio-Station-a29903/</loc></url>
  <url><loc>https://live365.com/station/KHYI-The-Range-a25891</loc></url>
  <url><loc>https://live365.com/station/Radio-a1234-Classics-a55555</loc></url>
  <url><loc>https://live365.com/station/AIFM-Pop-a43216</loc></url>
</urlset>
"""


def test_only_station_pages_become_stations() -> None:
    stations = live365.parse_sitemap(_SITEMAP)
    # Five station URLs, one of them repeated: four stations.
    assert len(stations) == 4


def test_the_id_is_taken_from_the_end_not_from_inside_the_slug() -> None:
    stations = {station.name: station for station in live365.parse_sitemap(_SITEMAP)}
    tricky = stations["Radio a1234 Classics"]
    assert tricky.stream_url == "https://streaming.live365.com/a55555"


def test_a_trailing_slash_does_not_hide_a_station() -> None:
    names = [station.name for station in live365.parse_sitemap(_SITEMAP)]
    assert "24 7 Christmas Music Radio Station" in names


def test_the_name_keeps_the_broadcaster_s_own_casing() -> None:
    """Title-casing would turn a callsign into a word: KHYI, not Khyi."""
    names = [station.name for station in live365.parse_sitemap(_SITEMAP)]
    assert "KHYI The Range" in names
    assert "AIFM Pop" in names


def test_the_stream_url_is_the_one_the_transform_already_built() -> None:
    station = next(s for s in live365.parse_sitemap(_SITEMAP) if s.name == "AIFM Pop")
    assert station.stream_url == live365.live365_stream_url("a43216")
    assert station.homepage == "https://live365.com/station/AIFM-Pop-a43216"
    # Not Radio Browser's namespace; see the note in station_from_entry.
    assert station.station_uuid == ""


def test_stations_come_back_sorted_by_name() -> None:
    names = [station.name for station in live365.parse_sitemap(_SITEMAP)]
    assert names == sorted(names, key=str.casefold)


def test_a_junk_document_yields_no_stations() -> None:
    for payload in ("", "<urlset></urlset>", "not xml at all"):
        assert live365.parse_sitemap(payload) == []


def test_letters_bucket_numbers_and_symbols_together() -> None:
    assert live365.letter_of("KHYI The Range") == "K"
    assert live365.letter_of("24 7 Christmas") == "#"
    assert live365.letter_of("") == "#"
    assert live365.letter_of("радио") == "#"
    assert live365.letters()[0] == "#"
    assert live365.letters()[1:] == [chr(c) for c in range(ord("A"), ord("Z") + 1)]


def test_safe_mode_refuses_the_directory_but_not_the_transform() -> None:
    with pytest.raises(live365.Live365Error):
        live365.fetch_stations(safe_mode=True)
    # The pure transform never leaves the machine, so it keeps working.
    assert live365.normalize_live365("https://player.live365.com/a25891") == (
        "https://streaming.live365.com/a25891"
    )


def test_search_returns_nothing_in_safe_mode_rather_than_raising() -> None:
    assert live365.search_stations("range", safe_mode=True) == []


def test_an_empty_query_makes_no_request(monkeypatch) -> None:
    def _boom(*_args, **_kwargs):  # pragma: no cover - must not be reached
        raise AssertionError("an empty query must not reach the network")

    monkeypatch.setattr(live365, "fetch_stations", _boom)
    assert live365.search_stations("") == []


def test_the_branch_offers_letters_with_counts_then_stations(monkeypatch) -> None:
    stations = live365.parse_sitemap(_SITEMAP)
    monkeypatch.setattr(live365, "fetch_stations", lambda **_kw: stations)
    monkeypatch.setattr(
        live365,
        "fetch_letter",
        lambda letter, **_kw: [s for s in stations if live365.letter_of(s.name) == letter],
    )
    letters = bs.browse("live365")
    labels = [node.label for node in letters]
    # Only letters that actually have stations, in reading order.
    assert labels == ["#", "A", "K", "R"]
    assert all(node.is_folder for node in letters)
    assert bs.browse("live365:#")[0].label.startswith("24 7")


def test_a_failing_sitemap_is_an_empty_branch_not_an_exception(monkeypatch) -> None:
    def _fail(**_kw):
        raise live365.Live365Error("down")

    monkeypatch.setattr(live365, "fetch_stations", _fail)
    assert bs.browse("live365") == []
