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

__all__ = ["securenet_candidates", "triton_candidates", "tunein_candidates"]


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
