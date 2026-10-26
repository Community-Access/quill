"""The two whole networks of 2026-10-25 (181.FM, laut.fm) and the new Networks
entries (181.FM, Big R Radio, 1.FM). No test touches the network."""

from __future__ import annotations

import pytest

from quill.core.radio import (
    browse_sources,
    browse_visibility,
    directory_cache,
    laut_fm,
    networks,
    one_eighty_one,
    search_sources,
)
from quill.core.radio.models import RadioStation

# What 181.FM's script really looks like, cut down: genres as keys, a bracket in
# a station's name, and a station cross-listed under two genres.
SCRIPT = (
    'var x=1;ft={Oldies:[{station:"Classic Hits 181",mount:"181-greatoldies",customImage:null,'
    'customUrl:null}],"80\'s Decade":[{station:"Awesome 80\'s",mount:"181-awesome80s",'
    'customImage:null,customUrl:null}],Pop:[{station:"Power 181 [E]",mount:"181-powerexplicit",'
    'customImage:null,customUrl:null},{station:"Awesome 80\'s",mount:"181-awesome80s",'
    'customImage:null,customUrl:null}],Christmas:[{station:"Christmas Classics",'
    'mount:"181-xtraditional",customImage:null,customUrl:null}]};'
)
INDEX = '<script defer="defer" src="/static/js/main.292511f4.js"></script>'


@pytest.fixture(autouse=True)
def _no_cache(monkeypatch):
    """Every test gets a fresh answer: the day-long cache is not consulted."""
    monkeypatch.setattr(
        directory_cache, "resolve", lambda key, fetch, **kw: (_safe(fetch, kw), None)
    )


def _safe(fetch, kw):
    try:
        return fetch()
    except Exception:  # noqa: BLE001 - resolve never raises; neither does this
        return kw.get("empty")


def _serve_181(monkeypatch, script: str = SCRIPT) -> list[str]:
    asked: list[str] = []

    def fetch(url: str) -> str:
        asked.append(url)
        return INDEX if url == one_eighty_one.HOMEPAGE else script

    monkeypatch.setattr(one_eighty_one, "_fetch", fetch)
    return asked


def test_the_whole_table_parses_even_with_a_bracket_in_a_name() -> None:
    table = dict(one_eighty_one.parse_catalog(SCRIPT))
    assert list(table) == ["Oldies", "80's Decade", "Pop", "Christmas"]
    assert table["Pop"] == [
        ("Power 181 [E]", "181-powerexplicit"),
        ("Awesome 80's", "181-awesome80s"),
    ]


def test_each_channel_once_with_every_genre_and_its_marks(monkeypatch) -> None:
    asked = _serve_181(monkeypatch)
    stations = {s.name: s for s in one_eighty_one.fetch_stations()}
    assert asked == [one_eighty_one.HOMEPAGE, "https://www.181.fm/static/js/main.292511f4.js"]
    assert len(stations) == 4
    awesome = stations["Awesome 80's"]
    assert awesome.stream_url == "https://listen.181fm.com/181-awesome80s_128k.mp3"
    assert awesome.tags[:2] == ("80's Decade", "Pop") and awesome.source == "181.FM"
    assert "Explicit" in stations["Power 181 (Explicit)"].tags
    assert "Seasonal" in stations["Christmas Classics"].tags


def test_the_branch_offers_all_stations_then_genres(monkeypatch) -> None:
    _serve_181(monkeypatch)
    nodes = browse_sources.browse("one81")
    assert [n.label for n in nodes] == [
        "All stations",
        "Oldies",
        "80's Decade",
        "Pop",
        "Christmas (seasonal)",
    ]
    assert len(browse_sources.browse("one81:All stations")) == 4
    pop = browse_sources.browse("one81:Pop")
    assert sorted(n.label for n in pop) == ["Awesome 80's", "Power 181 (Explicit)"]


def test_a_failed_or_empty_fetch_falls_back_to_the_snapshot(monkeypatch) -> None:
    from quill.core.radio.one_eighty_one_snapshot import SNAPSHOT

    def down(url: str) -> str:
        raise one_eighty_one.OneEightyOneError("down")

    monkeypatch.setattr(one_eighty_one, "_fetch", down)
    assert one_eighty_one.fetch_genres()[1:] == [genre for genre, _ in SNAPSHOT]
    _serve_181(monkeypatch, script="no table here")
    assert len(one_eighty_one.fetch_stations()) >= 80  # the snapshot, not nothing


def test_search_is_forgiving_and_the_network_name_lists_everything(monkeypatch) -> None:
    _serve_181(monkeypatch)
    assert [s.name for s in one_eighty_one.search_stations("awesome 80s")] == ["Awesome 80's"]
    assert len(one_eighty_one.search_stations("181.FM")) == 4
    assert [s.name for s in one_eighty_one.search_stations("christmas")] == ["Christmas Classics"]


def test_only_181fms_own_site_is_ever_fetched() -> None:
    with pytest.raises(one_eighty_one.OneEightyOneError):
        one_eighty_one._fetch("https://example.com/")


def test_both_networks_refuse_in_safe_mode() -> None:
    with pytest.raises(one_eighty_one.OneEightyOneError):
        one_eighty_one.fetch_genres(safe_mode=True)
    with pytest.raises(laut_fm.LautFmError):
        laut_fm.fetch_genres(safe_mode=True)


# -- laut.fm -----------------------------------------------------------------

LAUT_STATION = {
    "name": "justjazz",
    "display_name": "Just Jazz",
    "page_url": "https://laut.fm/justjazz",
    "stream_url": "https://justjazz.stream.laut.fm/justjazz",
    "genres": ["Jazz", "Smooth Jazz"],
    "active": True,
    "images": {"station_120x120": "https://assets.laut.fm/x?t=_120x120"},
}


def test_laut_genres_come_in_popularity_order_and_are_capped() -> None:
    payload = [{"name": f"g{i}", "score": float(i)} for i in range(100)]
    names = laut_fm.genres_from_json(payload, limit=3)
    assert names == ["g99", "g98", "g97"]


def test_a_laut_station_plays_and_an_inactive_one_is_left_out() -> None:
    station = laut_fm.station_from_json(LAUT_STATION)
    assert isinstance(station, RadioStation)
    assert station.name == "Just Jazz" and station.source == "laut.fm"
    assert station.tags == ("Jazz", "Smooth Jazz", "laut.fm")
    assert laut_fm.station_from_json({**LAUT_STATION, "active": False}) is None
    assert laut_fm.station_from_json({**LAUT_STATION, "stream_url": "http://x"}) is None


def test_laut_search_reads_the_grouped_reply(monkeypatch) -> None:
    reply = {
        "results": [
            {"items": [{"station": LAUT_STATION}]},
            {"items": [{"station": LAUT_STATION}]},  # the same station, matched twice
        ]
    }
    asked: list[str] = []
    monkeypatch.setattr(laut_fm, "_fetch", lambda path: asked.append(path) or reply)
    found = laut_fm.search_stations("jazz")
    assert [s.name for s in found] == ["Just Jazz"]
    assert asked == ["/search/stations?query=jazz&limit=50"]
    assert laut_fm.search_stations("laut.fm") == [] and laut_fm.search_stations("") == []


def test_the_laut_branch_lists_genres_then_stations(monkeypatch) -> None:
    def fetch(path: str) -> object:
        if path == "/genres":
            return [{"name": "Pop", "score": 3.0}, {"name": "Jazz", "score": 2.0}]
        assert path.startswith("/stations/genre/Jazz")
        return [LAUT_STATION]

    monkeypatch.setattr(laut_fm, "_fetch", fetch)
    assert [n.label for n in browse_sources.browse("lautfm")] == ["Pop", "Jazz"]
    assert [n.label for n in browse_sources.browse("lautfm:Jazz")] == ["Just Jazz"]


# -- the Networks entries, and reaching people who already chose sources ------


def test_a_name_prefix_keeps_only_the_network(monkeypatch) -> None:
    def search(query, **_kw):
        return [
            RadioStation("1.FM - Deep House Radio", "https://a"),
            RadioStation("011.FM - Cruise Control", "https://b"),
            RadioStation("1.FM - Deep House Radio", "https://a"),  # listed twice
            RadioStation("1.fm - Absolute 80s", "https://c"),
        ]

    monkeypatch.setattr(networks.radio_browser, "search_stations", search)
    kept = networks.network_stations(networks.get_network("1fm"))
    assert [s.name for s in kept] == ["1.FM - Deep House Radio", "1.fm - Absolute 80s"]


def test_the_new_networks_are_in_the_music_group() -> None:
    ids = {n.network_id for n in networks.networks_in_group(networks.GROUP_MUSIC)}
    assert {"181fm", "big-r-radio", "1fm"} <= ids


def test_the_branches_and_search_sources_reach_existing_profiles() -> None:
    assert ("one81", "lautfm") in browse_visibility.INTRODUCED_BY_EPOCH.values()
    assert browse_visibility.SOURCES_EPOCH == max(browse_visibility.INTRODUCED_BY_EPOCH)
    assert ("181fm", "lautfm") in search_sources.INTRODUCED_BY_EPOCH.values()
    assert search_sources.SEARCH_SOURCES_EPOCH == max(search_sources.INTRODUCED_BY_EPOCH)
    roots = dict(browse_sources.ROOT_SOURCES)
    assert roots["one81"] == "181.FM" and roots["lautfm"] == "laut.fm"
