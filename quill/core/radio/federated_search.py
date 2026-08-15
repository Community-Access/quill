"""Searching every library at once, and saying which one answered.

Quill Radio 3.0 grew fifteen browse branches and Find Stations kept searching
the same eight radio directories it always had. The asymmetry became surprising:
you could *walk* to a LibriVox book by author and could not *find* it by typing
its title. This is the other half.

It is deliberately not clever.

**No cross-provider ranking.** Each source returns its own order, and the
federated list keeps that order within each group. A relevance score that
compares a LibriVox chapter against an Internet Archive recording against a
podcast episode is a research project pretending to be a feature, and a wrong one
is worse than an honest concatenation.

**Grouped by what a thing *is*.** Stations, Audiobooks, Archive Recordings,
Podcasts -- because "23 results" spanning four kinds is a list somebody has to
sort out by reading it, and the group headings do that work instead.

**Every row names where it came from.** Provenance is N-7 in the PRD, and it is
not a details-pane footnote: a listener arrowing a merged list has to be able to
tell a LibriVox chapter from an Archive recording without opening anything.

**A source that cannot search says so.** Three of the new branches genuinely
cannot: Audius exposes trending rather than search, Mixcloud exposes categories,
and ccMixter is queryable only by tag. They are reported as unsearchable, once,
rather than silently contributing nothing -- because "no results from Mixcloud"
and "Mixcloud cannot be searched" are different facts and only one of them means
try again with different words.

wx-free, strict-typed. Concurrency belongs to the caller: every function here is
one blocking call to one source, so the UI layer can run them on the task manager
and merge as they land.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from quill.core.radio.models import RadioStation

#: The group a source's results belong to. Ordered as the merged list shows
#: them: the thing most people are looking for first.
GROUP_STATIONS = "Stations"
GROUP_AUDIOBOOKS = "Audiobooks"
GROUP_ARCHIVE = "Archive Recordings"
GROUP_PODCASTS = "Podcasts"

GROUP_ORDER: tuple[str, ...] = (
    GROUP_STATIONS,
    GROUP_AUDIOBOOKS,
    GROUP_ARCHIVE,
    GROUP_PODCASTS,
)


@dataclass(frozen=True, slots=True)
class LibrarySource:
    """One library that federated search can reach.

    ``search`` is left ``None`` for a source that genuinely cannot be searched,
    which is a fact worth carrying rather than an omission worth hiding.
    """

    id: str
    label: str
    group: str
    search: Callable[[str, bool], list[RadioStation]] | None = None
    #: Why this source cannot be searched, in words, for the ones that cannot.
    unsearchable_because: str = ""


@dataclass(slots=True)
class FederatedResults:
    """What a federated search found, and what it could not ask."""

    groups: dict[str, list[RadioStation]] = field(default_factory=dict)
    #: ``(source label, reason)`` for every source that cannot be searched.
    unsearchable: list[tuple[str, str]] = field(default_factory=list)
    #: ``(source label, message)`` for every source that failed.
    failed: list[tuple[str, str]] = field(default_factory=list)

    @property
    def total(self) -> int:
        return sum(len(rows) for rows in self.groups.values())

    def add(self, group: str, rows: list[RadioStation]) -> None:
        self.groups.setdefault(group, []).extend(rows)

    def ordered(self) -> list[tuple[str, list[RadioStation]]]:
        """Non-empty groups, in the order the list shows them."""
        return [(name, self.groups[name]) for name in GROUP_ORDER if self.groups.get(name)]


def _librivox(query: str, safe_mode: bool) -> list[RadioStation]:
    from quill.core.media.librivox import search as librivox_search

    if safe_mode:
        return []
    return [
        RadioStation(
            name=book.title,
            # A book is a folder of chapters, not a stream: the row carries the
            # book's identity and the tree resolves it, exactly as browsing does.
            stream_url="",
            station_uuid=f"librivoxbook:{book.book_id}",
            tags=tuple(part for part in (book.authors, book.total_time) if part),
            source="LibriVox",
        )
        for book in librivox_search(query, limit=25)
    ]


def _archive(query: str, safe_mode: bool) -> list[RadioStation]:
    from quill.core.radio import internet_archive as ia

    return [
        RadioStation(
            name=item.title or item.identifier,
            stream_url="",
            homepage=f"https://archive.org/details/{item.identifier}",
            tags=(item.creator,) if item.creator else (),
            source="Internet Archive",
        )
        for item in ia.search(query, safe_mode=safe_mode)
    ]


def _gutenberg(query: str, safe_mode: bool) -> list[RadioStation]:
    from quill.core.radio import gutendex

    return gutendex.audiobooks(query=query, limit=25, safe_mode=safe_mode)


def _podcasts(query: str, safe_mode: bool) -> list[RadioStation]:
    from quill.core.podcasts.itunes_search import search_podcasts

    return [
        RadioStation(
            name=result.title,
            stream_url="",
            homepage=result.feed_url,
            tags=(result.artist,) if result.artist else (),
            source="Podcasts (Apple)",
        )
        for result in search_podcasts(query, safe_mode=safe_mode)
    ]


#: Every library federated search knows about. The three that cannot be searched
#: are listed too, with their reason, because saying "Mixcloud cannot be
#: searched" is useful and saying nothing is not.
def _audius(query: str, safe_mode: bool) -> list[RadioStation]:
    from quill.core.radio.free_music import audius_search

    return audius_search(query, safe_mode=safe_mode)


def _mixcloud(query: str, safe_mode: bool) -> list[RadioStation]:
    from quill.core.radio.free_music import mixcloud_search

    return mixcloud_search(query, safe_mode=safe_mode)


def _ccmixter(query: str, safe_mode: bool) -> list[RadioStation]:
    from quill.core.radio.free_music import ccmixter_search

    return ccmixter_search(query, safe_mode=safe_mode)


LIBRARY_SOURCES: tuple[LibrarySource, ...] = (
    LibrarySource("librivox", "LibriVox", GROUP_AUDIOBOOKS, _librivox),
    LibrarySource("gutenberg", "Project Gutenberg", GROUP_AUDIOBOOKS, _gutenberg),
    LibrarySource("archive", "Internet Archive", GROUP_ARCHIVE, _archive),
    LibrarySource("apple_podcasts", "Podcasts (Apple)", GROUP_PODCASTS, _podcasts),
    # All three publish a keyword search, and all three were listed here as
    # unsearchable until somebody checked (2026-08-14). The browse tree offered
    # trending, categories and tags because those are good shelves -- not
    # because the services could not be asked a question. Saying "this cannot
    # be searched" about somebody else's product is the kind of confident wrong
    # answer this codebase exists to avoid, so it is worth recording that it was
    # wrong for a release rather than quietly deleting the line.
    LibrarySource("audius", "Audius", GROUP_STATIONS, _audius),
    LibrarySource("mixcloud", "Mixcloud", GROUP_STATIONS, _mixcloud),
    LibrarySource("ccmixter", "ccMixter", GROUP_STATIONS, _ccmixter),
)

_BY_ID = {source.id: source for source in LIBRARY_SOURCES}


def source(source_id: str) -> LibrarySource | None:
    return _BY_ID.get(source_id)


def searchable_ids() -> tuple[str, ...]:
    """Every library that can actually answer a query."""
    return tuple(s.id for s in LIBRARY_SOURCES if s.search is not None)


def dedupe(rows: list[RadioStation]) -> list[RadioStation]:
    """Drop rows that are the same thing twice, keeping the first.

    Matched on the playable address where there is one, else on the home page,
    else on name and source together -- the same ladder the station merge uses.
    First answer wins, because the order a source returned is the only ranking
    this module trusts.
    """
    seen: set[str] = set()
    kept: list[RadioStation] = []
    for row in rows:
        key = (row.stream_url or row.homepage or f"{row.name}|{row.source}").strip().lower()
        if key in seen:
            continue
        seen.add(key)
        kept.append(row)
    return kept


def describe(results: FederatedResults) -> str:
    """One sentence for the whole search, spoken once when it completes.

    Counts, then the groups, then -- last, because it is a caveat rather than a
    result -- what could not be asked. Never per source and never per arrival: a
    list that announces itself eight times is a list nobody can read.
    """
    if not results.total:
        said = "Nothing found in the libraries."
    else:
        parts = [f"{len(rows)} in {name}" for name, rows in results.ordered()]
        said = f"{results.total} found: {', '.join(parts)}."
    if results.failed:
        names = ", ".join(label for label, _why in results.failed)
        said += f" {names} could not be reached."
    if results.unsearchable:
        names = ", ".join(label for label, _why in results.unsearchable)
        said += f" {names} can be browsed but not searched."
    return said


def search_source(source_id: str, query: str, *, safe_mode: bool = False) -> list[RadioStation]:
    """Search one library. Blocking -- the caller decides about threads."""
    found = _BY_ID.get(source_id)
    if found is None or found.search is None or not query.strip():
        return []
    return dedupe(found.search(query.strip(), safe_mode))


def search_all(
    query: str,
    *,
    enabled: tuple[str, ...] | None = None,
    safe_mode: bool = False,
) -> FederatedResults:
    """Search every enabled library in turn.

    Sequential on purpose: this is the wx-free reference implementation, used by
    tests and by any caller that does not have a task manager. The UI runs each
    source through :func:`search_source` concurrently instead, and merges as they
    land -- which is why every source is reachable individually.
    """
    results = FederatedResults()
    wanted = enabled if enabled is not None else tuple(s.id for s in LIBRARY_SOURCES)
    for library in LIBRARY_SOURCES:
        if library.id not in wanted:
            continue
        if library.search is None:
            results.unsearchable.append((library.label, library.unsearchable_because))
            continue
        try:
            rows = library.search(query.strip(), safe_mode) if query.strip() else []
        except Exception as error:  # noqa: BLE001 - one source must never sink the search
            results.failed.append((library.label, str(error)))
            continue
        if rows:
            results.add(library.group, dedupe(rows))
    return results
