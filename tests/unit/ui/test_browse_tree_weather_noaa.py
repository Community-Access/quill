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


def test_wx_state_folders_count_from_the_directory_tier_not_the_live_count(monkeypatch) -> None:
    # The folder count must come from the same full-directory tier as the leaves,
    # so a folder's "(N items)" always matches what expanding it shows -- the NOAA
    # regression was a live /v1/states count that expanded to nothing.
    monkeypatch.setattr(
        wxindex,
        "_directory_stations",
        lambda **_k: [
            WxStation("KHB1", 162.55, state="VA", feeds=("u1",)),
            WxStation("KHB2", 162.40, state="VA", feeds=("u2",)),
            WxStation("KHB3", 162.45, state="AS", feeds=()),  # no playable feed -> AS hidden
        ],
    )
    monkeypatch.setattr(
        wxindex, "list_states", lambda **_k: [WxState("VA", "Virginia", stations_with_feeds=99)]
    )
    states = _wx_state_folders(safe_mode=False)
    assert [s.name for s in states] == ["Virginia"]  # feedless state hidden
    assert states[0].stations_with_feeds == 2  # from the directory tier, not the live 99


def test_wx_playable_stations_uses_feed_aware_resolver(monkeypatch) -> None:
    # Browse must source playable stations from the full-directory tier (which
    # carries feeds), not the feedless per-state live endpoint.
    monkeypatch.setattr(
        wxindex,
        "playable_stations_for_state",
        lambda slug, **_k: [WxStation("KHB36", 162.55, feeds=("https://s/khb36",))],
    )
    stations = _wx_playable_stations("VA", safe_mode=False)
    assert len(stations) == 1
    assert stations[0].source == "NOAA Weather Radio"
    assert stations[0].stream_url == "https://s/khb36"


def test_add_children_wx_states_labels_with_feed_count() -> None:
    d = _dialog()
    root = _Node()
    d._tree.SetItemData(root, {"kind": "wx_states", "payload": None})
    d._add_children(
        root, "wx_states", [WxState("VA", "Virginia", station_count=10, stations_with_feeds=2)]
    )
    labels = [label for _n, label in d._tree.children[root]]
    assert labels == ["Virginia (2)"]  # the playable-feed count, not the transmitter total
    data = _child_data(d, root)
    assert data[0]["kind"] == "wx_state"
    assert data[0]["payload"] == "VA"


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
