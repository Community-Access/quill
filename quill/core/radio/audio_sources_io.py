"""Find Streams reads a podcast feed, an Internet Archive item or an open directory.

The rows and rules are :mod:`quill.core.radio.audio_sources`; this fetches. One
public address, typed or pasted by the listener, is read once, through
:mod:`quill.core.net_public` (public http and https only, redirects re-checked,
a one-megabyte cap), and only after the site's ``robots.txt`` has been read and
has not asked programs to stay out of that path: a site that says no is
respected, and the sentence says so. A ``robots.txt`` that is missing or cannot
be read does not forbid anything.

Whether an address is one of these three is decided after reading it, so
:func:`worth_reading` keeps the common case, a station's own web page, from being
fetched twice: only an address that looks like a feed or a folder is read here.
Everything else returns ``None`` and takes the usual scan.

Archive items go through :mod:`quill.core.radio.internet_archive`, whose own
reviewed call site follows the Archive's automated-access policy.
"""

from __future__ import annotations

import urllib.parse
import urllib.robotparser
from collections.abc import Callable, Sequence

from quill.core import http_client, net_public
from quill.core.radio import audio_sources as src
from quill.core.radio import internet_archive
from quill.core.radio.find_fallback_io import FoundResult
from quill.core.radio.link_finder import PageScanResult
from quill.core.radio.live_check import HttpReply
from quill.core.radio.page_links import PageStreamCandidate

__all__ = ["REFUSED_BY_ROBOTS", "find_audio", "robots_allow", "worth_reading"]

REFUSED_BY_ROBOTS = "That site asks programs not to read that address, so Quill Radio did not."
NOT_READABLE = "That address could not be read."
_FEEDISH = ("feed", "rss", "atom", "podcast", ".xml", "xml")

Fetch = Callable[[str, int], HttpReply]


def _fetch(url: str, max_bytes: int) -> HttpReply:
    return net_public.fetch(
        url,
        max_bytes=max_bytes,
        timeout=15.0,
        deadline_seconds=30.0,
        headers={"User-Agent": http_client.user_agent()},
    )


def worth_reading(url: str) -> bool:
    """True for an address that looks like a feed or a folder, not a home page."""
    parts = urllib.parse.urlsplit(url if "://" in url else f"https://{url}")
    path = parts.path.casefold()
    if any(word in path for word in _FEEDISH) or "format=rss" in parts.query.casefold():
        return True
    return path.endswith("/") and path not in ("", "/")


def robots_allow(url: str, fetch: Fetch = _fetch) -> bool:
    """False only when the site's robots.txt disallows *url* for programs."""
    parts = urllib.parse.urlsplit(url)
    robots = f"{parts.scheme}://{parts.netloc}/robots.txt"
    try:
        reply = fetch(robots, 64 * 1024)
    except Exception:  # noqa: BLE001 - unreadable robots.txt forbids nothing
        return True
    if reply.status >= 400:
        return True
    parser = urllib.robotparser.RobotFileParser()
    parser.parse(reply.body.decode("utf-8", errors="replace").splitlines())
    return parser.can_fetch("*", url)


def _result(rows: list[PageStreamCandidate], title: str, how: str) -> FoundResult:
    return FoundResult(PageScanResult(title, "", rows, checked=True), how)


def find_audio(
    text: str,
    *,
    safe_mode: bool,
    fetch: Fetch | None = None,
    archive_files: Callable[[str], Sequence[object]] | None = None,
) -> FoundResult | None:
    """Tracks for a feed, an Archive item or an open directory; else ``None``."""
    if safe_mode:
        return None
    identifier = src.archive_identifier(text)
    if identifier:
        return _archive(identifier, archive_files)
    if not worth_reading(text):
        return None
    url = text.strip() if "://" in text else f"https://{text.strip()}"
    get = fetch or _fetch
    if not robots_allow(url, get):
        return _result([], "", REFUSED_BY_ROBOTS)
    try:
        reply = get(url, src.MAX_PAGE_BYTES)
    except Exception:  # noqa: BLE001 - the usual scan will say why a page cannot be read
        return None
    if reply.status >= 400:
        return None
    final = reply.final_url or url
    content_type = str(reply.headers.get("Content-Type", reply.headers.get("content-type", "")))
    if src.looks_like_feed(reply.body, content_type):
        return _feed(reply.body)
    page = reply.body.decode("utf-8", errors="replace")
    if src.looks_like_directory(page):
        rows = src.directory_tracks(page, final)
        if rows:
            return _result(rows, "", "Read as an open directory of audio files.")
    return None


def _feed(body: bytes) -> FoundResult | None:
    from quill.core.podcasts.feed_reader import FeedReaderError, parse_feed

    try:
        info = parse_feed(body)
    except FeedReaderError:
        return None
    rows = src.feed_tracks(info.episodes)
    how = "Read as a podcast feed: the audio of its episodes, newest first."
    return _result(rows, info.title, how if rows else "That podcast feed lists no audio.")


def _archive(identifier: str, files: Callable[[str], Sequence[object]] | None) -> FoundResult:
    get = files or (lambda item: internet_archive.item_files(item))
    try:
        stations = get(identifier)
    except Exception:  # noqa: BLE001 - the Archive being down is a sentence, not an error
        return _result([], "", "The Internet Archive did not answer for that item.")
    rows = [
        row
        for station in stations
        if (
            row := src.track(
                str(getattr(station, "stream_url", "")),
                str(getattr(station, "name", "")),
                reason="a file in the Internet Archive item",
            )
        )
        is not None
    ][: src.MAX_TRACKS]
    how = (
        "Read as an Internet Archive item." if rows else "That Internet Archive item has no audio."
    )
    return _result(rows, "", how)
