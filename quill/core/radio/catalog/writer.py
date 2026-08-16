"""Building the next catalog generation (the write half of the store).

Split from :mod:`quill.core.radio.catalog.store` under GATE-11, along the
seam that matters: :class:`~quill.core.radio.catalog.store.CatalogStore` is
read-only over the published generation, and this writer is the only thing
that produces a new one. Commit swaps the pointer; abandon deletes the file
and leaves the live catalog untouched - a crashed refresh can never publish
a half-written generation.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from quill.core.radio.catalog.store import CatalogStore, StationRow


class GenerationWriter:
    """One in-progress next generation. Commit swaps the pointer; abandon
    deletes the file and leaves the live catalog untouched."""

    def __init__(
        self, store: CatalogStore, con: sqlite3.Connection, generation: int, path: Path
    ) -> None:
        self._store = store
        self._con = con
        self._generation = generation
        self._path = path

    @property
    def connection(self) -> sqlite3.Connection:
        return self._con

    def set_meta(self, key: str, value: str) -> None:
        self._con.execute(
            "INSERT OR REPLACE INTO catalog_meta(key, value) VALUES (?, ?)", (key, value)
        )

    def upsert_stations(self, source_id: str, rows: list[StationRow], *, now: float) -> int:
        stamp = f"{now:.0f}"
        payload = [
            (
                row.key,
                row.name,
                row.stream_url,
                row.homepage,
                row.favicon,
                row.country,
                row.state,
                row.language,
                row.tags,
                row.codec,
                row.bitrate,
                row.votes,
                source_id,
                row.source_record_id,
                stamp,
                stamp,
            )
            for row in rows
            if row.key and row.name and row.stream_url
        ]
        self._con.executemany(
            "INSERT INTO stations(key, name, stream_url, homepage, favicon, country,"
            " state, language, tags, codec, bitrate, votes, source_id,"
            " source_record_id, first_seen, last_seen) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) "
            "ON CONFLICT(key) DO UPDATE SET name=excluded.name,"
            " stream_url=excluded.stream_url, homepage=excluded.homepage,"
            " favicon=excluded.favicon, country=excluded.country,"
            " state=excluded.state, language=excluded.language, tags=excluded.tags,"
            " codec=excluded.codec, bitrate=excluded.bitrate, votes=excluded.votes,"
            " last_seen=excluded.last_seen, vanished_at=NULL",
            payload,
        )
        return len(payload)

    def tombstone_missing(self, source_id: str, seen_keys: set[str], *, now: float) -> int:
        """Mark this source's rows that the refresh did not see. Never deletes;
        the grace-window purge happens in :meth:`purge_tombstones`."""
        stamp = f"{now:.0f}"
        cur = self._con.execute(
            "SELECT key FROM stations WHERE source_id=? AND vanished_at IS NULL",
            (source_id,),
        )
        missing = [key for (key,) in cur if key not in seen_keys]
        self._con.executemany(
            "UPDATE stations SET vanished_at=? WHERE key=?",
            [(stamp, key) for key in missing],
        )
        return len(missing)

    def purge_tombstones(self, *, now: float, grace_days: int = 14) -> int:
        cutoff = now - grace_days * 86400
        cur = self._con.execute(
            "DELETE FROM stations WHERE vanished_at IS NOT NULL AND CAST(vanished_at AS REAL) < ?",
            (cutoff,),
        )
        return int(cur.rowcount or 0)

    def record_source(
        self,
        source_id: str,
        *,
        status: str,
        error: str = "",
        content_hash: str = "",
        now: float,
    ) -> None:
        count = self._con.execute(
            "SELECT COUNT(*) FROM stations WHERE source_id=? AND vanished_at IS NULL",
            (source_id,),
        ).fetchone()[0]
        self._con.execute(
            "INSERT INTO sources(id, last_refresh, last_status, last_error,"
            " station_count, content_hash) VALUES (?,?,?,?,?,?) "
            "ON CONFLICT(id) DO UPDATE SET last_refresh=excluded.last_refresh,"
            " last_status=excluded.last_status, last_error=excluded.last_error,"
            " station_count=excluded.station_count, content_hash=excluded.content_hash",
            (source_id, f"{now:.0f}", status, error[:300], int(count), content_hash),
        )

    def source_hash(self, source_id: str) -> str:
        row = self._con.execute(
            "SELECT content_hash FROM sources WHERE id=?", (source_id,)
        ).fetchone()
        return str(row[0]) if row else ""

    def replace_audiobooks(
        self,
        source: str,
        books: list[tuple[str, str, str, str, str]],
        sections: list[tuple[str, int, str, str]],
    ) -> int:
        """Replace one library source wholesale: (id, title, authors, genres,
        language) plus (book_id, idx, title, url) sections."""
        self._con.execute("DELETE FROM audiobooks WHERE source=?", (source,))
        self._con.execute("DELETE FROM audiobook_sections WHERE source=?", (source,))
        self._con.executemany(
            "INSERT INTO audiobooks(source, book_id, title, authors, genres, language)"
            " VALUES (?,?,?,?,?,?)",
            [(source, *book) for book in books],
        )
        self._con.executemany(
            "INSERT INTO audiobook_sections(source, book_id, idx, title, url) VALUES (?,?,?,?,?)",
            [(source, *section) for section in sections],
        )
        return len(books)

    def replace_identities(self, authority: str, links: list[tuple[str, str]]) -> int:
        self._con.execute("DELETE FROM identities WHERE authority=?", (authority,))
        self._con.executemany(
            "INSERT OR REPLACE INTO identities(key, authority, identity) VALUES (?,?,?)",
            [(key, authority, identity) for key, identity in links],
        )
        return len(links)

    def commit(self) -> None:
        self._con.commit()
        self._con.close()
        self._store._commit_generation(self._generation)

    def abandon(self) -> None:
        try:
            self._con.close()
        finally:
            self._path.unlink(missing_ok=True)
