"""SQLite + FTS5 persistence for QuillBeacon (PRD section 22.1).

WAL mode, transactional migrations, an external-content FTS5 index kept in sync
manually, and tombstoned deletes. The store is the single source of truth for
the local-first experience; a future sync layer (PRD 45) will layer a commit
log on top of these rows without changing this API.

The class is wx-free so it can be unit-tested headlessly, following the
``quill.core.bookmarks`` precedent.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from quill.apps.beacon.model import (
    SCHEMA_VERSION,
    Attachment,
    Beacon,
    Collection,
    Location,
    MediaChapter,
    Relationship,
    Resource,
    SavedSearch,
    Tag,
    Trail,
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_meta (key TEXT PRIMARY KEY, value TEXT);

CREATE TABLE IF NOT EXISTS resources (
    resource_id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    canonical_id TEXT NOT NULL DEFAULT '',
    title TEXT NOT NULL DEFAULT '',
    creator TEXT NOT NULL DEFAULT '',
    mime TEXT NOT NULL DEFAULT '',
    primary_uri TEXT NOT NULL DEFAULT '',
    alt_uris TEXT NOT NULL DEFAULT '[]',
    provider_ids TEXT NOT NULL DEFAULT '{}',
    fingerprint TEXT NOT NULL DEFAULT '',
    availability TEXT NOT NULL DEFAULT 'available',
    metadata TEXT NOT NULL DEFAULT '{}',
    created INTEGER NOT NULL,
    updated INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_resources_canonical ON resources(canonical_id);
CREATE INDEX IF NOT EXISTS idx_resources_type ON resources(type);

CREATE TABLE IF NOT EXISTS beacons (
    beacon_id TEXT PRIMARY KEY,
    resource_id TEXT NOT NULL,
    title TEXT NOT NULL DEFAULT '',
    note TEXT NOT NULL DEFAULT '',
    favorite INTEGER NOT NULL DEFAULT 0,
    in_inbox INTEGER NOT NULL DEFAULT 1,
    archived INTEGER NOT NULL DEFAULT 0,
    trashed INTEGER NOT NULL DEFAULT 0,
    date_added INTEGER NOT NULL,
    last_opened INTEGER,
    open_count INTEGER NOT NULL DEFAULT 0,
    privacy TEXT NOT NULL DEFAULT 'private',
    health TEXT NOT NULL DEFAULT 'available',
    capture_source TEXT NOT NULL DEFAULT 'manual',
    version INTEGER NOT NULL DEFAULT 1,
    updated INTEGER NOT NULL DEFAULT 0,
    dirty INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_beacons_resource ON beacons(resource_id);
CREATE INDEX IF NOT EXISTS idx_beacons_added ON beacons(date_added);
CREATE INDEX IF NOT EXISTS idx_beacons_inbox ON beacons(in_inbox);
CREATE INDEX IF NOT EXISTS idx_beacons_trash ON beacons(trashed);

CREATE TABLE IF NOT EXISTS beacon_tombstones (
    beacon_id TEXT PRIMARY KEY,
    deleted_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS locations (
    location_id TEXT PRIMARY KEY,
    resource_id TEXT NOT NULL,
    type TEXT NOT NULL DEFAULT 'native',
    native_locator TEXT NOT NULL DEFAULT '{}',
    structural_locator TEXT NOT NULL DEFAULT '{}',
    text_quote TEXT NOT NULL DEFAULT '{}',
    positional_locator TEXT NOT NULL DEFAULT '{}',
    recovery_hints TEXT NOT NULL DEFAULT '{}',
    media_start_ms INTEGER,
    media_end_ms INTEGER,
    heading_path TEXT NOT NULL DEFAULT '[]',
    display_summary TEXT NOT NULL DEFAULT '',
    confidence REAL NOT NULL DEFAULT 1.0,
    last_resolved INTEGER,
    resolution_history TEXT NOT NULL DEFAULT '[]'
);
CREATE INDEX IF NOT EXISTS idx_locations_resource ON locations(resource_id);

CREATE TABLE IF NOT EXISTS collections (
    collection_id TEXT PRIMARY KEY,
    name TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    parent_id TEXT,
    manual_order INTEGER NOT NULL DEFAULT 0,
    sharing TEXT NOT NULL DEFAULT 'private',
    color TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS beacon_collections (
    beacon_id TEXT NOT NULL,
    collection_id TEXT NOT NULL,
    position INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (beacon_id, collection_id)
);

CREATE TABLE IF NOT EXISTS tags (
    tag_id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    aliases TEXT NOT NULL DEFAULT '[]',
    parent_id TEXT
);

CREATE TABLE IF NOT EXISTS beacon_tags (
    beacon_id TEXT NOT NULL,
    tag_id TEXT NOT NULL,
    PRIMARY KEY (beacon_id, tag_id)
);

CREATE TABLE IF NOT EXISTS trails (
    trail_id TEXT PRIMARY KEY,
    title TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    current_step INTEGER NOT NULL DEFAULT 0,
    sharing TEXT NOT NULL DEFAULT 'private',
    steps TEXT NOT NULL DEFAULT '[]'
);

CREATE TABLE IF NOT EXISTS relationships (
    src_beacon TEXT NOT NULL,
    tgt_beacon TEXT NOT NULL,
    type TEXT NOT NULL DEFAULT 'relatedTo',
    note TEXT NOT NULL DEFAULT '',
    created INTEGER NOT NULL,
    PRIMARY KEY (src_beacon, tgt_beacon, type)
);

CREATE TABLE IF NOT EXISTS media_chapters (
    chapter_id TEXT PRIMARY KEY,
    resource_id TEXT NOT NULL,
    source_type TEXT NOT NULL DEFAULT 'publisher',
    title TEXT NOT NULL DEFAULT '',
    start_ms INTEGER NOT NULL DEFAULT 0,
    end_ms INTEGER,
    url TEXT NOT NULL DEFAULT '',
    image_ref TEXT NOT NULL DEFAULT '',
    publisher_id TEXT NOT NULL DEFAULT '',
    user_edit TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_chapters_resource ON media_chapters(resource_id);

CREATE TABLE IF NOT EXISTS attachments (
    attachment_id TEXT PRIMARY KEY,
    beacon_id TEXT NOT NULL,
    name TEXT NOT NULL DEFAULT '',
    kind TEXT NOT NULL DEFAULT 'file',
    uri TEXT NOT NULL DEFAULT '',
    content TEXT NOT NULL DEFAULT '',
    mime TEXT NOT NULL DEFAULT '',
    size INTEGER NOT NULL DEFAULT 0,
    fingerprint TEXT NOT NULL DEFAULT '',
    created INTEGER NOT NULL,
    metadata TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_attachments_beacon ON attachments(beacon_id);

CREATE TABLE IF NOT EXISTS saved_searches (
    search_id TEXT PRIMARY KEY,
    name TEXT NOT NULL DEFAULT '',
    query TEXT NOT NULL DEFAULT '',
    sort TEXT NOT NULL DEFAULT 'added',
    scope_collection TEXT NOT NULL DEFAULT '',
    created INTEGER NOT NULL
);

-- Full-text index (PRD 15). Standalone FTS5 table maintained manually so the
-- denormalized tag/collection/heading text can be searched without joins at
-- query time. type is UNINDEXED (used for filtering, not matching).
CREATE VIRTUAL TABLE IF NOT EXISTS beacon_fts USING fts5(
    beacon_id UNINDEXED,
    title, note, url, path, tags, collection, heading, text_quote, transcript,
    type UNINDEXED,
    tokenize = "unicode61 remove_diacritics 2"
);
"""


class BeaconStore:
    """Local-first persistence. All writes are transactional."""

    def __init__(self, path: str | Path, *, check_same_thread: bool = True) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.path), check_same_thread=check_same_thread)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self.conn.execute("PRAGMA busy_timeout=5000")
        self._migrate()

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> BeaconStore:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # -- schema ---------------------------------------------------------------

    def _migrate(self) -> None:
        self.conn.executescript(SCHEMA)
        self.conn.execute(
            "INSERT OR IGNORE INTO schema_meta(key, value) VALUES('version', ?)",
            (str(SCHEMA_VERSION),),
        )
        self.conn.commit()
        row = self.conn.execute("SELECT value FROM schema_meta WHERE key='version'").fetchone()
        current = int(row["value"]) if row else 1
        if current > SCHEMA_VERSION:
            raise RuntimeError(f"library schema v{current} newer than engine v{SCHEMA_VERSION}")
        # Additive migrations: each step brings an older library up to date.
        # SCHEMA uses CREATE TABLE IF NOT EXISTS, so brand-new DBs already have
        # every column; these ALTERs only affect libraries created under v1.
        if current < 2:
            self._migrate_to_v2()
            self.conn.execute(
                "UPDATE schema_meta SET value=? WHERE key='version'",
                (str(SCHEMA_VERSION),),
            )
            self.conn.commit()
        # Index on dirty exists for both fresh and migrated libraries.
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_beacons_dirty ON beacons(dirty)")
        self.conn.commit()

    def _migrate_to_v2(self) -> None:
        """Add beacons.updated / beacons.dirty and the tombstones table (v2).

        Existing rows get updated=date_added and dirty=0; the first incremental
        sync after upgrade commits only genuinely new edits, not the whole
        library (PRD 45.8).
        """
        cols = {r["name"] for r in self.conn.execute("PRAGMA table_info(beacons)")}
        if "updated" not in cols:
            self.conn.execute("ALTER TABLE beacons ADD COLUMN updated INTEGER NOT NULL DEFAULT 0")
        if "dirty" not in cols:
            self.conn.execute("ALTER TABLE beacons ADD COLUMN dirty INTEGER NOT NULL DEFAULT 0")
        self.conn.execute("UPDATE beacons SET updated=date_added WHERE updated=0")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_beacons_dirty ON beacons(dirty)")
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS beacon_tombstones "
            "(beacon_id TEXT PRIMARY KEY, deleted_at INTEGER NOT NULL)"
        )
        self.conn.commit()

    # -- resources ------------------------------------------------------------

    def put_resource(self, res: Resource) -> Resource:
        with self.conn:
            self.conn.execute(
                """INSERT INTO resources (resource_id, type, canonical_id, title,
                   creator, mime, primary_uri, alt_uris, provider_ids, fingerprint,
                   availability, metadata, created, updated)
                   VALUES (:resource_id, :type, :canonical_id, :title, :creator,
                   :mime, :primary_uri, :alt_uris, :provider_ids, :fingerprint,
                   :availability, :metadata, :created, :updated)
                   ON CONFLICT(resource_id) DO UPDATE SET
                   type=excluded.type, canonical_id=excluded.canonical_id,
                   title=excluded.title, creator=excluded.creator, mime=excluded.mime,
                   primary_uri=excluded.primary_uri, alt_uris=excluded.alt_uris,
                   provider_ids=excluded.provider_ids, fingerprint=excluded.fingerprint,
                   availability=excluded.availability, metadata=excluded.metadata,
                   updated=excluded.updated""",
                res.to_row(),
            )
        return res

    def get_resource(self, resource_id: str) -> Resource | None:
        row = self.conn.execute(
            "SELECT * FROM resources WHERE resource_id=?", (resource_id,)
        ).fetchone()
        return Resource.from_row(dict(row)) if row else None

    def find_resource_by_canonical(self, canonical_id: str) -> Resource | None:
        row = self.conn.execute(
            "SELECT * FROM resources WHERE canonical_id=?", (canonical_id,)
        ).fetchone()
        return Resource.from_row(dict(row)) if row else None

    # -- beacons --------------------------------------------------------------

    def put_beacon(
        self, beacon: Beacon, resource: Resource | None = None, *, touch: bool = True
    ) -> Beacon:
        """Insert or update a beacon.

        ``touch`` stamps ``updated`` and sets ``dirty`` so the next sync commits
        the change. The sync apply path passes ``touch=False`` to preserve the
        remote timestamp and avoid re-committing pulled records (PRD 45.8).
        """
        if touch:
            beacon.updated = _now_ms()
            beacon.dirty = 1
        with self.conn:
            if resource is not None:
                self.put_resource(resource)
                beacon.resource_id = resource.resource_id
            self.conn.execute(
                """INSERT INTO beacons (beacon_id, resource_id, title, note, favorite,
                   in_inbox, archived, trashed, date_added, last_opened, open_count,
                   privacy, health, capture_source, version, updated, dirty)
                   VALUES (:beacon_id, :resource_id, :title, :note, :favorite,
                   :in_inbox, :archived, :trashed, :date_added, :last_opened,
                   :open_count, :privacy, :health, :capture_source, :version,
                   :updated, :dirty)
                   ON CONFLICT(beacon_id) DO UPDATE SET
                   resource_id=excluded.resource_id, title=excluded.title,
                   note=excluded.note, favorite=excluded.favorite,
                   in_inbox=excluded.in_inbox, archived=excluded.archived,
                   trashed=excluded.trashed, last_opened=excluded.last_opened,
                   open_count=excluded.open_count, privacy=excluded.privacy,
                   health=excluded.health, capture_source=excluded.capture_source,
                   version=excluded.version, updated=excluded.updated,
                   dirty=excluded.dirty""",
                beacon.to_row(),
            )
            self._sync_tags(beacon)
            self._sync_collections(beacon)
            self._sync_locations(beacon)
            self._reindex_beacon(beacon)
        return beacon

    def _sync_tags(self, beacon: Beacon) -> None:
        self.conn.execute("DELETE FROM beacon_tags WHERE beacon_id=?", (beacon.beacon_id,))
        for tag_name in beacon.tags:
            tag_id = self._ensure_tag(tag_name)
            self.conn.execute(
                "INSERT OR IGNORE INTO beacon_tags(beacon_id, tag_id) VALUES(?, ?)",
                (beacon.beacon_id, tag_id),
            )

    def _ensure_tag(self, name: str) -> str:
        row = self.conn.execute("SELECT tag_id FROM tags WHERE name=?", (name,)).fetchone()
        if row:
            return row["tag_id"]
        tag = Tag(name=name)
        self.conn.execute(
            "INSERT INTO tags(tag_id, name, aliases, parent_id) VALUES(?, ?, ?, ?)",
            (tag.tag_id, tag.name, json.dumps(tag.aliases), tag.parent_id),
        )
        return tag.tag_id

    def _sync_collections(self, beacon: Beacon) -> None:
        self.conn.execute("DELETE FROM beacon_collections WHERE beacon_id=?", (beacon.beacon_id,))
        for pos, name in enumerate(beacon.collections):
            col_id = self._ensure_collection(name)
            self.conn.execute(
                "INSERT OR REPLACE INTO beacon_collections(beacon_id, collection_id, position) "
                "VALUES(?, ?, ?)",
                (beacon.beacon_id, col_id, pos),
            )

    def _ensure_collection(self, name: str) -> str:
        row = self.conn.execute(
            "SELECT collection_id FROM collections WHERE name=?", (name,)
        ).fetchone()
        if row:
            return row["collection_id"]
        col = Collection(name=name)
        self.conn.execute(
            "INSERT INTO collections(collection_id, name, description, parent_id, "
            "manual_order, sharing, color) VALUES(?, ?, ?, ?, ?, ?, ?)",
            (
                col.collection_id,
                col.name,
                col.description,
                col.parent_id,
                col.manual_order,
                col.sharing,
                col.color,
            ),
        )
        return col.collection_id

    def _sync_locations(self, beacon: Beacon) -> None:
        if not beacon.resource_id:
            return
        self.conn.execute("DELETE FROM locations WHERE resource_id=?", (beacon.resource_id,))
        for loc in beacon.locations:
            loc.resource_id = beacon.resource_id
            self.conn.execute(
                """INSERT INTO locations (location_id, resource_id, type,
                   native_locator, structural_locator, text_quote, positional_locator,
                   recovery_hints, media_start_ms, media_end_ms, heading_path,
                   display_summary, confidence, last_resolved, resolution_history)
                   VALUES (:location_id, :resource_id, :type, :native_locator,
                   :structural_locator, :text_quote, :positional_locator,
                   :recovery_hints, :media_start_ms, :media_end_ms, :heading_path,
                   :display_summary, :confidence, :last_resolved, :resolution_history)""",
                loc.to_row(),
            )

    def _reindex_beacon(self, beacon: Beacon) -> None:
        res = self.get_resource(beacon.resource_id) if beacon.resource_id else None
        url = res.primary_uri if res else ""
        path = res.canonical_id if res and res.type in ("file", "folder") else ""
        headings = " > ".join(
            loc.heading_path[0] if loc.heading_path else "" for loc in beacon.locations
        )
        text_quote = " ".join(
            str(loc.text_quote.get("exact", "")) for loc in beacon.locations if loc.text_quote
        )
        transcript = " ".join(
            str(loc.text_quote.get("text", ""))
            for loc in beacon.locations
            if loc.text_quote.get("text")
        )
        rtype = res.type if res else "uri"
        self.conn.execute("DELETE FROM beacon_fts WHERE beacon_id=?", (beacon.beacon_id,))
        self.conn.execute(
            """INSERT INTO beacon_fts(beacon_id, title, note, url, path, tags,
               collection, heading, text_quote, transcript, type)
               VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                beacon.beacon_id,
                beacon.title,
                beacon.note,
                url,
                path,
                " ".join(beacon.tags),
                " ".join(beacon.collections),
                headings,
                text_quote,
                transcript,
                rtype,
            ),
        )

    def get_beacon(self, beacon_id: str) -> Beacon | None:
        row = self.conn.execute("SELECT * FROM beacons WHERE beacon_id=?", (beacon_id,)).fetchone()
        if not row:
            return None
        beacon = Beacon.from_row(dict(row))
        self._load_joins(beacon)
        return beacon

    def _load_joins(self, beacon: Beacon) -> None:
        tags = self.conn.execute(
            "SELECT t.name FROM tags t JOIN beacon_tags bt ON bt.tag_id=t.tag_id "
            "WHERE bt.beacon_id=?",
            (beacon.beacon_id,),
        ).fetchall()
        beacon.tags = [r["name"] for r in tags]
        cols = self.conn.execute(
            "SELECT c.name FROM collections c JOIN beacon_collections bc "
            "ON bc.collection_id=c.collection_id WHERE bc.beacon_id=? "
            "ORDER BY bc.position",
            (beacon.beacon_id,),
        ).fetchall()
        beacon.collections = [r["name"] for r in cols]
        if beacon.resource_id:
            locs = self.conn.execute(
                "SELECT * FROM locations WHERE resource_id=?", (beacon.resource_id,)
            ).fetchall()
            beacon.locations = [Location.from_row(dict(r)) for r in locs]

    def list_beacons(
        self,
        *,
        include_trashed: bool = False,
        include_archived: bool = True,
        limit: int = 1000,
    ) -> list[Beacon]:
        clauses = []
        if not include_trashed:
            clauses.append("trashed=0")
        if not include_archived:
            clauses.append("archived=0")
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self.conn.execute(
            f"SELECT * FROM beacons {where} ORDER BY date_added DESC LIMIT ?", (limit,)
        ).fetchall()
        out = []
        for r in rows:
            b = Beacon.from_row(dict(r))
            self._load_joins(b)
            out.append(b)
        return out

    def count(self, *, include_trashed: bool = False) -> int:
        where = "" if include_trashed else "WHERE trashed=0"
        row = self.conn.execute(f"SELECT COUNT(*) AS n FROM beacons {where}").fetchone()
        return row["n"]

    def record_open(self, beacon_id: str) -> None:
        with self.conn:
            self.conn.execute(
                "UPDATE beacons SET open_count=open_count+1, last_opened=? WHERE beacon_id=?",
                (_now_ms(), beacon_id),
            )

    def trash(self, beacon_id: str) -> None:
        with self.conn:
            self.conn.execute(
                "UPDATE beacons SET trashed=1, dirty=1, updated=? WHERE beacon_id=?",
                (_now_ms(), beacon_id),
            )

    def restore(self, beacon_id: str) -> None:
        with self.conn:
            self.conn.execute(
                "UPDATE beacons SET trashed=0, archived=0, dirty=1, updated=? WHERE beacon_id=?",
                (_now_ms(), beacon_id),
            )

    def archive(self, beacon_id: str) -> None:
        with self.conn:
            self.conn.execute(
                "UPDATE beacons SET archived=1, in_inbox=0, dirty=1, updated=? WHERE beacon_id=?",
                (_now_ms(), beacon_id),
            )

    def delete_permanent(self, beacon_id: str) -> None:
        """Permanently remove a beacon and record a sync tombstone (PRD 23.5).

        The tombstone lets an incremental sync propagate the deletion to other
        devices without having to re-scan every beacon each cycle.
        """
        with self.conn:
            self.conn.execute("DELETE FROM beacons WHERE beacon_id=?", (beacon_id,))
            self.conn.execute("DELETE FROM beacon_tags WHERE beacon_id=?", (beacon_id,))
            self.conn.execute("DELETE FROM beacon_collections WHERE beacon_id=?", (beacon_id,))
            self.conn.execute("DELETE FROM beacon_fts WHERE beacon_id=?", (beacon_id,))
            self.conn.execute(
                "INSERT OR IGNORE INTO beacon_tombstones(beacon_id, deleted_at) VALUES(?, ?)",
                (beacon_id, _now_ms()),
            )

    # -- incremental sync helpers (PRD 45.8) ---------------------------------

    def dirty_beacon_ids(self) -> list[str]:
        rows = self.conn.execute("SELECT beacon_id FROM beacons WHERE dirty=1").fetchall()
        return [r["beacon_id"] for r in rows]

    def tombstone_ids(self) -> list[str]:
        rows = self.conn.execute("SELECT beacon_id FROM beacon_tombstones").fetchall()
        return [r["beacon_id"] for r in rows]

    def clear_dirty(self, beacon_ids: list[str]) -> None:
        if not beacon_ids:
            return
        with self.conn:
            self.conn.executemany(
                "UPDATE beacons SET dirty=0 WHERE beacon_id=?",
                [(i,) for i in beacon_ids],
            )

    def clear_tombstones(self, beacon_ids: list[str]) -> None:
        if not beacon_ids:
            return
        with self.conn:
            self.conn.executemany(
                "DELETE FROM beacon_tombstones WHERE beacon_id=?",
                [(i,) for i in beacon_ids],
            )

    # -- collections / tags / trails ------------------------------------------

    def list_collections(self) -> list[Collection]:
        rows = self.conn.execute("SELECT * FROM collections ORDER BY manual_order, name").fetchall()
        return [Collection.from_row(dict(r)) for r in rows]

    def put_collection(self, col: Collection) -> Collection:
        with self.conn:
            self.conn.execute(
                """INSERT INTO collections (collection_id, name, description,
                   parent_id, manual_order, sharing, color) VALUES
                   (:collection_id, :name, :description, :parent_id,
                   :manual_order, :sharing, :color)
                   ON CONFLICT(collection_id) DO UPDATE SET name=excluded.name,
                   description=excluded.description, parent_id=excluded.parent_id,
                   manual_order=excluded.manual_order, sharing=excluded.sharing,
                   color=excluded.color""",
                col.to_row(),
            )
        return col

    def get_collection(self, collection_id: str) -> Collection | None:
        row = self.conn.execute(
            "SELECT * FROM collections WHERE collection_id=?", (collection_id,)
        ).fetchone()
        return Collection.from_row(dict(row)) if row else None

    def collection_by_name(self, name: str) -> Collection | None:
        row = self.conn.execute("SELECT * FROM collections WHERE name=?", (name,)).fetchone()
        return Collection.from_row(dict(row)) if row else None

    def delete_collection(self, collection_id: str, *, reassign: str | None = None) -> None:
        """Remove a collection. Members are unlinked, never deleted.

        If ``reassign`` names another collection, members are moved there first
        so a user never loses items by renaming/restructuring a collection.
        """
        with self.conn:
            if reassign:
                tgt = self.collection_by_name(reassign)
                if tgt:
                    src_rows = self.conn.execute(
                        "SELECT beacon_id FROM beacon_collections WHERE collection_id=?",
                        (collection_id,),
                    ).fetchall()
                    for r in src_rows:
                        self.conn.execute(
                            "INSERT OR IGNORE INTO beacon_collections"
                            "(beacon_id, collection_id, position) VALUES(?, ?, 0)",
                            (r["beacon_id"], tgt.collection_id),
                        )
            self.conn.execute(
                "DELETE FROM beacon_collections WHERE collection_id=?", (collection_id,)
            )
            self.conn.execute("DELETE FROM collections WHERE collection_id=?", (collection_id,))

    def list_tags(self) -> list[Tag]:
        rows = self.conn.execute("SELECT * FROM tags ORDER BY name").fetchall()
        return [Tag.from_row(dict(r)) for r in rows]

    def rename_tag(self, old: str, new: str) -> None:
        with self.conn:
            self.conn.execute("UPDATE tags SET name=? WHERE name=?", (new, old))
            self._reindex_all()

    def merge_tags(self, source: str, target: str) -> None:
        with self.conn:
            src = self.conn.execute("SELECT tag_id FROM tags WHERE name=?", (source,)).fetchone()
            tgt = self.conn.execute("SELECT tag_id FROM tags WHERE name=?", (target,)).fetchone()
            if not src or not tgt:
                return
            self.conn.execute(
                "UPDATE OR IGNORE beacon_tags SET tag_id=? WHERE tag_id=?",
                (tgt["tag_id"], src["tag_id"]),
            )
            self.conn.execute("DELETE FROM tags WHERE tag_id=?", (src["tag_id"],))
            self._reindex_all()

    def put_trail(self, trail: Trail) -> Trail:
        with self.conn:
            self.conn.execute(
                """INSERT INTO trails (trail_id, title, description, current_step,
                   sharing, steps) VALUES (:trail_id, :title, :description,
                   :current_step, :sharing, :steps)
                   ON CONFLICT(trail_id) DO UPDATE SET title=excluded.title,
                   description=excluded.description, current_step=excluded.current_step,
                   sharing=excluded.sharing, steps=excluded.steps""",
                trail.to_row(),
            )
        return trail

    def list_trails(self) -> list[Trail]:
        rows = self.conn.execute("SELECT * FROM trails ORDER BY title").fetchall()
        return [Trail.from_row(dict(r)) for r in rows]

    def get_trail(self, trail_id: str) -> Trail | None:
        row = self.conn.execute("SELECT * FROM trails WHERE trail_id=?", (trail_id,)).fetchone()
        return Trail.from_row(dict(row)) if row else None

    # -- relationships --------------------------------------------------------

    def add_relationship(self, rel: Relationship) -> None:
        with self.conn:
            self.conn.execute(
                "INSERT OR REPLACE INTO relationships(src_beacon, tgt_beacon, type, note, created) "
                "VALUES(?, ?, ?, ?, ?)",
                (rel.src_beacon, rel.tgt_beacon, rel.type, rel.note, rel.created),
            )

    def relationships_for(self, beacon_id: str) -> list[Relationship]:
        rows = self.conn.execute(
            "SELECT * FROM relationships WHERE src_beacon=? OR tgt_beacon=?",
            (beacon_id, beacon_id),
        ).fetchall()
        return [
            Relationship(
                src_beacon=r["src_beacon"],
                tgt_beacon=r["tgt_beacon"],
                type=r["type"],
                note=r["note"],
                created=r["created"],
            )
            for r in rows
        ]

    # -- media chapters -------------------------------------------------------

    def put_chapter(self, chapter: MediaChapter) -> MediaChapter:
        with self.conn:
            self.conn.execute(
                """INSERT INTO media_chapters (chapter_id, resource_id, source_type,
                   title, start_ms, end_ms, url, image_ref, publisher_id, user_edit)
                   VALUES (:chapter_id, :resource_id, :source_type, :title, :start_ms,
                   :end_ms, :url, :image_ref, :publisher_id, :user_edit)
                   ON CONFLICT(chapter_id) DO UPDATE SET title=excluded.title,
                   start_ms=excluded.start_ms, end_ms=excluded.end_ms,
                   url=excluded.url, user_edit=excluded.user_edit""",
                chapter.to_row(),
            )
        return chapter

    def chapters_for(self, resource_id: str) -> list[MediaChapter]:
        rows = self.conn.execute(
            "SELECT * FROM media_chapters WHERE resource_id=? ORDER BY start_ms",
            (resource_id,),
        ).fetchall()
        return [MediaChapter.from_row(dict(r)) for r in rows]

    # -- attachments (PRD 24.1, 44.3) -----------------------------------------

    def put_attachment(self, att: Attachment) -> Attachment:
        with self.conn:
            self.conn.execute(
                """INSERT INTO attachments (attachment_id, beacon_id, name, kind,
                   uri, content, mime, size, fingerprint, created, metadata)
                   VALUES (:attachment_id, :beacon_id, :name, :kind, :uri,
                   :content, :mime, :size, :fingerprint, :created, :metadata)
                   ON CONFLICT(attachment_id) DO UPDATE SET
                   beacon_id=excluded.beacon_id, name=excluded.name,
                   kind=excluded.kind, uri=excluded.uri, content=excluded.content,
                   mime=excluded.mime, size=excluded.size,
                   fingerprint=excluded.fingerprint, metadata=excluded.metadata""",
                att.to_row(),
            )
        return att

    def attachments_for(self, beacon_id: str) -> list[Attachment]:
        rows = self.conn.execute(
            "SELECT * FROM attachments WHERE beacon_id=? ORDER BY created",
            (beacon_id,),
        ).fetchall()
        return [Attachment.from_row(dict(r)) for r in rows]

    def delete_attachment(self, attachment_id: str) -> None:
        with self.conn:
            self.conn.execute("DELETE FROM attachments WHERE attachment_id=?", (attachment_id,))

    # -- saved searches / Smart Collections (PRD 15.6) -----------------------

    def put_saved_search(self, ss: SavedSearch) -> SavedSearch:
        with self.conn:
            self.conn.execute(
                """INSERT INTO saved_searches (search_id, name, query, sort,
                   scope_collection, created) VALUES (:search_id, :name, :query,
                   :sort, :scope_collection, :created)
                   ON CONFLICT(search_id) DO UPDATE SET name=excluded.name,
                   query=excluded.query, sort=excluded.sort,
                   scope_collection=excluded.scope_collection""",
                ss.to_row(),
            )
        return ss

    def list_saved_searches(self) -> list[SavedSearch]:
        rows = self.conn.execute("SELECT * FROM saved_searches ORDER BY name").fetchall()
        return [SavedSearch.from_row(dict(r)) for r in rows]

    def get_saved_search(self, search_id: str) -> SavedSearch | None:
        row = self.conn.execute(
            "SELECT * FROM saved_searches WHERE search_id=?", (search_id,)
        ).fetchone()
        return SavedSearch.from_row(dict(row)) if row else None

    def delete_saved_search(self, search_id: str) -> None:
        with self.conn:
            self.conn.execute("DELETE FROM saved_searches WHERE search_id=?", (search_id,))

    # -- maintenance ----------------------------------------------------------

    def _reindex_all(self) -> None:
        with self.conn:
            self.conn.execute("DELETE FROM beacon_fts")
            for b in self.list_beacons(include_trashed=True, limit=100000):
                self._reindex_beacon(b)

    def integrity_check(self) -> bool:
        row = self.conn.execute("PRAGMA integrity_check").fetchone()
        return row[0] == "ok"


def _now_ms() -> int:
    import time

    return int(time.time() * 1000)
