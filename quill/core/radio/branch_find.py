"""Branch-smart Find: the fastest honest answer for a browse subtree.

"Find in this folder" used to answer one way everywhere: crawl the subtree
and match labels. That is the right fallback, and the wrong first choice for
branches that have a real search engine behind them -- anchored on the
Podcasts branch it crawled chart pages and never asked Apple's search API,
which is why a show as findable as Double Tap came back "no matches"
(reported 2026-08-16). This module routes a Find to the fastest channel that
honors the anchor's scope:

- **Podcasts (Apple), any level** -> the iTunes Search API (keyless, ~0.6 s),
  answering with show *folders* that expand into episodes.
- **A catalog-served Radio Browser axis** -> the local FTS index, scoped to
  the anchored country/state/language/genre/codec. Instant, offline included.
- **Every branch with a search engine behind it** -> that engine: LibriVox
  (books as folders of chapters), the Internet Archive (drillable items),
  Project Gutenberg, SomaFM, TuneIn (streams resolved), iHeart (sitemap
  index), NOAA (call sign / SAME / county), Audius, Mixcloud, ccMixter.
- **Anything else** -> ``None``, and the caller falls back to the crawl.

Every route returns ``(nodes, provenance)`` where *provenance* is the spoken
sentence fragment naming what answered ("searched the podcast directory",
"from your catalog") -- a fast answer whose origin is stated beats a fast
answer that could be mistaken for a complete one. wx-free, strict-typed.
"""

from __future__ import annotations

from typing import Any

from quill.core.radio.browse_nodes import BrowseNode, folder, leaf, make_id, split_id

#: How a guarded route reports that a source did not answer. Federated browse
#: (:mod:`quill.core.radio.federated_browse`) asks every route at once and has
#: to tell "nothing matched" apart from "nobody answered", so the wording is a
#: constant rather than a sentence typed twice.
UNREACHABLE = "could not be reached"

#: Apple kinds where Find means "ask the podcast directory".
_APPLE_KINDS = frozenset({"apple", "applechart", "applegenre", "appleshow"})

#: Catalog-scoped kinds: axis kind -> which search() filter its argument fills.
_AXIS_FILTERS = {
    "rbcountry": "country",
    "rbstate": "state",
    "rblang": "language",
    "rbgenre": "tag",
    "rbcodec": "codec",
}


def _find_apple(query: str, *, safe_mode: bool) -> tuple[list[BrowseNode], str]:
    from quill.core.podcasts.itunes_search import search_podcasts

    nodes = [
        folder(
            make_id("appleshow", show.collection_id),
            show.title,
            note=show.artist,
        )
        for show in search_podcasts(query, safe_mode=safe_mode)
        if show.collection_id
    ]
    return nodes, "searched the whole podcast directory"


def _find_podcast_index(query: str, *, safe_mode: bool) -> tuple[list[BrowseNode], str]:
    """Search the open index rather than the store.

    Its rows are *feeds*, so each one opens straight into that show's episodes
    -- no subscription, and no second lookup to find the feed the way an Apple
    collection id needs one.
    """
    from quill.core.radio import browse_podcast_index

    nodes = browse_podcast_index.search(query, safe_mode=safe_mode)
    return nodes, "searched the Podcast Index"


def _find_catalog(
    catalog: Any, kind: str, args: list[str], query: str
) -> tuple[list[BrowseNode], str] | None:
    scope: dict[str, str] = {}
    if args and args[0]:
        scope[_AXIS_FILTERS[kind]] = args[0]
        if kind == "rbcountry" and len(args) > 1 and args[1]:
            scope["state"] = args[1]
    try:
        rows = catalog.search(query, limit=200, **scope)
    except Exception:  # noqa: BLE001 - no catalog answer means fall back, never break
        return None
    from quill.core.radio.catalog.read import _SOURCE_LABELS

    nodes = [
        leaf(row.to_station(source_label=_SOURCE_LABELS.get(row.source_id, row.source_id)))
        for row in rows
    ]
    return nodes, "from your catalog"


def _find_librivox(query: str, *, safe_mode: bool) -> tuple[list[BrowseNode], str]:
    from quill.core.media import librivox

    nodes = [
        folder(
            make_id("librivoxbook", book.book_id),
            book.title,
            note=", ".join(part for part in (book.authors, book.total_time) if part),
        )
        for book in librivox.search(query)
    ]
    return nodes, "searched LibriVox"


def _find_archive(query: str, *, safe_mode: bool) -> tuple[list[BrowseNode], str]:
    from quill.core.radio import internet_archive as ia

    nodes = [
        folder(
            make_id("archive" if item.is_collection else "archiveitem", item.identifier),
            item.title or item.identifier,
            note=", ".join(part for part in (item.creator, item.year) if part),
        )
        for item in ia.search(query, safe_mode=safe_mode)
    ]
    return nodes, "searched the Internet Archive"


def _find_gutenberg(query: str, *, safe_mode: bool) -> tuple[list[BrowseNode], str]:
    from quill.core.radio import gutendex

    rows = gutendex.audiobooks(query=query, safe_mode=safe_mode)
    return [leaf(station) for station in rows], "searched Project Gutenberg"


def _find_soma(query: str, *, safe_mode: bool) -> tuple[list[BrowseNode], str]:
    from quill.core.radio import soma_fm

    rows = soma_fm.search_stations(query, safe_mode=safe_mode)
    return [leaf(station) for station in rows], "searched SomaFM"


def _find_tunein(query: str, *, safe_mode: bool) -> tuple[list[BrowseNode], str]:
    from quill.core.radio.directory_search import tunein_search_stations

    rows = tunein_search_stations(query, safe_mode=safe_mode)
    return [leaf(station) for station in rows], "searched TuneIn"


def _find_iheart(query: str, *, safe_mode: bool) -> tuple[list[BrowseNode], str]:
    from quill.core.radio import iheart

    # iHeart's own relevance search: two GETs, ranked results, streams
    # embedded -- not a substring filter over a sitemap index that itself cost
    # two GETs and then a page fetch per match.
    rows = iheart.search_stations(query, safe_mode=safe_mode)
    return [leaf(station) for station in rows], "searched iHeart"


def _find_shoutcast(query: str, *, safe_mode: bool) -> tuple[list[BrowseNode], str]:
    from quill.core.radio import shoutcast
    from quill.core.radio.browse_directories import shoutcast_rows

    # resolve=False: these become lazy rows that fetch their address when they
    # are played, so a SHOUTcast search inside the tree is ONE request rather
    # than one per result.
    rows = shoutcast.search_stations(query, safe_mode=safe_mode, resolve=False)
    return shoutcast_rows(rows), "searched the SHOUTcast directory"


def _find_live365(query: str, *, safe_mode: bool) -> tuple[list[BrowseNode], str]:
    from quill.core.radio import live365

    rows = live365.search_stations(query, safe_mode=safe_mode)
    return [leaf(station) for station in rows], "searched Live365"


def _find_radio_paradise(query: str, *, safe_mode: bool) -> tuple[list[BrowseNode], str]:
    from quill.core.radio import radio_paradise

    rows = radio_paradise.search_stations(query, safe_mode=safe_mode)
    return [leaf(station) for station in rows], "searched Radio Paradise"


def _find_tv(query: str, *, safe_mode: bool) -> tuple[list[BrowseNode], str]:
    from quill.core.radio import iptv

    rows = iptv.search_stations(query, safe_mode=safe_mode)
    return [leaf(station) for station in rows], "searched the TV catalog"


def _find_wx(query: str, *, safe_mode: bool) -> tuple[list[BrowseNode], str]:
    from quill.core.radio import wxindex
    from quill.core.radio.wxindex_models import to_radio_station

    stations = [
        to_radio_station(s) for s in wxindex.search_stations(query, safe_mode=safe_mode) if s.feeds
    ]
    return [leaf(station) for station in stations], "searched NOAA's directory"


def _find_free_music(kind: str, query: str, *, safe_mode: bool) -> tuple[list[BrowseNode], str]:
    from quill.core.radio import free_music

    if kind.startswith("audius"):
        return [
            leaf(s) for s in free_music.audius_search(query, safe_mode=safe_mode)
        ], "searched Audius"
    if kind.startswith("ccmixter"):
        return [
            leaf(s) for s in free_music.ccmixter_search(query, safe_mode=safe_mode)
        ], "searched ccMixter"
    return [
        leaf(s, note="opens on Mixcloud in your browser")
        for s in free_music.mixcloud_search(query, safe_mode=safe_mode)
    ], "searched Mixcloud"


#: Kind prefixes that route to a real search engine. Matched by prefix so a
#: sub-level anchor (a genre, a letter, a state) still reaches its source's
#: search -- scope inside one source is the source.
_PREFIX_ROUTES: tuple[tuple[str, Any], ...] = (
    ("librivox", _find_librivox),
    ("archive", _find_archive),
    ("gutenberg", _find_gutenberg),
    ("soma", _find_soma),
    ("tunein", _find_tunein),
    ("iheart", _find_iheart),
    ("shoutcast", _find_shoutcast),
    ("live365", _find_live365),
    ("radioparadise", _find_radio_paradise),
    ("tv", _find_tv),
    ("wx", _find_wx),
    ("audius", _find_free_music),
    ("mixcloud", _find_free_music),
    ("ccmixter", _find_free_music),
    # Before "pi" would ever collide with anything: the four Podcast Index
    # kinds all begin with it, and all of them search the same way.
    ("podcastindex", _find_podcast_index),
    ("pitrending", _find_podcast_index),
    ("picategories", _find_podcast_index),
    ("pishow", _find_podcast_index),
)


def fast_find(
    node_id: str, query: str, *, safe_mode: bool, catalog: Any = None
) -> tuple[list[BrowseNode], str] | None:
    """The fast route for *query* under *node_id*, or ``None`` to crawl.

    A route that fails (network, an unreachable directory) answers with an
    empty list and an honest provenance rather than raising into the caller's
    task -- Find never crashes, it reports.
    """
    kind, args = split_id(node_id)
    if kind in _AXIS_FILTERS and catalog is not None:
        return _find_catalog(catalog, kind, args, query)
    if safe_mode:
        return None  # network routes refuse; the crawl says why, per source
    if kind in _APPLE_KINDS:
        return _guarded(_find_apple, "the podcast directory", query, safe_mode=safe_mode)
    for prefix, route in _PREFIX_ROUTES:
        if kind.startswith(prefix):
            if route is _find_free_music:
                return _guarded(
                    lambda q, *, safe_mode: _find_free_music(kind, q, safe_mode=safe_mode),
                    prefix,
                    query,
                    safe_mode=safe_mode,
                )
            return _guarded(route, prefix, query, safe_mode=safe_mode)
    return None


def _guarded(
    route: Any, label: str, query: str, *, safe_mode: bool
) -> tuple[list[BrowseNode], str]:
    try:
        nodes, provenance = route(query, safe_mode=safe_mode)
        return list(nodes), str(provenance)
    except Exception:  # noqa: BLE001 - an unreachable directory is an answer, not a crash
        return [], f"{label} {UNREACHABLE}"
