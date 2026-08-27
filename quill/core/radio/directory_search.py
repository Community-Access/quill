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
#: How many results are resolved at once. Small enough to be polite to a
#: directory and large enough that the cap below is one round trip rather than
#: several.
RESOLVE_WORKERS = 10


def _in_parallel(work: object, items: list) -> list:
    """Run *work* over *items* concurrently, in order, never raising.

    A tiny helper rather than a pool per call site, because the two callers
    below had the same fault -- a sequential loop of network round trips -- and
    the fix should not be written twice and then diverge.
    """
    from concurrent.futures import ThreadPoolExecutor

    if not items:
        return []
    if len(items) == 1:
        try:
            return [work(items[0])]  # type: ignore[operator]
        except Exception:  # noqa: BLE001 - a search must never raise into its caller
            return []
    with ThreadPoolExecutor(max_workers=min(RESOLVE_WORKERS, len(items))) as pool:
        try:
            return list(pool.map(work, items))  # type: ignore[arg-type]
        except Exception:  # noqa: BLE001 - same rule
            return []


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
    plus any it absorbed as a duplicate. A blank source maps to "Radio Browser"
    (the default facet for an unlabelled RadioBrowser result). Any podcast
    source name additionally answers to the plain "Podcasts" facet -- episode
    rows are stamped differently by search, the browse tree, and Subscriptions
    (see downloadable.ALLOWED_SOURCES), and the facet should not care which."""
    labels = {station.source or "Radio Browser"}
    for src in station.alt_sources:
        labels.add(src or "Radio Browser")
    if labels & {"Podcasts (Apple)", "Podcast", "Apple Podcasts", "Subscribed Podcasts"}:
        labels.add("Podcasts")
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
    wanted = [result for result in results if result.is_station][:cap]

    def _resolve(result: tunein.TuneInResult) -> RadioStation | None:
        try:
            streams = tunein.resolve_station_streams(result.guide_id, safe_mode=safe_mode)
        except tunein.TuneInError:
            return None
        if not streams:
            return None
        return tunein.to_radio_station(result, tunein.best_stream(streams))

    # Concurrently, and this is the whole difference between a search that
    # takes a second and one that takes ten: TuneIn needs a round trip PER
    # station to turn a guide id into an address, and ten of those end to end
    # is ten times the slowest thing on the network. Reported 2026-08-26 as
    # "search is still way too slow"; the loop that was here resolved them one
    # after another, so the wait was the sum rather than the maximum.
    return [row for row in _in_parallel(_resolve, wanted) if row is not None]


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
    matched = [station for station in index if iheart.station_matches(station, name)][:cap]

    def _resolve(station: IHeartStation) -> RadioStation | None:
        try:
            stream = iheart.resolve_stream(station.page_url, safe_mode=safe_mode)
        except iheart.IHeartError:
            return None
        return iheart.to_radio_station(station, stream) if stream else None

    # One station-page GET each, run at the same time rather than in a queue --
    # see the note in tunein_search_stations.
    return [row for row in _in_parallel(_resolve, matched) if row is not None]


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


def directory_provider_stations(query: str, *, safe_mode: bool = False) -> list[RadioStation]:
    """Stations contributed by enabled Quillin ``radio.directory`` providers.

    Consults :mod:`quill.core.radio.directory_registry`, which a
    :class:`~quill.core.quillins.app_host.QuillinAppHost` populates from every
    enabled provider. Each contributed row (``{"name", "url", "source"}``) becomes
    a :class:`RadioStation` badged with the provider's Source label, so the Find
    Stations fan-out can merge and rank them beside the built-in sources. A
    provider handler makes no network call of its own, so this adds no egress.

    Safe Mode contributes nothing (the host loads no Quillins in Safe Mode, so the
    registry is already empty, but the guard keeps that explicit here too).
    """
    if safe_mode or not query.strip():
        return []
    from quill.core.radio import directory_registry

    stations: list[RadioStation] = []
    for row in directory_registry.stations_from_providers(query):
        stations.append(RadioStation(name=row["name"], stream_url=row["url"], source=row["source"]))
    return stations


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
