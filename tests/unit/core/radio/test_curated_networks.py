"""The curated networks snapshot (from BlindRadio, MIT) and its place in Browse.

No test touches the network: the snapshot is a file in the package, and the
Radio Browser query path is replaced with one that fails loudly if reached.
"""

from __future__ import annotations

import json

import pytest

from quill.core.radio import browse_sources, curated_networks, networks


def _doc() -> dict:
    return json.loads(curated_networks.snapshot_path().read_text(encoding="utf-8"))


@pytest.fixture
def no_radio_browser(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*_a, **_kw):
        raise AssertionError("a curated network must not query Radio Browser")

    monkeypatch.setattr(networks.radio_browser, "search_stations", refuse)


def test_the_snapshot_loads_and_has_no_problems() -> None:
    assert curated_networks.problems(_doc()) == []
    loaded = curated_networks.networks()
    assert len(loaded) == len(_doc()["networks"]), "no network was dropped as malformed"
    assert sum(len(n.channels) for n in loaded) > 400


def test_every_address_is_https_or_says_why_not() -> None:
    for network in curated_networks.networks():
        for channel in network.channels:
            if channel.url.startswith("http://"):
                assert channel.http_reason, f"{network.network_id}/{channel.channel_id}"
            else:
                assert channel.url.startswith("https://")


def test_ids_are_unique_and_every_network_says_where_it_came_from() -> None:
    ids = [n.network_id for n in curated_networks.networks()]
    assert len(ids) == len(set(ids))
    for network in curated_networks.networks():
        channel_ids = [c.channel_id for c in network.channels]
        assert len(channel_ids) == len(set(channel_ids)), network.network_id
        assert network.origin, network.network_id


def test_the_mit_notice_travels_with_the_data() -> None:
    doc = _doc()
    assert "BlindRadio by serrebidev" in doc["attribution"]
    assert doc["license"].startswith("MIT License")
    assert "Copyright (c) 2026 serrebidev" in doc["license"]
    beside = curated_networks.snapshot_path().with_name("radio_networks.LICENSE.txt")
    assert "Copyright (c) 2026 serrebidev" in beside.read_text(encoding="utf-8")


def test_no_seasonal_bauer_or_retired_channel_is_carried() -> None:
    names = " ".join(
        f"{n.display_name} {c.name} {c.url}".casefold()
        for n in curated_networks.networks()
        for c in n.channels
    )
    for word in ("christmas", "xmas", "weihnacht", "halloween"):
        assert word not in names
    # Bauer withdrew its brands from third-party apps; SomaFM is retired here.
    for word in ("absolute radio", "kiss fm", "magic radio", "planet rock", "somafm"):
        assert word not in names


@pytest.mark.parametrize(
    "problem, mutate",
    [
        ("appears twice", lambda d: d["networks"].append(dict(d["networks"][0]))),
        (
            "plain HTTP with no reason",
            lambda d: d["networks"][0]["channels"][0].update(url="http://example.com/x"),
        ),
        ("no origin", lambda d: d["networks"][0].update(origin="")),
        ("MIT notice", lambda d: d.update(license="")),
    ],
)
def test_problems_names_what_is_wrong(problem: str, mutate) -> None:
    doc = _doc()
    mutate(doc)
    assert any(problem in line for line in curated_networks.problems(doc))


def test_a_channel_is_a_station_with_a_stable_identity() -> None:
    wfmu = curated_networks.get("wfmu")
    assert wfmu is not None
    station = curated_networks.to_station(wfmu, wfmu.channels[0])
    assert station.station_uuid == f"net:wfmu:{wfmu.channels[0].channel_id}"
    assert station.source == "WFMU" and station.stream_url.startswith("https://")
    assert station.codec == "AAC" and station.bitrate_kbps == 128


def test_a_replacing_network_takes_the_place_and_id_of_the_query() -> None:
    catalog = networks.catalog()
    ids = [n.network_id for n in catalog]
    assert ids.count("bbc") == 1, "the BBC is shown once, not twice"
    bbc = networks.get_network("bbc")
    assert bbc is not None and bbc.curated and bbc.group == networks.GROUP_PUBLIC
    # Same place in the list as the query it replaced.
    assert ids.index("bbc") == [n.network_id for n in networks.NETWORKS].index("bbc")
    for replaced in curated_networks.replaced_ids():
        assert networks.get_network(replaced).curated  # type: ignore[union-attr]


def test_merge_rules_are_deliberate() -> None:
    query = (
        networks.Network("bbc", "BBC", networks.GROUP_PUBLIC, query="BBC"),
        networks.Network("npr", "NPR", networks.GROUP_US_NEWS, tag="npr"),
    )
    channel = (curated_networks.CuratedChannel("one", "One", "https://a/1"),)
    curated = (
        curated_networks.CuratedNetwork(
            "bbc", "BBC", networks.GROUP_PUBLIC, channel, replaces="bbc"
        ),
        # Collides with a query it does not say it replaces: dropped, not doubled.
        curated_networks.CuratedNetwork("npr", "NPR again", networks.GROUP_US_NEWS, channel),
        curated_networks.CuratedNetwork("wfmu", "WFMU", networks.GROUP_US_PUBLIC, channel),
        # An unknown group lands in Music rather than vanishing.
        curated_networks.CuratedNetwork("odd", "Odd", "Nowhere", channel),
    )
    merged = networks.merge(query, curated)
    assert [(n.network_id, n.curated) for n in merged] == [
        ("bbc", True),
        ("npr", False),
        ("wfmu", True),
        ("odd", True),
    ]
    assert merged[-1].group == networks.GROUP_MUSIC
    assert merged[0].channel_count == 1


def test_the_browse_tree_shows_a_curated_network_and_plays_its_channels(
    no_radio_browser: None,
) -> None:
    groups = [node.label for node in browse_sources.browse("networks")]
    assert networks.GROUP_COMMERCIAL in groups and networks.GROUP_CHRISTIAN in groups
    members = browse_sources.browse(f"networkgroup:{networks.GROUP_US_PUBLIC}")
    wfmu = next(node for node in members if node.node_id == "network:wfmu")
    assert wfmu.child_count == len(curated_networks.get("wfmu").channels)  # type: ignore[union-attr]
    rows = browse_sources.browse("network:wfmu")
    assert rows and all(row.is_leaf and row.station is not None for row in rows)
    assert [row.label for row in rows] == sorted((row.label for row in rows), key=str.casefold)
    assert all(row.station.station_uuid.startswith("net:wfmu:") for row in rows)  # type: ignore[union-attr]


def test_a_query_network_still_queries(monkeypatch: pytest.MonkeyPatch) -> None:
    asked: list[str] = []
    monkeypatch.setattr(
        networks.radio_browser,
        "search_stations",
        lambda query="", **_kw: asked.append(query) or [],
    )
    networks.network_stations(networks.get_network("npr"))  # type: ignore[arg-type]
    assert asked == [""]  # NPR is a tag query


def test_search_finds_a_channel_by_its_name_and_network() -> None:
    found = curated_networks.search_stations("radio 4")
    assert any(s.source == "BBC" for s in found)
    assert curated_networks.search_stations("") == []
    wfmu = curated_networks.search_stations("wfmu drummer")
    assert [s.name for s in wfmu] == ["Give the Drummer Radio"]


def test_a_missing_snapshot_leaves_the_query_networks(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(curated_networks, "snapshot_path", lambda: tmp_path / "gone.json")
    curated_networks.networks.cache_clear()
    try:
        assert curated_networks.networks() == ()
        assert networks.get_network("bbc") is not None and not networks.get_network("bbc").curated  # type: ignore[union-attr]
    finally:
        curated_networks.networks.cache_clear()
