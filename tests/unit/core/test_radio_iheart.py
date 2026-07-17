"""Tests for the iHeart sitemap directory client (pure parsing; no network)."""

from __future__ import annotations

import pytest

import quill.core.radio.iheart as iheart
from quill.core.radio.iheart import (
    IHeartError,
    extract_stream_url,
    livestations_sitemap_url,
    parse_livestations_sitemap,
    refuse_in_safe_mode,
)

_INDEX_XML = """<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <sitemap><loc>https://www.iheart.com/sitemap/2026-07-12T20-00-25-852Z/data/podcasts/podcasts-000.xml</loc></sitemap>
  <sitemap><loc>https://www.iheart.com/sitemap/2026-07-12T20-00-25-852Z/data/livestations/livestations-000-000.xml</loc></sitemap>
</sitemapindex>
"""

_LIVESTATIONS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://www.iheart.com/live/delilah-4846/</loc></url>
  <url><loc>https://www.iheart.com/live/973-kbco-2804/</loc></url>
  <url><loc>https://www.iheart.com/news/not-a-station/</loc></url>
</urlset>
"""


def test_refuse_in_safe_mode() -> None:
    with pytest.raises(IHeartError):
        refuse_in_safe_mode(True)
    refuse_in_safe_mode(False)  # no raise


def test_livestations_sitemap_url_picks_the_livestations_entry() -> None:
    url = livestations_sitemap_url(_INDEX_XML)
    assert url is not None and url.endswith("livestations/livestations-000-000.xml")


def test_livestations_sitemap_url_none_when_absent() -> None:
    assert livestations_sitemap_url("<sitemapindex></sitemapindex>") is None
    assert livestations_sitemap_url("not xml") is None


def test_parse_livestations_sitemap_reads_stations_and_ids() -> None:
    stations = parse_livestations_sitemap(_LIVESTATIONS_XML)
    by_id = {s.station_id: s for s in stations}
    assert set(by_id) == {"4846", "2804"}  # the /news/ URL is skipped
    assert by_id["4846"].slug == "delilah"
    assert by_id["4846"].name == "Delilah"
    assert by_id["4846"].page_url == "https://www.iheart.com/live/delilah-4846/"
    assert by_id["2804"].name == "973 Kbco"


def test_extract_stream_url_prefers_revma_hls() -> None:
    html = (
        '<script>var cfg={"streams":{"secure_hls_stream":'
        '"https://stream.revma.ihrhls.com/zc4846/hls.m3u8"}};</script>'
    )
    assert extract_stream_url(html) == "https://stream.revma.ihrhls.com/zc4846/hls.m3u8"


def test_extract_stream_url_handles_escaped_json_slashes() -> None:
    html = (
        r'{"secure_hls_stream":'
        r'"https:\/\/stream.revma.ihrhls.com\/zc4846\/hls.m3u8"}'
    )
    assert extract_stream_url(html) == "https://stream.revma.ihrhls.com/zc4846/hls.m3u8"


def test_extract_stream_url_falls_back_to_streamtheworld_redirect() -> None:
    html = (
        "no revma here, but "
        '"https://playerservices.streamtheworld.com/api/livestream-redirect/WHTZFM.m3u8"'
    )
    assert extract_stream_url(html) == (
        "https://playerservices.streamtheworld.com/api/livestream-redirect/WHTZFM.m3u8"
    )


def test_extract_stream_url_empty_when_none() -> None:
    assert extract_stream_url("<html>no stream here</html>") == ""


def test_fetch_station_index_is_two_gets(monkeypatch) -> None:
    calls: list[str] = []

    def fake_fetch(url: str) -> str:
        calls.append(url)
        if url == "https://www.iheart.com/sitemap.xml":
            return _INDEX_XML
        return _LIVESTATIONS_XML

    monkeypatch.setattr(iheart, "_fetch", fake_fetch)
    stations = iheart.fetch_station_index()
    assert len(stations) == 2
    assert len(calls) == 2  # index + the one livestations sub-sitemap
    assert calls[0] == "https://www.iheart.com/sitemap.xml"


def test_fetch_station_index_empty_when_no_livestations(monkeypatch) -> None:
    monkeypatch.setattr(iheart, "_fetch", lambda url: "<sitemapindex></sitemapindex>")
    assert iheart.fetch_station_index() == []


def test_resolve_stream_extracts_from_the_page(monkeypatch) -> None:
    monkeypatch.setattr(
        iheart,
        "_fetch",
        lambda url: '"https://stream.revma.ihrhls.com/zc4846/hls.m3u8"',
    )
    assert iheart.resolve_stream("https://www.iheart.com/live/delilah-4846/") == (
        "https://stream.revma.ihrhls.com/zc4846/hls.m3u8"
    )


def test_to_radio_station_carries_source_and_id() -> None:
    stations = parse_livestations_sitemap(_LIVESTATIONS_XML)
    delilah = next(s for s in stations if s.station_id == "4846")
    station = iheart.to_radio_station(delilah, "https://stream.revma.ihrhls.com/zc4846/hls.m3u8")
    assert station.source == "iHeart"
    assert station.station_uuid == "iheart:4846"
    assert station.homepage == "https://www.iheart.com/live/delilah-4846/"


def test_fetch_station_index_refused_in_safe_mode(monkeypatch) -> None:
    monkeypatch.setattr(
        iheart, "_fetch", lambda url: (_ for _ in ()).throw(AssertionError("no net"))
    )
    with pytest.raises(IHeartError):
        iheart.fetch_station_index(safe_mode=True)
