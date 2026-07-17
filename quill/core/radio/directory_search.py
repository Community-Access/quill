"""Blend the TuneIn and iHeart directory clients into RadioStation results.

The station browser fans a search out across several sources and merges the
results into one list. RadioBrowser and SomaFM already return
:class:`~quill.core.radio.models.RadioStation` objects directly; TuneIn and
iHeart return their own directory rows whose playable stream must still be
resolved. These two helpers do that resolution and the conversion, bounded and
failure-tolerant, so the UI's off-thread search worker can just call them and
concatenate.

Both resolve at most ``cap`` matches per search, because each resolve is a live
network round trip (TuneIn's ``Tune.ashx``; an iHeart station page) -- the
blended sources add a handful of immediately-playable results without turning
one search into dozens of GETs. Any hiccup (the search itself, or a single
resolve) is swallowed so a down source never blanks the surrounding list.

wx-free, strict-typed. Safe Mode is enforced by the underlying clients' own
``refuse_in_safe_mode`` (and the browser blocks search entirely in Safe Mode).
"""

from __future__ import annotations

from quill.core.radio import iheart, tunein
from quill.core.radio.iheart import IHeartStation
from quill.core.radio.models import RadioStation

#: Per-search resolve caps for the blended directories (one GET each).
TUNEIN_RESOLVE_CAP = 10
IHEART_RESOLVE_CAP = 5


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
            stations.append(tunein.to_radio_station(result, streams[0]))
    return stations


def iheart_search_stations(
    index: list[IHeartStation], name: str, *, safe_mode: bool = False, cap: int = IHEART_RESOLVE_CAP
) -> list[RadioStation]:
    """iHeart stations from *index* matching *name*, as ``source="iHeart"``.

    Filters the already-fetched sitemap *index* by a case-insensitive name
    substring, then resolves up to *cap* matches to a playable stream (each one
    station-page GET, so the cap keeps a search cheap). A resolve error or an
    unresolvable page is skipped.
    """
    lowered = name.strip().lower()
    if not lowered:
        return []
    stations: list[RadioStation] = []
    for station in index:
        if len(stations) >= cap:
            break
        if lowered not in station.name.lower():
            continue
        try:
            stream = iheart.resolve_stream(station.page_url, safe_mode=safe_mode)
        except iheart.IHeartError:
            continue
        if stream:
            stations.append(iheart.to_radio_station(station, stream))
    return stations
