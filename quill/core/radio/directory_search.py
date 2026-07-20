"""Blend the TuneIn, iHeart, and NOAA Weather Radio directory clients into
RadioStation results.

The station browser fans a search out across several sources and merges the
results into one list. RadioBrowser and SomaFM already return
:class:`~quill.core.radio.models.RadioStation` objects directly; TuneIn and
iHeart return their own directory rows whose playable stream must still be
resolved. These two helpers do that resolution and the conversion, bounded and
failure-tolerant, so the UI's off-thread search worker can just call them and
concatenate. NOAA Weather Radio (``wxindex``) already returns
directly-playable feeds -- its helper below just adapts and filters.

Both TuneIn and iHeart resolve at most ``cap`` matches per search, because each
resolve is a live network round trip (TuneIn's ``Tune.ashx``; an iHeart station
page) -- the blended sources add a handful of immediately-playable results
without turning one search into dozens of GETs. Any hiccup (the search itself,
or a single resolve) is swallowed so a down source never blanks the
surrounding list.

wx-free, strict-typed. Safe Mode is enforced by the underlying clients' own
``refuse_in_safe_mode`` (and the browser blocks search entirely in Safe Mode).
NOAA Weather Radio is the exception: it falls back to its bundled snapshot in
Safe Mode instead of refusing outright (see ``wxindex.search_stations``).
"""

from __future__ import annotations

from collections.abc import Iterable

from quill.core.radio import iheart, reading_services, tunein, wxindex
from quill.core.radio.iheart import IHeartStation
from quill.core.radio.models import RadioStation
from quill.core.radio.wxindex_models import to_radio_station as _wx_to_radio_station

#: Per-search resolve caps for the blended directories (one GET each).
TUNEIN_RESOLVE_CAP = 10
IHEART_RESOLVE_CAP = 5


def merge_and_rank(
    result_lists: Iterable[list[RadioStation]], query: str = ""
) -> list[RadioStation]:
    """Merge per-source station lists into one de-duped, ranked list.

    The Unified Find Stations model: every source returns its own
    :class:`RadioStation` list; this collapses them into a single list.

    De-dup, first occurrence wins (so the caller controls source priority by
    the order it passes the lists): by ``stream_url`` first (the same stream on
    two directories is one entry), then by ``(name, country)`` (the same station
    with a different mount URL is still one entry). Ranking then floats
    exact-name matches for *query* to the top; everything else keeps its
    merged order, so each source's own relevance ordering is preserved beneath
    the exact hits. An empty *query* just de-dups without re-ordering.
    """
    survivor_by_url: dict[str, RadioStation] = {}
    survivor_by_name_country: dict[tuple[str, str], RadioStation] = {}
    merged: list[RadioStation] = []
    for stations in result_lists:
        for station in stations:
            url_key = (station.stream_url or "").strip().lower()
            name_key = (station.name or "").strip().lower()
            country_key = (station.country or "").strip().lower()
            name_country = (name_key, country_key)
            survivor: RadioStation | None = None
            if url_key and url_key in survivor_by_url:
                survivor = survivor_by_url[url_key]
            elif name_key and name_country in survivor_by_name_country:
                survivor = survivor_by_name_country[name_country]
            if survivor is not None:
                _absorb_source(survivor, station.source)
                continue
            if url_key:
                survivor_by_url[url_key] = station
            survivor_by_name_country[name_country] = station
            merged.append(station)
    normalized_query = query.strip().lower()
    if not normalized_query:
        return merged
    exact = [s for s in merged if (s.name or "").strip().lower() == normalized_query]
    rest = [s for s in merged if (s.name or "").strip().lower() != normalized_query]
    return exact + rest


def _absorb_source(survivor: RadioStation, dropped_source: str) -> None:
    """Record that ``dropped_source`` also carried the station kept as
    ``survivor`` during de-dup, so the Source filter can still match it there.

    The survivor's own ``source`` is already represented; we only add the
    dropped duplicate's source when it is genuinely a different directory.
    """
    if dropped_source == survivor.source:
        return
    if dropped_source in survivor.alt_sources:
        return
    survivor.alt_sources = (*survivor.alt_sources, dropped_source)


def station_source_labels(station: RadioStation) -> set[str]:
    """Every Source-filter label a merged station should match: its own source
    plus any it absorbed as a duplicate. A blank source maps to "RadioBrowser"
    (the default facet for an unlabelled RadioBrowser result)."""
    labels = {station.source or "RadioBrowser"}
    for src in station.alt_sources:
        labels.add(src or "RadioBrowser")
    return labels


def tunein_search_stations(
    query: str, *, safe_mode: bool = False, cap: int = TUNEIN_RESOLVE_CAP
) -> list[RadioStation]:
    """TuneIn stations for *query*, streams resolved, as ``source="TuneIn"``.

    Searches the TuneIn directory, then resolves up to *cap* station results to
    a playable stream. A TuneIn error (search or a single resolve) is swallowed;
    a result that resolves to nothing is dropped.
    """
    if not query.strip():
        return []
    try:
        results = tunein.search(query, safe_mode=safe_mode)
    except tunein.TuneInError:
        return []
    stations: list[RadioStation] = []
    for result in results:
        if len(stations) >= cap:
            break
        if not result.is_station:
            continue
        try:
            streams = tunein.resolve_station_streams(result.guide_id, safe_mode=safe_mode)
        except tunein.TuneInError:
            continue
        if streams:
            stations.append(tunein.to_radio_station(result, tunein.best_stream(streams)))
    return stations


def iheart_search_stations(
    index: list[IHeartStation], name: str, *, safe_mode: bool = False, cap: int = IHEART_RESOLVE_CAP
) -> list[RadioStation]:
    """iHeart stations from *index* matching *name*, as ``source="iHeart"``.

    Filters the already-fetched sitemap *index* with
    :func:`iheart.station_matches` -- a punctuation-insensitive match over each
    station's name, slug and numeric id -- then resolves up to *cap* matches to a
    playable stream (each one station-page GET, so the cap keeps a search cheap).
    A resolve error or an unresolvable page is skipped.
    """
    if not name.strip():
        return []
    stations: list[RadioStation] = []
    for station in index:
        if len(stations) >= cap:
            break
        if not iheart.station_matches(station, name):
            continue
        try:
            stream = iheart.resolve_stream(station.page_url, safe_mode=safe_mode)
        except iheart.IHeartError:
            continue
        if stream:
            stations.append(iheart.to_radio_station(station, stream))
    return stations


def wxindex_search_stations(query: str, *, safe_mode: bool = False) -> list[RadioStation]:
    """NOAA Weather Radio stations for *query*, as ``source="NOAA Weather Radio"``.

    Routes through :func:`wxindex.search_stations`, which treats *query* as a
    SAME code, callsign, ``"County, ST"``, or free-text state/name search (see
    that function for the routing rules) and already gates on Safe Mode,
    falling back to the bundled snapshot rather than refusing outright. A
    station with no live stream feed has nothing to play, so it is dropped
    here the same way an unresolvable TuneIn or iHeart match is dropped.
    """
    if not query.strip():
        return []
    try:
        results = wxindex.search_stations(query, safe_mode=safe_mode)
    except wxindex.WxIndexError:
        return []
    return [_wx_to_radio_station(station) for station in results if station.feeds]


def reading_services_search_stations(query: str, *, safe_mode: bool = False) -> list[RadioStation]:
    """Radio Reading Services matching *query*, as ``source="Radio Reading Service"``.

    Routes through :func:`reading_services.list_reading_services` (its own
    fresh-cache -> live-refresh -> stale-cache -> bundled-snapshot resolver,
    already Safe-Mode-aware) and keeps the ones whose name, tags, or state --
    live/cached entries carry the RadioBrowser tags they were resolved with,
    which can include a state name -- case-insensitively contain *query*. A
    service with no live stream feed has nothing to play, so it is dropped
    here the same way an unresolvable TuneIn or iHeart match is dropped.
    """
    normalized = query.strip().lower()
    if not normalized:
        return []
    matches: list[RadioStation] = []
    for station in reading_services.list_reading_services(safe_mode=safe_mode):
        if not station.stream_url:
            continue
        haystack = [station.name, station.country, *station.tags]
        if any(normalized in field.lower() for field in haystack if field):
            matches.append(station)
    return matches
