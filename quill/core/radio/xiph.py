"""Xiph / Icecast public directory (dir.xiph.org): browse the long-running,
keyless Icecast "yellow pages" of free internet radio, by genre, on demand.

The directory has no JSON/OPML API -- only server-rendered HTML -- so this reads
its public pages: ``/genres`` lists every genre, and ``/genres/<name>`` lists
that genre's station cards, each of which advertises a **directly playable**
stream URL in its Play button (no separate resolve step, unlike TuneIn/iHeart).
The two small regex parsers below are deliberately tolerant: a directory HTML
tweak degrades to "fewer/zero rows", never a crash.

Fetched on demand and refreshable (never bundled). One HTTPS GET per action to
``dir.xiph.org`` -- a single reviewed egress site (:func:`_fetch`, see
``quill/tools/network_egress_audit.py``) -- HTTPS-only over a verified TLS
context with a bounded timeout/size, disabled in Safe Mode via
:func:`refuse_in_safe_mode`. wx-free, strict-typed.
"""

from __future__ import annotations

import html as _html
import re
import ssl
import urllib.error
import urllib.request

from quill.core.error_codes import CodedError
from quill.core.radio import directory_cache
from quill.core.radio.models import RadioStation

_BASE = "https://dir.xiph.org"
_GENRES_URL = f"{_BASE}/genres"
_USER_AGENT: str | None = None
_TIMEOUT_SECONDS = 15.0
_MAX_BYTES = 4_000_000
#: The ``/genres`` index alone is far bigger than a genre page -- 5.3 MB and
#: growing on 2026-08-13 -- so the shared 4 MB cap was cutting it mid-tag and
#: silently discarding 412 genres, with the surviving count drifting run to run.
#: A separate, generous cap for the index; :func:`_fetch` now *detects* a
#: truncation rather than degrading quietly if the page ever outgrows this too.
_MAX_INDEX_BYTES = 24_000_000
#: How much of the index a *bounded* :func:`fetch_genres` reads. The index is
#: use-ordered, so the popular genres are all near the front: 512 KB arrives in
#: about a second and carries ~1,700 genres, where the full 5.3 MB page takes
#: about nine. Reading a prefix is only correct because we only ever wanted the
#: head -- see the ``allow_partial`` note in :func:`_fetch`.
_INDEX_HEAD_BYTES = 512_000

CATEGORY_LABEL = "Xiph"
#: Spoken/shown attribution for this genre catalog. It names the ordering
#: because :func:`fetch_genres` returns the most-used genres rather than all
#: 3,000-odd of them -- a listener hearing "120 genres" should know which 120.
CATALOG_CREDIT = "the Xiph/Icecast public directory, most popular first"

#: How many genres :func:`fetch_genres` offers by default. The directory serves
#: its index in descending use order, and past roughly this depth the tail is
#: one-off free-text strings a single station typed. Pass ``limit=0`` for all.
POPULAR_GENRE_LIMIT = 120

#: Strings the directory serves as genres that are not genres: an unset Icecast
#: field, and the tail of an HTML entity that some stations put in the name
#: (``R&amp;B`` mis-split). Small and explicit rather than clever -- each entry
#: was observed in the live index.
_NOT_A_GENRE = frozenset({"null", "none", "n/a", "unknown", "amp", "and", "the"})

#: A genre that is really a frequency or a station name: ``104.5``,
#: ``103.9 Radyo Natin FM - Pinamungajan``.
_FREQUENCY_RE = re.compile(r"^\d{2,3}[.,]\d")
#: A genre that is entirely digits and punctuation: ``00``, ``100``, ``1989``.
_NUMERIC_RE = re.compile(r"^[\d\s.,'\-]+$")

#: A genre link on the /genres index: ``/genres/<name>``.
_GENRE_LINK_RE = re.compile(r'href="/genres/([^"/]+)"', re.IGNORECASE)
#: One station card: its title, then the first Play button's stream URL. The
#: non-greedy span stops at the card's own Play button.
_CARD_RE = re.compile(
    r'<h5[^>]*class="card-title"[^>]*>(?P<title>.*?)</h5>.*?'
    r'<a[^>]+href="(?P<url>https?://[^"]+)"[^>]*class="btn btn-sm btn-primary"',
    re.IGNORECASE | re.DOTALL,
)
#: The codec badge inside a card (best-effort; ``""`` if absent).
_CODEC_RE = re.compile(r'href="/codecs/([^"]+)"', re.IGNORECASE)


class XiphError(CodedError):
    """A Xiph/Icecast directory request failed (network, or Safe Mode refusal)."""

    code = "QUILL-RADIO-XIPH-REQUEST"


def refuse_in_safe_mode(safe_mode: bool) -> None:
    """Raise :class:`XiphError` when Safe Mode is active."""
    if safe_mode:
        raise XiphError(
            "The Xiph/Icecast directory is disabled in Safe Mode. "
            "Restart QUILL normally to browse it."
        )


# --- pure parsers -----------------------------------------------------------


def is_useful_genre(name: str) -> bool:
    """True when *name* is a genre a listener could want to browse (pure).

    Icecast's genre field is free text, so the directory's index is part real
    taxonomy and part whatever three thousand broadcasters typed. This drops the
    entries that are certainly not genres -- an unset field, a frequency, a bare
    number, a station name, a sentence -- and keeps everything else, including
    odd-but-real ones like ``Smooth`` or ``Pinoy``. Deliberately conservative:
    dropping a real genre is worse than keeping an odd one.
    """
    value = name.strip()
    if len(value) < 2 or len(value) > 28:
        return False
    if value.casefold() in _NOT_A_GENRE:
        return False
    if _NUMERIC_RE.match(value) or _FREQUENCY_RE.match(value):
        return False
    return value.count(" ") < 3  # "Deep House" yes; a whole station strapline no


def parse_genres(page_html: str) -> list[str]:
    """Genre names from the ``/genres`` index (pure), **in the directory's own
    order**, de-duplicated case-insensitively and filtered to plausible genres.

    The order matters and was previously thrown away. ``dir.xiph.org`` serves
    the index in descending use order -- ``various, Pop, Rock, Dance, 80s,
    House, Oldies, ...`` -- which is exactly the order a browse list wants.
    Sorting it alphabetically, as this function used to, put ``00``, ``00s`` and
    ``100.1`` at the top and buried Jazz three thousand rows down.

    De-duplication is case-insensitive (the directory lists both ``Pop`` and
    ``pop``) and keeps the first spelling seen, which under source order is the
    more-used one. Filtering is :func:`is_useful_genre`.

    The href segment is percent-encoded (``/genres/%C3%89clectique``), so it is
    URL-decoded to the real genre name here -- :func:`fetch_genre_stations` then
    re-encodes it exactly once when building the page URL."""
    import urllib.parse

    seen: dict[str, str] = {}
    for raw in _GENRE_LINK_RE.findall(page_html):
        name = _html.unescape(urllib.parse.unquote(raw)).strip()
        key = name.casefold()
        if name and key not in seen and is_useful_genre(name):
            seen[key] = name
    return list(seen.values())


def genre_display(name: str) -> str:
    """A human genre label (pure): ``80s`` stays ``80s``, ``jazz`` -> ``Jazz``."""
    return name if name.isupper() or any(c.isdigit() for c in name) else name.title()


def parse_stations(page_html: str) -> list[RadioStation]:
    """Playable stations from a genre page's cards (pure).

    Each card yields a title and the directly playable stream URL from its Play
    button; duplicate stream URLs are collapsed (first title wins). A card
    without a recognisable Play link is skipped."""
    stations: list[RadioStation] = []
    seen: set[str] = set()
    for match in _CARD_RE.finditer(page_html):
        url = match.group("url").strip()
        if not url or url in seen:
            continue
        title = _html.unescape(re.sub(r"<[^>]+>", "", match.group("title"))).strip()
        if not title:
            continue
        seen.add(url)
        codec = _CODEC_RE.search(page_html[match.start() : match.end()])
        stations.append(
            RadioStation(
                name=title,
                stream_url=url,
                station_uuid="",
                country="",
                tags=(CATEGORY_LABEL,),
                codec=codec.group(1).upper() if codec else "",
                source=CATEGORY_LABEL,
            )
        )
    return stations


# --- network ----------------------------------------------------------------


def _user_agent() -> str:
    global _USER_AGENT
    if _USER_AGENT is None:
        from quill import __version__

        _USER_AGENT = f"QUILL/{__version__} (https://github.com/Community-Access/quill)"
    return _USER_AGENT


def _fetch(url: str, *, max_bytes: int = _MAX_BYTES, allow_partial: bool = False) -> str:
    """One HTTPS GET of a public dir.xiph.org page -- the reviewed egress site.

    Reads one byte past *max_bytes* so an over-long page is **detected** rather
    than silently handed to a tolerant parser as a truncated document. That
    tolerance is right for a directory HTML tweak and wrong for a size cap: it
    turned "the index grew past 4 MB" into "some genres quietly disappeared,
    and the count changes every refresh".

    *allow_partial* is the one case where a prefix is correct rather than a bug:
    :func:`fetch_genres` asking only for the head of a use-ordered index it has
    no intention of reading to the end. A caller that wants the whole document
    leaves it False and gets an error instead of a quiet half.
    """
    if not url.startswith("https://"):
        raise XiphError("Only https:// URLs can be fetched.")
    request = urllib.request.Request(url, headers={"User-Agent": _user_agent()})
    context = ssl.create_default_context()
    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS, context=context) as resp:
            payload: bytes = resp.read(max_bytes if allow_partial else max_bytes + 1)
    except (urllib.error.URLError, TimeoutError, ssl.SSLError, OSError) as error:
        raise XiphError(f"Could not reach the Xiph directory: {error}") from error
    if not allow_partial and len(payload) > max_bytes:
        raise XiphError(
            f"The Xiph directory page is larger than {max_bytes} bytes, so it was not read. "
            "Reading part of it would silently drop entries."
        )
    return payload.decode("utf-8", errors="replace")


#: Cache key for the genre index. One key whatever the caller's ``limit``: the
#: list is stored whole (or marked incomplete) and sliced per call, so asking
#: for 120 and later for all of them does not fetch the page twice.
_GENRES_CACHE_KEY = "xiph:genres"


def _fetch_genre_index(limit: int) -> tuple[list[str], bool]:
    """Read the genre index; return its genres and whether that is all of them.

    A bounded call reads only the head, which is what makes it fast: the whole
    5.3 MB page takes about nine seconds, its first 512 KB about one, and that
    prefix already carries well over a thousand genres. If the prefix yields
    fewer than *limit*, the full page is read rather than a short list being
    passed off as the answer.
    """
    if limit > 0:
        head = parse_genres(_fetch(_GENRES_URL, max_bytes=_INDEX_HEAD_BYTES, allow_partial=True))
        if len(head) >= limit:
            return head, False
    return parse_genres(_fetch(_GENRES_URL, max_bytes=_MAX_INDEX_BYTES)), True


def fetch_genres(
    *, safe_mode: bool = False, limit: int = POPULAR_GENRE_LIMIT, refresh: bool = False
) -> list[str]:
    """The directory's most-used genres, cached between sessions.

    Bounded on purpose. The index carries roughly 3,400 genres, nearly all of
    them one-off free text a single broadcaster typed, and a browse list of
    3,400 folders is not a browse list. *limit* takes the head of the
    directory's own use-ordered index; ``limit=0`` returns every genre that
    passes :func:`is_useful_genre`, for a caller that wants to page or group
    them itself. ``CATALOG_CREDIT`` names the ordering so the count a listener
    hears is not mistaken for the whole directory.

    Cached for a day (:mod:`quill.core.radio.directory_cache`), so opening the
    Xiph branch a second time is instant rather than a multi-second wait on a
    5.3 MB page. *refresh* is what a node's Refresh command passes; a refresh
    that fails keeps the previous list rather than blanking the branch. Use
    :func:`fetch_genres_with_age` when the caller wants to say how old it is.
    """
    genres, _age = fetch_genres_with_age(safe_mode=safe_mode, limit=limit, refresh=refresh)
    return genres


def fetch_genres_with_age(
    *, safe_mode: bool = False, limit: int = POPULAR_GENRE_LIMIT, refresh: bool = False
) -> tuple[list[str], float | None]:
    """:func:`fetch_genres`, plus how old the answer is in seconds.

    ``None`` means it was fetched live just now; a float means it came from the
    cache and the caller should say so -- :func:`directory_cache.spoken_age`
    turns it into words. Telling a listener the list is from yesterday costs one
    clause, and is the difference between a cache and a quiet lie.
    """
    refuse_in_safe_mode(safe_mode)
    fetched_complete = True

    def _fetch_now() -> list[str]:
        nonlocal fetched_complete
        genres, fetched_complete = _fetch_genre_index(limit)
        return genres

    payload, age = directory_cache.resolve(
        _GENRES_CACHE_KEY,
        _fetch_now,
        refresh=refresh,
        require_complete=limit <= 0,
        # A callable, not the value: whether the read was complete is only known
        # once _fetch_now has run, and by-value would bind it before the fetch.
        complete=lambda: fetched_complete,
        empty=[],
    )
    genres = [str(name) for name in payload] if isinstance(payload, list) else []
    return (genres[:limit] if limit > 0 else genres), age


def fetch_genre_stations(genre: str, *, safe_mode: bool = False) -> list[RadioStation]:
    """Every station in one genre, fetched fresh (Refresh re-calls this)."""
    refuse_in_safe_mode(safe_mode)
    if not genre.strip():
        return []
    return parse_stations(_fetch(f"{_GENRES_URL}/{urllib_quote(genre.strip())}"))


def urllib_quote(value: str) -> str:
    """URL-quote a genre segment (its own helper so the path build stays clear)."""
    import urllib.parse

    return urllib.parse.quote(value, safe="")
