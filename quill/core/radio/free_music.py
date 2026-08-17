"""Three keyless free-music sources: Audius, Mixcloud, and ccMixter.

One module rather than three because they are small, they share a fetch
chokepoint, and three near-identical 120-line files is how a codebase acquires
three slightly different retry policies. Each is independent and each can be
switched off on its own.

**Audius** -- independent music, no key at all. A client identifies itself with
an ``app_name`` parameter; that is identification, not authentication, so there
is no token to leak. Worth correcting an old note in ``radio.md``: the advice
used to be "fetch the discovery-node list from api.audius.co, pick one, query
it". As of 2026-08-13 that host answers with *itself* and serves the ``/v1``
routes directly, so the node-selection machinery is a fallback rather than the
happy path.

**Mixcloud, Mode A only** -- DJ sets, radio shows, specialty talk. The public
API gives categories, popular and latest with no key. **Quill Radio never
extracts a Mixcloud stream URL and never embeds their widget.** Activating a
show opens it on Mixcloud in the listener's own browser, and the row says so
before Enter is pressed rather than after. Browsing is metadata, which is
exactly what Mode A permits; playing is theirs.

**ccMixter** -- Creative Commons music, keyless, and the ideal shape: every row
carries a direct audio URL *and* an explicit licence, so nothing needs resolving
and nothing needs guessing about rights.

Each request funnels through the single reviewed egress site (:func:`_fetch` --
see ``quill/tools/network_egress_audit.py``), HTTPS-only over a verified TLS
context with a bounded timeout and size, reached only by an explicit browse
action, cached via :mod:`quill.core.radio.directory_cache`, and disabled in Safe
Mode via :func:`refuse_in_safe_mode`. wx-free, strict-typed.
"""

from __future__ import annotations

import http.client
import json
import ssl
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass

from quill import __version__
from quill.core.error_codes import CodedError
from quill.core.radio import directory_cache
from quill.core.radio.models import RadioStation

_USER_AGENT = f"QUILL-Radio/{__version__} (+https://github.com/Community-Access/quill)"
_TIMEOUT_SECONDS = 20.0
_MAX_BYTES = 4_000_000
_MAX_AGE_SECONDS = 6 * 3600

#: Audius identifies callers by name, not by key.
AUDIUS_APP_NAME = "QuillRadio"
_AUDIUS_HOST = "https://api.audius.co"
#: Audius publishes no genre-list endpoint; this is its documented enum, curated
#: like ``networks.py``'s catalog. An unknown genre returns nothing, not an error.
AUDIUS_GENRES: tuple[str, ...] = (
    "Electronic",
    "Rock",
    "Metal",
    "Alternative",
    "Hip-Hop/Rap",
    "Experimental",
    "Punk",
    "Folk",
    "Pop",
    "Ambient",
    "Soundtrack",
    "World",
    "Jazz",
    "Acoustic",
    "Funk",
    "R&B/Soul",
    "Devotional",
    "Classical",
    "Reggae",
    "Podcasts",
    "Country",
    "Spoken Word",
    "Comedy",
    "Blues",
    "Kids",
    "Audiobooks",
    "Latin",
)

_MIXCLOUD_HOST = "https://api.mixcloud.com"
_CCMIXTER_QUERY = "https://ccmixter.org/api/query"
#: ccMixter puts a copy of the result into an HTTP header, so a large page
#: size produces a header line over the 64 KB the standard library accepts and
#: the request dies before the body is read. 15 works, 20 does not (measured
#: 2026-08-13). This is a hard ceiling, not a preference.
CCMIXTER_MAX_LIMIT = 15

#: ccMixter tags worth offering as folders. Its tag space is open, so this is a
#: starting shelf rather than a taxonomy.
CCMIXTER_TAGS: tuple[str, ...] = (
    "jazz",
    "blues",
    "rock",
    "electronic",
    "ambient",
    "classical",
    "folk",
    "hiphop",
    "funk",
    "acoustic",
    "piano",
    "guitar",
    "instrumental",
    "chill",
    "experimental",
    "vocal",
)


class FreeMusicError(CodedError):
    """A free-music directory request failed (network, or Safe Mode refusal)."""

    code = "QUILL-RADIO-FREEMUSIC-REQUEST"


def refuse_in_safe_mode(safe_mode: bool) -> None:
    """Raise :class:`FreeMusicError` when Safe Mode is active."""
    if safe_mode:
        raise FreeMusicError(
            "These music directories are disabled in Safe Mode. "
            "Restart QUILL normally to browse them."
        )


#: ``http.client`` refuses a header line over 64 KB, and **ccMixter echoes its
#: entire JSON response back in an ``X-JSON`` header** -- 90 KB for a 15-row
#: page, measured 2026-08-16. The body it refuses to reach is perfectly good, so
#: every ccMixter tag failed on a cold cache while the same tag served fine from
#: a warm one, which is why this read as an intermittent outage for so long.
#: Raising the ceiling for our own reads is the whole fix; it is a *limit*, so a
#: larger value only ever permits more, and it stays bounded well under
#: ``_MAX_BYTES`` so a hostile server cannot use it to spend memory.
_MAX_HEADER_BYTES = 512_000


def _fetch(url: str) -> str:
    """One HTTPS GET -- the single reviewed egress site for all three sources."""
    if not url.startswith("https://"):
        raise FreeMusicError("Only https:// URLs can be fetched.")
    request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    context = ssl.create_default_context()
    previous_maxline = http.client._MAXLINE  # type: ignore[attr-defined]
    if previous_maxline < _MAX_HEADER_BYTES:
        http.client._MAXLINE = _MAX_HEADER_BYTES  # type: ignore[attr-defined]
    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS, context=context) as resp:
            payload: bytes = resp.read(_MAX_BYTES)
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
        raise FreeMusicError(f"Could not reach that music directory: {error}") from error
    finally:
        http.client._MAXLINE = previous_maxline  # type: ignore[attr-defined]
    return payload.decode("utf-8", errors="replace")


def _cached(key: str, build: Callable[[], list], *, refresh: bool = False) -> list:
    payload, _age = directory_cache.resolve(
        key, build, max_age_seconds=_MAX_AGE_SECONDS, refresh=refresh, empty=[]
    )
    return payload if isinstance(payload, list) else []


def _rows(payload: list) -> list[RadioStation]:
    return [
        RadioStation(
            name=str(row.get("name", "")),
            stream_url=str(row.get("url", "")),
            homepage=str(row.get("home", "")),
            tags=tuple(str(t) for t in row.get("tags", []) or []),
            source=str(row.get("src", "")),
            # Mixcloud rows are web pages, not recordings; the others are.
            is_recording=str(row.get("src", "")) in ("Audius", "ccMixter"),
        )
        for row in payload
        if isinstance(row, dict) and row.get("name") and row.get("url")
    ]


def _row(station: RadioStation) -> dict:
    return {
        "name": station.name,
        "url": station.stream_url,
        "home": station.homepage,
        "tags": list(station.tags),
        "src": station.source,
    }


# --- Audius -------------------------------------------------------------------


def parse_audius_tracks(json_text: str) -> list[RadioStation]:
    """Audius trending/track rows into playable stations (pure).

    The stream URL is the documented ``/v1/tracks/<id>/stream`` endpoint, which
    redirects to a content node. Gated tracks are dropped rather than listed and
    then refused at play time -- ``radio.md`` section 7 is right that paid
    content must never be presented as ordinary free content.
    """
    try:
        data = json.loads(json_text)
    except (ValueError, TypeError):
        return []
    rows = data.get("data") if isinstance(data, dict) else None
    stations: list[RadioStation] = []
    for track in rows if isinstance(rows, list) else []:
        if not isinstance(track, dict):
            continue
        track_id = str(track.get("id", "")).strip()
        title = str(track.get("title", "")).strip()
        if not track_id or not title:
            continue
        if track.get("is_streamable") is False or track.get("is_delete"):
            continue
        if track.get("is_stream_gated") or track.get("is_download_gated"):
            continue
        raw_user = track.get("user")
        user: dict = raw_user if isinstance(raw_user, dict) else {}
        artist = str(user.get("name", "") or "").strip()
        genre = str(track.get("genre", "") or "").strip()
        stations.append(
            RadioStation(
                name=f"{title} -- {artist}" if artist else title,
                stream_url=(
                    f"{_AUDIUS_HOST}/v1/tracks/{urllib.parse.quote(track_id)}/stream"
                    f"?app_name={AUDIUS_APP_NAME}"
                ),
                homepage=str(track.get("permalink", "") or ""),
                tags=(genre,) if genre else (),
                source="Audius",
                is_recording=True,
            )
        )
    return stations


def audius_trending(
    genre: str = "", *, limit: int = 60, safe_mode: bool = False, refresh: bool = False
) -> list[RadioStation]:
    """Audius trending tracks, optionally within *genre*."""
    refuse_in_safe_mode(safe_mode)
    params = {"app_name": AUDIUS_APP_NAME, "limit": max(1, min(limit, 100))}
    if genre.strip():
        params["genre"] = genre.strip()
    url = f"{_AUDIUS_HOST}/v1/tracks/trending?{urllib.parse.urlencode(params)}"
    payload = _cached(
        f"audius:trending:{genre.strip().lower()}",
        lambda: [_row(s) for s in parse_audius_tracks(_fetch(url))],
        refresh=refresh,
    )
    return _rows(payload)


def audius_search(
    query: str, *, limit: int = 40, safe_mode: bool = False, refresh: bool = False
) -> list[RadioStation]:
    """Audius tracks matching *query*.

    The same keyless endpoint family as trending, and the same parser: a search
    result and a trending result are the same object. Added because the browse
    tree offered Audius as a shelf you could only be handed things from, while
    the service has published a keyword search all along -- and "this cannot be
    searched" was a claim about somebody else's product that was not true.
    """
    refuse_in_safe_mode(safe_mode)
    text = query.strip()
    if not text:
        return []
    params = {
        "query": text,
        "app_name": AUDIUS_APP_NAME,
        "limit": max(1, min(limit, 100)),
    }
    url = f"{_AUDIUS_HOST}/v1/tracks/search?{urllib.parse.urlencode(params)}"
    payload = _cached(
        f"audius:search:{text.lower()}",
        lambda: [_row(s) for s in parse_audius_tracks(_fetch(url))],
        refresh=refresh,
    )
    return _rows(payload)


# --- Mixcloud (Mode A: metadata only) -----------------------------------------


@dataclass(frozen=True, slots=True)
class MixcloudCategory:
    """One Mixcloud category. ``fmt`` is ``music`` or ``talk``."""

    slug: str
    name: str
    fmt: str = "music"


def parse_mixcloud_categories(json_text: str) -> list[MixcloudCategory]:
    """Mixcloud's category list (pure). 28 music and 10 talk on 2026-08-13."""
    try:
        data = json.loads(json_text)
    except (ValueError, TypeError):
        return []
    rows = data.get("data") if isinstance(data, dict) else None
    categories: list[MixcloudCategory] = []
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict):
            continue
        name = str(row.get("name", "")).strip()
        slug = str(row.get("slug", "") or "").strip()
        if not name or not slug:
            continue
        categories.append(
            MixcloudCategory(slug=slug, name=name, fmt=str(row.get("format", "music")).strip())
        )
    return categories


def parse_mixcloud_shows(json_text: str) -> list[RadioStation]:
    """Mixcloud shows as rows whose "stream" is their **web page** (pure).

    Deliberately the page and not the audio: Mode A means Quill Radio never
    extracts a Mixcloud stream. The browse tree marks these rows so they say
    they open in a browser before the listener presses Enter.
    """
    try:
        data = json.loads(json_text)
    except (ValueError, TypeError):
        return []
    rows = data.get("data") if isinstance(data, dict) else None
    shows: list[RadioStation] = []
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict):
            continue
        name = str(row.get("name", "")).strip()
        url = str(row.get("url", "")).strip()
        if not name or not url.startswith("http"):
            continue
        raw_user = row.get("user")
        user: dict = raw_user if isinstance(raw_user, dict) else {}
        artist = str(user.get("name", "") or "").strip()
        shows.append(
            RadioStation(
                name=f"{name} -- {artist}" if artist else name,
                stream_url=url,
                homepage=url,
                source="Mixcloud",
            )
        )
    return shows


def mixcloud_categories(
    *, safe_mode: bool = False, refresh: bool = False
) -> list[MixcloudCategory]:
    """Every Mixcloud category, music and talk."""
    refuse_in_safe_mode(safe_mode)
    payload = _cached(
        "mixcloud:categories",
        lambda: [
            {"slug": c.slug, "name": c.name, "fmt": c.fmt}
            for c in parse_mixcloud_categories(_fetch(f"{_MIXCLOUD_HOST}/categories/"))
        ],
        refresh=refresh,
    )
    return [
        MixcloudCategory(str(r["slug"]), str(r["name"]), str(r.get("fmt", "music")))
        for r in payload
        if isinstance(r, dict) and r.get("slug") and r.get("name")
    ]


def mixcloud_shows(
    category: str, *, order: str = "popular", limit: int = 40, safe_mode: bool = False
) -> list[RadioStation]:
    """Shows in one category. *order* is ``popular`` or ``latest``."""
    refuse_in_safe_mode(safe_mode)
    slug = category.strip().strip("/").split("/")[-1]
    if not slug:
        return []
    kind = "latest" if order == "latest" else "popular"
    rows = max(1, min(limit, 100))
    url = f"{_MIXCLOUD_HOST}/discover/{urllib.parse.quote(slug)}/{kind}/?limit={rows}"
    payload = _cached(
        f"mixcloud:{slug}:{kind}", lambda: [_row(s) for s in parse_mixcloud_shows(_fetch(url))]
    )
    return _rows(payload)


def mixcloud_search(query: str, *, limit: int = 40, safe_mode: bool = False) -> list[RadioStation]:
    """Mixcloud shows matching *query*. **Still Mode A: metadata only.**

    Mixcloud publishes a keyword search, so the old "cannot be searched" was
    wrong. What remains true is the thing that actually governs this source: no
    stream URL is ever extracted, so a row is the show's page and opening it
    hands over to the browser. Searching changes how a row is *found* and
    nothing about what it is, which is why every caller must keep labelling
    these rows as opening on Mixcloud.
    """
    refuse_in_safe_mode(safe_mode)
    text = query.strip()
    if not text:
        return []
    params = {"q": text, "type": "cloudcast", "limit": max(1, min(limit, 100))}
    url = f"{_MIXCLOUD_HOST}/search/?{urllib.parse.urlencode(params)}"
    payload = _cached(
        f"mixcloud:search:{text.lower()}",
        lambda: [_row(s) for s in parse_mixcloud_shows(_fetch(url))],
    )
    return _rows(payload)


# --- ccMixter -----------------------------------------------------------------


def parse_ccmixter(json_text: str) -> list[RadioStation]:
    """ccMixter uploads into playable stations (pure).

    The response is a bare JSON array. Each upload carries its files with direct
    download URLs and an explicit licence name, so the licence rides along in
    the row's tags -- for Creative Commons material, showing the terms is the
    whole courtesy.
    """
    try:
        data = json.loads(json_text)
    except (ValueError, TypeError):
        return []
    stations: list[RadioStation] = []
    for upload in data if isinstance(data, list) else []:
        if not isinstance(upload, dict):
            continue
        name = str(upload.get("upload_name", "")).strip()
        artist = str(upload.get("user_name", "") or "").strip()
        licence = str(upload.get("license_name", "") or "").strip()
        audio = ""
        for entry in upload.get("files", []) or []:
            if not isinstance(entry, dict):
                continue
            url = str(entry.get("download_url", "")).strip()
            if url.lower().endswith((".mp3", ".ogg", ".flac", ".m4a")):
                audio = url
                break
        if not name or not audio:
            continue
        stations.append(
            RadioStation(
                name=f"{name} -- {artist}" if artist else name,
                stream_url=audio,
                homepage=str(upload.get("file_page_url", "") or ""),
                tags=(licence,) if licence else (),
                source="ccMixter",
                is_recording=True,
            )
        )
    return stations


def ccmixter_by_tag(
    tag: str, *, limit: int = CCMIXTER_MAX_LIMIT, safe_mode: bool = False
) -> list[RadioStation]:
    """Creative Commons uploads carrying *tag*."""
    refuse_in_safe_mode(safe_mode)
    if not tag.strip():
        return []
    params = urllib.parse.urlencode({
        "f": "json",
        "limit": max(1, min(limit, CCMIXTER_MAX_LIMIT)),
        "tags": tag.strip(),
    })
    payload = _cached(
        f"ccmixter:{tag.strip().lower()}",
        lambda: [_row(s) for s in parse_ccmixter(_fetch(f"{_CCMIXTER_QUERY}?{params}"))],
    )
    return _rows(payload)


def ccmixter_search(
    query: str, *, limit: int = CCMIXTER_MAX_LIMIT, safe_mode: bool = False
) -> list[RadioStation]:
    """Creative Commons uploads matching *query*.

    The same ``api/query`` endpoint the tag folders already use, with ``search``
    instead of ``tags`` -- so this was one parameter away the whole time, and
    the browse tree offering tags was a shelf rather than a limit.

    :data:`CCMIXTER_MAX_LIMIT` still applies and is still a hard ceiling rather
    than a preference: ccMixter echoes the result into an HTTP header, and a
    larger page produces a header line over the 64 KB the standard library
    accepts, which kills the request before the body is read.
    """
    refuse_in_safe_mode(safe_mode)
    text = query.strip()
    if not text:
        return []
    params = urllib.parse.urlencode({
        "f": "json",
        "limit": max(1, min(limit, CCMIXTER_MAX_LIMIT)),
        "search": text,
    })
    payload = _cached(
        f"ccmixter:search:{text.lower()}",
        lambda: [_row(s) for s in parse_ccmixter(_fetch(f"{_CCMIXTER_QUERY}?{params}"))],
    )
    return _rows(payload)
