"""Find Streams' other ways, wired to the real scanners.

The order and the sentences are :mod:`quill.core.radio.find_fallback`; this is
the part that calls the website scanner and the directories. Every directory
call is one the app already makes (Radio Browser and IPRD, both in the network
egress inventory), nothing new is contacted, and both honour Safe Mode, which
refuses before any request. Directory rows pass through the same live check as
a scanned link and are listed only when that check does not prove them not
audio.

Errors never escape from a directory: one that is down finds nothing, as it does
for Find Stations.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from quill.core import http_client, net_public
from quill.core.radio import find_fallback as fb
from quill.core.radio import iprd, link_finder, live_check, radio_browser, radio_garden
from quill.core.radio.link_finder import PageScanResult
from quill.core.radio.page_links import PageStreamCandidate

__all__ = ["FoundResult", "find", "search_directories"]

_DIRECTORY_LIMIT = 60


@dataclass(slots=True)
class FoundResult:
    """A scan's result and how it was found (the sentence may be empty)."""

    scan: PageScanResult
    how: str = ""


def garden_fetch(url: str, timeout: float, max_bytes: int) -> net_public.HttpReply:
    """One read of a public Radio Garden address, through the public-only guard."""
    return net_public.fetch(
        url,
        max_bytes=max_bytes,
        timeout=timeout,
        deadline_seconds=timeout * 2,
        headers={"User-Agent": http_client.user_agent()},
    )


def _garden_candidates(
    query: str, notes: list[str] | None, fetch: radio_garden.Fetch
) -> list[PageStreamCandidate]:
    hits = radio_garden.search(query, fetch)
    if hits is None:
        if notes is not None:
            notes.append(radio_garden.NOT_ANSWERING)
        return []
    found = (radio_garden.resolve(hit, fetch) for hit in hits[: radio_garden.MAX_PLAYBACK_LOOKUPS])
    return [candidate for candidate in found if candidate is not None]


def search_directories(
    query: str,
    *,
    safe_mode: bool = False,
    on_checked: Callable[[str, live_check.Verdict], None] | None = None,
    notes: list[str] | None = None,
    garden: radio_garden.Fetch | None = None,
) -> list[PageStreamCandidate]:
    """Live-checked candidates from Radio Browser, IPRD and Radio Garden for *query*.

    *notes* collects plain sentences about a directory that could not help (Radio
    Garden, which has no official API, may refuse a program).
    """
    if safe_mode or not fb.compact(query):
        return []
    stations = []
    try:
        stations += radio_browser.search_stations(
            fb.name_query(query), limit=_DIRECTORY_LIMIT, safe_mode=safe_mode
        )
    except Exception:  # noqa: BLE001 - a directory that is down finds nothing
        pass
    try:
        stations += iprd.search_stations(fb.name_query(query), safe_mode=safe_mode)
        if " " not in query.strip():  # "bbcradio4" must find "BBC Radio 4"
            wanted = fb.compact(query)
            stations += [
                iprd.to_station(row)
                for row in iprd.catalog(safe_mode=safe_mode)
                if wanted in fb.compact(str(row[0]))
            ][:_DIRECTORY_LIMIT]
    except Exception:  # noqa: BLE001
        pass
    rows = fb.directory_candidates(stations, query)
    kept: list[PageStreamCandidate] = []
    if rows:
        kept, _left_out, _not_public = link_finder._apply_live_check(
            rows, link_finder.live_check.MAX_CHECKS, on_checked
        )
    # Radio Garden's rows are already checked on the way (resolve follows the
    # redirect to the real stream and judges it), so they skip the second check.
    seen = {c.url for c in kept}
    extra = _garden_candidates(fb.name_query(query), notes, garden or garden_fetch)
    return kept + [c for c in extra if c.url not in seen]


def find(
    text: str,
    *,
    safe_mode: bool,
    fallback: bool,
    on_checked: Callable[[str, live_check.Verdict], None] | None = None,
) -> FoundResult:
    """Run Find Streams for what was typed, trying the ways in order.

    Raises what the website scanner raises when the page cannot be read **and**
    no other way found anything, so the listener hears the real reason.
    """
    garden_id = radio_garden.station_id(text)
    if garden_id:
        return _garden_page(garden_id, text, safe_mode)
    from quill.core.radio import audio_sources_io

    audio = (
        audio_sources_io.find_audio(text, safe_mode=safe_mode)
        if fb.typed_kind(text) == "address"
        else None
    )
    if audio is not None:  # a podcast feed, an Archive item or an open directory
        return audio
    kind = fb.typed_kind(text)
    query = fb.name_query(text) if kind == "name" else fb.site_name(text)
    notes: list[str] = []
    website_error: list[BaseException] = []
    scanned: list[PageScanResult] = []

    def scan_website() -> tuple[list[PageStreamCandidate], object]:
        try:
            result = link_finder.scan_page_for_streams(
                text, safe_mode=safe_mode, check_live=True, on_checked=on_checked
            )
        except link_finder.LinkFinderError as error:
            website_error.append(error)
            return [], None
        scanned.append(result)
        return list(result.candidates), result

    outcome, _ = fb.run(
        kind,
        scan_website=scan_website,
        search_directories=lambda q: search_directories(
            q, safe_mode=safe_mode, on_checked=on_checked, notes=notes
        ),
        query=query,
        fallback=fallback,
    )
    if outcome.method == fb.METHOD_DIRECTORY:
        scan = PageScanResult("", "", outcome.candidates, checked=True)
        return FoundResult(scan, fb.found_by_sentence(outcome))
    if scanned:
        return FoundResult(
            scanned[0], "" if not fallback else fb.describe_attempts(outcome.attempts)
        )
    if website_error:
        raise website_error[0]
    return FoundResult(
        PageScanResult("", "", [], checked=True),
        " ".join([fb.describe_attempts(outcome.attempts), *notes]).strip(),
    )


def _garden_page(
    channel_id: str, text: str, safe_mode: bool, fetch: radio_garden.Fetch | None = None
) -> FoundResult:
    """A pasted Radio Garden station page: its real stream, or one plain sentence."""
    empty = PageScanResult("", "", [], checked=True)
    if safe_mode:
        return FoundResult(empty, "Radio Garden is not contacted in Safe Mode.")
    get = fetch or garden_fetch
    title = radio_garden.channel_title(channel_id, get)
    slug = text.rstrip("/").rsplit("/", 2)[-2].replace("-", " ") if "/" in text else ""
    candidate = radio_garden.resolve(
        radio_garden.Hit(channel_id, title or slug or "Radio Garden"), get
    )
    if candidate is None:
        return FoundResult(empty, radio_garden.NO_PLAYBACK if title else radio_garden.NOT_ANSWERING)
    scan = PageScanResult(title, "", [candidate], checked=True)
    return FoundResult(scan, f"Found by {radio_garden.SOURCE}.")
