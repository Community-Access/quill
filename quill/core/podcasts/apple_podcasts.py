"""Apple Podcasts as a browsable directory -- keyless, and the only one we use.

`itunes_search.py` already finds a show by name without a key. This is the other
half: **browse**, for the listener who cannot name what they want. Everyone
reaches for ``itunes.apple.com/search``, which demands a ``term`` and offers no
way to enumerate, and concludes Apple cannot be browsed. That is the wrong door.
Apple publishes two other endpoints that together form a complete tree, both
public, both keyless, both verified live on 2026-08-13:

* **The genre tree** -- ``MZStoreServices.woa/ws/genres?id=26`` returns the whole
  podcast taxonomy as nested JSON, each node carrying ``name``, ``id``, and its
  own ``subgenres``. Id 26 is Podcasts; 1301 is Arts, with Books (1482) and
  Design (1402) beneath it; 1303 is Comedy.
* **The charts** -- ``rss.marketingtools.apple.com/api/v2/<storefront>/podcasts/
  top/<n>/podcasts.json`` returns the top shows for any storefront, which is the
  axis almost no desktop client offers: the top podcasts in Ireland or Japan are
  one substitution away.

A chart row carries Apple's collection id, not a feed, so the last hop is
``itunes.apple.com/lookup?id=<id>&entity=podcast``, which returns ``feedUrl``.
That is done **lazily, on activation** -- the same shape as ``iheart.py``'s
"resolve on demand, never bulk-fetch thousands of pages to refresh a list".

And that is where Apple stops being involved. The chain ends at an RSS feed,
which ``feed_reader.py`` parses and whose ``<podcast:transcript>`` tag
``transcripts.py`` fetches. Apple is a way to find the feed and nothing more, so
switching this source off costs discovery and never playback.

**Podcast Index is deliberately not used anywhere in QUILL.** Jeff's decision,
2026-08-13: iTunes for everything. Nothing here needs a key, an account, or a
registration, and no transcript, subscription, or episode depends on a directory
-- see the chain above. Do not add a Podcast Index client "as an option"; the
point of a single keyless directory is that there is no second path to maintain,
no key to configure, and no feature that quietly requires one.

These are Apple's own public marketing and store-services endpoints, read as
published, returning only what Apple already serves to its own web surfaces --
the same standard under which the TuneIn OPML and iHeart sitemap integrations
cleared review (see :mod:`quill.core.radio.tunein`, approved 2026-07-17). Not a
scrape of a competitor's data files.

Every request funnels through the single reviewed egress site (:func:`_fetch` --
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
from dataclasses import dataclass, field

from quill import __version__
from quill.core.error_codes import CodedError
from quill.core.radio import directory_cache

_USER_AGENT = f"QUILL/{__version__} (https://github.com/Community-Access/quill)"
_TIMEOUT_SECONDS = 15.0
_MAX_BYTES = 4_000_000

#: Apple's store-services genre tree. Id 26 is the Podcasts root.
_GENRES_URL = "https://itunes.apple.com/WebObjects/MZStoreServices.woa/ws/genres?id=26"
PODCASTS_GENRE_ID = "26"
#: Per-storefront chart feeds. ``{storefront}`` is a two-letter code, ``{count}``
#: is how many rows (Apple serves 10, 25, 50, 100).
_CHARTS_URL = (
    "https://rss.marketingtools.apple.com/api/v2/{storefront}/podcasts/top/{count}/{kind}.json"
)
#: The two chart kinds Apple publishes. ``podcasts`` is shows; the second is the
#: top individual *episodes* in a storefront, which is a different and often more
#: useful question -- "what is everyone listening to right now" rather than
#: "which shows are big". Confirmed live on 2026-08-13.
CHART_SHOWS = "podcasts"
CHART_EPISODES = "podcast-episodes"
CHART_KINDS: tuple[tuple[str, str], ...] = (
    (CHART_SHOWS, "Top Podcasts"),
    (CHART_EPISODES, "Top Episodes"),
)
_LOOKUP_URL = "https://itunes.apple.com/lookup"

#: Storefronts offered as the first browse level, in display order. Apple has
#: ~175; these are the ones an English-speaking, accessibility-focused audience
#: actually asks for, plus the large markets. A listener wanting another can
#: still pass any two-letter code -- this list is the menu, not the limit.
DEFAULT_STOREFRONTS: tuple[tuple[str, str], ...] = (
    ("us", "United States"),
    ("gb", "United Kingdom"),
    ("ca", "Canada"),
    ("au", "Australia"),
    ("ie", "Ireland"),
    ("nz", "New Zealand"),
    ("de", "Germany"),
    ("fr", "France"),
    ("es", "Spain"),
    ("it", "Italy"),
    ("mx", "Mexico"),
    ("br", "Brazil"),
    ("jp", "Japan"),
    ("in", "India"),
    ("se", "Sweden"),
    ("nl", "Netherlands"),
)

#: How many chart rows a genre node offers. Apple accepts 10/25/50/100.
DEFAULT_CHART_COUNT = 100

#: Cache windows. The taxonomy changes a few times a year; charts change daily.
_GENRES_MAX_AGE = 7 * 24 * 3600
_CHARTS_MAX_AGE = 6 * 3600


class ApplePodcastsError(CodedError):
    """An Apple Podcasts directory request failed (network, or Safe Mode)."""

    code = "QUILL-PODCASTS-APPLE-DIRECTORY"


@dataclass(frozen=True, slots=True)
class AppleGenre:
    """One node of Apple's podcast taxonomy."""

    genre_id: str
    name: str
    subgenres: tuple[AppleGenre, ...] = field(default_factory=tuple)

    @property
    def has_children(self) -> bool:
        return bool(self.subgenres)


@dataclass(frozen=True, slots=True)
class AppleShow:
    """One podcast from a chart. ``feed_url`` is filled in lazily."""

    collection_id: str
    name: str
    artist: str = ""
    artwork_url: str = ""
    page_url: str = ""
    genre_ids: tuple[str, ...] = ()
    explicit: bool = False
    feed_url: str = ""

    @property
    def display_name(self) -> str:
        return f"{self.name} -- {self.artist}" if self.artist else self.name

    @property
    def spoken_note(self) -> str:
        """What the row says beyond its name, so nothing surprises after Enter."""
        parts = []
        if self.explicit:
            parts.append("explicit")
        parts.append("opens its feed" if not self.feed_url else "ready to play")
        return ", ".join(parts)


def refuse_in_safe_mode(safe_mode: bool) -> None:
    """Raise :class:`ApplePodcastsError` when Safe Mode is active."""
    if safe_mode:
        raise ApplePodcastsError(
            "The Apple Podcasts directory is disabled in Safe Mode. "
            "Restart QUILL normally to browse it."
        )


# --- pure parsers ------------------------------------------------------------


def parse_genres(json_text: str) -> list[AppleGenre]:
    """Apple's nested genre tree into :class:`AppleGenre` (pure).

    The document is keyed by genre id at every level, with children under
    ``subgenres``. Only the Podcasts root (26) is walked, so a document that
    also carries music or app genres contributes nothing unexpected. Tolerant:
    a malformed document, or a node missing a name, yields fewer rows -- never
    an exception.
    """
    try:
        data = json.loads(json_text)
    except (ValueError, TypeError):
        return []
    if not isinstance(data, dict):
        return []
    root = data.get(PODCASTS_GENRE_ID)
    if not isinstance(root, dict):
        return []
    return _genre_children(root)


def _genre_children(node: dict) -> list[AppleGenre]:
    subgenres = node.get("subgenres")
    if not isinstance(subgenres, dict):
        return []
    genres: list[AppleGenre] = []
    for key, child in subgenres.items():
        if not isinstance(child, dict):
            continue
        name = str(child.get("name", "")).strip()
        if not name:
            continue
        genre_id = str(child.get("id") or key).strip()
        genres.append(AppleGenre(genre_id, name, tuple(_genre_children(child))))
    # Apple's JSON object order is its own display order; keep it rather than
    # sorting, for the same reason the Xiph index order is kept.
    return genres


def parse_charts(json_text: str) -> list[AppleShow]:
    """A storefront chart feed into :class:`AppleShow` rows (pure)."""
    try:
        data = json.loads(json_text)
    except (ValueError, TypeError):
        return []
    feed = data.get("feed") if isinstance(data, dict) else None
    results = feed.get("results") if isinstance(feed, dict) else None
    if not isinstance(results, list):
        return []
    shows: list[AppleShow] = []
    for row in results:
        if not isinstance(row, dict):
            continue
        collection_id = str(row.get("id", "")).strip()
        name = str(row.get("name", "")).strip()
        if not collection_id or not name:
            continue
        genre_ids = tuple(
            str(genre.get("genreId", "")).strip()
            for genre in row.get("genres", []) or []
            if isinstance(genre, dict) and genre.get("genreId")
        )
        shows.append(
            AppleShow(
                collection_id=collection_id,
                name=name,
                artist=str(row.get("artistName", "")).strip(),
                artwork_url=str(row.get("artworkUrl100", "")).strip(),
                page_url=str(row.get("url", "")).strip(),
                genre_ids=genre_ids,
                # Apple spells this "Explict" in its own feed. Match both.
                explicit=str(row.get("contentAdvisoryRating", "")).lower().startswith("expl"),
            )
        )
    return shows


def parse_feed_url(json_text: str) -> str:
    """The ``feedUrl`` from a lookup response (pure), or ``""``.

    Empty rather than an error for "no such id": a stale chart row degrades to
    "could not open that show" instead of a raised exception in a browse tree.
    """
    return parse_show_details(json_text).feed_url


@dataclass(frozen=True, slots=True)
class ShowDetails:
    """What one lookup row says about a show, beyond the feed itself.

    Artwork and homepage exist so Subscribe can hand them to the shared
    podcast library: a show followed from Quill Radio used to arrive in
    Quill Cast as a bare title -- no tile, no site link -- because the
    subscribe path threw these fields away. Field spellings mirror
    ``itunes_search.PodcastSearchResult`` (artworkUrl600 first, homepage
    from collectionViewUrl) so both apps describe a show the same way.
    """

    feed_url: str = ""
    artwork_url: str = ""
    homepage: str = ""


def parse_show_details(json_text: str) -> ShowDetails:
    """Feed, artwork and homepage from a lookup response (pure).

    All-empty rather than an error for "no such id", for the same reason
    :func:`parse_feed_url` answers ``""``.
    """
    try:
        data = json.loads(json_text)
    except (ValueError, TypeError):
        return ShowDetails()
    results = data.get("results") if isinstance(data, dict) else None
    if not isinstance(results, list):
        return ShowDetails()
    for row in results:
        if isinstance(row, dict):
            feed = str(row.get("feedUrl", "")).strip()
            if feed.startswith(("http://", "https://")):
                return ShowDetails(
                    feed_url=feed,
                    artwork_url=str(row.get("artworkUrl600") or row.get("artworkUrl100") or ""),
                    homepage=str(row.get("collectionViewUrl", "")),
                )
    return ShowDetails()


def genres_in(genres: list[AppleGenre], genre_id: str) -> AppleGenre | None:
    """Find a genre anywhere in the tree by id (pure), or ``None``."""
    for genre in genres:
        if genre.genre_id == genre_id:
            return genre
        found = genres_in(list(genre.subgenres), genre_id)
        if found is not None:
            return found
    return None


def genre_id_set(genre: AppleGenre) -> frozenset[str]:
    """*genre*'s id plus every descendant's (pure).

    Needed because a chart row is tagged with the **leaf** genre, not its
    ancestors: a show under Arts > Books carries ``1482`` and never ``1301``.
    Matching a top-level genre against raw row tags therefore finds nothing,
    which is exactly what the first live run of this module did -- "Arts, 0
    shows" against a chart full of arts podcasts.
    """
    ids = {genre.genre_id}
    for child in genre.subgenres:
        ids |= genre_id_set(child)
    return frozenset(ids)


def storefront_name(code: str) -> str:
    """A storefront's display name (pure), falling back to the code itself."""
    lowered = code.strip().lower()
    for candidate, name in DEFAULT_STOREFRONTS:
        if candidate == lowered:
            return name
    return code.strip().upper()


# --- network -----------------------------------------------------------------


def _fetch(url: str) -> str:
    """One HTTPS GET of a public Apple endpoint -- the reviewed egress site."""
    if not url.startswith("https://"):
        raise ApplePodcastsError("Only https:// URLs can be fetched.")
    request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    context = ssl.create_default_context()
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
        raise ApplePodcastsError(f"Could not reach Apple Podcasts: {error}") from error
    return payload.decode("utf-8", errors="replace")


def fetch_genres(*, safe_mode: bool = False, refresh: bool = False) -> list[AppleGenre]:
    """Apple's podcast genre tree, cached for a week.

    The taxonomy changes a few times a year, so refetching it on every browse
    is pure waste. A failed refresh keeps the previous tree rather than blanking
    the branch.
    """
    refuse_in_safe_mode(safe_mode)
    payload, _age = directory_cache.resolve(
        "apple:genres",
        lambda: _genres_as_json(_fetch(_GENRES_URL)),
        max_age_seconds=_GENRES_MAX_AGE,
        refresh=refresh,
        empty=[],
    )
    return _genres_from_json(payload)


def fetch_charts(
    storefront: str = "us",
    *,
    genre_id: str = "",
    kind: str = CHART_SHOWS,
    count: int = DEFAULT_CHART_COUNT,
    safe_mode: bool = False,
    refresh: bool = False,
) -> list[AppleShow]:
    """The top shows for *storefront*, optionally filtered to *genre_id*.

    Apple's chart feed is per-storefront, not per-genre, so a genre node filters
    the storefront chart by the ``genres`` each row already carries. That is one
    request for every genre in a storefront rather than one per genre, which is
    both faster and considerably politer.

    The filter matches *genre_id* **or any of its descendants**, because a chart
    row is tagged with its leaf genre and never its ancestors -- see
    :func:`genre_id_set`. Filtering on the bare id finds nothing for every
    top-level genre, which is the whole first level of the tree.
    """
    refuse_in_safe_mode(safe_mode)
    rows = max(10, min(int(count), 100))
    chart = kind if kind in (CHART_SHOWS, CHART_EPISODES) else CHART_SHOWS
    key = f"apple:charts:{storefront.strip().lower()}:{rows}:{chart}"
    url = _CHARTS_URL.format(
        storefront=urllib.parse.quote(storefront.strip().lower()), count=rows, kind=chart
    )
    payload, _age = directory_cache.resolve(
        key,
        lambda: _shows_as_json(parse_charts(_fetch(url))),
        max_age_seconds=_CHARTS_MAX_AGE,
        refresh=refresh,
        empty=[],
    )
    shows = _shows_from_json(payload)
    wanted = genre_id.strip()
    if not wanted:
        return shows
    node = genres_in(fetch_genres(safe_mode=safe_mode), wanted)
    accepted = genre_id_set(node) if node is not None else frozenset({wanted})
    return [show for show in shows if accepted.intersection(show.genre_ids)]


def resolve_feed_url(collection_id: str, *, safe_mode: bool = False) -> str:
    """The RSS feed URL behind an Apple collection id (one keyless GET).

    Cached indefinitely-ish (a show's feed URL almost never changes) because
    this is on the activation path: a listener pressing Enter on a chart row
    should not wait for a round trip they already paid for.

    Returns ``""`` rather than raising when the id is unknown, so a stale chart
    row degrades to "could not open that show".
    """
    refuse_in_safe_mode(safe_mode)
    identifier = collection_id.strip()
    if not identifier:
        return ""
    params = urllib.parse.urlencode({"id": identifier, "entity": "podcast"})
    payload, _age = directory_cache.resolve(
        f"apple:feed:{identifier}",
        lambda: parse_feed_url(_fetch(f"{_LOOKUP_URL}?{params}")),
        max_age_seconds=30 * 24 * 3600,
        empty="",
    )
    return str(payload or "")


def resolve_show_details(collection_id: str, *, safe_mode: bool = False) -> ShowDetails:
    """Feed, artwork and homepage behind a collection id (one keyless GET).

    The same lookup request :func:`resolve_feed_url` makes, kept as its own
    cache entry (``apple:show:``) so existing feed-only cache entries stay
    valid. Subscribe uses this one: the extra two fields are what let the
    shared library show a tile and a site link in Quill Cast.
    """
    refuse_in_safe_mode(safe_mode)
    identifier = collection_id.strip()
    if not identifier:
        return ShowDetails()
    params = urllib.parse.urlencode({"id": identifier, "entity": "podcast"})
    payload, _age = directory_cache.resolve(
        f"apple:show:{identifier}",
        lambda: _details_as_dict(parse_show_details(_fetch(f"{_LOOKUP_URL}?{params}"))),
        max_age_seconds=30 * 24 * 3600,
        empty={},
    )
    data = payload if isinstance(payload, dict) else {}
    return ShowDetails(
        feed_url=str(data.get("feed", "")),
        artwork_url=str(data.get("artwork", "")),
        homepage=str(data.get("homepage", "")),
    )


def _details_as_dict(details: ShowDetails) -> dict:
    if not details.feed_url:
        # An unknown id answers the ``empty`` sentinel, exactly as the
        # feed-only resolver answers "" -- not a 30-day cache of nothing.
        return {}
    return {
        "feed": details.feed_url,
        "artwork": details.artwork_url,
        "homepage": details.homepage,
    }


# --- cache serialisation ------------------------------------------------------
# The cache stores JSON, so the dataclasses go through plain dict forms. Kept
# here rather than as dataclass methods so the models stay dumb.


def _genres_as_json(json_text: str) -> list[dict]:
    return [_genre_to_dict(genre) for genre in parse_genres(json_text)]


def _genre_to_dict(genre: AppleGenre) -> dict:
    return {
        "id": genre.genre_id,
        "name": genre.name,
        "subgenres": [_genre_to_dict(child) for child in genre.subgenres],
    }


def _genres_from_json(payload: object) -> list[AppleGenre]:
    if not isinstance(payload, list):
        return []
    genres: list[AppleGenre] = []
    for row in payload:
        if not isinstance(row, dict) or not row.get("name"):
            continue
        genres.append(
            AppleGenre(
                str(row.get("id", "")),
                str(row["name"]),
                tuple(_genres_from_json(row.get("subgenres", []))),
            )
        )
    return genres


def _shows_as_json(shows: list[AppleShow]) -> list[dict]:
    return [
        {
            "id": show.collection_id,
            "name": show.name,
            "artist": show.artist,
            "artwork": show.artwork_url,
            "page": show.page_url,
            "genres": list(show.genre_ids),
            "explicit": show.explicit,
        }
        for show in shows
    ]


def _shows_from_json(payload: object) -> list[AppleShow]:
    if not isinstance(payload, list):
        return []
    shows: list[AppleShow] = []
    for row in payload:
        if not isinstance(row, dict) or not row.get("id") or not row.get("name"):
            continue
        shows.append(
            AppleShow(
                collection_id=str(row["id"]),
                name=str(row["name"]),
                artist=str(row.get("artist", "")),
                artwork_url=str(row.get("artwork", "")),
                page_url=str(row.get("page", "")),
                genre_ids=tuple(str(g) for g in row.get("genres", []) or []),
                explicit=bool(row.get("explicit")),
            )
        )
    return shows
