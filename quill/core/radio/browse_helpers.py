"""Pure helpers for the Browse Stations tree: iHeart letter grouping and the
NOAA Weather Radio state/station folder builders.

Originally extracted from ``browse_tree_dialog`` to keep that module under the
GATE-11 size budget, and it lived under ``quill/ui/radio/`` for that reason.
It was always wx-free and imported nothing but core, so when
:mod:`quill.core.radio.browse_sources` needed it the honest fix was to move it
here rather than have core reach up into the UI layer. No wx, no dialog state
-- just data.
"""

from __future__ import annotations

from collections.abc import Callable

from quill.core.radio import wxindex
from quill.core.radio.browse_nodes import BrowseNode
from quill.core.radio.models import RadioStation
from quill.core.radio.natural_order import natural_key
from quill.core.radio.wxindex_models import WxState, to_radio_station


def iheart_letter_groups(
    stations: list[RadioStation],
) -> list[tuple[str, list[RadioStation]]]:
    """Group iHeart stations into an alphabetised sub-directory.

    The original of :func:`letter_groups`, kept as a named convenience for its
    callers and now implemented *as* the generalisation -- two hand-maintained
    copies of the same bucketing is how three slightly different alphabets end
    up in one tree.
    """
    return letter_groups(stations, lambda station: station.name or "")


def letter_groups[T](rows: list[T], label: Callable[[T], str]) -> list[tuple[str, list[T]]]:
    """Group any labelled rows into a "0-9", A-Z, "#" sub-directory (pure).

    The generalisation of :func:`iheart_letter_groups`, which did this for
    stations only. Any long ranked or alphabetical list wants it -- 317 iHeart
    markets, a few hundred Radio Browser tags -- and duplicating the bucketing
    per source is how three slightly different alphabets end up in one tree.
    """
    buckets: dict[str, list[T]] = {}
    for row in rows:
        first = (label(row) or "").strip()[:1].upper()
        if first.isalpha():
            key = first
        elif first.isdigit():
            key = "0-9"
        else:
            key = "#"
        buckets.setdefault(key, []).append(row)

    def _order(key: str) -> tuple[int, str]:
        if key == "0-9":
            return (0, key)  # digits before letters
        if key == "#":
            return (2, key)  # symbols last
        return (1, key)

    return [
        (key, sorted(buckets[key], key=lambda row: natural_key(label(row))))
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


def row_label(child: BrowseNode) -> str:
    """The text of one row in the browse tree.

    The label, plus whatever the source wants said about the row *before* the
    listener commits to opening or playing it: how many things are inside a
    folder (where the source can say cheaply, so a wait can be judged before it
    is spent) and its note -- "opens in your browser", "from Wikidata", the
    licence on a Creative Commons track. One string, because a screen reader
    reads a row, not a set of columns.
    """
    parts = [child.label]
    if child.is_folder and child.child_count is not None:
        parts.append(f"{child.child_count}")
    if child.note:
        parts.append(child.note)
    return f"{parts[0]}  ({', '.join(parts[1:])})" if len(parts) > 1 else parts[0]
