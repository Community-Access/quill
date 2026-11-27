"""More places to find audio: podcast feeds, Internet Archive items, open directories.

Find Streams already lists the streams and the audio files on a web page,
including the ones an article or a demo page embeds (``<audio>``, ``<source>``
and links to audio files; ``page_links``). This adds three more kinds of address,
each listing **audio files** (tracks) rather than live streams:

* **A podcast feed** -- the audio each episode names as its enclosure, in the
  feed's own order.
* **A public Internet Archive item** (``archive.org/details/<id>``) -- the audio
  files the item holds.
* **An open directory of audio files** -- the plain "Index of /" page a web
  server shows for a folder, read for its audio files, their sizes and their
  dates.

Not here, on purpose: torrents and web seeds, and video. Everything fetched is
untrusted: it is read as text only, capped (:data:`MAX_TRACKS` rows, one
megabyte of page), limited to the address's own site for a directory, and never
run. Public http and https only, by the same guard as the rest of Find Streams.

The tracks come back as ordinary Find Streams rows (``check == "file"``) that
the list's sort orders handle: names **case-insensitively and naturally**, so
"Track 2" comes before "Track 10"; format; size; date. Enter plays the selected
tracks in the order shown.

The idea of reading open directories and more kinds of address comes from Andre
Louis's StreamSift (https://github.com/OnjLouis/StreamSift, MIT); this is
QUILL's own code. wx-free, network-free, strict-typed.
"""

from __future__ import annotations

import html
import re
import urllib.parse
from collections.abc import Iterable
from datetime import datetime
from email.utils import parsedate_to_datetime

from quill.core.radio.page_links import PageStreamCandidate

__all__ = [
    "AUDIO_FORMATS",
    "MAX_PAGE_BYTES",
    "MAX_TRACKS",
    "archive_identifier",
    "directory_tracks",
    "feed_tracks",
    "format_for",
    "looks_like_directory",
    "looks_like_feed",
    "track",
]

MAX_TRACKS = 500
MAX_PAGE_BYTES = 1024 * 1024
#: File ending -> the format name Find Streams shows and filters by.
AUDIO_FORMATS: dict[str, str] = {
    ".mp3": "MP3",
    ".aac": "AAC",
    ".m4a": "AAC",
    ".ogg": "Ogg",
    ".oga": "Ogg",
    ".opus": "Opus",
    ".flac": "FLAC",
    ".wav": "WAV",
}
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")
_ANCHOR = re.compile(r"<a\s[^>]*?href\s*=\s*([\"'])(.*?)\1[^>]*>(.*?)</a\s*>", re.I | re.S)
_TAG = re.compile(r"<[^>]+>")
_DATE_ISO = re.compile(r"\b(\d{4}-\d{2}-\d{2})(?:[ T](\d{2}:\d{2}))?")
_DATE_APACHE = re.compile(r"\b(\d{1,2})-([A-Za-z]{3})-(\d{4})(?:\s+(\d{2}:\d{2}))?")
_SIZE = re.compile(r"(?<![\w.])(\d+(?:\.\d+)?)\s*([KMG]i?B?|[KMG])?(?![\w.])", re.I)
_MONTHS = {
    m: i
    for i, m in enumerate(
        ("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"), 1
    )
}


def format_for(name_or_url: str) -> str:
    """The format a file's name says it is, or ``""`` when it is not audio."""
    path = urllib.parse.urlsplit(name_or_url).path or name_or_url
    dot = path.rfind(".")
    return AUDIO_FORMATS.get(path[dot:].casefold(), "") if dot >= 0 else ""


def track(
    url: str, name: str, *, reason: str, size_bytes: int = 0, modified: str = ""
) -> PageStreamCandidate | None:
    """One audio file as a Find Streams row, or ``None`` when it is not one."""
    codec = format_for(url)
    if not codec or urllib.parse.urlsplit(url).scheme.lower() not in ("http", "https"):
        return None
    return PageStreamCandidate(
        url=url,
        reason=reason,
        label=" ".join(name.split()) or urllib.parse.unquote(url.rsplit("/", 1)[-1]),
        check="file",
        codec=codec,
        label_is_name=True,
        size_bytes=max(0, size_bytes),
        modified=modified,
    )


def archive_identifier(text: str) -> str:
    """The item id in an ``archive.org/details/<id>`` address, or ``""`` (pure)."""
    value = text.strip()
    if not value or any(ch.isspace() for ch in value):
        return ""
    parts = urllib.parse.urlsplit(value if "://" in value else f"https://{value}")
    if (parts.hostname or "").lower().removeprefix("www.") != "archive.org":
        return ""
    pieces = [p for p in parts.path.split("/") if p]
    if len(pieces) >= 2 and pieces[0] == "details" and _ID.match(pieces[1]):
        return pieces[1]
    return ""


# -- podcast feeds -----------------------------------------------------------------


def looks_like_feed(body: bytes, content_type: str = "") -> bool:
    head = body[:2048].lstrip().lower()
    if head.startswith((b"<?xml", b"<rss", b"<feed")) or "xml" in content_type.lower():
        return b"<rss" in body[:8192].lower() or b"<feed" in body[:8192].lower()
    return False


def _date_of(published: str) -> str:
    text = (published or "").strip()
    if not text:
        return ""
    try:
        return parsedate_to_datetime(text).strftime("%Y-%m-%d")
    except (TypeError, ValueError, IndexError):
        found = _DATE_ISO.search(text)
        return found.group(1) if found else ""


def feed_tracks(episodes: Iterable[object]) -> list[PageStreamCandidate]:
    """Episodes (anything with ``title``, ``audio_url`` and ``published``) as rows."""
    rows: list[PageStreamCandidate] = []
    for episode in episodes:
        url = str(getattr(episode, "audio_url", "") or "").strip()
        row = track(
            url,
            str(getattr(episode, "title", "") or ""),
            reason="an episode in the podcast feed",
            modified=_date_of(str(getattr(episode, "published", "") or "")),
        )
        if row is None and url.lower().startswith(("http://", "https://")):
            # An enclosure with no audio ending (a redirect link): still the
            # episode's audio, so it stays, its format unknown.
            row = PageStreamCandidate(
                url=url,
                reason="an episode in the podcast feed",
                label=" ".join(str(getattr(episode, "title", "") or "").split()),
                check="file",
                label_is_name=True,
                modified=_date_of(str(getattr(episode, "published", "") or "")),
            )
        if row is not None:
            rows.append(row)
        if len(rows) >= MAX_TRACKS:
            break
    return rows


# -- open directories --------------------------------------------------------------


def looks_like_directory(page: str) -> bool:
    """True when *page* is a web server's plain index of a folder."""
    head = page[:4000].casefold()
    return (
        "index of /" in head
        or "directory listing for" in head
        or "parent directory" in head
        or "?c=n;o=d" in head
        or "?c=n&amp;o=d" in head
    )


def _size_of(text: str) -> int:
    """Bytes from "3.4M", "812K", "3412345" in the cell after a file's name."""
    for found in _SIZE.finditer(text):
        number, unit = float(found.group(1)), (found.group(2) or "").upper().rstrip("B").rstrip("I")
        factor = {"": 1, "K": 1024, "M": 1024**2, "G": 1024**3}.get(unit)
        if factor is None:
            continue
        # A bare number that is a year or a time fragment is not a size.
        if not unit and number < 1000:
            continue
        return int(number * factor)
    return 0


def _date_in(text: str) -> str:
    found = _DATE_ISO.search(text)
    if found:
        return " ".join(part for part in found.groups() if part)
    apache = _DATE_APACHE.search(text)
    if apache:
        day, month, year, clock = apache.groups()
        number = _MONTHS.get(month.casefold())
        if number:
            return " ".join(p for p in (f"{year}-{number:02d}-{int(day):02d}", clock) if p)
    return ""


def directory_tracks(page: str, base_url: str) -> list[PageStreamCandidate]:
    """The audio files a folder index lists, with the size and date it gives.

    Only files on the same site as *base_url* are kept (an index that links to
    another host is not an index of this folder), and the parent folder, the
    sort-order links and sub-folders are ignored.
    """
    base = urllib.parse.urlsplit(base_url)
    rows: list[PageStreamCandidate] = []
    seen: set[str] = set()
    matches = list(_ANCHOR.finditer(page))
    for number, match in enumerate(matches):
        href = html.unescape(match.group(2)).strip()
        if not href or href.startswith(("?", "#", "/?")) or href.endswith("/"):
            continue
        url = urllib.parse.urljoin(base_url, href)
        parts = urllib.parse.urlsplit(url)
        if parts.scheme not in ("http", "https") or parts.netloc.lower() != base.netloc.lower():
            continue
        if parts.query or url in seen:
            continue
        end = matches[number + 1].start() if number + 1 < len(matches) else len(page)
        tail = html.unescape(_TAG.sub(" ", page[match.end() : min(end, match.end() + 300)]))
        name = html.unescape(_TAG.sub("", match.group(3))).strip()
        name = urllib.parse.unquote(parts.path.rsplit("/", 1)[-1]) if name.endswith("..>") else name
        row = track(
            url,
            name,
            reason="a file in the open directory",
            size_bytes=_size_of(_DATE_ISO.sub(" ", _DATE_APACHE.sub(" ", tail))),
            modified=_date_in(tail),
        )
        if row is not None:
            seen.add(url)
            rows.append(row)
        if len(rows) >= MAX_TRACKS:
            break
    return rows


def parsed_when(modified: str) -> datetime | None:
    """A row's date as a datetime, or ``None`` (used by tests and sorting checks)."""
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(modified, fmt)
        except ValueError:
            continue
    return None
