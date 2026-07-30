"""SQLite + FTS5 persistence for QUILL Social (PRD 30, 31).

WAL mode, foreign keys on, transactional writes, and an FTS5 index over posts
and drafts for fast local search (PRD 26, 35). The store is the single source
of truth for the local-first experience (PRD 6.6): reading, drafting,
organizing, and reviewing schedules all work with no network.

Two rules from the PRD are enforced here:

- Cache eviction never removes drafts, notes, schedules, folders, campaigns, or
  delivery history (PRD 30). Only ``SocialItem`` rows are disposable cache.
- Re-fetching a post preserves local-only state -- read, flagged, folders,
  tags -- so a background refresh never marks a read post unread or drops the
  folder a user filed it in (PRD 12.5).

The class is wx-free so it can be unit-tested headlessly, following the
``quill_beacon.db`` precedent.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from quill_social.model import (
    Account,
    Campaign,
    Draft,
    Folder,
    Note,
    PublicationPlan,
    ReadingPosition,
    SavedSearch,
    SocialItem,
    Workspace,
    now_ms,
)

SCHEMA_VERSION = 1

SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_meta (key TEXT PRIMARY KEY, value TEXT);

CREATE TABLE IF NOT EXISTS workspaces (
    workspace_id TEXT PRIMARY KEY,
    name TEXT NOT NULL DEFAULT '',
    position INTEGER NOT NULL DEFAULT 0,
    created INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS accounts (
    account_id TEXT PRIMARY KEY,
    network TEXT NOT NULL,
    handle TEXT NOT NULL DEFAULT '',
    display_name TEXT NOT NULL DEFAULT '',
    instance TEXT NOT NULL DEFAULT '',
    did TEXT NOT NULL DEFAULT '',
    local_alias TEXT NOT NULL DEFAULT '',
    workspace_id TEXT NOT NULL DEFAULT '',
    is_default INTEGER NOT NULL DEFAULT 0,
    paused INTEGER NOT NULL DEFAULT 0,
    color TEXT NOT NULL DEFAULT '',
    signature TEXT NOT NULL DEFAULT '',
    created INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_accounts_ws ON accounts(workspace_id);

CREATE TABLE IF NOT EXISTS items (
    item_id TEXT PRIMARY KEY,
    network TEXT NOT NULL,
    account_id TEXT NOT NULL DEFAULT '',
    remote_id TEXT NOT NULL DEFAULT '',
    uri TEXT NOT NULL DEFAULT '',
    author_handle TEXT NOT NULL DEFAULT '',
    author_display TEXT NOT NULL DEFAULT '',
    author_id TEXT NOT NULL DEFAULT '',
    text TEXT NOT NULL DEFAULT '',
    lang TEXT NOT NULL DEFAULT '',
    created_at INTEGER NOT NULL DEFAULT 0,
    visibility TEXT NOT NULL DEFAULT 'public',
    content_warning TEXT NOT NULL DEFAULT '',
    sensitive INTEGER NOT NULL DEFAULT 0,
    in_reply_to TEXT NOT NULL DEFAULT '',
    thread_root TEXT NOT NULL DEFAULT '',
    quote_of TEXT NOT NULL DEFAULT '',
    reblog_of TEXT NOT NULL DEFAULT '',
    reblog_by TEXT NOT NULL DEFAULT '',
    thread_level INTEGER NOT NULL DEFAULT 0,
    reply_count INTEGER NOT NULL DEFAULT 0,
    reblog_count INTEGER NOT NULL DEFAULT 0,
    favourite_count INTEGER NOT NULL DEFAULT 0,
    favourited INTEGER NOT NULL DEFAULT 0,
    bookmarked INTEGER NOT NULL DEFAULT 0,
    reblogged INTEGER NOT NULL DEFAULT 0,
    moderation_labels TEXT NOT NULL DEFAULT '[]',
    media TEXT NOT NULL DEFAULT '[]',
    poll TEXT NOT NULL DEFAULT '',
    read INTEGER NOT NULL DEFAULT 0,
    flagged INTEGER NOT NULL DEFAULT 0,
    folders TEXT NOT NULL DEFAULT '[]',
    tags TEXT NOT NULL DEFAULT '[]',
    fetched_at INTEGER NOT NULL DEFAULT 0
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_items_remote
    ON items(network, account_id, remote_id);
CREATE INDEX IF NOT EXISTS idx_items_account ON items(account_id);
CREATE INDEX IF NOT EXISTS idx_items_created ON items(created_at);
CREATE INDEX IF NOT EXISTS idx_items_read ON items(read);
CREATE INDEX IF NOT EXISTS idx_items_bookmarked ON items(bookmarked);
CREATE INDEX IF NOT EXISTS idx_items_flagged ON items(flagged);

CREATE TABLE IF NOT EXISTS drafts (
    draft_id TEXT PRIMARY KEY,
    text TEXT NOT NULL DEFAULT '',
    targets TEXT NOT NULL DEFAULT '[]',
    visibility TEXT NOT NULL DEFAULT 'public',
    content_warning TEXT NOT NULL DEFAULT '',
    lang TEXT NOT NULL DEFAULT '',
    in_reply_to TEXT NOT NULL DEFAULT '',
    quote_of TEXT NOT NULL DEFAULT '',
    thread_mode INTEGER NOT NULL DEFAULT 0,
    media TEXT NOT NULL DEFAULT '[]',
    poll TEXT NOT NULL DEFAULT '',
    variants TEXT NOT NULL DEFAULT '{}',
    campaign_id TEXT NOT NULL DEFAULT '',
    name TEXT NOT NULL DEFAULT '',
    local_only INTEGER NOT NULL DEFAULT 0,
    created INTEGER NOT NULL,
    updated INTEGER NOT NULL,
    version INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS folders (
    folder_id TEXT PRIMARY KEY,
    name TEXT NOT NULL DEFAULT '',
    parent_id TEXT NOT NULL DEFAULT '',
    kind TEXT NOT NULL DEFAULT 'manual',
    rule TEXT NOT NULL DEFAULT '{}',
    position INTEGER NOT NULL DEFAULT 0,
    created INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS folder_members (
    folder_id TEXT NOT NULL,
    item_id TEXT NOT NULL,
    position INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (folder_id, item_id)
);

CREATE TABLE IF NOT EXISTS notes (
    note_id TEXT PRIMARY KEY,
    target_type TEXT NOT NULL DEFAULT 'profile',
    target_id TEXT NOT NULL DEFAULT '',
    text TEXT NOT NULL DEFAULT '',
    alias TEXT NOT NULL DEFAULT '',
    follow_up_at INTEGER,
    tags TEXT NOT NULL DEFAULT '[]',
    confidential INTEGER NOT NULL DEFAULT 0,
    created INTEGER NOT NULL,
    updated INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_notes_target ON notes(target_type, target_id);

CREATE TABLE IF NOT EXISTS campaigns (
    campaign_id TEXT PRIMARY KEY,
    name TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    start_at INTEGER,
    end_at INTEGER,
    account_ids TEXT NOT NULL DEFAULT '[]',
    hashtags TEXT NOT NULL DEFAULT '[]',
    created INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS plans (
    plan_id TEXT PRIMARY KEY,
    draft_id TEXT NOT NULL DEFAULT '',
    account_id TEXT NOT NULL DEFAULT '',
    network TEXT NOT NULL DEFAULT 'mock',
    tier TEXT NOT NULL DEFAULT 'local',
    scheduled_for INTEGER,
    state TEXT NOT NULL DEFAULT 'queued',
    remote_id TEXT NOT NULL DEFAULT '',
    campaign_id TEXT NOT NULL DEFAULT '',
    attempts TEXT NOT NULL DEFAULT '[]',
    next_retry_at INTEGER,
    created INTEGER NOT NULL,
    updated INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_plans_state ON plans(state);
CREATE INDEX IF NOT EXISTS idx_plans_due ON plans(scheduled_for);
CREATE INDEX IF NOT EXISTS idx_plans_draft ON plans(draft_id);

CREATE TABLE IF NOT EXISTS saved_searches (
    search_id TEXT PRIMARY KEY,
    name TEXT NOT NULL DEFAULT '',
    query TEXT NOT NULL DEFAULT '',
    scope TEXT NOT NULL DEFAULT 'local',
    created INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS reading_positions (
    account_id TEXT NOT NULL,
    feed TEXT NOT NULL,
    item_id TEXT NOT NULL DEFAULT '',
    updated INTEGER NOT NULL,
    PRIMARY KEY (account_id, feed)
);

CREATE VIRTUAL TABLE IF NOT EXISTS item_fts USING fts5(
    item_id UNINDEXED,
    text, author, handle, cw, tags, folders,
    network UNINDEXED,
    tokenize = "unicode61 remove_diacritics 2"
);

-- Generic JSON document store (PRD 30). A single flexible table so services
-- (templates, filters, notification policies, queue schedules, plugins, github
-- items, transcripts, analytics events, ...) can persist their own record types
-- without each one adding a bespoke table. Durable user data -- never treated
-- as disposable cache. Keyed by (kind, doc_id); ``ordinal`` gives a stable sort.
CREATE TABLE IF NOT EXISTS documents (
    kind TEXT NOT NULL,
    doc_id TEXT NOT NULL,
    data TEXT NOT NULL DEFAULT '{}',
    ordinal INTEGER NOT NULL DEFAULT 0,
    updated INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (kind, doc_id)
);
CREATE INDEX IF NOT EXISTS idx_documents_kind ON documents(kind);
"""


class SocialStore:
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

    def __enter__(self) -> SocialStore:
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
            raise RuntimeError(f"store schema v{current} is newer than engine v{SCHEMA_VERSION}")
        # Future additive migrations land here, mirroring quill_beacon.db.

    # -- workspaces -----------------------------------------------------------

    def put_workspace(self, ws: Workspace) -> Workspace:
        with self.conn:
            self.conn.execute(
                """INSERT INTO workspaces (workspace_id, name, position, created)
                   VALUES (:workspace_id, :name, :position, :created)
                   ON CONFLICT(workspace_id) DO UPDATE SET
                   name=excluded.name, position=excluded.position""",
                ws.to_row(),
            )
        return ws

    def list_workspaces(self) -> list[Workspace]:
        rows = self.conn.execute("SELECT * FROM workspaces ORDER BY position, created").fetchall()
        return [Workspace.from_row(dict(r)) for r in rows]

    # -- accounts -------------------------------------------------------------

    def put_account(self, account: Account) -> Account:
        with self.conn:
            self.conn.execute(
                """INSERT INTO accounts (account_id, network, handle, display_name,
                   instance, did, local_alias, workspace_id, is_default, paused,
                   color, signature, created)
                   VALUES (:account_id, :network, :handle, :display_name, :instance,
                   :did, :local_alias, :workspace_id, :is_default, :paused, :color,
                   :signature, :created)
                   ON CONFLICT(account_id) DO UPDATE SET
                   network=excluded.network, handle=excluded.handle,
                   display_name=excluded.display_name, instance=excluded.instance,
                   did=excluded.did, local_alias=excluded.local_alias,
                   workspace_id=excluded.workspace_id, is_default=excluded.is_default,
                   paused=excluded.paused, color=excluded.color,
                   signature=excluded.signature""",
                account.to_row(),
            )
        return account

    def get_account(self, account_id: str) -> Account | None:
        row = self.conn.execute(
            "SELECT * FROM accounts WHERE account_id=?", (account_id,)
        ).fetchone()
        return Account.from_row(dict(row)) if row else None

    def list_accounts(self, *, include_paused: bool = True) -> list[Account]:
        where = "" if include_paused else "WHERE paused=0"
        rows = self.conn.execute(f"SELECT * FROM accounts {where} ORDER BY created").fetchall()
        return [Account.from_row(dict(r)) for r in rows]

    def delete_account(self, account_id: str) -> None:
        with self.conn:
            self.conn.execute("DELETE FROM accounts WHERE account_id=?", (account_id,))
            self.conn.execute(
                "DELETE FROM item_fts WHERE item_id IN "
                "(SELECT item_id FROM items WHERE account_id=?)",
                (account_id,),
            )
            self.conn.execute("DELETE FROM items WHERE account_id=?", (account_id,))

    # -- items ----------------------------------------------------------------

    def upsert_item(self, item: SocialItem) -> SocialItem:
        """Insert or refresh a post, preserving local-only state on re-fetch.

        Dedupe key is (network, account_id, remote_id). When a matching row
        exists, its read/flagged/folders/tags and item_id are kept so a
        background refresh never resets what the user did locally (PRD 12.5).
        """
        existing = None
        if item.remote_id:
            row = self.conn.execute(
                "SELECT * FROM items WHERE network=? AND account_id=? AND remote_id=?",
                (item.network, item.account_id, item.remote_id),
            ).fetchone()
            if row:
                existing = SocialItem.from_row(dict(row))
        if existing:
            item.item_id = existing.item_id
            item.read = existing.read
            item.flagged = existing.flagged
            # union of remote + local organization so neither side loses data
            item.folders = existing.folders or item.folders
            if existing.tags:
                item.tags = sorted(set(existing.tags) | set(item.tags))
        item.fetched_at = now_ms()
        with self.conn:
            self.conn.execute(
                """INSERT INTO items (item_id, network, account_id, remote_id, uri,
                   author_handle, author_display, author_id, text, lang, created_at,
                   visibility, content_warning, sensitive, in_reply_to, thread_root,
                   quote_of, reblog_of, reblog_by, thread_level, reply_count,
                   reblog_count, favourite_count, favourited, bookmarked, reblogged,
                   moderation_labels, media, poll, read, flagged, folders, tags,
                   fetched_at)
                   VALUES (:item_id, :network, :account_id, :remote_id, :uri,
                   :author_handle, :author_display, :author_id, :text, :lang,
                   :created_at, :visibility, :content_warning, :sensitive,
                   :in_reply_to, :thread_root, :quote_of, :reblog_of, :reblog_by,
                   :thread_level, :reply_count, :reblog_count, :favourite_count,
                   :favourited, :bookmarked, :reblogged, :moderation_labels, :media,
                   :poll, :read, :flagged, :folders, :tags, :fetched_at)
                   ON CONFLICT(item_id) DO UPDATE SET
                   uri=excluded.uri, author_handle=excluded.author_handle,
                   author_display=excluded.author_display, text=excluded.text,
                   lang=excluded.lang, visibility=excluded.visibility,
                   content_warning=excluded.content_warning,
                   sensitive=excluded.sensitive, reply_count=excluded.reply_count,
                   reblog_count=excluded.reblog_count,
                   favourite_count=excluded.favourite_count,
                   favourited=excluded.favourited, bookmarked=excluded.bookmarked,
                   reblogged=excluded.reblogged,
                   moderation_labels=excluded.moderation_labels, media=excluded.media,
                   poll=excluded.poll, read=excluded.read, flagged=excluded.flagged,
                   folders=excluded.folders, tags=excluded.tags,
                   fetched_at=excluded.fetched_at""",
                item.to_row(),
            )
            self._reindex_item(item)
        return item

    def _reindex_item(self, item: SocialItem) -> None:
        self.conn.execute("DELETE FROM item_fts WHERE item_id=?", (item.item_id,))
        self.conn.execute(
            """INSERT INTO item_fts(item_id, text, author, handle, cw, tags, folders,
               network) VALUES(?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                item.item_id,
                item.text,
                item.author_display,
                item.author_handle,
                item.content_warning,
                " ".join(item.tags),
                " ".join(item.folders),
                item.network,
            ),
        )

    def get_item(self, item_id: str) -> SocialItem | None:
        row = self.conn.execute("SELECT * FROM items WHERE item_id=?", (item_id,)).fetchone()
        return SocialItem.from_row(dict(row)) if row else None

    def list_items(
        self,
        *,
        account_id: str | None = None,
        network: str | None = None,
        bookmarked: bool | None = None,
        flagged: bool | None = None,
        favourited: bool | None = None,
        unread_only: bool = False,
        thread_root: str | None = None,
        limit: int = 500,
        offset: int = 0,
        newest_first: bool = True,
    ) -> list[SocialItem]:
        clauses: list[str] = []
        params: list[object] = []
        if account_id:
            clauses.append("account_id=?")
            params.append(account_id)
        if network:
            clauses.append("network=?")
            params.append(network)
        if bookmarked is not None:
            clauses.append("bookmarked=?")
            params.append(int(bookmarked))
        if flagged is not None:
            clauses.append("flagged=?")
            params.append(int(flagged))
        if favourited is not None:
            clauses.append("favourited=?")
            params.append(int(favourited))
        if unread_only:
            clauses.append("read=0")
        if thread_root is not None:
            clauses.append("(thread_root=? OR item_id=? OR remote_id=?)")
            params.extend([thread_root, thread_root, thread_root])
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        order = "DESC" if newest_first else "ASC"
        params.extend([limit, offset])
        rows = self.conn.execute(
            f"SELECT * FROM items {where} ORDER BY created_at {order} LIMIT ? OFFSET ?",
            params,
        ).fetchall()
        return [SocialItem.from_row(dict(r)) for r in rows]

    def count_unread(self, account_id: str | None = None) -> int:
        if account_id:
            row = self.conn.execute(
                "SELECT COUNT(*) AS n FROM items WHERE read=0 AND account_id=?",
                (account_id,),
            ).fetchone()
        else:
            row = self.conn.execute("SELECT COUNT(*) AS n FROM items WHERE read=0").fetchone()
        return row["n"]

    def set_read(self, item_id: str, read: bool = True) -> None:
        with self.conn:
            self.conn.execute("UPDATE items SET read=? WHERE item_id=?", (int(read), item_id))

    def set_flag(self, item_id: str, column: str, value: bool) -> None:
        if column not in ("favourited", "bookmarked", "reblogged", "flagged", "read"):
            raise ValueError(f"not a togglable column: {column}")
        with self.conn:
            self.conn.execute(
                f"UPDATE items SET {column}=? WHERE item_id=?",
                (int(value), item_id),
            )

    def mark_all_read(
        self, *, account_ids: list[str] | None = None, read: bool = True
    ) -> list[str]:
        """Bulk-set read state across a scope; return the item_ids that changed.

        Scope is all cached items, or -- when ``account_ids`` is given -- just
        those feeds/accounts (the set of feed subscriptions under a folder, for a
        per-folder "mark all read"). Returning only the rows whose state actually
        flipped lets the UI announce an accurate count and offer an exact undo via
        :meth:`set_read_bulk` (plan xxx.md 3.10.3).
        """
        target = int(read)
        where = "read != ?"
        params: list[object] = [target]
        if account_ids is not None:
            if not account_ids:
                return []
            placeholders = ",".join("?" for _ in account_ids)
            where += f" AND account_id IN ({placeholders})"
            params.extend(account_ids)
        with self.conn:
            changed = [
                r["item_id"]
                for r in self.conn.execute(
                    f"SELECT item_id FROM items WHERE {where}", params
                ).fetchall()
            ]
            if changed:
                self.conn.execute(f"UPDATE items SET read={target} WHERE {where}", params)
        return changed

    def set_read_bulk(self, item_ids: list[str], read: bool = True) -> None:
        """Set read state for an explicit set of items (the undo of a bulk mark)."""
        if not item_ids:
            return
        with self.conn:
            self.conn.executemany(
                "UPDATE items SET read=? WHERE item_id=?",
                [(int(read), iid) for iid in item_ids],
            )

    def search_items(self, query: str, *, limit: int = 200) -> list[SocialItem]:
        """Full-text search over cached posts (PRD 26)."""
        q = _fts_query(query)
        if not q:
            return []
        rows = self.conn.execute(
            """SELECT i.* FROM item_fts f JOIN items i ON i.item_id = f.item_id
               WHERE item_fts MATCH ? ORDER BY i.created_at DESC LIMIT ?""",
            (q, limit),
        ).fetchall()
        return [SocialItem.from_row(dict(r)) for r in rows]

    def prune_items(
        self,
        *,
        keep_days: int = 30,
        protect_flagged: bool = True,
        account_id: str | None = None,
    ) -> int:
        """Evict old cached posts. Never touches bookmarked/flagged rows.

        Drafts, notes, schedules, folders, and campaigns are separate tables and
        are never affected (PRD 30). When ``account_id`` is given, only that
        account's (feed's) items are considered -- per-feed retention that never
        evicts starred/kept entries. Returns the number of rows removed.
        """
        cutoff = now_ms() - keep_days * 86_400_000
        clauses = ["fetched_at < ?"]
        params: list[object] = [cutoff]
        if protect_flagged:
            clauses.append("flagged=0 AND bookmarked=0")
        if account_id is not None:
            clauses.append("account_id=?")
            params.append(account_id)
        where = " AND ".join(clauses)
        with self.conn:
            doomed = [
                r["item_id"]
                for r in self.conn.execute(
                    f"SELECT item_id FROM items WHERE {where}",
                    tuple(params),
                ).fetchall()
            ]
            for iid in doomed:
                self.conn.execute("DELETE FROM item_fts WHERE item_id=?", (iid,))
                self.conn.execute("DELETE FROM items WHERE item_id=?", (iid,))
        return len(doomed)

    # -- drafts ---------------------------------------------------------------

    def put_draft(self, draft: Draft) -> Draft:
        draft.updated = now_ms()
        with self.conn:
            self.conn.execute(
                """INSERT INTO drafts (draft_id, text, targets, visibility,
                   content_warning, lang, in_reply_to, quote_of, thread_mode, media,
                   poll, variants, campaign_id, name, local_only, created, updated,
                   version)
                   VALUES (:draft_id, :text, :targets, :visibility, :content_warning,
                   :lang, :in_reply_to, :quote_of, :thread_mode, :media, :poll,
                   :variants, :campaign_id, :name, :local_only, :created, :updated,
                   :version)
                   ON CONFLICT(draft_id) DO UPDATE SET
                   text=excluded.text, targets=excluded.targets,
                   visibility=excluded.visibility,
                   content_warning=excluded.content_warning, lang=excluded.lang,
                   in_reply_to=excluded.in_reply_to, quote_of=excluded.quote_of,
                   thread_mode=excluded.thread_mode, media=excluded.media,
                   poll=excluded.poll, variants=excluded.variants,
                   campaign_id=excluded.campaign_id, name=excluded.name,
                   local_only=excluded.local_only, updated=excluded.updated,
                   version=excluded.version""",
                draft.to_row(),
            )
        return draft

    def get_draft(self, draft_id: str) -> Draft | None:
        row = self.conn.execute("SELECT * FROM drafts WHERE draft_id=?", (draft_id,)).fetchone()
        return Draft.from_row(dict(row)) if row else None

    def list_drafts(self, *, campaign_id: str | None = None) -> list[Draft]:
        if campaign_id:
            rows = self.conn.execute(
                "SELECT * FROM drafts WHERE campaign_id=? ORDER BY updated DESC",
                (campaign_id,),
            ).fetchall()
        else:
            rows = self.conn.execute("SELECT * FROM drafts ORDER BY updated DESC").fetchall()
        return [Draft.from_row(dict(r)) for r in rows]

    def delete_draft(self, draft_id: str) -> None:
        with self.conn:
            self.conn.execute("DELETE FROM drafts WHERE draft_id=?", (draft_id,))

    # -- folders --------------------------------------------------------------

    def put_folder(self, folder: Folder) -> Folder:
        with self.conn:
            self.conn.execute(
                """INSERT INTO folders (folder_id, name, parent_id, kind, rule,
                   position, created)
                   VALUES (:folder_id, :name, :parent_id, :kind, :rule, :position,
                   :created)
                   ON CONFLICT(folder_id) DO UPDATE SET
                   name=excluded.name, parent_id=excluded.parent_id,
                   kind=excluded.kind, rule=excluded.rule,
                   position=excluded.position""",
                folder.to_row(),
            )
        return folder

    def list_folders(self, *, kind: str | None = None) -> list[Folder]:
        if kind:
            rows = self.conn.execute(
                "SELECT * FROM folders WHERE kind=? ORDER BY position, name", (kind,)
            ).fetchall()
        else:
            rows = self.conn.execute("SELECT * FROM folders ORDER BY position, name").fetchall()
        return [Folder.from_row(dict(r)) for r in rows]

    def delete_folder(self, folder_id: str) -> None:
        with self.conn:
            self.conn.execute("DELETE FROM folders WHERE folder_id=?", (folder_id,))
            self.conn.execute("DELETE FROM folder_members WHERE folder_id=?", (folder_id,))

    def add_to_folder(self, folder_id: str, item_id: str) -> None:
        with self.conn:
            pos = self.conn.execute(
                "SELECT COALESCE(MAX(position), -1) + 1 AS p FROM folder_members WHERE folder_id=?",
                (folder_id,),
            ).fetchone()["p"]
            self.conn.execute(
                "INSERT OR IGNORE INTO folder_members(folder_id, item_id, position) "
                "VALUES(?, ?, ?)",
                (folder_id, item_id, pos),
            )

    def remove_from_folder(self, folder_id: str, item_id: str) -> None:
        with self.conn:
            self.conn.execute(
                "DELETE FROM folder_members WHERE folder_id=? AND item_id=?",
                (folder_id, item_id),
            )

    def list_folder_items(self, folder_id: str) -> list[SocialItem]:
        rows = self.conn.execute(
            """SELECT i.* FROM folder_members m JOIN items i ON i.item_id = m.item_id
               WHERE m.folder_id=? ORDER BY m.position""",
            (folder_id,),
        ).fetchall()
        return [SocialItem.from_row(dict(r)) for r in rows]

    # -- notes ----------------------------------------------------------------

    def put_note(self, note: Note) -> Note:
        note.updated = now_ms()
        with self.conn:
            self.conn.execute(
                """INSERT INTO notes (note_id, target_type, target_id, text, alias,
                   follow_up_at, tags, confidential, created, updated)
                   VALUES (:note_id, :target_type, :target_id, :text, :alias,
                   :follow_up_at, :tags, :confidential, :created, :updated)
                   ON CONFLICT(note_id) DO UPDATE SET
                   text=excluded.text, alias=excluded.alias,
                   follow_up_at=excluded.follow_up_at, tags=excluded.tags,
                   confidential=excluded.confidential, updated=excluded.updated""",
                note.to_row(),
            )
        return note

    def notes_for(self, target_type: str, target_id: str) -> list[Note]:
        rows = self.conn.execute(
            "SELECT * FROM notes WHERE target_type=? AND target_id=? ORDER BY updated DESC",
            (target_type, target_id),
        ).fetchall()
        return [Note.from_row(dict(r)) for r in rows]

    def delete_note(self, note_id: str) -> None:
        with self.conn:
            self.conn.execute("DELETE FROM notes WHERE note_id=?", (note_id,))

    # -- campaigns ------------------------------------------------------------

    def put_campaign(self, campaign: Campaign) -> Campaign:
        with self.conn:
            self.conn.execute(
                """INSERT INTO campaigns (campaign_id, name, description, start_at,
                   end_at, account_ids, hashtags, created)
                   VALUES (:campaign_id, :name, :description, :start_at, :end_at,
                   :account_ids, :hashtags, :created)
                   ON CONFLICT(campaign_id) DO UPDATE SET
                   name=excluded.name, description=excluded.description,
                   start_at=excluded.start_at, end_at=excluded.end_at,
                   account_ids=excluded.account_ids, hashtags=excluded.hashtags""",
                campaign.to_row(),
            )
        return campaign

    def list_campaigns(self) -> list[Campaign]:
        rows = self.conn.execute("SELECT * FROM campaigns ORDER BY created DESC").fetchall()
        return [Campaign.from_row(dict(r)) for r in rows]

    # -- publication plans ----------------------------------------------------

    def put_plan(self, plan: PublicationPlan) -> PublicationPlan:
        plan.updated = now_ms()
        with self.conn:
            self.conn.execute(
                """INSERT INTO plans (plan_id, draft_id, account_id, network, tier,
                   scheduled_for, state, remote_id, campaign_id, attempts,
                   next_retry_at, created, updated)
                   VALUES (:plan_id, :draft_id, :account_id, :network, :tier,
                   :scheduled_for, :state, :remote_id, :campaign_id, :attempts,
                   :next_retry_at, :created, :updated)
                   ON CONFLICT(plan_id) DO UPDATE SET
                   state=excluded.state, remote_id=excluded.remote_id,
                   scheduled_for=excluded.scheduled_for, tier=excluded.tier,
                   attempts=excluded.attempts, next_retry_at=excluded.next_retry_at,
                   campaign_id=excluded.campaign_id, updated=excluded.updated""",
                plan.to_row(),
            )
        return plan

    def get_plan(self, plan_id: str) -> PublicationPlan | None:
        row = self.conn.execute("SELECT * FROM plans WHERE plan_id=?", (plan_id,)).fetchone()
        return PublicationPlan.from_row(dict(row)) if row else None

    def list_plans(
        self, *, state: str | None = None, draft_id: str | None = None
    ) -> list[PublicationPlan]:
        clauses, params = [], []
        if state:
            clauses.append("state=?")
            params.append(state)
        if draft_id:
            clauses.append("draft_id=?")
            params.append(draft_id)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self.conn.execute(
            f"SELECT * FROM plans {where} ORDER BY COALESCE(scheduled_for, created)",
            params,
        ).fetchall()
        return [PublicationPlan.from_row(dict(r)) for r in rows]

    def due_plans(self, *, now: int | None = None) -> list[PublicationPlan]:
        """Scheduled/queued plans whose time has arrived (PRD 18.3 local tier)."""
        at = now if now is not None else now_ms()
        rows = self.conn.execute(
            """SELECT * FROM plans
               WHERE state IN ('queued', 'scheduled')
               AND (scheduled_for IS NULL OR scheduled_for <= ?)
               AND (next_retry_at IS NULL OR next_retry_at <= ?)
               ORDER BY COALESCE(scheduled_for, created)""",
            (at, at),
        ).fetchall()
        return [PublicationPlan.from_row(dict(r)) for r in rows]

    # -- saved searches -------------------------------------------------------

    def put_saved_search(self, s: SavedSearch) -> SavedSearch:
        with self.conn:
            self.conn.execute(
                """INSERT INTO saved_searches (search_id, name, query, scope, created)
                   VALUES (:search_id, :name, :query, :scope, :created)
                   ON CONFLICT(search_id) DO UPDATE SET
                   name=excluded.name, query=excluded.query, scope=excluded.scope""",
                s.to_row(),
            )
        return s

    def list_saved_searches(self) -> list[SavedSearch]:
        rows = self.conn.execute("SELECT * FROM saved_searches ORDER BY created DESC").fetchall()
        return [SavedSearch.from_row(dict(r)) for r in rows]

    def delete_saved_search(self, search_id: str) -> None:
        with self.conn:
            self.conn.execute("DELETE FROM saved_searches WHERE search_id=?", (search_id,))

    # -- reading positions ----------------------------------------------------

    def set_position(self, pos: ReadingPosition) -> None:
        pos.updated = now_ms()
        with self.conn:
            self.conn.execute(
                """INSERT INTO reading_positions (account_id, feed, item_id, updated)
                   VALUES (:account_id, :feed, :item_id, :updated)
                   ON CONFLICT(account_id, feed) DO UPDATE SET
                   item_id=excluded.item_id, updated=excluded.updated""",
                pos.to_row(),
            )

    def get_position(self, account_id: str, feed: str) -> ReadingPosition | None:
        row = self.conn.execute(
            "SELECT * FROM reading_positions WHERE account_id=? AND feed=?",
            (account_id, feed),
        ).fetchone()
        return ReadingPosition.from_row(dict(row)) if row else None

    # -- generic document store -----------------------------------------------
    #
    # Services persist their own record types here as JSON, keyed by (kind,
    # doc_id), without adding bespoke tables. ``put_document`` stamps ``updated``;
    # ``ordinal`` is an optional stable sort key the caller controls.

    def put_document(self, kind: str, doc_id: str, data: dict, *, ordinal: int = 0) -> None:
        import json as _json

        with self.conn:
            self.conn.execute(
                """INSERT INTO documents (kind, doc_id, data, ordinal, updated)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(kind, doc_id) DO UPDATE SET
                   data=excluded.data, ordinal=excluded.ordinal,
                   updated=excluded.updated""",
                (kind, doc_id, _json.dumps(data, ensure_ascii=False), ordinal, now_ms()),
            )

    def get_document(self, kind: str, doc_id: str) -> dict | None:
        import json as _json

        row = self.conn.execute(
            "SELECT data FROM documents WHERE kind=? AND doc_id=?", (kind, doc_id)
        ).fetchone()
        if not row:
            return None
        try:
            return _json.loads(row["data"])
        except (ValueError, TypeError):
            return None

    def list_documents(self, kind: str) -> list[dict]:
        import json as _json

        rows = self.conn.execute(
            "SELECT data FROM documents WHERE kind=? ORDER BY ordinal, updated",
            (kind,),
        ).fetchall()
        out: list[dict] = []
        for r in rows:
            try:
                out.append(_json.loads(r["data"]))
            except (ValueError, TypeError):
                continue
        return out

    def delete_document(self, kind: str, doc_id: str) -> None:
        with self.conn:
            self.conn.execute("DELETE FROM documents WHERE kind=? AND doc_id=?", (kind, doc_id))


def _fts_query(query: str) -> str:
    """Turn a plain user query into a safe FTS5 MATCH expression.

    Quotes each bare term and ANDs them, so punctuation in the query can never
    produce an FTS syntax error. Empty input yields an empty string.
    """
    terms = [t for t in query.replace('"', " ").split() if t]
    if not terms:
        return ""
    return " AND ".join(f'"{t}"*' for t in terms)
