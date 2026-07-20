"""Search engine for QuillBeacon (PRD section 15).

A small query grammar (section 15.3) parsed into an FTS5 match string plus
structured filters, run against ``beacon_fts``. Filters and sort map to SQL
on the beacons table. Duplicate detection (section 17.5) lives here too.

Pure logic over the store; wx-free and unit-testable.
"""

from __future__ import annotations

import re
import shlex
from dataclasses import dataclass, field
from typing import Any

from quill.apps.beacon import db as dbmod
from quill.apps.beacon.model import Beacon, SavedSearch

# Sort modes (PRD 15.6).
SORT_RELEVANCE = "relevance"
SORT_TITLE = "title"
SORT_ADDED = "added"
SORT_MODIFIED = "modified"
SORT_OPENED = "opened"
SORT_MOST_OPENED = "mostOpened"
SORT_TYPE = "type"
SORT_HEALTH = "health"

SORTS = (
    SORT_RELEVANCE,
    SORT_TITLE,
    SORT_ADDED,
    SORT_MODIFIED,
    SORT_OPENED,
    SORT_MOST_OPENED,
    SORT_TYPE,
    SORT_HEALTH,
)


@dataclass
class ParsedQuery:
    terms: list[str] = field(default_factory=list)
    phrase: str = ""
    types: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    collections: list[str] = field(default_factory=list)
    domains: list[str] = field(default_factory=list)
    health: list[str] = field(default_factory=list)
    has_note: bool | None = None
    has_transcript: bool | None = None
    not_archived: bool = False
    favorites_only: bool = False
    inbox_only: bool = False
    trashed: bool = False
    raw_fts: str = ""  # compiled FTS5 MATCH expression


def parse(query: str) -> ParsedQuery:
    """Parse the section 15.3 grammar into structured filters + an FTS match.

    Recognized tokens (all optional, any order):
      type:episode tag:research show:"Living Blindfully" domain:arizona.edu
      heading:policy collection:"Title II" modified:last30days health:broken
      has:note not:archived added:today opened:never favorite inbox trash
    Bare words become FTS terms; quoted phrases become an FTS phrase.
    """
    pq = ParsedQuery()
    if not query or not query.strip():
        return pq
    try:
        tokens = shlex.split(query, posix=True)
    except ValueError:
        tokens = query.split()
    fts_terms: list[str] = []
    for tok in tokens:
        # Bare keywords (no colon) that act as filters, not search terms.
        low = tok.lower()
        if low == "favorite":
            pq.favorites_only = True
            continue
        if low == "inbox":
            pq.inbox_only = True
            continue
        if low == "trash":
            pq.trashed = True
            continue
        if ":" not in tok:
            fts_terms.append(tok)
            continue
        key, _, val = tok.partition(":")
        key = key.lower()
        if key == "type":
            pq.types.append(val)
        elif key == "tag":
            pq.tags.append(val)
        elif key in ("collection", "col"):
            pq.collections.append(val)
        elif key in ("domain", "site"):
            pq.domains.append(val)
        elif key == "health":
            pq.health.append(val)
        elif key == "heading":
            fts_terms.append(val)  # heading text is in the FTS heading column
        elif key == "show":
            fts_terms.append(val)
        elif key == "transcript":
            fts_terms.append(f'"{_fts_quote(val)}"')
            pq.has_transcript = True
        elif key == "has":
            if val == "note":
                pq.has_note = True
            elif val == "transcript":
                pq.has_transcript = True
        elif key == "not":
            if val == "archived":
                pq.not_archived = True
        elif key in ("added", "modified", "opened"):
            # Date filters are applied as SQL; record as a term for now.
            fts_terms.append(val)
        elif key == "favorite":
            pq.favorites_only = True
        elif key == "inbox":
            pq.inbox_only = True
        elif key == "trash":
            pq.trashed = True
        else:
            fts_terms.append(tok)
    pq.raw_fts = _compile_fts(fts_terms)
    return pq


def _compile_fts(terms: list[str]) -> str:
    """Build an FTS5 MATCH string from bare terms and quoted phrases."""
    if not terms:
        return ""
    parts: list[str] = []
    for t in terms:
        if t.startswith('"') and t.endswith('"'):
            parts.append(t)
        else:
            # prefix matching: foo* matches food; keeps search incremental.
            parts.append(f"{_fts_quote(t)}*")
    return " ".join(parts)


def _fts_quote(term: str) -> str:
    # Escape double quotes for FTS5 phrase use.
    return term.replace('"', '""')


def search(
    store: dbmod.BeaconStore,
    query: str,
    *,
    scope_collection: str | None = None,
    sort: str = SORT_RELEVANCE,
    limit: int = 500,
) -> list[Beacon]:
    """Run a search and return matching Beacons in order.

    When the query is empty, returns all (non-trashed) Beacons in the chosen
    sort, so the results pane is never empty on first launch.
    """
    pq = parse(query)
    sql_parts: list[str] = []
    args: list[Any] = []

    # Base join: FTS hit or full scan. FTS5 MATCH uses the table name on the
    # left of the operator, so beacon_fts is not aliased in the join.
    if pq.raw_fts:
        sql_parts.append(
            "SELECT b.beacon_id FROM beacons b "
            "JOIN beacon_fts ON beacon_fts.beacon_id = b.beacon_id "
            "WHERE beacon_fts MATCH ?"
        )
        args.append(pq.raw_fts)
    else:
        sql_parts.append("SELECT b.beacon_id FROM beacons b WHERE 1=1")

    # Trashed / inbox / archive visibility.
    if pq.trashed:
        sql_parts.append("AND b.trashed=1")
    else:
        sql_parts.append("AND b.trashed=0")
    if pq.inbox_only:
        sql_parts.append("AND b.in_inbox=1")
    if pq.not_archived:
        sql_parts.append("AND b.archived=0")
    if pq.favorites_only:
        sql_parts.append("AND b.favorite=1")
    if pq.has_note is True:
        sql_parts.append("AND b.note != ''")

    # Type and domain filters route through the resources table so they work
    # even when there is no FTS match (the beacon_fts join is optional above).
    if pq.types or pq.domains:
        sql_parts.append("AND EXISTS (SELECT 1 FROM resources r WHERE r.resource_id=b.resource_id")
        if pq.types:
            placeholders = ",".join("?" for _ in pq.types)
            sql_parts.append(f" AND r.type IN ({placeholders})")
            args.extend(pq.types)
        if pq.domains:
            d_clauses = " OR ".join("r.primary_uri LIKE ?" for _ in pq.domains)
            sql_parts.append(f" AND ({d_clauses})")
            args.extend(f"%{d}%" for d in pq.domains)
        sql_parts.append(")")

    # Health filter.
    if pq.health:
        placeholders = ",".join("?" for _ in pq.health)
        sql_parts.append(f"AND b.health IN ({placeholders})")
        args.extend(pq.health)

    # Tag filter.
    if pq.tags:
        for tag in pq.tags:
            sql_parts.append(
                "AND EXISTS (SELECT 1 FROM beacon_tags bt JOIN tags t "
                "ON t.tag_id=bt.tag_id WHERE bt.beacon_id=b.beacon_id "
                "AND (t.name=? OR t.aliases LIKE ?))"
            )
            args.extend([tag, f'%"{tag}"%'])

    # Collection filter / scope.
    colls = list(pq.collections)
    if scope_collection:
        colls.append(scope_collection)
    if colls:
        for col in colls:
            sql_parts.append(
                "AND EXISTS (SELECT 1 FROM beacon_collections bc JOIN collections c "
                "ON c.collection_id=bc.collection_id WHERE bc.beacon_id=b.beacon_id "
                "AND c.name=?)"
            )
            args.append(col)

    # Order.
    order = _order_clause(sort, pq.raw_fts)
    sql = " ".join(sql_parts) + f" ORDER BY {order} LIMIT ?"
    args.append(limit)

    rows = store.conn.execute(sql, args).fetchall()
    out: list[Beacon] = []
    for r in rows:
        b = store.get_beacon(r["beacon_id"])
        if b is not None:
            out.append(b)
    return out


def _order_clause(sort: str, has_fts: bool) -> str:
    if sort == SORT_TITLE:
        return "b.title COLLATE NOCASE ASC"
    if sort == SORT_ADDED:
        return "b.date_added DESC"
    if sort == SORT_MODIFIED:
        return "b.date_added DESC"
    if sort == SORT_OPENED:
        return "b.last_opened DESC NULLS LAST"
    if sort == SORT_MOST_OPENED:
        return "b.open_count DESC"
    if sort == SORT_TYPE:
        return "b.resource_id, b.title"
    if sort == SORT_HEALTH:
        return "b.health, b.title"
    # relevance
    if has_fts:
        return "rank"
    return "b.date_added DESC"


def find_duplicates(store: dbmod.BeaconStore, limit: int = 200) -> list[list[Beacon]]:
    """Group Beacons that likely point at the same thing (PRD 17.5).

    Groups by normalized canonical_id and by primary_uri host+path with
    tracking parameters stripped. Returns only groups with >1 member.
    """
    beacons = store.list_beacons(include_trashed=False, limit=100000)
    groups: dict[str, list[Beacon]] = {}
    for b in beacons:
        res = store.get_resource(b.resource_id) if b.resource_id else None
        key = _dup_key(res, b)
        if key:
            groups.setdefault(key, []).append(b)
    return [g for g in groups.values() if len(g) > 1][:limit]


def _dup_key(res, beacon: Beacon) -> str:
    if not res:
        return ""
    canon = (res.canonical_id or "").strip()
    if canon:
        return f"canon:{_strip_tracking(canon)}"
    uri = (res.primary_uri or "").strip()
    if uri:
        return f"uri:{_strip_tracking(uri)}"
    return ""


_TRACK_PARAMS = re.compile(r"[?&](utm_[\w]+|gclid|fbclid|mc_eid|ref|igshid)=[^&]*")


def _strip_tracking(url: str) -> str:
    url = _TRACK_PARAMS.sub("", url)
    url = url.replace("http://", "https://").rstrip("?&")
    return url.lower()


def evaluate_saved_search(
    store: dbmod.BeaconStore,
    ss: SavedSearch,
    *,
    limit: int = 500,
) -> list[Beacon]:
    """Run a SavedSearch live against the store (PRD 15.6 Smart Collections).

    A Smart Collection always reflects the current library: it re-evaluates the
    Section-15 grammar on every open, never a frozen snapshot. ``scope_collection``
    pins the view to a parent collection if the saved search was defined within one.
    """
    return search(
        store,
        ss.query,
        scope_collection=ss.scope_collection or None,
        sort=ss.sort or SORT_ADDED,
        limit=limit,
    )


def facets(store: dbmod.BeaconStore) -> dict[str, dict[str, int]]:
    """Return facet counts for the filter pane (PRD 15.5)."""
    out: dict[str, dict[str, int]] = {"type": {}, "health": {}, "tag": {}, "collection": {}}
    for b in store.list_beacons(include_trashed=False, limit=100000):
        res = store.get_resource(b.resource_id) if b.resource_id else None
        if res:
            out["type"][res.type] = out["type"].get(res.type, 0) + 1
        out["health"][b.health] = out["health"].get(b.health, 0) + 1
        for t in b.tags:
            out["tag"][t] = out["tag"].get(t, 0) + 1
        for c in b.collections:
            out["collection"][c] = out["collection"].get(c, 0) + 1
    return out
