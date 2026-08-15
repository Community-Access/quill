"""Weather/NOAA browse helpers -- state folders and their playable stations.

The helpers moved to ``quill/core/radio/browse_helpers.py`` with the rest of the
browse plumbing; the State -> Station tree they feed is asserted in
``tests/unit/core/radio/test_browse_sources.py``.
"""

from __future__ import annotations

from quill.core.radio import wxindex
from quill.core.radio.browse_helpers import wx_playable_stations, wx_state_folders
from quill.core.radio.wxindex_models import WxState, WxStation


def test_wx_state_folders_count_from_the_directory_tier_not_the_live_count(monkeypatch) -> None:
    # The folder count must come from the same full-directory tier as the leaves,
    # so a folder's "(N items)" always matches what expanding it shows -- the NOAA
    # regression was a live /v1/states count that expanded to nothing.
    called: list[bool] = []

    def fake(*, safe_mode: bool):
        called.append(safe_mode)
        return [WxState(name="Arizona", slug="AZ", stations_with_feeds=3)]

    monkeypatch.setattr(wxindex, "states_with_playable_feeds", fake)
    states = wx_state_folders(safe_mode=False)
    assert [s.name for s in states] == ["Arizona"]
    assert states[0].stations_with_feeds == 3
    assert called == [False]


def test_wx_playable_stations_converts_to_radio_stations(monkeypatch) -> None:
    monkeypatch.setattr(
        wxindex,
        "playable_stations_for_state",
        lambda slug: [
            WxStation(
                callsign="KEC61",
                frequency_mhz=162.55,
                name="Phoenix",
                feeds=("https://a/1",),
            )
        ],
    )
    stations = wx_playable_stations("AZ", safe_mode=False)
    assert len(stations) == 1
    assert stations[0].stream_url == "https://a/1"
