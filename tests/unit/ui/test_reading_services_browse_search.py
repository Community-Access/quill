"""Radio Reading Services: the Browse "stations" loader and the Search blend.

Mirrors the wxindex (Task 7/Browse-Weather-NOAA) test shape: no wx.App and no
network -- ``reading_services.list_reading_services`` is monkeypatched, and
the Browse loader / Search helper are exercised as plain functions.
"""

from __future__ import annotations

from quill.core.radio import browse_sources, reading_services
from quill.core.radio.directory_search import reading_services_search_stations
from quill.core.radio.models import RadioStation


def _rs(name: str, *, tags: tuple[str, ...] = (), country: str = "") -> RadioStation:
    return RadioStation(
        name=name,
        stream_url=f"https://stream/{name}",
        country=country,
        tags=tags,
        source="Radio Reading Service",
    )


def test_browse_reading_services_returns_playable_leaves(monkeypatch) -> None:
    expected = [_rs("WRBH 88.3 FM Reading Radio")]
    monkeypatch.setattr(
        reading_services, "list_reading_services", lambda *, safe_mode=False: expected
    )
    nodes = browse_sources.browse("reading")
    assert [n.station for n in nodes] == expected
    assert all(n.is_leaf for n in nodes)


def test_browse_reading_services_passes_safe_mode(monkeypatch) -> None:
    seen: dict[str, bool] = {}

    def fake_list(*, safe_mode: bool = False) -> list[RadioStation]:
        seen["safe_mode"] = safe_mode
        return []

    monkeypatch.setattr(reading_services, "list_reading_services", fake_list)
    browse_sources.browse("reading", safe_mode=True)
    assert seen["safe_mode"] is True


def test_reading_services_search_matches_name(monkeypatch) -> None:
    monkeypatch.setattr(
        reading_services,
        "list_reading_services",
        lambda *, safe_mode=False: [
            _rs("WRBH 88.3 FM Reading Radio"),
            _rs("KPBS Radio Reading Service"),
        ],
    )
    stations = reading_services_search_stations("WRBH")
    assert len(stations) == 1
    assert stations[0].name == "WRBH 88.3 FM Reading Radio"
    assert stations[0].source == "Radio Reading Service"


def test_reading_services_search_matches_tags_and_state(monkeypatch) -> None:
    monkeypatch.setattr(
        reading_services,
        "list_reading_services",
        lambda *, safe_mode=False: [
            _rs("Down East Radio Reading Service", tags=("reading service", "North Carolina")),
            _rs("WRBH 88.3 FM Reading Radio", tags=("reading service", "Louisiana")),
        ],
    )
    stations = reading_services_search_stations("louisiana")
    assert [s.name for s in stations] == ["WRBH 88.3 FM Reading Radio"]


def test_reading_services_search_drops_stations_without_stream(monkeypatch) -> None:
    no_stream = RadioStation(name="WRBH ghost", stream_url="", source="Radio Reading Service")
    monkeypatch.setattr(
        reading_services, "list_reading_services", lambda *, safe_mode=False: [no_stream]
    )
    assert reading_services_search_stations("WRBH") == []


def test_reading_services_search_empty_query_returns_nothing(monkeypatch) -> None:
    monkeypatch.setattr(
        reading_services,
        "list_reading_services",
        lambda *, safe_mode=False: (_ for _ in ()).throw(AssertionError("no call")),
    )
    assert reading_services_search_stations("   ") == []
