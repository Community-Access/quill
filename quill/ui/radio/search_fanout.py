"""Fanning one typed search out across every enabled directory.

Lifted out of :mod:`quill.ui.radio.station_browser_dialog` when the aggressive
query fan-out landed (2026-09-14): the dialog was at its GATE-11 ceiling, and
the rule there is to extract rather than to raise the number. Nothing about the
search changed in the move -- the order of the sources, their failure
tolerance, and which ones a country-only query skips are all exactly as they
were.

The one thing worth reading twice is how much of this is *not* a network call
per source. Three of the lanes -- the local catalog, NOAA Weather Radio and the
Radio Reading Services list -- answer from data already on the machine, which
is why they ride along unconditionally: they cost nothing and they are the
lanes that still work when the connection does not.

wx-free: *host* is the station browser, consulted only for which sources are
switched on and for the Spotify client it owns.
"""

from __future__ import annotations

from typing import Any

from quill.core.radio import iptv, live365, radio_paradise, shoutcast, soma_fm
from quill.core.radio.directory_search import (
    iheart_variants,
    radio_browser_variants,
    reading_services_search_stations,
    tunein_variants,
    wxindex_search_stations,
)
from quill.core.radio.models import RadioStation
from quill.core.radio.spotify_search import spotify_search_stations, youtube_search_stations

__all__ = ["run_search"]


def run_search(
    host: Any,
    *,
    name: str,
    tag: str,
    country: str,
    limit: int,
    safe_mode: bool = False,
) -> tuple[list[RadioStation], list[RadioStation]]:
    """Every enabled directory, searched for *name*/*tag*/*country*.

    Returns ``(radio, extras)`` -- the Radio Browser page (with the local
    catalog's rows in front of it) and everything the blended directories
    added -- because the caller merges and ranks the two lists with the source
    priority that order encodes.

    Runs on a worker thread: it must never touch wx, and it must never raise
    except when the search genuinely has nothing to show.
    """
    # The catalog lane (quill/ui/radio/catalog_search.py): local FTS
    # answers in ~1 ms, so an outage costs live rows, not the search.
    from quill.ui.radio.catalog_search import catalog_search_rows

    catalog_rows = catalog_search_rows(getattr(host, "_catalog", None), name, limit=limit)
    try:
        # The variant fan-out: what was typed, then the other spellings
        # of it, then the same query narrowed to the place it named.
        radio = (
            radio_browser_variants(
                name,
                tag=tag,
                country=country,
                limit=limit,
                safe_mode=safe_mode,
            )
            if host._source_on("radio_browser")
            else []
        )
    except Exception:
        if not catalog_rows:
            raise
        radio = []  # offline: the catalog carries the search
    radio = catalog_rows + radio
    # Blended in after the RadioBrowser page, each failure-tolerant so
    # one down source never blanks the list. Name/tag searches only:
    # these directories have no country field of their own, so a
    # country-only query skips them rather than returning noise. They
    # ride along with the first RadioBrowser page; "More Stations" pages
    # RadioBrowser alone.
    extras: list[RadioStation] = []
    query = name or tag
    if query:
        if host._source_on("somafm"):
            try:
                extras += soma_fm.search_stations(query, safe_mode=safe_mode)
            except soma_fm.SomaFmError:
                pass
        if host._source_on("tunein"):
            extras += tunein_variants(query, safe_mode=safe_mode)
        # SHOUTcast, Live365 and Radio Paradise each swallow their own
        # errors and return [], so they ride along without a try block
        # -- the same contract tunein_search_stations honours above.
        if host._source_on("shoutcast"):
            extras += shoutcast.search_stations(query, safe_mode=safe_mode)
        if host._source_on("live365"):
            extras += live365.search_stations(query, safe_mode=safe_mode)
        if host._source_on("radioparadise"):
            extras += radio_paradise.search_stations(query, safe_mode=safe_mode)
        if host._source_on("tv"):
            extras += iptv.search_stations(query, safe_mode=safe_mode)
        # NOAA Weather Radio: a SAME code, callsign, or "County, ST"/state
        # query resolves to authoritative stations; anything else just
        # comes back empty, so this rides along unconditionally.
        if host._source_on("wxindex"):
            extras += wxindex_search_stations(query, safe_mode=safe_mode)
        # Radio Reading Services: a name/tag/state match against the
        # curated ~20-service list; empty for anything else, so this
        # rides along unconditionally too.
        if host._source_on("reading_services"):
            extras += reading_services_search_stations(query, safe_mode=safe_mode)
        # Spotify: search is open to every account tier, so these rows
        # ride along whenever the user has connected Spotify. They stay
        # useful on a free account -- Enter needs Premium, but "Open
        # Website" opens the track in Spotify's own app, where a free
        # account plays it normally.
        if host._source_on("spotify"):
            extras += spotify_search_stations(
                query,
                client=host._spotify_client(),
                safe_mode=safe_mode,
            )
        # YouTube: yt-dlp's keyless ytsearch, the same extraction route
        # FreeTube/NewPipe/Invidious use. Each row is a page URL, so it
        # becomes an ordinary station you can play, favorite and record.
        if host._source_on("youtube"):
            extras += youtube_search_stations(query, safe_mode=safe_mode)
    if name and host._source_on("iheart"):
        # iHeart's own relevance search (two GETs, ranked, streams
        # embedded); the sitemap-index route this replaced is retired
        # in directory_search's history.
        extras += iheart_variants(name, safe_mode=safe_mode)
    return radio, extras
