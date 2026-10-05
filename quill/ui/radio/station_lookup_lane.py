"""The "what is known about it" lane of a station search.

Find Stations and Search All Sources both ask this for the stations they cannot
find by name: the ones you tagged, and the flagship stations of the teams the
query names (see :mod:`quill.core.radio.station_lookup` for the matching). It
lives beside the searches rather than inside them because both callers are at
their GATE-11 ceilings, and because the one thing it adds -- turning a call
sign into a playable row -- is the same for both.

**Where a flagship's stream comes from.** The local station catalog first: it
is a snapshot of the whole directory on this machine, answers in a millisecond
and works offline and in Safe Mode. Only when the catalog has nothing does it
ask Radio Browser -- the same name search Find Stations already sends, never a
new address -- and only a handful of times per search, so "MLB" cannot turn
into thirty requests.

wx-free and run on the search worker: it must never touch wx and never raise.
"""

from __future__ import annotations

from typing import Any

from quill.core.radio.models import RadioStation

__all__ = ["NETWORK_LOOKUPS", "favorites_of", "lane_rows", "prepend_to_federated"]

#: Radio Browser questions one search may ask for flagships the catalog lacked.
NETWORK_LOOKUPS = 6


def favorites_of(host: Any) -> Any:
    """The favorites store a search or a tag edit should use, or ``None``."""
    for name in ("_favorites", "_radio_favorites", "_store"):
        store = getattr(host, name, None)
        if store is not None and hasattr(store, "favorites"):
            return store
    owner = getattr(host, "_host", None)
    return getattr(owner, "_radio_favorites", None) if owner is not None else None


def _source_on(host: Any, source_id: str) -> bool:
    check = getattr(host, "_source_on", None)
    try:
        return bool(check(source_id)) if callable(check) else True
    except Exception:  # noqa: BLE001 - an unknown source is an enabled one
        return True


def lane_rows(
    host: Any, query: str, *, safe_mode: bool, network: bool = True
) -> list[RadioStation]:
    """Tagged and flagship rows for *query*. ``[]`` on any failure.

    *network* False keeps it to the catalog -- the fast first pass of Search
    All Sources promises an answer from this machine alone.
    """
    text = str(query or "").strip()
    if not text:
        return []
    try:
        from quill.core.paths import app_data_dir
        from quill.core.radio import station_lookup
        from quill.core.radio.station_tags import load_tag_store
        from quill.ui.radio.catalog_search import catalog_search_rows

        catalog = getattr(host, "_catalog", None)
        budget = [NETWORK_LOOKUPS if network and _source_on(host, "radio_browser") else 0]

        def find(wanted: str) -> list[RadioStation]:
            rows = catalog_search_rows(catalog, wanted, limit=15)
            if rows or safe_mode or budget[0] <= 0:
                return rows
            budget[0] -= 1
            from quill.core.radio import radio_browser

            return radio_browser.search_stations(wanted, limit=15, safe_mode=safe_mode)

        return station_lookup.lane_rows(
            text,
            favorites=favorites_of(host),
            store=load_tag_store(app_data_dir()),
            find=find,
        )
    except Exception:  # noqa: BLE001 - this lane only ever adds to a search
        return []


def prepend_to_federated(
    host: Any, query: str, found: Any, *, safe_mode: bool, network: bool = True
) -> Any:
    """Put the lane's rows at the top of a Search All Sources answer.

    Each becomes an ordinary playable browse row whose note is the reason it
    was found, so it reads "carries the Detroit Tigers" where a directory row
    would read its source. Rows already in the answer are not repeated.
    """
    try:
        from quill.core.radio.browse_nodes import leaf

        rows = lane_rows(host, query, safe_mode=safe_mode, network=network)
        if not rows:
            return found
        have = {node.node_id.strip().casefold() for node in found.rows}
        added = []
        for station in rows:
            node = leaf(station, note=f"Station, {station.match_reason}")
            if node.node_id.strip().casefold() not in have:
                have.add(node.node_id.strip().casefold())
                added.append(node)
        if added:
            found.rows = [*added, *found.rows]
            found.counts["Station"] = found.counts.get("Station", 0) + len(added)
    except Exception:  # noqa: BLE001 - the search's own answer always stands
        pass
    return found
