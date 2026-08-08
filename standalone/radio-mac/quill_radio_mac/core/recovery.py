"""Self-healing recovery for a station whose stream won't play.

Ported near-verbatim from upstream ``quill.core.radio.recovery``. A
directory station's listed stream can be dead even though the station is
perfectly live -- most often because the "real" stream is behind a Triton /
StreamTheWorld JavaScript player on the station's own site, so the URL the
directory carries (or a URL the user copied off the site's play button) is a
web-player address, not a stream.

This module does that digging automatically, as a ladder of increasingly
speculative strategies, each returning a :class:`RecoveryResult` the UI then
acts on by confidence:

* **Strategy A -- re-resolve a StreamTheWorld mount (high confidence, always).**
  If the failed URL is itself ``*.streamtheworld.com/<MOUNT>``, that mount is
  simply re-resolved through Triton's provisioning API (see
  :mod:`quill_radio_mac.core.triton`) to its current server. Deterministic,
  same station and provider -- no guessing.
* **Strategy B -- refresh from the directory (high confidence).** If the
  station has a RadioBrowser id, its current URL is re-fetched; a genuinely
  different URL is the directory having healed itself.
* **Strategy C -- scan the station's website (opt-in).** The station's homepage
  (and the failed URL itself, if it is a web page) is scanned with the same
  Triton + "Listen Live" link-following logic the manual Find Streams feature
  uses. A single unambiguous result -- a resolved Triton player, or exactly one
  stream candidate -- is treated as high confidence and offered as a ready
  station; several candidates are returned for the user to choose from, never
  auto-played.

Every network step goes through the already-reviewed egress sites
(``triton._fetch_api``, ``radio_browser``, ``link_finder._fetch_html``) and is
Safe-Mode gated by the caller. wx-free, strict-typed; the UI calls
:func:`recover_stream` off-thread and applies the result on the UI thread.

Threading contract: :func:`recover_stream` performs blocking network calls
(through the sibling modules); callers invoke it off the UI thread and apply
the :class:`RecoveryResult` back on the UI thread.

macOS notes: none -- fully platform-neutral.
"""

from __future__ import annotations

import re
import urllib.parse
from dataclasses import dataclass, replace

from quill_radio_mac.core.link_finder import LinkFinderError, PageStreamCandidate
from quill_radio_mac.core.models import RadioStation

#: Confidence/source of a recovery, for the announcement and telemetry.
SOURCE_STREAMTHEWORLD = "streamtheworld"
SOURCE_DIRECTORY = "directory"
SOURCE_WEBSITE = "website"

#: URL suffixes that are a stream/playlist, not a web page worth scanning.
_STREAMISH_SUFFIXES = (".mp3", ".aac", ".ogg", ".opus", ".m3u", ".m3u8", ".pls", ".flac")


@dataclass(slots=True)
class RecoveryResult:
    """What a recovery attempt found.

    Exactly one of these outcomes holds:

    * ``station`` set -> a ready-to-play healed station (high confidence); the
      UI plays it and speaks ``message``.
    * ``candidates`` non-empty -> the website offered several possibilities the
      UI should present (e.g. pre-load Find Streams); ``message`` explains.
    * both empty -> nothing found; ``message`` says so.
    """

    station: RadioStation | None = None
    candidates: tuple[PageStreamCandidate, ...] = ()
    source: str = ""
    message: str = ""


def recover_stream(
    station: RadioStation,
    *,
    allow_website: bool = True,
    safe_mode: bool = False,
) -> RecoveryResult:
    """Try to find a working stream for *station* (network; call off-thread).

    Runs strategy A, then B, then -- only when *allow_website* and the earlier
    strategies came up empty -- C. Returns the first confident hit, or the
    website candidates for the user to choose from, or an empty result. Never
    raises: any strategy's network failure is swallowed so recovery degrades to
    "nothing found", never an error on top of a playback error.
    """
    if safe_mode:
        return RecoveryResult(message="Stream recovery is off in Safe Mode.")

    healed = _recover_from_streamtheworld(station)
    if healed is not None:
        return RecoveryResult(
            station=healed,
            source=SOURCE_STREAMTHEWORLD,
            message="That stream moved; trying its current address.",
        )

    healed = _recover_from_directory(station, safe_mode=safe_mode)
    if healed is not None:
        return RecoveryResult(
            station=healed,
            source=SOURCE_DIRECTORY,
            message="That stream has moved; trying its current address.",
        )

    if allow_website:
        return _recover_from_website(station, safe_mode=safe_mode)

    return RecoveryResult(message="Could not find a working stream for this station.")


def streamtheworld_mount(url: str) -> str:
    """The mount of a ``*.streamtheworld.com/<MOUNT>`` URL, or "" (pure)."""
    parts = urllib.parse.urlsplit(url)
    if not parts.netloc.lower().endswith("streamtheworld.com"):
        return ""
    return parts.path.strip("/").split("/")[-1] if parts.path.strip("/") else ""


def _recover_from_streamtheworld(station: RadioStation) -> RadioStation | None:
    """Strategy A: re-resolve a dead StreamTheWorld mount to its current server."""
    mount = streamtheworld_mount(station.stream_url)
    if not mount:
        return None
    from quill_radio_mac.core import triton

    try:
        streams = triton.resolve_station_streams(mount)
    except triton.TritonResolverError:
        return None
    if not streams:
        return None
    best = streams[0]
    if best.url == station.stream_url:  # same address that just failed -- no help
        return None
    return replace(station, stream_url=best.url, codec=best.codec or station.codec)


def _recover_from_directory(station: RadioStation, *, safe_mode: bool) -> RadioStation | None:
    """Strategy B: re-fetch the station's current URL from RadioBrowser."""
    uuid = station.station_uuid.strip()
    if not uuid:
        return None
    from quill_radio_mac.core import radio_browser

    try:
        fresh = radio_browser.lookup_station(uuid, safe_mode=safe_mode)
    except radio_browser.RadioBrowserError:
        return None
    if fresh is None or not fresh.stream_url or fresh.stream_url == station.stream_url:
        return None
    return fresh


def _recover_from_website(station: RadioStation, *, safe_mode: bool) -> RecoveryResult:
    """Strategy C: scan the station's website for a working stream.

    Scans the homepage (and the failed URL, when it looks like a web page
    rather than a stream) with the shared Find-Streams scanner, which already
    resolves Triton players and follows "Listen Live" links. A single
    unambiguous result becomes a ready station; several become candidates for
    the user to choose from.
    """
    from quill_radio_mac.core import link_finder

    candidates: list[PageStreamCandidate] = []
    seen: set[str] = set()
    for page in _pages_to_scan(station):
        try:
            result = link_finder.scan_page_for_streams(page, safe_mode=safe_mode)
        except LinkFinderError:
            continue
        for candidate in result.candidates:
            if candidate.url not in seen and candidate.url != station.stream_url:
                seen.add(candidate.url)
                candidates.append(candidate)

    if not candidates:
        return RecoveryResult(message="Could not find a working stream on the station's website.")

    confident = _confident_candidate(candidates)
    if confident is not None:
        return RecoveryResult(
            station=replace(station, stream_url=confident.url),
            source=SOURCE_WEBSITE,
            message="Found a working stream on the station's website; playing it now.",
        )

    plural = "" if len(candidates) == 1 else "s"
    return RecoveryResult(
        candidates=tuple(candidates),
        source=SOURCE_WEBSITE,
        message=(
            f"That stream isn't working. I found {len(candidates)} possible "
            f"stream{plural} on the station's website -- open Find Streams from a "
            "Website to pick one."
        ),
    )


def _pages_to_scan(station: RadioStation) -> list[str]:
    """The web pages worth scanning for *station*: its homepage, plus the failed
    URL itself when that looks like a web page (the user may have pasted the
    site's play-button link, not a stream)."""
    pages: list[str] = []
    homepage = station.homepage.strip()
    if homepage:
        pages.append(homepage)
    failed = station.stream_url.strip()
    if (
        failed
        and failed.lower().startswith("http")
        and not failed.lower().endswith(_STREAMISH_SUFFIXES)
        and failed not in pages
    ):
        pages.append(failed)
    return pages


#: A SecureNet *mount* lives on an ``ice<N>`` host. The player front-ends
#: (``radio.``, ``streamdb<N>web.``) sit on the same domain but serve pages, and
#: a player page links to itself -- so matching the domain would promote the
#: page's own links right along with the stream.
_SECURENET_MOUNT_RE = re.compile(r"^https?://ice\d+\.securenetsystems\.net/", re.IGNORECASE)


def _is_resolved_player_mount(url: str) -> bool:
    """True when *url* **is** a page's own resolved stream rather than a guess
    taken off it: a Triton/StreamTheWorld mount, or a SecureNet ice mount.
    """
    return "streamtheworld.com" in url.lower() or bool(_SECURENET_MOUNT_RE.match(url))


def _confident_candidate(candidates: list[PageStreamCandidate]) -> PageStreamCandidate | None:
    """A single high-confidence pick from website candidates, or ``None``.

    A *resolved player mount* is unambiguous -- it is the live stream the page
    itself advertises, not one of the page's links that merely looks like audio
    -- so a lone one is confident even beside other guesses. Two platforms
    qualify: Triton/StreamTheWorld (resolved through its provisioning API) and a
    SecureNet Cirrus player's own ``ice<N>`` mount. The SecureNet case is why
    this matters in practice: its player pages also carry ordinary links that
    survive the scan, so without this a station saved from such a page would
    stay broken purely because its page was chatty. Failing that, exactly one
    candidate overall is confident; two or more genuinely different guesses are
    left for the user to choose between.
    """
    resolved = [c for c in candidates if _is_resolved_player_mount(c.url)]
    if len(resolved) == 1:
        return resolved[0]
    if len(candidates) == 1:
        return candidates[0]
    return None
