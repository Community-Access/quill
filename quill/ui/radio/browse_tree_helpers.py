"""Pure, wx-free helpers for the Browse Stations tree.

Extracted from ``browse_tree_dialog`` to keep that module under the GATE-11
size budget: the alphabetised iHeart letter grouping, and the NOAA Weather
Radio state/station folder builders. No wx, no dialog state -- just data.
"""

from __future__ import annotations

from quill.core.radio import wxindex
from quill.core.radio.models import RadioStation
from quill.core.radio.wxindex_models import WxState, to_radio_station


def iheart_letter_groups(
    stations: list[RadioStation],
) -> list[tuple[str, list[RadioStation]]]:
    """Group iHeart stations into an alphabetised sub-directory: a "0-9" bucket
    for digit-led names first, then A-Z folders (case-insensitive by first
    letter), then a "#" bucket for anything else. Stations inside each bucket
    are sorted by name, case-insensitively, so the whole list reads in order."""
    buckets: dict[str, list[RadioStation]] = {}
    for station in stations:
        first = (station.name or "").strip()[:1].upper()
        if first.isalpha():
            key = first
        elif first.isdigit():
            key = "0-9"
        else:
            key = "#"
        buckets.setdefault(key, []).append(station)

    def _order(key: str) -> tuple[int, str]:
        if key == "0-9":
            return (0, key)  # digits before letters
        if key == "#":
            return (2, key)  # symbols last
        return (1, key)

    return [
        (key, sorted(buckets[key], key=lambda s: (s.name or "").lower()))
        for key in sorted(buckets, key=_order)
    ]


def wx_state_folders(*, safe_mode: bool) -> list[WxState]:
    """States with a playable NOAA transmitter, counted from the SAME
    full-directory tier the station leaves come from -- so a folder's "(N items)"
    always matches what expanding it shows (never "9 items" then nothing).
    Most NWR transmitters have no internet re-stream and whole states have none,
    so feedless states are omitted; ``_add_children`` turns each into a
    "wx_state" node."""
    return wxindex.states_with_playable_feeds(safe_mode=safe_mode)


def wx_playable_stations(slug: str, *, safe_mode: bool) -> list[RadioStation]:
    """Station leaves for one State: its transmitters that have a playable
    internet re-stream feed. Sourced via ``wxindex.playable_stations_for_state``
    from the full-directory tier (bundled snapshot or the refreshed
    directory cache), which is the only tier that carries feed URLs -- the
    per-state live endpoint returns just a feed count, so building the tree
    from it would leave every state's folder empty online."""
    return [to_radio_station(s) for s in wxindex.playable_stations_for_state(slug)]
