"""Unit tests for the curated Networks directory (quill.core.radio.networks)."""

from __future__ import annotations

import pytest

from quill.core.radio import networks
from quill.core.radio.models import RadioStation


def test_catalog_integrity() -> None:
    ids = [n.network_id for n in networks.NETWORKS]
    assert len(ids) == len(set(ids)), "network ids must be unique"
    for n in networks.NETWORKS:
        assert n.display_name.strip()
        assert n.group in networks.GROUP_ORDER, f"{n.network_id} has an unknown group"
        # every network must carry at least one query dimension
        assert n.query or n.tag or n.country, f"{n.network_id} has no query/tag/country"


def test_cbs_news_radio_is_excluded() -> None:
    # CBS News Radio is ending 2026-05-22; it must not be a network node.
    names = " ".join(n.display_name.lower() for n in networks.NETWORKS)
    ids = " ".join(n.network_id for n in networks.NETWORKS)
    assert "cbs" not in names and "cbs" not in ids


def test_groups_are_ordered_and_present() -> None:
    present = networks.groups()
    # returned groups are a subset of GROUP_ORDER, in that order, and non-empty
    assert present
    assert list(present) == [g for g in networks.GROUP_ORDER if g in present]
    for group in present:
        assert networks.networks_in_group(group), f"{group} claims presence but has no networks"


def test_get_network_roundtrip() -> None:
    assert networks.get_network("bbc") is not None
    assert networks.get_network("nope") is None
    assert networks.get_network("npr").tag == "npr"  # NPR uses a tag, not a name query


def test_syndicators_carry_an_honest_note() -> None:
    for n in networks.networks_in_group(networks.GROUP_SYNDICATORS):
        assert n.note.strip(), (
            f"{n.network_id} is a syndicator and must explain it has no single stream"
        )


def test_network_stations_uses_radio_browser_query(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_search(query="", *, tag="", country="", limit=80, offset=0, safe_mode=False):
        captured.update(query=query, tag=tag, country=country, limit=limit, safe_mode=safe_mode)
        return [
            RadioStation(name="BBC Radio 4", stream_url="http://example/r4", source="Radio Browser")
        ]

    monkeypatch.setattr(networks.radio_browser, "search_stations", fake_search)
    bbc = networks.get_network("bbc")
    result = networks.network_stations(bbc, safe_mode=True)
    assert [s.name for s in result] == ["BBC Radio 4"]
    assert captured == {
        "query": bbc.query,
        "tag": bbc.tag,
        "country": bbc.country,
        "limit": bbc.limit,
        "safe_mode": True,
    }
