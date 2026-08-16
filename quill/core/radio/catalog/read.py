"""Serving browse branches from the catalog (wx-free).

`browse_sources.browse` consults this module first for the kinds the catalog
can answer. The contract is deliberately narrow: :func:`serve` returns a list
of :class:`BrowseNode` **or None**, and None means "not mine - use the live
path". The UI cannot tell which path answered, which is the point: the parity
tests assert the shapes match.

Rankings (Popular, Trending) are the one deliberate inversion: they stay
live-first, because a ranking is a statement about *now*. The catalog serves
them only as an offline fallback, labeled honestly - "as of 2 hours ago" -
per the decision of 2026-08-15.
"""

from __future__ import annotations

from quill.core.radio.browse_nodes import BrowseNode, folder, leaf, make_id
from quill.core.radio.catalog.store import CatalogStore, StationRow
from quill.core.radio.catalog.summary import spoken_age

#: The kinds the catalog answers outright when it is present and enabled.
AXIS_KINDS = frozenset({"rbcountry", "rbstate", "rblang", "rbgenre", "rbcodec", "soma"})

#: Rankings: live-first, catalog fallback labeled with its age.
RANKING_KINDS = frozenset({"popular", "trending"})

#: The library shelf (Class A2).
LIBRARY_KINDS = frozenset({
    "librivoxrecent",
    "librivoxgenres",
    "librivoxauthors",
    "librivoxbook",
    "gutenbergtopic",
})

_SOURCE_LABELS = {"radio_browser": "Radio Browser", "soma_fm": "SomaFM", "xiph": "Xiph"}


def _leaves(rows: list[StationRow]) -> list[BrowseNode]:
    return [
        leaf(row.to_station(source_label=_SOURCE_LABELS.get(row.source_id, row.source_id)))
        for row in rows
    ]


def serve(store: CatalogStore, kind: str, args: list[str]) -> list[BrowseNode] | None:
    """Answer one browse question from the catalog, or None to go live.

    Never raises for a store problem: a corrupt or missing catalog degrades
    to the live path (and the caller's error handling) rather than taking the
    branch down. An *empty* correct answer is returned as [], exactly like the
    live path would.
    """
    try:
        return _serve(store, kind, args)
    except Exception:  # noqa: BLE001 - degrade to live, never break the branch
        return None


def _serve(store: CatalogStore, kind: str, args: list[str]) -> list[BrowseNode] | None:
    if kind == "rbcountry":
        if not (args and args[0]):
            # Every folder carries its count - the announcement upgrade the
            # live path could never afford (measured: all 240 in 7.3 ms).
            return [
                folder(make_id("rbcountry", name), name, child_count=count)
                for name, count in store.countries()
            ]
        country = args[0]
        states = store.states(country)
        if states:
            return [folder(make_id("rbstate", country, state), state) for state in states]
        return _leaves(store.by_country(country))
    if kind == "rbstate":
        country = args[0] if args else ""
        state = args[1] if len(args) > 1 else ""
        return _leaves(store.by_country(country, state=state))
    if kind == "rblang":
        if args and args[0]:
            return _leaves(store.by_language(args[0]))
        return [
            folder(make_id("rblang", name), name.title(), child_count=count)
            for name, count in store.languages()
        ]
    if kind == "rbgenre":
        if args and args[0]:
            return _leaves(store.by_tag(args[0]))
        return [
            folder(make_id("rbgenre", name), name.title(), child_count=count)
            for name, count in store.tags()
        ]
    if kind == "rbcodec":
        if args and args[0]:
            return _leaves(store.by_codec(args[0]))
        return [
            folder(make_id("rbcodec", name), name, child_count=count)
            for name, count in store.codecs()
        ]
    if kind == "soma":
        rows = store.by_source("soma_fm")
        return _leaves(rows) if rows else None  # empty -> let live fill it
    if kind in LIBRARY_KINDS:
        return _serve_library(store, kind, args)
    return None


def rankings_fallback(store: CatalogStore, kind: str) -> list[BrowseNode] | None:
    """Popular/Trending when the live directory cannot answer.

    Served from the vote snapshot and labeled with the catalog's age - "as of
    2 hours ago" - because an unlabeled stale ranking is a small lie, and a
    labeled one is a rescue.
    """
    try:
        rows = store.top_voted(limit=100)
        if not rows:
            return None
        age = spoken_age(store.age_seconds())
        note = f"as of {age}" if age != "never" else "from your catalog"
        return [
            leaf(
                row.to_station(source_label=_SOURCE_LABELS.get(row.source_id, row.source_id)),
                note=note,
            )
            for row in rows
        ]
    except Exception:  # noqa: BLE001
        return None


def _serve_library(store: CatalogStore, kind: str, args: list[str]) -> list[BrowseNode] | None:
    from quill.core.radio.models import RadioStation

    def book_nodes(source: str, genre: str = "") -> list[BrowseNode] | None:
        books = store.audiobooks(source, genre=genre)
        if not books:
            return None  # shelf not seeded yet -> live path
        nodes: list[BrowseNode] = []
        for book_id, title, authors, _language in books:
            sections = store.audiobook_sections(source, book_id)
            if len(sections) == 1:
                nodes.append(
                    leaf(
                        RadioStation(
                            name=title,
                            stream_url=sections[0][2],
                            source="LibriVox" if source == "librivox" else "Project Gutenberg",
                            is_recording=True,
                        ),
                        note=authors,
                    )
                )
            else:
                nodes.append(
                    folder(
                        make_id("catalogbook", source, book_id),
                        title,
                        note=authors,
                        child_count=len(sections),
                    )
                )
        return nodes

    if kind == "librivoxgenres":
        if args and args[0]:
            return book_nodes("librivox", genre=args[0])
        return None  # the genre index itself stays the curated bundled list
    if kind == "librivoxrecent":
        return None  # "recent" is a ranking; stays live-first
    if kind == "gutenbergtopic":
        return book_nodes("gutenberg", genre=args[0] if args else "")
    if kind == "catalogbook":
        return None
    return None


def book_sections(store: CatalogStore, source: str, book_id: str) -> list[BrowseNode]:
    """A seeded book's chapters, playable."""
    from quill.core.radio.models import RadioStation

    label = "LibriVox" if source == "librivox" else "Project Gutenberg"
    return [
        leaf(
            RadioStation(
                name=title or f"Section {idx + 1}", stream_url=url, source=label, is_recording=True
            ),
            note=f"section {idx + 1}",
        )
        for idx, title, url in store.audiobook_sections(source, book_id)
        if url
    ]


def provenance_sentence(store: CatalogStore | None, kind: str) -> str:
    """The details-panel line: what answers this branch, and how fresh (6.5)."""
    if store is None or kind in RANKING_KINDS:
        return "Asks the internet each time; nothing is stored."
    if kind in AXIS_KINDS or kind in LIBRARY_KINDS:
        try:
            age = spoken_age(store.age_seconds())
        except Exception:  # noqa: BLE001
            return "Asks the internet each time; nothing is stored."
        return f"Answers from your catalog, updated {age}."
    return "Asks the internet each time; nothing is stored."
