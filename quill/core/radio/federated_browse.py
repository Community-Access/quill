"""Search every source at once, and answer in *browse rows*.

:mod:`quill.core.radio.federated_search` already searches the libraries and
answers with ``RadioStation``s, which is the right shape for the Find Stations
window's flat result list and the wrong one for the browse tree: a station is a
row you play, and half of what a search finds -- a podcast show, a LibriVox
book, an Archive item -- is a row you *open*. Handed back as stations they
arrive stripped of the identity that makes them useful: the show cannot be
subscribed to, the book cannot be expanded into its chapters, and the context
menu falls back to the four things every playable row offers.

So this module answers in :class:`~quill.core.radio.browse_nodes.BrowseNode`s,
with the same ids browsing that source would have produced. A result row *is* a
browse row: same menu, same expansion, same everything -- found by typing
instead of by walking.

Three rules it keeps:

**Every route is one that already exists.** :mod:`quill.core.radio.branch_find`
routes a scoped Find to each source's own search engine and returns browse
nodes; this asks all of them at once. There is no second implementation of
"search LibriVox" here to drift from the first.

**Every row says what it is.** A merged list spanning stations, shows, books
and recordings is unreadable without it, so each row's note leads with its type
and the source that answered -- "Podcast, Apple Podcasts" -- before whatever
that source wanted to say about the row.

**A source that could not be reached is named.** Silence is indistinguishable
from "no results", and only one of those means try again.

wx-free, strict-typed.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field, replace
from typing import Any

from quill.core.radio import branch_find
from quill.core.radio.browse_nodes import BrowseNode, leaf

#: What a row IS, in the order the merged list groups them: the thing most
#: people are looking for first, and the long tail of niche catalogues last.
TYPE_ORDER: tuple[str, ...] = (
    "Station",
    "TV channel",
    "Weather station",
    "Podcast",
    "Audiobook",
    "Recording",
    "Track",
    "Show",
)

#: At most this many rows from any one source, so a directory that answers
#: with two hundred cannot bury the eleven the other eleven sources found.
PER_SOURCE_LIMIT = 40

#: At most this many rows in total. A tree row costs a keystroke to pass.
TOTAL_LIMIT = 400


@dataclass(frozen=True, slots=True)
class SearchTarget:
    """One source federated browse can ask, and how to ask it.

    *seed_id* is a browse node id whose kind routes to that source's search in
    :func:`quill.core.radio.branch_find.fast_find` -- the id of the source's own
    root branch, which is exactly what an unscoped Find on that branch would
    use.
    """

    seed_id: str
    label: str
    type_label: str


#: Every source worth asking, in the order they are asked (which is not the
#: order results are shown -- see :data:`TYPE_ORDER`). Radio Browser is handled
#: separately: it is the one source with an offline answer.
TARGETS: tuple[SearchTarget, ...] = (
    SearchTarget("tunein", "TuneIn", "Station"),
    SearchTarget("iheart", "iHeart", "Station"),
    SearchTarget("shoutcast", "SHOUTcast", "Station"),
    SearchTarget("live365", "Live365", "Station"),
    SearchTarget("radioparadise", "Radio Paradise", "Station"),
    SearchTarget("soma", "SomaFM", "Station"),
    SearchTarget("tv", "TV (iptv.org)", "TV channel"),
    SearchTarget("wx", "NOAA Weather Radio", "Weather station"),
    SearchTarget("apple", "Apple Podcasts", "Podcast"),
    # Two podcast directories, asked together: the index finds independent,
    # self-hosted and de-listed shows the store does not carry, and its rows
    # open into episodes without subscribing.
    SearchTarget("podcastindex", "Podcast Index", "Podcast"),
    SearchTarget("librivox", "LibriVox", "Audiobook"),
    SearchTarget("gutenberg", "Project Gutenberg", "Audiobook"),
    SearchTarget("archive", "Internet Archive", "Recording"),
    SearchTarget("audius", "Audius", "Track"),
    SearchTarget("ccmixter", "ccMixter", "Track"),
    SearchTarget("mixcloud", "Mixcloud", "Show"),
)

#: The station directory, asked from the local catalog when there is one (and
#: in Safe Mode, where it is the only thing that can answer at all).
STATIONS = SearchTarget("rbgenre", "Radio Browser", "Station")


#: The sources that answer from something already on this machine: the station
#: catalog (a seeded SQLite snapshot), NOAA's bundled index, and the two whose
#: whole directory is held in a local cache for hours at a time. They are what a
#: **first pass** asks, because they come back in well under a second and a
#: listener should be reading results while the network is still being polite.
#:
#: Being in this list is a claim about *latency*, not about quality: everything
#: here is also asked in the full pass, so a source that turns out to need the
#: network simply arrives in the second answer like everything else.
FAST_SEED_IDS: frozenset[str] = frozenset({"rbgenre", "wx", "live365", "radioparadise", "tv"})


def fast_targets(
    targets: tuple[SearchTarget, ...] | None = None,
) -> tuple[SearchTarget, ...]:
    """The subset of *targets* worth asking first (pure)."""
    wanted = targets if targets is not None else (STATIONS, *TARGETS)
    return tuple(target for target in wanted if target.seed_id in FAST_SEED_IDS)


def targets_of_type(type_label: str) -> tuple[SearchTarget, ...]:
    """Every source that answers with rows of one type.

    What narrows "Search for a Podcast..." to the podcast directories without
    a second list of sources to keep in step with :data:`TARGETS`.
    """
    return tuple(t for t in (STATIONS, *TARGETS) if t.type_label == type_label)


@dataclass(slots=True)
class FederatedBrowse:
    """What a federated browse found, and what it could not ask."""

    #: Every row, already ordered by type and capped. Ready to render.
    rows: list[BrowseNode] = field(default_factory=list)
    #: ``(source label, why)`` for every source that could not be reached.
    failed: list[tuple[str, str]] = field(default_factory=list)
    #: Source labels that answered, whether or not they found anything.
    asked: list[str] = field(default_factory=list)
    #: How many rows a per-source or total cap dropped.
    dropped: int = 0
    #: Type label -> how many rows of it, for the spoken summary.
    counts: dict[str, int] = field(default_factory=dict)

    @property
    def total(self) -> int:
        return len(self.rows)


def _annotate(node: BrowseNode, target: SearchTarget) -> BrowseNode:
    """The same row, saying what it is and who answered, before its own note.

    The type leads because it decides what the row *does* -- open or play --
    and a listener arrowing a merged list needs that before anything else.
    """
    said = f"{target.type_label}, {target.label}"
    return replace(node, note=f"{said}, {node.note}" if node.note else said)


def _stations(query: str, *, safe_mode: bool, catalog: Any) -> tuple[list[BrowseNode], str]:
    """The station directory: the local catalog first, the live API otherwise.

    The catalog is a same-day snapshot of the whole directory shipped with the
    app, so this is instant, offline, and the only station answer Safe Mode can
    give. Without one (a build that skipped the seed), the live search stands in.
    """
    if catalog is not None:
        found = branch_find.fast_find(STATIONS.seed_id, query, safe_mode=safe_mode, catalog=catalog)
        if found is not None:
            return found
    if safe_mode:
        return [], "Radio Browser needs the network"
    from quill.core.radio import radio_browser

    try:
        rows = radio_browser.search_stations(query, limit=PER_SOURCE_LIMIT, safe_mode=safe_mode)
    except Exception as error:  # noqa: BLE001 - an unreachable directory is an answer
        return [], str(error) or "could not be reached"
    return [leaf(station) for station in rows], "searched Radio Browser"


def _ask(
    target: SearchTarget, query: str, *, safe_mode: bool, catalog: Any
) -> tuple[list[BrowseNode], str]:
    """One source's answer, already annotated, plus why it is empty if it is.

    ``fast_find`` returns ``None`` when it has no route -- which is what Safe
    Mode does to every network source -- and that is not a failure worth
    reporting per source: the summary says Safe Mode once. A route that ran and
    could not reach its directory *is* worth reporting, and says so through
    :data:`branch_find.UNREACHABLE`.
    """
    if target is STATIONS:
        nodes, provenance = _stations(query, safe_mode=safe_mode, catalog=catalog)
    else:
        found = branch_find.fast_find(target.seed_id, query, safe_mode=safe_mode, catalog=catalog)
        nodes, provenance = (list(found[0]), found[1]) if found is not None else ([], "")
    why = provenance if provenance.endswith(branch_find.UNREACHABLE) else ""
    return [_annotate(node, target) for node in nodes[:PER_SOURCE_LIMIT]], why


#: How long the whole cross-source search may take before the stragglers are
#: left behind. Reported 2026-08-26 as "very very slow": the search is only as
#: fast as the slowest directory in it, and one service having a bad afternoon
#: made every search feel broken. Everything that arrived inside this window is
#: shown; everything that did not is **named** in ``failed`` rather than
#: silently dropped, so a short list never passes itself off as a complete one.
#:
#: Eight seconds rather than the twelve it started at, because the two sources
#: that used to need the extra four -- TuneIn and iHeart, each resolving its
#: results one network round trip after another -- now resolve them at the same
#: time. The ceiling exists for a service having a bad afternoon, not for a
#: shape of work we chose.
SEARCH_DEADLINE_SECONDS = 8.0


def search_everything(
    query: str,
    *,
    safe_mode: bool = False,
    catalog: Any = None,
    targets: tuple[SearchTarget, ...] | None = None,
    max_workers: int = 0,
    deadline_seconds: float = SEARCH_DEADLINE_SECONDS,
) -> FederatedBrowse:
    """Ask every source for *query* at once and merge what comes back.

    Concurrent because sequential is unusable: sixteen directories at a second
    each is a sixteen-second wait for a list that could arrive in two. Two
    things make it as fast as the network allows rather than as fast as the
    pool allows:

    * **One wave.** ``max_workers`` defaults to *the number of sources*, so
      every directory is asked at the same moment. It used to be six, which
      with sixteen targets meant three waves and a wall-clock of three slow
      services back to back rather than one.
    * **A deadline.** The whole search is bounded by *deadline_seconds*; a
      source still thinking when it expires is reported as such and its answer
      is discarded. The alternative -- what shipped before -- is that the
      slowest service on earth decides how long every search takes.

    Rows come back ordered by type and then by the order their source returned
    them, which is the only ranking this module trusts (see
    :mod:`quill.core.radio.federated_search` on why there is no cross-source
    relevance score).
    """
    result = FederatedBrowse()
    text = query.strip()
    if not text:
        return result
    wanted = targets if targets is not None else (STATIONS, *TARGETS)
    by_target: dict[str, list[BrowseNode]] = {}

    def _one(target: SearchTarget) -> tuple[SearchTarget, list[BrowseNode], str]:
        nodes, why = _ask(target, text, safe_mode=safe_mode, catalog=catalog)
        return target, nodes, why

    workers = max_workers if max_workers > 0 else min(24, max(1, len(wanted)))
    pool = ThreadPoolExecutor(max_workers=workers)
    pending = {pool.submit(_one, target): target for target in wanted}
    try:
        for future in as_completed(pending, timeout=max(0.5, deadline_seconds)):
            try:
                target, nodes, why = future.result()
            except Exception as error:  # noqa: BLE001 - a route must never raise here
                straggler = pending[future]
                result.asked.append(straggler.label)
                result.failed.append((straggler.label, str(error) or "could not be searched"))
                continue
            by_target[target.seed_id] = nodes
            result.asked.append(target.label)
            if why:
                result.failed.append((target.label, why))
    except TimeoutError:
        pass
    finally:
        for future, target in pending.items():
            if not future.done():
                # Named, never silently dropped: a source that ran out of time
                # is a source worth asking again, and a listener reading a
                # short list deserves to know which one is missing from it.
                result.asked.append(target.label)
                result.failed.append((
                    target.label,
                    f"did not answer within {int(deadline_seconds)} seconds",
                ))
        # wait=False: the search is over, and a request still in flight must not
        # hold the worker that ran it. Nothing it produces is read.
        pool.shutdown(wait=False, cancel_futures=True)

    seen: set[str] = set()
    ordered: list[BrowseNode] = []
    for type_label in TYPE_ORDER:
        for target in wanted:
            if target.type_label != type_label:
                continue
            for node in by_target.get(target.seed_id, []):
                # Two directories carrying the same station is the common case
                # (TuneIn and Radio Browser both list the big ones); the first
                # answer wins, exactly as the flat federated search does.
                key = node.node_id.strip().lower()
                if key in seen:
                    continue
                seen.add(key)
                ordered.append(node)
                result.counts[type_label] = result.counts.get(type_label, 0) + 1
    if len(ordered) > TOTAL_LIMIT:
        result.dropped = len(ordered) - TOTAL_LIMIT
        ordered = ordered[:TOTAL_LIMIT]
    result.rows = ordered
    return result


def describe(query: str, found: FederatedBrowse, *, safe_mode: bool = False) -> str:
    """One sentence for the whole search, spoken once when it completes.

    Counts by type, then the caveats -- never per source and never per arrival.
    """
    if not found.total:
        said = f"Nothing found for {query}."
    else:
        parts = [
            f"{count} {label.lower()}{'' if count == 1 else 's'}"
            for label, count in found.counts.items()
            if count
        ]
        said = f"{found.total} found for {query}: {', '.join(parts)}."
    if found.dropped:
        said += f" {found.dropped} more not shown; search for something narrower."
    if safe_mode:
        said += " Safe Mode: only your offline station catalog was searched."
    if found.failed:
        names = ", ".join(label for label, _why in found.failed)
        said += f" {names} could not be reached."
    return said
