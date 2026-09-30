"""Double Tap Live: the blind tech show's channel, one branch under ACB Media."""

from __future__ import annotations

from quill.core.radio import browse_sources, browse_visibility, double_tap
from quill.core.radio.browse_flat import LOCAL_SOURCES


def test_the_one_station_by_its_radio_co_address() -> None:
    stations = double_tap.double_tap_stations()
    assert len(stations) == 1
    station = stations[0]
    assert station.name == "Double Tap Live"
    assert station.stream_url == "https://s2.radio.co/s1eb3875b8/listen"
    assert station.homepage == "https://doubletaponair.com/live/"
    assert station.source == "Double Tap Live"
    assert "blind people talk tech" in station.notes
    assert station.codec == "MP3"


def test_the_branch_sits_directly_under_acb_media() -> None:
    ids = [source_id for source_id, _label in browse_sources.ROOT_SOURCES]
    assert ids.index("doubletap") == ids.index("acb") + 1
    assert ("doubletap", "Double Tap Live") in browse_sources.ROOT_SOURCES
    visible = [info.id for info in browse_visibility.BROWSE_SOURCES]
    assert visible.index("doubletap") == visible.index("acb") + 1
    info = next(i for i in browse_visibility.BROWSE_SOURCES if i.id == "doubletap")
    assert info.group == "Accessibility" and not info.network and info.default_on


def test_the_branch_needs_no_network_to_list() -> None:
    assert "doubletap" in LOCAL_SOURCES
    assert browse_sources.LOCAL_SOURCES is LOCAL_SOURCES
    nodes = browse_sources.browse("doubletap", safe_mode=True)
    assert len(nodes) == 1 and not nodes[0].is_folder
