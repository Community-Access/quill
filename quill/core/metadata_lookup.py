"""Book metadata lookup from free public catalogs (Open Library, MusicBrainz).

Fills the Audio Studio's book-details fields from public records: search by
title and author, pick a result, and the tags land in the form. Ported from
ChapterForge (``s:\\code99\\forum``, MIT) onto QUILL's egress idioms.

Privacy: both APIs are free, keyless, and receive only the typed title/author.
Every request funnels through the single reviewed egress site
(:func:`_http_json` — see ``quill/tools/network_egress_audit.py``), HTTPS-only
with a verified TLS context, and runs only when the user presses the "Look up
book details" button (the UI states what will be contacted before the first
call). MusicBrainz asks for one request per second per IP; a module-level
throttle honors it. wx-free, strict-typed.
"""

from __future__ import annotations

import json
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from quill import __version__
from quill.core.error_codes import CodedError

_USER_AGENT = f"QUILL/{__version__} (https://github.com/Community-Access/quill)"
_MB_BASE = "https://musicbrainz.org/ws/2"
_OL_BASE = "https://openlibrary.org"
_OL_COVERS_BASE = "https://covers.openlibrary.org"
_TIMEOUT_SECONDS = 12.0
#: Anything smaller than this is Open Library's "no cover" placeholder, not art.
_MIN_COVER_BYTES = 1000

_last_musicbrainz_request: float = 0.0


class LookupError_(CodedError):
    """A lookup failed in a way worth telling the user about (network down)."""

    code = "QUILL-AUDIO-METADATA-LOOKUP"


@dataclass(slots=True)
class LookupResult:
    """One catalog match, ready to fill the book-details fields."""

    title: str
    author: str
    genre: str = ""
    year: str = ""
    series_title: str = ""
    source: str = ""
    score: int = 0
    #: Open Library cover id (``cover_i``); 0 when the match has no cover.
    cover_id: int = 0

    @property
    def display(self) -> str:
        """The accessible list row: title, author, year, source in one sentence."""
        parts = [self.title or "(untitled)"]
        if self.author:
            parts.append(f"by {self.author}")
        if self.year:
            parts.append(f"({self.year})")
        parts.append(f"— {self.source}")
        return " ".join(parts)


def _http_json(url: str) -> dict[str, object]:
    """One HTTPS GET returning decoded JSON — the reviewed egress site."""
    if not url.startswith("https://"):
        raise LookupError_("Refusing a non-HTTPS lookup request.")
    request = urllib.request.Request(
        url, headers={"User-Agent": _USER_AGENT, "Accept": "application/json"}
    )
    context = ssl.create_default_context()
    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS, context=context) as resp:
            payload = resp.read().decode("utf-8")
        parsed = json.loads(payload) if payload else {}
    except (urllib.error.URLError, TimeoutError, ssl.SSLError, ValueError) as error:
        raise LookupError_(f"Could not reach the catalog: {error}") from error
    return parsed if isinstance(parsed, dict) else {}


def _musicbrainz_get(path: str, params: dict[str, object]) -> dict[str, object]:
    """A MusicBrainz call honoring the 1-request-per-second courtesy limit."""
    global _last_musicbrainz_request
    elapsed = time.monotonic() - _last_musicbrainz_request
    if elapsed < 1.05:
        time.sleep(1.05 - elapsed)
    query = urllib.parse.urlencode({**params, "fmt": "json"})
    data = _http_json(f"{_MB_BASE}/{path}?{query}")
    _last_musicbrainz_request = time.monotonic()
    return data


def _lucene_escape(value: str) -> str:
    """Escape a term for MusicBrainz's Lucene query (backslash first, then quote)."""
    return value.replace("\\", "\\\\").replace('"', '\\"')


def search_musicbrainz(title: str, artist: str = "") -> list[LookupResult]:
    """Releases matching *title* (and optional *artist*); empty list on failure."""
    query_parts = [f'release:"{_lucene_escape(title)}"']
    if artist:
        query_parts.append(f'artist:"{_lucene_escape(artist)}"')
    try:
        data = _musicbrainz_get("release", {"query": " AND ".join(query_parts), "limit": 5})
    except LookupError_:
        return []
    return results_from_musicbrainz(data)


def results_from_musicbrainz(data: dict[str, object]) -> list[LookupResult]:
    """Parse a MusicBrainz release-search payload (pure; tolerant of junk)."""
    results: list[LookupResult] = []
    releases = data.get("releases")
    for release in releases if isinstance(releases, list) else []:
        if not isinstance(release, dict):
            continue
        credits_ = release.get("artist-credit") or []
        artist_name = ""
        if isinstance(credits_, list) and credits_ and isinstance(credits_[0], dict):
            artist_name = str(credits_[0].get("name", ""))
        results.append(
            LookupResult(
                title=str(release.get("title", "")),
                author=artist_name,
                year=str(release.get("date") or "")[:4],
                source="MusicBrainz",
                score=int(release.get("score", 0) or 0),
            )
        )
    return results


def search_open_library(title: str, author: str = "") -> list[LookupResult]:
    """Books matching *title* (and optional *author*); empty list on failure."""
    params: dict[str, object] = {
        "title": title,
        "limit": 5,
        "fields": "title,author_name,first_publish_year,subject,series,cover_i",
    }
    if author:
        params["author"] = author
    try:
        data = _http_json(f"{_OL_BASE}/search.json?{urllib.parse.urlencode(params)}")
    except LookupError_:
        return []
    return results_from_open_library(data, title)


def results_from_open_library(data: dict[str, object], title: str) -> list[LookupResult]:
    """Parse an Open Library search payload (pure; tolerant of junk)."""
    results: list[LookupResult] = []
    docs = data.get("docs")
    for doc in (docs if isinstance(docs, list) else [])[:5]:
        if not isinstance(doc, dict):
            continue
        authors = doc.get("author_name") or []
        subjects = doc.get("subject") or []
        series = doc.get("series") or []
        doc_title = str(doc.get("title", ""))
        results.append(
            LookupResult(
                title=doc_title,
                author=str(authors[0]) if authors else "",
                genre=str(subjects[0]) if subjects else "",
                year=str(doc.get("first_publish_year") or ""),
                series_title=str(series[0]) if series else "",
                source="Open Library",
                score=95 if doc_title.lower().strip() == title.lower().strip() else 75,
                cover_id=int(doc.get("cover_i") or 0),
            )
        )
    return results


def cover_url(cover_id: int) -> str:
    """The large-jacket URL for an Open Library *cover_id* (`?default=false`
    makes a missing cover a clean 404 instead of a placeholder image)."""
    return f"{_OL_COVERS_BASE}/b/id/{int(cover_id)}-L.jpg?default=false"


def fetch_cover(cover_id: int, target: Path) -> Path:
    """Download the Open Library jacket for *cover_id* to *target* (cover.jpg).

    Same consent posture as the search: free, keyless, called only from the
    explicit lookup flow after the user says yes. Raises :class:`LookupError_`
    when the cover is missing or unreachable.
    """
    if cover_id <= 0:
        raise LookupError_("That match has no cover image.")
    url = cover_url(cover_id)
    request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    context = ssl.create_default_context()
    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS, context=context) as resp:
            payload = bytes(resp.read())
    except (urllib.error.URLError, TimeoutError, ssl.SSLError) as error:
        raise LookupError_(f"Could not fetch the cover: {error}") from error
    if len(payload) < _MIN_COVER_BYTES:
        raise LookupError_("Open Library has no usable cover for that match.")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(payload)
    return target


def search(title: str, author: str = "", *, prefer_books: bool = True) -> list[LookupResult]:
    """Search both catalogs; merged best-first (books first for audiobooks)."""
    results: list[LookupResult] = []
    if prefer_books:
        results += search_open_library(title, author)
    results += search_musicbrainz(title, author)
    if not prefer_books:
        results += search_open_library(title, author)
    results.sort(key=lambda r: r.score, reverse=True)
    return results[:8]
