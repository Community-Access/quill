"""The Networks branch is wired into the Browse Stations tree."""

from __future__ import annotations

from quill.core.radio import networks
from quill.ui.radio import browse_tree_dialog as btd


def test_networks_is_a_top_level_source() -> None:
    labels = [label for label, _kind, _payload in btd._SOURCES]
    kinds = {kind for _label, kind, _payload in btd._SOURCES}
    assert "Networks" in labels
    assert "networks" in kinds


def test_network_kinds_are_expandable_and_the_leaf_fetches_stations() -> None:
    assert {"networks", "network-group", "network"} <= set(btd._EXPANDABLE)
    # a "network" node's fetch returns playable stations, so it is a leaf kind
    assert "network" in btd._LEAF_KINDS


def test_catalog_has_groups_to_show() -> None:
    # The browse branch expands to these group folders; make sure there are some.
    assert networks.groups()
    for group in networks.groups():
        assert networks.networks_in_group(group)
