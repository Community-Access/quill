"""Platform players whose stream the page's HTML does not simply contain.

Split from :mod:`quill.core.radio.link_finder` (GATE-11). Each function takes a
page that was already fetched and answers its stream candidates, or ``[]``
when the page is not that platform's player. A failure of any kind (not the
platform, no callsign, an API that does not answer, Safe Mode) degrades to an
empty list, so it never breaks the rest of a scan.

wx-free, strict-typed.
"""

from __future__ import annotations

from quill.core.radio.page_links import PageStreamCandidate

__all__ = [
    "directory_candidates",
    "global_player_candidates",
    "securenet_candidates",
    "soundmap_candidates",
    "triton_candidates",
    "tunein_candidates",
]


def triton_candidates(url: str, html: str, *, safe_mode: bool) -> list[PageStreamCandidate]:
    """A Triton Digital / StreamTheWorld player page's real mounts.

    A Triton player's stream is JS-computed and absent from the HTML. When the
    page looks like a Triton player and advertises a callsign, this resolves it
    through Triton's JS-free provisioning API.
    """
    from quill.core.radio import triton

    if not triton.page_is_triton_player(url, html):
        return []
    callsign = triton.callsign_from_page(url, html)
    if not callsign:
        return []
    try:
        streams = triton.resolve_station_streams(callsign, safe_mode=safe_mode)
    except triton.TritonResolverError:
        return []
    return [
        PageStreamCandidate(
            url=stream.url,
            reason=f"{stream.codec} stream from the station's player ({stream.mount})",
            label=stream.mount,
        )
        for stream in streams
    ]


def tunein_candidates(url: str, html: str, *, safe_mode: bool) -> list[PageStreamCandidate]:
    """A TuneIn (RadioTime) station page's streams, through the keyless OPML API.

    A TuneIn station page never carries the playable stream in its HTML; it is
    keyed by the station's ``s``-prefixed guide id, which the page does show.
    """
    from quill.core.radio import tunein

    if not tunein.page_is_tunein(url, html):
        return []
    guide_id = tunein.guide_id_from_page(url) or tunein.guide_id_from_page(html)
    if not guide_id:
        return []
    try:
        stream_urls = tunein.resolve_station_streams(guide_id, safe_mode=safe_mode)
    except tunein.TuneInError:
        return []
    return [
        PageStreamCandidate(
            url=stream_url,
            reason=f"stream from the TuneIn station page ({guide_id})",
            label=guide_id,
        )
        for stream_url in stream_urls
    ]


def securenet_candidates(url: str, html: str) -> list[PageStreamCandidate]:
    """A SecureNet Systems (Cirrus) player page's own mount.

    No API call: a Cirrus player carries its mount in the page HTML. The generic
    parser misses it because the mount is a bare Icecast path
    (``https://ice66.securenetsystems.net/ROM``) with no extension and no
    ``/stream``-style hint. Recognising the platform is what makes the URL
    trustworthy; the shape alone never could. Being fetch-free, this also runs
    in Safe Mode.
    """
    from quill.core.radio import securenet

    if not securenet.page_is_securenet_player(url, html):
        return []
    callsign = securenet.callsign_from_page(url, html)
    return [
        PageStreamCandidate(
            url=stream_url,
            reason=f"stream from the station's player ({callsign})"
            if callsign
            else "stream from the station's player",
            label=callsign,
        )
        for stream_url in securenet.stream_urls_from_page(html)
    ]


def global_player_candidates(url: str, html: str) -> list[PageStreamCandidate]:
    """A Global Player station page's free streams, read from its page state.

    No API call: the page carries its own playback list, and only the entries
    Global lets anyone play are taken (see :mod:`quill.core.radio.global_player`).
    """
    from quill.core.radio import global_player

    if not global_player.is_station_page(url):
        return []
    title = global_player.station_title(html)
    return [
        PageStreamCandidate(
            url=stream_url,
            reason="stream from the Global Player station page",
            label=title,
        )
        for stream_url in global_player.stream_urls_from_page(html)
    ]


def soundmap_candidates(url: str, *, safe_mode: bool) -> list[PageStreamCandidate]:
    """Every open microphone on air, when *url* is the Locus Sonus Soundmap page."""
    from quill.core.radio import locus_sonus

    if not locus_sonus.is_soundmap_page(url):
        return []
    try:
        stations = locus_sonus.fetch_stations(safe_mode=safe_mode)
    except locus_sonus.LocusSonusError:
        return []
    return [
        PageStreamCandidate(
            url=station.stream_url,
            reason="open microphone on the Locus Sonus Soundmap",
            label=station.name,
        )
        for station in stations
    ]


def directory_candidates(url: str, *, safe_mode: bool) -> list[PageStreamCandidate]:
    """Streams IPRD lists for this website, from the catalogue already cached.

    Matched by the station's homepage, never by name, and never by starting
    the catalogue download (:func:`quill.core.radio.iprd.stations_for_website`).
    """
    from quill.core.radio import iprd

    return [
        PageStreamCandidate(
            url=station.stream_url,
            reason="listed for this website in IPRD (Public Radio Directory)",
            label=station.name,
        )
        for station in iprd.stations_for_website(url, safe_mode=safe_mode)
    ]
