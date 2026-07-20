"""Browse Stations -- Weather/NOAA source: wxindex State -> Station tree.

Characterizes the module-level fetch helpers directly (no wx.App needed,
mirroring test_browse_tree_dialog.py's approach), then drives
``_add_children`` against a fake tree to prove the "wx_states" folder and
"wx_state" station-leaf node shapes match the dialog's real genres/stations
conventions.
"""

from __future__ import annotations

from quill.core.radio import wxindex
from quill.core.radio.wxindex_models import WxState, WxStation
from quill.ui.radio.browse_tree_dialog import (
    _wx_playable_stations,
    _wx_state_folders,
)
from tests.unit.ui.test_browse_tree_dialog import _child_data, _dialog, _Node


def test_wx_state_folders_loads_states(monkeypatch) -> None:
    monkeypatch.setattr(wxindex, "list_states", lambda **_k: [WxState("virginia", "Virginia", 1)])
    states = _wx_state_folders(safe_mode=False)
    assert len(states) == 1
    assert states[0].name == "Virginia"
    assert states[0].slug == "virginia"


def test_wx_playable_stations_filters_to_stations_with_feeds(monkeypatch) -> None:
    monkeypatch.setattr(
        wxindex,
        "stations_for_state",
        lambda slug, **_k: [
            WxStation("KHB36", 162.55, feeds=("https://s/khb36",)),
            WxStation("KEC99", 162.40, feeds=()),  # no internet re-stream -- must be dropped
        ],
    )
    stations = _wx_playable_stations("virginia", safe_mode=False)
    assert len(stations) == 1
    assert stations[0].source == "NOAA Weather Radio"
    assert stations[0].stream_url == "https://s/khb36"


def test_add_children_wx_states_makes_state_folders() -> None:
    d = _dialog()
    root = _Node()
    d._tree.SetItemData(root, {"kind": "wx_states", "payload": None})
    d._add_children(root, "wx_states", [WxState("virginia", "Virginia", 2)])
    labels = [label for _n, label in d._tree.children[root]]
    assert labels == ["Virginia (2)"]
    data = _child_data(d, root)
    assert data[0]["kind"] == "wx_state"
    assert data[0]["payload"] == "virginia"


def test_add_children_wx_state_makes_station_leaves() -> None:
    from quill.core.radio.models import RadioStation

    d = _dialog()
    root = _Node()
    d._tree.SetItemData(root, {"kind": "wx_state", "payload": "virginia"})
    station = RadioStation(
        name="NOAA Weather Radio - KHB36 - 162.55 MHz",
        stream_url="https://s/khb36",
        source="NOAA Weather Radio",
    )
    d._add_children(root, "wx_state", [station])
    data = _child_data(d, root)
    assert data[0]["kind"] == "station"
    assert data[0]["station"].source == "NOAA Weather Radio"
