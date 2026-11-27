"""Find Streams: other ways to find a stream when the first one finds none.

Three ideas from Andre Louis's StreamSift (https://github.com/OnjLouis/StreamSift,
MIT), written in QUILL's own code:

* **Automatic fallback** (a setting, off by default). When the website scan finds
  no playable stream, try the public directories next -- Radio Browser, IPRD and Radio Garden,
  by the name the site's address carries ("kexp" from ``www.kexp.org``) -- and
  say which way found the result. Quill Radio has no browser-assisted method, so
  that last step of the idea does not exist here; it is not faked.
* **A name typed as a name.** ``kexp``, ``bbcradio4`` (no spaces) and
  ``kexp.mp3`` (an ending) are not websites. They used to be sent to the
  website scanner and fail with a sentence about a network. They are now looked
  up by name in the directories, whatever the setting says, because there is
  no website to try first. Matching ignores spaces and punctuation, so
  ``bbcradio4`` finds "BBC Radio 4".
* **A recent website that matches.** If what was typed is the name of a website
  Find Streams already found a live stream on, it offers to check that site
  again.

Nothing here touches the network itself: the scanners are passed in, so the
order and the sentences are tested with fakes. Directory rows pass through the
same live check as everything else before they are listed, and only streams that
check out are shown.

wx-free, strict-typed.
"""

from __future__ import annotations

import re
import urllib.parse
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field

from quill.core.radio.models import RadioStation
from quill.core.radio.page_links import PageStreamCandidate
from quill.core.radio.page_url import looks_like_url

__all__ = [
    "AUDIO_ENDINGS",
    "METHOD_DIRECTORY",
    "METHOD_WEBSITE",
    "Attempt",
    "FallbackOutcome",
    "compact",
    "directory_candidates",
    "found_by_sentence",
    "matching_recent_site",
    "name_query",
    "site_name",
    "typed_kind",
]

METHOD_WEBSITE = "website"
METHOD_DIRECTORY = "directory"
_METHOD_WORDS = {
    METHOD_WEBSITE: "the website",
    METHOD_DIRECTORY: "the public directories (Radio Browser, IPRD and Radio Garden)",
}

#: Endings people type onto a name: the stream's own file type.
AUDIO_ENDINGS = (".mp3", ".aac", ".ogg", ".opus", ".flac", ".m3u", ".m3u8", ".pls", ".xspf", ".asx")
_MAX_ROWS = 25
_NON_WORD = re.compile(r"[\W_]+", re.UNICODE)


def compact(text: str) -> str:
    """Lower-case letters and digits only: "BBC Radio 4" and "bbcradio4" match."""
    return _NON_WORD.sub("", text.casefold())


def _has_ending(value: str) -> bool:
    return value.casefold().endswith(AUDIO_ENDINGS)


def typed_kind(text: str) -> str:
    """``"empty"``, ``"address"`` or ``"name"`` for what was typed (pure).

    An address has a scheme or a ``host.tld``. A name has spaces, or no dot, or
    only a file ending after one word and nothing else (``kexp.mp3``): with a
    scheme or a path it is still an address, because that is a stream link.
    """
    value = text.strip()
    if not value:
        return "empty"
    if not looks_like_url(value):
        return "name"
    if "://" not in value and "/" not in value and _has_ending(value):
        stem = value.rsplit(".", 1)[0]
        if "." not in stem:
            return "name"
    return "address"


def name_query(text: str) -> str:
    """The words to look up: the typed text without a file ending or ``www.``."""
    value = text.strip()
    if _has_ending(value):
        value = value.rsplit(".", 1)[0]
    value = value.removeprefix("www.").removeprefix("WWW.")
    return " ".join(value.replace("_", " ").replace("-", " ").split())


def site_name(address: str) -> str:
    """The name a website's address carries: ``kexp`` for ``https://www.kexp.org/x``."""
    parts = urllib.parse.urlsplit(address if "://" in address else f"//{address}")
    host = (parts.hostname or "").removeprefix("www.")
    labels = [label for label in host.split(".") if label]
    if len(labels) >= 3 and labels[-2] in {"co", "com", "org", "net", "gov", "ac"}:
        return labels[-3]
    return labels[-2] if len(labels) >= 2 else (labels[0] if labels else "")


def matching_recent_site(text: str, recent: Iterable[str]) -> str:
    """The recent website whose name is what was typed, or ``""`` (pure)."""
    wanted = compact(name_query(text))
    if len(wanted) < 3:
        return ""
    for site in recent:
        if compact(site_name(site)) == wanted:
            return site
    return ""


def directory_candidates(
    stations: Iterable[RadioStation], query: str, *, limit: int = _MAX_ROWS
) -> list[PageStreamCandidate]:
    """Directory rows whose name holds *query* (ignoring spaces), as candidates.

    Exact (compact) names first, then names that merely contain it; a station
    listed twice by address is kept once.
    """
    wanted = compact(query)
    if not wanted:
        return []
    exact: list[PageStreamCandidate] = []
    partial: list[PageStreamCandidate] = []
    seen: set[str] = set()
    for station in stations:
        url = (station.stream_url or "").strip()
        name = compact(station.name)
        if not url or url in seen or wanted not in name:
            continue
        seen.add(url)
        source = station.source or "Radio Browser"
        row = PageStreamCandidate(
            url=url,
            reason=f"found in the {source} directory",
            label=station.name,
            codec=station.codec,
            bitrate_kbps=station.bitrate_kbps,
            label_is_name=True,
        )
        (exact if name == wanted else partial).append(row)
    return (exact + partial)[:limit]


@dataclass(slots=True)
class Attempt:
    """One way tried: which, and how many playable streams it gave."""

    method: str
    found: int


@dataclass(slots=True)
class FallbackOutcome:
    """What the ways tried came to."""

    candidates: list[PageStreamCandidate]
    method: str = ""
    attempts: list[Attempt] = field(default_factory=list)

    @property
    def tried_more_than_one(self) -> bool:
        return len(self.attempts) > 1


def found_by_sentence(outcome: FallbackOutcome) -> str:
    """ "Found by the public directories (Radio Browser, IPRD and Radio Garden) ..." or ``""``.

    Said only when more than one way was tried or a name was looked up, because
    a plain website scan that worked needs no explaining. When the website found
    nothing and the directories did, the sentence says both.
    """
    if not outcome.method or not outcome.candidates:
        return ""
    how = _METHOD_WORDS.get(outcome.method, outcome.method)
    if outcome.tried_more_than_one:
        return f"The website had none, so these were found by {how}."
    if outcome.method == METHOD_DIRECTORY:
        return f"Found by {how}."
    return ""


def run(
    kind: str,
    *,
    scan_website: Callable[[], tuple[list[PageStreamCandidate], object]] | None,
    search_directories: Callable[[str], list[PageStreamCandidate]],
    query: str,
    fallback: bool,
) -> tuple[FallbackOutcome, object]:
    """Try the ways in order; return what was found and the website scan's result.

    *kind* is ``"address"`` or ``"name"``. An address is scanned first; the
    directories follow only when *fallback* is on and the scan found nothing. A
    name goes straight to the directories. The website scan's own result (its
    counts and sentence) is returned so a scan that found nothing still says why.
    """
    attempts: list[Attempt] = []
    scan_result: object = None
    if kind == "address" and scan_website is not None:
        rows, scan_result = scan_website()
        attempts.append(Attempt(METHOD_WEBSITE, len(rows)))
        if rows:
            return FallbackOutcome(rows, METHOD_WEBSITE, attempts), scan_result
        if not fallback:
            return FallbackOutcome([], "", attempts), scan_result
    found = search_directories(query)
    attempts.append(Attempt(METHOD_DIRECTORY, len(found)))
    return FallbackOutcome(found, METHOD_DIRECTORY if found else "", attempts), scan_result


def describe_attempts(attempts: Sequence[Attempt]) -> str:
    """ "Tried the website and the public directories." for a search that found none."""
    ways = [_METHOD_WORDS.get(a.method, a.method) for a in attempts]
    return "Tried " + " and ".join(ways) + "." if ways else ""
