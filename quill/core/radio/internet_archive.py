"""Internet Archive audio: Old Time Radio, concerts, lectures, at enormous scale.

No key, no account. The Archive is the single largest addition Quill Radio can
make, and it needs almost no browse tree invented for it, because **it already is
one**: every item declares its parent collections, and a collection is itself an
item. So one query shape walks the whole thing to any depth::

    collection:<id> AND mediatype:collection   -> the sub-collections
    collection:<id> AND mediatype:audio        -> the recordings

**Use advancedsearch.php, not the scrape endpoint.** An earlier draft of this
work specified ``services/search/v1/scrape``, and probing it found the answer to
one fixed question changing with the ``fields`` list *and* changing between runs
(8710, then 8849, and 0 whenever ``title`` was requested); in some runs it
ignored the ``mediatype`` clause altogether, which would have shown episodes
where the tree promised series. ``advancedsearch.php`` answered identically on
every repeat, pages cleanly to page 150 with no overlap, and honours the filter.
Measured 2026-08-13; the probe that found it lives in ``S:\\radio-probes``.

**A collection can list itself as a child.** The walker must carry a seen-set or
it recurses forever -- the first version of the probe walked one identifier into
itself twice. It is two lines to prevent and an afternoon to diagnose.

The Archive's automated-access policy is not optional and is honoured here: a
descriptive User-Agent identifying the tool and version, caching (browse levels
go through :mod:`quill.core.radio.directory_cache`), ``Retry-After`` respected on
HTTP 429 rather than retried blindly, and one request at a time. Rights metadata
is shown when an item publishes it, and it usually does not -- which is exactly
why the honest rule is "show what is published, never imply public domain".

Every request funnels through the single reviewed egress site (:func:`_fetch` --
see ``quill/tools/network_egress_audit.py``), HTTPS-only over a verified TLS
context with a bounded timeout and size, reached only by an explicit browse
action, and disabled in Safe Mode via :func:`refuse_in_safe_mode`. wx-free.
"""

from __future__ import annotations

import http.client
import json
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

from quill import __version__
from quill.core.error_codes import CodedError
from quill.core.radio import directory_cache
from quill.core.radio.models import RadioStation

_USER_AGENT = f"QUILL-Radio/{__version__} (+https://github.com/Community-Access/quill)"
_TIMEOUT_SECONDS = 25.0
_MAX_BYTES = 8_000_000

_SEARCH_URL = "https://archive.org/advancedsearch.php"
_METADATA_URL = "https://archive.org/metadata"
_DOWNLOAD_URL = "https://archive.org/download"
_DETAILS_URL = "https://archive.org/details"

#: The top-level collections offered as browse folders, curated by hand because
#: the Archive's own root is far too broad to be a starting point. Old Time Radio
#: is first deliberately: it is thousands of hours of exactly what this audience
#: seeks, organised as series with episodes, and if only one of these shipped it
#: should be that one. Dated 2026-08-13; identifiers change rarely.
ROOT_COLLECTIONS: tuple[tuple[str, str], ...] = (
    ("oldtimeradio", "Old Time Radio"),
    ("audio_bookspoetry", "Audiobooks & Poetry"),
    ("etree", "Live Music Archive"),
    ("radioprograms", "Radio Programs"),
    ("audio_podcast", "Podcasts"),
    ("audio_news", "News & Public Affairs"),
    ("audio_religion", "Religion & Spirituality"),
    ("audio_tech", "Computers & Technology"),
    ("opensource_audio", "Community Audio"),
)

#: Audio file extensions we will play, most preferred first.
_AUDIO_PREFERENCE = (".mp3", ".ogg", ".oga", ".m4a", ".flac", ".wav")

#: How many rows a folder shows before offering "More...".
PAGE_SIZE = 100

#: Browse levels change slowly; a day is generous and the Archive asks for
#: caching in as many words.
_MAX_AGE_SECONDS = 24 * 3600


class InternetArchiveError(CodedError):
    """An Internet Archive request failed (network, rate limit, or Safe Mode)."""

    code = "QUILL-RADIO-ARCHIVE-REQUEST"


@dataclass(frozen=True, slots=True)
class ArchiveItem:
    """One Archive item -- a sub-collection, or a recording."""

    identifier: str
    title: str
    is_collection: bool = False
    creator: str = ""
    year: str = ""

    @property
    def display_name(self) -> str:
        parts = [self.title or self.identifier]
        if self.creator:
            parts.append(self.creator)
        if self.year:
            parts.append(self.year)
        return " -- ".join(parts)

    @property
    def details_url(self) -> str:
        return f"{_DETAILS_URL}/{urllib.parse.quote(self.identifier)}"


def refuse_in_safe_mode(safe_mode: bool) -> None:
    """Raise :class:`InternetArchiveError` when Safe Mode is active."""
    if safe_mode:
        raise InternetArchiveError(
            "The Internet Archive is disabled in Safe Mode. Restart QUILL normally to browse it."
        )


# --- network -----------------------------------------------------------------


def _fetch(url: str) -> str:
    """One HTTPS GET of a public Archive endpoint -- the reviewed egress site.

    HTTP 429 is honoured rather than retried blindly: the Archive publishes a
    ``Retry-After`` and asking again immediately is how a polite client becomes
    a blocked one. We wait once, briefly, and then give up for this action --
    a browse folder that takes a minute is worse than one that says it could not
    load and offers Refresh.
    """
    if not url.startswith("https://"):
        raise InternetArchiveError("Only https:// URLs can be fetched.")
    request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    context = ssl.create_default_context()
    for attempt in (1, 2):
        try:
            with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS, context=context) as resp:
                payload: bytes = resp.read(_MAX_BYTES)
            return payload.decode("utf-8", errors="replace")
        except urllib.error.HTTPError as error:
            if error.code == 429 and attempt == 1:
                delay = _retry_after_seconds(error.headers.get("Retry-After"))
                time.sleep(delay)
                continue
            raise InternetArchiveError(
                f"The Internet Archive declined that request (HTTP {error.code})."
            ) from error
        except (
            urllib.error.URLError,
            TimeoutError,
            ssl.SSLError,
            OSError,
            # LineTooLong and friends are HTTPException, NOT OSError -- ccMixter
            # echoes a >64 KB HTTP header at larger page sizes, and without this
            # the exception escaped as an unhandled type and the branch went
            # silently empty instead of saying it could not load.
            http.client.HTTPException,
        ) as error:
            raise InternetArchiveError(f"Could not reach the Internet Archive: {error}") from error
    raise InternetArchiveError("The Internet Archive is rate-limiting us; try again shortly.")


def _retry_after_seconds(header: str | None) -> float:
    """Seconds to wait from a ``Retry-After`` header (pure), bounded.

    Capped at 10 seconds: honouring the header matters, blocking a browse tree
    for the two minutes a server might ask for does not.
    """
    try:
        return max(0.5, min(float(header or 2.0), 10.0))
    except (TypeError, ValueError):
        return 2.0


# --- pure parsers -------------------------------------------------------------


def parse_search(json_text: str) -> tuple[int, list[ArchiveItem]]:
    """``(numFound, items)`` from an advancedsearch response (pure).

    ``numFound`` is the child count a folder announces before it is opened, and
    it is why this endpoint is used rather than the scrape one, whose total was
    not stable.
    """
    try:
        data = json.loads(json_text)
    except (ValueError, TypeError):
        return 0, []
    response = data.get("response") if isinstance(data, dict) else None
    if not isinstance(response, dict):
        return 0, []
    docs = response.get("docs")
    items: list[ArchiveItem] = []
    for doc in docs if isinstance(docs, list) else []:
        if not isinstance(doc, dict):
            continue
        identifier = str(doc.get("identifier", "")).strip()
        if not identifier:
            continue
        items.append(
            ArchiveItem(
                identifier=identifier,
                title=str(doc.get("title", "") or identifier).strip(),
                is_collection=str(doc.get("mediatype", "")).strip() == "collection",
                creator=_first_str(doc.get("creator")),
                year=str(doc.get("year", "") or "").strip(),
            )
        )
    return int(response.get("numFound") or 0), items


def _first_str(value: object) -> str:
    """The Archive returns some fields as a string and some as a list of them."""
    if isinstance(value, list):
        return str(value[0]).strip() if value else ""
    return str(value or "").strip()


def parse_item_files(json_text: str, identifier: str) -> list[RadioStation]:
    """Playable files from an item's metadata (pure).

    Preference order is MP3, then Ogg, then anything else mpv accepts. Derivative
    files the Archive generates (``_64kb``, ``_spoken``) are kept: for a lot of
    old-time-radio uploads the derivative is the only usable copy.
    """
    try:
        data = json.loads(json_text)
    except (ValueError, TypeError):
        return []
    if not isinstance(data, dict):
        return []
    raw_metadata = data.get("metadata")
    metadata: dict = raw_metadata if isinstance(raw_metadata, dict) else {}
    rights = _rights_note(metadata)
    files = data.get("files")
    rows: list[tuple[int, str, str]] = []
    for entry in files if isinstance(files, list) else []:
        if not isinstance(entry, dict):
            continue
        name = str(entry.get("name", "")).strip()
        lowered = name.lower()
        for rank, extension in enumerate(_AUDIO_PREFERENCE):
            if lowered.endswith(extension):
                title = str(entry.get("title", "") or "").strip() or name.rsplit("/", 1)[-1]
                rows.append((rank, title, name))
                break
    rows.sort(key=lambda row: (row[0], row[1].lower()))
    stations: list[RadioStation] = []
    seen: set[str] = set()
    for _rank, title, name in rows:
        # One entry per logical track: the same recording in two formats should
        # not appear twice, and the preference sort means the first wins.
        key = title.rsplit(".", 1)[0].lower()
        if key in seen:
            continue
        seen.add(key)
        stations.append(
            RadioStation(
                name=title,
                stream_url=f"{_DOWNLOAD_URL}/{urllib.parse.quote(identifier)}/{urllib.parse.quote(name)}",
                homepage=f"{_DETAILS_URL}/{urllib.parse.quote(identifier)}",
                tags=(rights,) if rights else (),
                source="Internet Archive",
                # A recording, not a live mount: it seeks, reports position,
                # and remembers where you stopped.
                is_recording=True,
            )
        )
    return stations


def _rights_note(metadata: dict) -> str:
    """What the item says about its own rights, or ``""`` (pure).

    Most items publish nothing, which is precisely why this must never be
    filled in with an assumption. "No rights information published" is the
    truthful thing to show, and the caller says it.
    """
    for key in ("licenseurl", "rights", "usage"):
        value = _first_str(metadata.get(key))
        if value:
            return value
    return ""


# --- browse -------------------------------------------------------------------


def _search_url(query: str, *, rows: int, page: int) -> str:
    params = [
        ("q", query),
        ("fl[]", "identifier"),
        ("fl[]", "title"),
        ("fl[]", "mediatype"),
        ("fl[]", "creator"),
        ("fl[]", "year"),
        ("rows", str(rows)),
        ("page", str(page)),
        # A stable sort is what makes "page 2 does not repeat page 1" true.
        ("sort[]", "identifier asc"),
        ("output", "json"),
    ]
    return f"{_SEARCH_URL}?{urllib.parse.urlencode(params)}"


def children(
    collection: str,
    *,
    collections: bool,
    page: int = 1,
    safe_mode: bool = False,
    refresh: bool = False,
) -> tuple[int, list[ArchiveItem]]:
    """One page of a collection's children, and how many there are in total.

    *collections* selects sub-collections rather than recordings, which is what
    gives the tree its levels: the two sets are disjoint.
    """
    refuse_in_safe_mode(safe_mode)
    if not collection.strip():
        return 0, []
    mediatype = "collection" if collections else "audio"
    query = f"collection:{collection.strip()} AND mediatype:{mediatype}"
    key = f"archive:{mediatype}:{collection.strip()}:{page}"
    payload, _age = directory_cache.resolve(
        key,
        lambda: _as_json(parse_search(_fetch(_search_url(query, rows=PAGE_SIZE, page=page)))),
        max_age_seconds=_MAX_AGE_SECONDS,
        refresh=refresh,
        empty={"total": 0, "items": []},
    )
    return _from_json(payload)


def search(query: str, *, limit: int = 40, safe_mode: bool = False) -> list[ArchiveItem]:
    """Free-text search across the Archive's audio, for federated search.

    Same endpoint, same reviewed egress site and same parser as the browse tree
    -- this adds a query shape, not a new way out of the process. Scoped to
    ``mediatype:audio`` because a federated *radio* search that returned scanned
    books would be answering a question nobody asked.
    """
    refuse_in_safe_mode(safe_mode)
    wanted = query.strip()
    if not wanted:
        return []
    _total, items = parse_search(
        _fetch(_search_url(f"({wanted}) AND mediatype:audio", rows=max(1, limit), page=1))
    )
    return items


def item_files(identifier: str, *, safe_mode: bool = False) -> list[RadioStation]:
    """The playable files inside one item."""
    refuse_in_safe_mode(safe_mode)
    if not identifier.strip():
        return []
    url = f"{_METADATA_URL}/{urllib.parse.quote(identifier.strip())}"
    payload, _age = directory_cache.resolve(
        f"archive:item:{identifier.strip()}",
        lambda: [_station_to_json(s) for s in parse_item_files(_fetch(url), identifier.strip())],
        max_age_seconds=_MAX_AGE_SECONDS,
        empty=[],
    )
    return [_station_from_json(row) for row in payload if isinstance(row, dict)]


# --- cache serialisation ------------------------------------------------------


def _as_json(found: tuple[int, list[ArchiveItem]]) -> dict:
    total, items = found
    return {
        "total": total,
        "items": [
            {
                "id": item.identifier,
                "title": item.title,
                "collection": item.is_collection,
                "creator": item.creator,
                "year": item.year,
            }
            for item in items
        ],
    }


def _from_json(payload: object) -> tuple[int, list[ArchiveItem]]:
    if not isinstance(payload, dict):
        return 0, []
    items = []
    for row in payload.get("items", []) or []:
        if not isinstance(row, dict) or not row.get("id"):
            continue
        items.append(
            ArchiveItem(
                identifier=str(row["id"]),
                title=str(row.get("title", "")),
                is_collection=bool(row.get("collection")),
                creator=str(row.get("creator", "")),
                year=str(row.get("year", "")),
            )
        )
    return int(payload.get("total") or 0), items


def _station_to_json(station: RadioStation) -> dict:
    return {
        "name": station.name,
        "url": station.stream_url,
        "home": station.homepage,
        "tags": list(station.tags),
    }


def _station_from_json(row: dict) -> RadioStation:
    return RadioStation(
        name=str(row.get("name", "")),
        stream_url=str(row.get("url", "")),
        homepage=str(row.get("home", "")),
        tags=tuple(str(t) for t in row.get("tags", []) or []),
        source="Internet Archive",
        is_recording=True,
    )
