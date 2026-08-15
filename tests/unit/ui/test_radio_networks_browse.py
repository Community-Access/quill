"""The Networks branch is wired into the Browse Stations tree."""

from __future__ import annotations

from quill.core.radio import browse_sources, networks
from quill.core.radio.models import RadioStation


def test_networks_is_a_top_level_source() -> None:
    assert ("networks", "Networks") in browse_sources.ROOT_SOURCES


def test_networks_expands_group_then_network_then_stations(monkeypatch) -> None:
    groups = browse_sources.browse("networks")
    assert groups and all(node.is_folder for node in groups)

    members = browse_sources.browse(groups[0].node_id)
    assert members and all(node.is_folder for node in members)

    monkeypatch.setattr(
        networks,
        "network_stations",
        lambda network, **_kw: [RadioStation(name="BBC Radio 4", stream_url="https://a/1")],
    )
    stations = browse_sources.browse(members[0].node_id)
    assert [node.label for node in stations] == ["BBC Radio 4"]
    assert stations[0].is_leaf


def test_a_syndicator_says_it_is_an_affiliate_search() -> None:
    # The note is the honesty: there is no single stream behind these.
    noted = [
        node
        for group in browse_sources.browse("networks")
        for node in browse_sources.browse(group.node_id)
        if node.note
    ]
    assert noted, "at least one network is labelled with its note"


def test_networks_needs_no_network_of_its_own() -> None:
    # The folder structure is a local catalog; only opening a network queries
    # Radio Browser, so Safe Mode can leave the branch browsable.
    assert not browse_sources.needs_network("networks")


def test_catalog_has_groups_to_show() -> None:
    assert networks.groups()
    for group in networks.groups():
        assert networks.networks_in_group(group)
