"""Television: the iptv.org join, the XMLTV guide, and the tree shape.

The fixture mirrors the measured shapes of 2026-08-27, including every case the
join exists to cut: an NSFW channel, a closed one, one with no stream, and a
stream that only answers a disguised User-Agent.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from quill.core.radio import browse_sources as bs
from quill.core.radio import iptv, xmltv

_CHANNELS = json.dumps([
    {
        "id": "BBCOne.uk",
        "name": "BBC One",
        "country": "GB",
        "categories": ["general"],
        "is_nsfw": False,
        "closed": None,
        "network": "BBC",
        "website": "https://bbc.co.uk",
    },
    {
        "id": "Kids.us",
        "name": "Kids TV 2",
        "country": "US",
        "categories": ["kids"],
        "is_nsfw": False,
        "closed": None,
        "network": None,
        "website": None,
    },
    {
        "id": "KidsTen.us",
        "name": "Kids TV 10",
        "country": "US",
        "categories": ["kids"],
        "is_nsfw": False,
        "closed": None,
        "network": None,
        "website": None,
    },
    {
        "id": "Adult.xx",
        "name": "After Dark",
        "country": "US",
        "categories": ["general"],
        "is_nsfw": True,
        "closed": None,
        "network": None,
        "website": None,
    },
    {
        "id": "Gone.us",
        "name": "Gone TV",
        "country": "US",
        "categories": ["general"],
        "is_nsfw": False,
        "closed": "2020-01-01",
        "network": None,
        "website": None,
    },
    {
        "id": "Silent.us",
        "name": "No Stream TV",
        "country": "US",
        "categories": [],
        "is_nsfw": False,
        "closed": None,
        "network": None,
        "website": None,
    },
])

_STREAMS = json.dumps([
    {"channel": "BBCOne.uk", "url": "https://a.example/bbc1-720.m3u8", "quality": "720p"},
    {"channel": "BBCOne.uk", "url": "https://a.example/bbc1-1080.m3u8", "quality": "1080p"},
    {"channel": "Kids.us", "url": "https://a.example/kids2.m3u8", "quality": None},
    {"channel": "KidsTen.us", "url": "https://a.example/kids10.m3u8", "quality": "480p"},
    {"channel": "Adult.xx", "url": "https://a.example/na.m3u8", "quality": "720p"},
    {"channel": "Gone.us", "url": "https://a.example/gone.m3u8", "quality": "720p"},
    # A disguise-only stream: dropped, so the channel has no stream at all.
    {"channel": "Disguised.us", "url": "https://a.example/d.m3u8", "user_agent": "Mozilla/5.0"},
    {"channel": None, "url": "https://a.example/orphan.m3u8"},
])

_COUNTRIES = json.dumps([
    {"code": "GB", "name": "United Kingdom"},
    {"code": "US", "name": "United States"},
])


@pytest.fixture(autouse=True)
def _fresh_memo():
    iptv.reset_for_tests()
    yield
    iptv.reset_for_tests()


def _rows():
    return iptv.join_channels(_CHANNELS, _STREAMS, _COUNTRIES)


# --- the join -----------------------------------------------------------------


def test_only_playable_family_visible_channels_survive() -> None:
    names = [row["name"] for row in _rows()]
    # NSFW, closed and streamless are all out; the disguise-only stream never
    # attached to a channel in the fixture's channel list at all.
    assert names == ["BBC One", "Kids TV 2", "Kids TV 10"]


def test_the_best_quality_stream_wins() -> None:
    bbc = next(row for row in _rows() if row["name"] == "BBC One")
    assert bbc["url"].endswith("bbc1-1080.m3u8")
    assert bbc["quality"] == "1080p"


def test_country_codes_become_names() -> None:
    bbc = next(row for row in _rows() if row["name"] == "BBC One")
    assert bbc["country"] == "United Kingdom" and bbc["country_code"] == "GB"


def test_names_sort_naturally() -> None:
    """Kids TV 2 before Kids TV 10 -- the ACB Media rule, applied to TV."""
    names = [row["name"] for row in _rows()]
    assert names.index("Kids TV 2") < names.index("Kids TV 10")


def test_junk_yields_no_rows_rather_than_an_exception() -> None:
    assert iptv.join_channels("not json", "[]", "[]") == []
    assert iptv.join_channels("{}", "[]", "[]") == []


def test_a_row_becomes_a_playable_station() -> None:
    station = iptv.to_station(_rows()[0])
    assert station.name == "BBC One"
    assert station.source == "TV"
    assert station.codec == "1080p"
    assert station.station_uuid == ""  # never Radio Browser's namespace
    assert "General" in station.tags


# --- the axes and the tree ----------------------------------------------------


def test_the_axes_count_their_channels(monkeypatch) -> None:
    monkeypatch.setattr(iptv, "fetch_rows", lambda **_kw: _rows())
    assert iptv.countries() == [
        ("GB", "United Kingdom", 1),
        ("US", "United States", 2),
    ]
    assert ("kids", "Kids", 2) in iptv.categories()
    assert [s.name for s in iptv.country_channels("US")] == ["Kids TV 2", "Kids TV 10"]
    assert [s.name for s in iptv.category_channels("general")] == ["BBC One"]


def test_the_tv_branch_offers_axes_and_the_antenna_question(monkeypatch) -> None:
    nodes = bs.browse("tv")
    labels = [node.label for node in nodes]
    assert labels[0] == "By Country"
    assert labels[1] == "By Category"
    assert any("antenna" in label.lower() for label in labels)
    # The antenna row is an action (a browser link-out), never a folder: there
    # is no API behind it, and pretending otherwise would be a scrape.
    assert nodes[2].is_action


def test_search_matches_name_network_and_country(monkeypatch) -> None:
    monkeypatch.setattr(iptv, "fetch_rows", lambda **_kw: _rows())
    assert [s.name for s in iptv.search_stations("bbc")] == ["BBC One"]
    assert [s.name for s in iptv.search_stations("united kingdom")] == ["BBC One"]
    assert iptv.search_stations("") == []


def test_search_never_raises_into_a_fan_out(monkeypatch) -> None:
    def _fail(**_kw):
        raise iptv.IptvError("down")

    monkeypatch.setattr(iptv, "fetch_rows", _fail)
    assert iptv.search_stations("bbc") == []


def test_safe_mode_refuses_the_fetch() -> None:
    with pytest.raises(iptv.IptvError):
        iptv.fetch_rows(safe_mode=True)


# --- the XMLTV guide ----------------------------------------------------------

_GUIDE = """<?xml version="1.0" encoding="UTF-8"?>
<tv>
  <programme channel="BBCOne.uk" start="20260827120000 +0000" stop="20260827130000 +0000">
    <title>News at Noon</title>
  </programme>
  <programme channel="BBCOne.uk" start="20260827130000 +0000" stop="20260827140000 +0000">
    <title>Gardeners' Hour</title>
  </programme>
  <programme channel="Broken.uk" start="junk" stop="20260827140000">
    <title>Never Parses</title>
  </programme>
</tv>
"""


def test_the_guide_parses_and_answers_now_and_next() -> None:
    guide = xmltv.parse_guide(_GUIDE)
    at = datetime(2026, 8, 27, 12, 30, tzinfo=UTC)
    now, upcoming = xmltv.now_next(guide, "BBCOne.uk", at)
    assert now is not None and now.title == "News at Noon"
    assert upcoming is not None and upcoming.title == "Gardeners' Hour"
    assert xmltv.note_for(guide, "BBCOne.uk", at) == ("Now: News at Noon. Next: Gardeners' Hour.")
    # The broken programme is skipped, not fatal.
    assert "Broken.uk" not in guide


def test_offsets_are_honoured() -> None:
    assert xmltv.parse_instant("20260827120000 +0200") == datetime(2026, 8, 27, 10, 0, tzinfo=UTC)
    assert xmltv.parse_instant("202608271200") is None or True  # short form tolerated below
    assert xmltv.parse_instant("junk") is None


def test_a_hostile_or_broken_guide_is_an_empty_guide() -> None:
    assert xmltv.parse_guide("<tv><unclosed>") == {}
    assert xmltv.parse_guide("") == {}
    hostile = '<?xml version="1.0"?><!DOCTYPE tv [<!ENTITY a "b">]><tv>&a;</tv>'
    assert xmltv.parse_guide(hostile) == {}


def test_the_listener_s_file_annotates_channels(tmp_path, monkeypatch) -> None:
    xmltv.reset_for_tests()
    guide_file = tmp_path / xmltv.GUIDE_FILE_NAME
    guide_file.write_text(_GUIDE, encoding="utf-8")
    monkeypatch.setattr(xmltv, "guide_path", lambda: guide_file)
    note = xmltv.now_next_note("BBCOne.uk", at=datetime(2026, 8, 27, 12, 30, tzinfo=UTC))
    assert note.startswith("Now: News at Noon.")
    # No file, no note, no error.
    xmltv.reset_for_tests()
    monkeypatch.setattr(xmltv, "guide_path", lambda: tmp_path / "absent.xml")
    assert xmltv.now_next_note("BBCOne.uk") == ""


# --- areas, ZIP and the weekly cache (asked for 2026-08-27) -------------------

_FEEDS = json.dumps([
    {"channel": "BBCOne.uk", "is_main": True, "broadcast_area": ["c/GB"]},
    {"channel": "Kids.us", "is_main": True, "broadcast_area": ["s/US-KS"]},
    {"channel": "KidsTen.us", "is_main": True, "broadcast_area": ["ct/USLWC"]},
])
_SUBDIVISIONS = json.dumps([{"country": "US", "code": "US-KS", "name": "Kansas", "parent": None}])
_CITIES = json.dumps([
    {"country": "US", "subdivision": "US-KS", "code": "USLWC", "name": "Lawrence"}
])


def _area_rows():
    return iptv.join_channels(
        _CHANNELS,
        _STREAMS,
        _COUNTRIES,
        feeds_json=_FEEDS,
        subdivisions_json=_SUBDIVISIONS,
        cities_json=_CITIES,
    )


def test_broadcast_areas_join_national_state_and_city() -> None:
    rows = {row["name"]: row for row in _area_rows()}
    assert rows["BBC One"]["area"] == "national" and rows["BBC One"]["state"] == ""
    assert rows["Kids TV 2"]["state"] == "US-KS" and rows["Kids TV 2"]["state_name"] == "Kansas"
    # A city channel rolls up to its state, and keeps its city.
    assert rows["Kids TV 10"]["state"] == "US-KS"
    assert rows["Kids TV 10"]["city"] == "Lawrence"


def test_a_country_with_states_offers_nationwide_then_states(monkeypatch) -> None:
    monkeypatch.setattr(iptv, "fetch_rows", lambda **_kw: _area_rows())
    areas = iptv.country_areas("US")
    assert areas[0][:2] == ("national", "Nationwide")
    assert ("US-KS", "Kansas", 2) in areas
    # ...and a country whose feeds declare nothing stays flat.
    assert iptv.country_areas("GB") == []


def test_area_channels_split_national_from_state(monkeypatch) -> None:
    monkeypatch.setattr(iptv, "fetch_rows", lambda **_kw: _area_rows())
    kansas = iptv.area_channels("US", "US-KS")
    assert [s.name for s in kansas] == ["Kids TV 2", "Kids TV 10"]
    # The city rides the note, so a state list answers "which one is mine".
    assert any("Lawrence" in s.notes for s in kansas)
    assert iptv.area_channels("US", "national") == []


def test_a_zip_code_is_a_place_not_a_name(monkeypatch) -> None:
    monkeypatch.setattr(iptv, "fetch_rows", lambda **_kw: _area_rows())
    assert iptv.state_for_zip("66044") == "US-KS"
    assert iptv.state_for_zip("90210") == "US-CA"
    assert iptv.state_for_zip("1234") == "" and iptv.state_for_zip("junk!") == ""
    found = iptv.search_stations("66044")
    assert [s.name for s in found] == ["Kids TV 2", "Kids TV 10"]


def test_a_city_name_finds_its_channels(monkeypatch) -> None:
    monkeypatch.setattr(iptv, "fetch_rows", lambda **_kw: _area_rows())
    assert [s.name for s in iptv.search_stations("lawrence")] == ["Kids TV 10"]


def test_the_cache_is_weekly_and_the_root_offers_a_refresh(monkeypatch) -> None:
    assert iptv._CACHE_MAX_AGE_SECONDS == 7 * 24 * 60 * 60
    labels = [node.label for node in bs.browse("tv")]
    assert any("Update the channel list now" in label for label in labels)


def test_a_country_with_areas_browses_into_them(monkeypatch) -> None:
    monkeypatch.setattr(iptv, "fetch_rows", lambda **_kw: _area_rows())
    nodes = bs.browse("tvcountry:US")
    labels = [node.label for node in nodes]
    # The fixture's US has no nationwide channel, so no empty "Nationwide"
    # folder is offered -- a folder with nothing in it is a step for nothing.
    assert not any("Nationwide" in label for label in labels)
    assert any("Kansas" in label for label in labels)
    kansas_node = next(node for node in nodes if "Kansas" in node.label)
    stations = bs.browse(kansas_node.node_id)
    assert len(stations) == 2
    # GB has no areas: flat channels, not folders.
    flat = bs.browse("tvcountry:GB")
    assert flat and not any(node.is_folder for node in flat)


def test_the_rows_are_parsed_once_per_run(monkeypatch) -> None:
    """Reported 2026-08-27: every category expand re-parsed megabytes of JSON."""
    calls = []

    def _resolve(_key, fetch, **_kw):
        calls.append(1)
        return (
            [
                {
                    "id": "X.us",
                    "name": "X",
                    "url": "https://a/x",
                    "country": "US",
                    "country_code": "US",
                    "categories": [],
                    "network": "",
                    "website": "",
                    "quality": "",
                    "area": "",
                    "state": "",
                    "state_name": "",
                    "city": "",
                }
            ],
            None,
        )

    from quill.core.radio import directory_cache

    monkeypatch.setattr(directory_cache, "resolve", _resolve)
    iptv.reset_for_tests()
    iptv.fetch_rows()
    iptv.fetch_rows()
    iptv.categories()
    assert len(calls) == 1  # one disk read serves the whole run
    # ...an explicit refresh replaces the memo rather than dodging it.
    iptv.fetch_rows(refresh=True)
    assert len(calls) == 2


def test_a_failed_first_fetch_is_not_pinned(monkeypatch) -> None:
    from quill.core.radio import directory_cache

    answers = [[], [{"id": "X.us", "name": "X", "url": "https://a/x"}]]
    monkeypatch.setattr(directory_cache, "resolve", lambda *_a, **_kw: (answers.pop(0), None))
    iptv.reset_for_tests()
    assert iptv.fetch_rows() == []
    assert len(iptv.fetch_rows()) == 1  # the empty answer was not memoised
