"""The catalog store: SQLite generations behind a pointer file.

The only module that touches the database. Everything above it speaks in
:class:`~quill.core.radio.models.RadioStation` and plain values.

**Why generations and a pointer, not swap-in-place:** measured on Windows,
``os.replace`` over a database an open connection holds raises
PermissionError. So a refresh never touches the live file: it copies the
current generation to ``catalog.<n+1>.db``, applies its changes there, then
atomically replaces the tiny ``CURRENT`` pointer. Readers resolve the pointer
when they (re)open; a crashed refresh leaves a garbage numbered file and an
untouched pointer - always consistent. Stale generations are deleted on the
next open, where nothing can be holding them.

The catalog is derived data: :meth:`CatalogStore.destroy` removes the whole
directory and loses nothing the listener owns, which is what makes every
error path here allowed to end in "rebuild from seed".
"""

from __future__ import annotations

import logging
import os
import re
import shutil
import sqlite3
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from quill.core.radio.catalog import CatalogCorruptError
from quill.core.radio.models import RadioStation

if TYPE_CHECKING:
    from quill.core.radio.catalog.writer import GenerationWriter

logger = logging.getLogger(__name__)

DIR_NAME = "radio-catalog"
POINTER = "CURRENT"
_GEN_RE = re.compile(r"^catalog\.(\d+)\.db$")

SCHEMA_VERSION = 1

_SCHEMA = """
CREATE TABLE IF NOT EXISTS catalog_meta(
  key   TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sources(
  id            TEXT PRIMARY KEY,
  last_refresh  TEXT NOT NULL DEFAULT '',
  last_status   TEXT NOT NULL DEFAULT '',
  last_error    TEXT NOT NULL DEFAULT '',
  station_count INTEGER NOT NULL DEFAULT 0,
  content_hash  TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS stations(
  key        TEXT PRIMARY KEY,
  name       TEXT NOT NULL,
  stream_url TEXT NOT NULL,
  homepage   TEXT NOT NULL DEFAULT '',
  favicon    TEXT NOT NULL DEFAULT '',
  country    TEXT NOT NULL DEFAULT '',
  state      TEXT NOT NULL DEFAULT '',
  language   TEXT NOT NULL DEFAULT '',
  tags       TEXT NOT NULL DEFAULT '',
  codec      TEXT NOT NULL DEFAULT '',
  bitrate    INTEGER NOT NULL DEFAULT 0,
  votes      INTEGER NOT NULL DEFAULT 0,
  source_id  TEXT NOT NULL,
  source_record_id TEXT NOT NULL DEFAULT '',
  first_seen TEXT NOT NULL DEFAULT '',
  last_seen  TEXT NOT NULL DEFAULT '',
  vanished_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_st_geo   ON stations(country, state);
CREATE INDEX IF NOT EXISTS idx_st_lang  ON stations(language);
CREATE INDEX IF NOT EXISTS idx_st_src   ON stations(source_id);
-- Measured: 41 ms bare, 0.53 ms with this index, for a by-country browse
-- ordered the way the tree shows it.
CREATE INDEX IF NOT EXISTS idx_st_votes ON stations(country, votes DESC);
CREATE VIRTUAL TABLE IF NOT EXISTS stations_fts USING fts5(
  name, tags, country, content='stations', content_rowid='rowid'
);
CREATE TRIGGER IF NOT EXISTS st_ai AFTER INSERT ON stations BEGIN
  INSERT INTO stations_fts(rowid, name, tags, country)
  VALUES (new.rowid, new.name, new.tags, new.country);
END;
CREATE TRIGGER IF NOT EXISTS st_ad AFTER DELETE ON stations BEGIN
  INSERT INTO stations_fts(stations_fts, rowid, name, tags, country)
  VALUES ('delete', old.rowid, old.name, old.tags, old.country);
END;
CREATE TRIGGER IF NOT EXISTS st_au AFTER UPDATE ON stations BEGIN
  INSERT INTO stations_fts(stations_fts, rowid, name, tags, country)
  VALUES ('delete', old.rowid, old.name, old.tags, old.country);
  INSERT INTO stations_fts(rowid, name, tags, country)
  VALUES (new.rowid, new.name, new.tags, new.country);
END;
CREATE TABLE IF NOT EXISTS audiobooks(
  source  TEXT NOT NULL,
  book_id TEXT NOT NULL,
  title   TEXT NOT NULL,
  authors TEXT NOT NULL DEFAULT '',
  genres  TEXT NOT NULL DEFAULT '',
  language TEXT NOT NULL DEFAULT '',
  PRIMARY KEY(source, book_id)
);
CREATE TABLE IF NOT EXISTS audiobook_sections(
  source  TEXT NOT NULL,
  book_id TEXT NOT NULL,
  idx     INTEGER NOT NULL,
  title   TEXT NOT NULL DEFAULT '',
  url     TEXT NOT NULL,
  PRIMARY KEY(source, book_id, idx)
);
CREATE TABLE IF NOT EXISTS identities(
  key        TEXT NOT NULL,
  authority  TEXT NOT NULL,
  identity   TEXT NOT NULL,
  PRIMARY KEY(key, authority)
);
"""


@dataclass(frozen=True, slots=True)
class SourceHealth:
    """One source's refresh state, for the status view and the summary."""

    id: str
    last_refresh: str
    last_status: str
    last_error: str
    station_count: int


@dataclass(frozen=True, slots=True)
class StationRow:
    """One station as the catalog stores it - superset of RadioStation."""

    key: str
    name: str
    stream_url: str
    homepage: str = ""
    favicon: str = ""
    country: str = ""
    state: str = ""
    language: str = ""
    tags: str = ""
    codec: str = ""
    bitrate: int = 0
    votes: int = 0
    source_id: str = ""
    source_record_id: str = ""

    def to_station(self, *, source_label: str) -> RadioStation:
        return RadioStation(
            name=self.name,
            stream_url=self.stream_url,
            station_uuid=self.source_record_id,
            homepage=self.homepage,
            favicon=self.favicon,
            country=self.country,
            language=self.language,
            tags=tuple(t for t in self.tags.split(",") if t)[:8],
            codec=self.codec,
            bitrate_kbps=self.bitrate,
            votes=self.votes,
            source=source_label,
        )


def catalog_dir(data_dir: Path | str) -> Path:
    return Path(data_dir) / DIR_NAME


def _generation_path(root: Path, generation: int) -> Path:
    return root / f"catalog.{generation}.db"


def current_generation(root: Path) -> int | None:
    """The generation the pointer names, or ``None`` when there is no catalog."""
    try:
        name = (root / POINTER).read_text(encoding="utf-8").strip()
    except OSError:
        return None
    match = _GEN_RE.match(name)
    if match is None or not (root / name).is_file():
        return None
    return int(match.group(1))


def _set_pointer(root: Path, generation: int) -> None:
    tmp = root / (POINTER + ".tmp")
    tmp.write_text(_generation_path(root, generation).name, encoding="utf-8")
    os.replace(tmp, root / POINTER)


def _collect_garbage(root: Path, keep: int) -> None:
    """Delete stale generations. Failures are fine - they retry next open."""
    for entry in root.glob("catalog.*.db"):
        match = _GEN_RE.match(entry.name)
        if match is None or int(match.group(1)) == keep:
            continue
        try:
            entry.unlink()
        except OSError:
            pass


class CatalogStore:
    """Read access to the current generation, and generation-building for refresh.

    One instance per app session, opened lazily on first query so an app that
    never browses never pays for it. Not thread-safe by contract: readers run
    on the task manager one query at a time, exactly like the source fetchers
    they replace, and refresh builds a *different* file.
    """

    def __init__(self, data_dir: Path | str) -> None:
        self._root = catalog_dir(data_dir)
        # One connection PER THREAD. sqlite3 refuses a connection used from a
        # thread other than the one that created it, and this store is opened
        # on a task-manager worker (the startup refresh) and then read from the
        # UI thread on every browse -- so a single shared connection raised
        # ProgrammingError on every catalog-served branch and the tree quietly
        # fell back to the network. Read-only, so per-thread costs nothing and
        # needs no lock.
        self._local = threading.local()
        self._generation: int | None = None

    # -- lifecycle ------------------------------------------------------------

    @property
    def root(self) -> Path:
        return self._root

    def exists(self) -> bool:
        return current_generation(self._root) is not None

    def _connect(self) -> sqlite3.Connection:
        existing: sqlite3.Connection | None = getattr(self._local, "con", None)
        if existing is not None:
            return existing
        generation = current_generation(self._root)
        if generation is None:
            raise CatalogCorruptError("No catalog generation is present.")
        path = _generation_path(self._root, generation)
        try:
            con = sqlite3.connect(path)
            con.execute("PRAGMA query_only=ON")
            version = con.execute(
                "SELECT value FROM catalog_meta WHERE key='schema_version'"
            ).fetchone()
        except sqlite3.Error as error:
            raise CatalogCorruptError(f"The catalog could not be opened: {error}") from error
        if version is None or int(version[0]) != SCHEMA_VERSION:
            con.close()
            # Derived data: a schema mismatch is a rebuild, never a migration.
            raise CatalogCorruptError("The catalog is from a different schema version.")
        self._local.con = con
        self._generation = generation
        _collect_garbage(self._root, keep=generation)
        return con

    def close(self) -> None:
        """Close this thread's connection. Other threads close their own.

        A connection can only be closed by its owning thread, so there is no
        honest way to close them all from here; each is read-only and is
        released when its thread ends or reopens on a newer generation.
        """
        con = getattr(self._local, "con", None)
        if con is not None:
            try:
                con.close()
            finally:
                self._local.con = None
                self._generation = None

    def reopen_if_stale(self) -> None:
        """Pick up a newer generation after a refresh swapped the pointer."""
        if getattr(self._local, "con", None) is None:
            return
        if current_generation(self._root) != self._generation:
            self.close()

    def destroy(self) -> None:
        """Delete the whole catalog directory. Loses nothing the listener owns."""
        self.close()
        shutil.rmtree(self._root, ignore_errors=True)

    # -- meta and health ------------------------------------------------------

    def meta(self, key: str) -> str:
        row = (
            self._connect().execute("SELECT value FROM catalog_meta WHERE key=?", (key,)).fetchone()
        )
        return str(row[0]) if row else ""

    def age_seconds(self, now: float | None = None) -> float | None:
        """Seconds since the newest successful source refresh (or the seed)."""
        stamps = [
            value
            for (value,) in self._connect().execute(
                "SELECT last_refresh FROM sources WHERE last_status='ok'"
            )
            if value
        ]
        stamps.append(self.meta("imported_at"))
        best = max((float(v) for v in stamps if v), default=None)
        if best is None:
            return None
        return max(0.0, (now if now is not None else time.time()) - best)

    def source_health(self) -> list[SourceHealth]:
        rows = (
            self
            ._connect()
            .execute(
                "SELECT id, last_refresh, last_status, last_error, station_count "
                "FROM sources ORDER BY id"
            )
            .fetchall()
        )
        return [SourceHealth(*row) for row in rows]

    # -- reads: the browse axes ----------------------------------------------

    def countries(self) -> list[tuple[str, int]]:
        return [
            (str(name), int(count))
            for name, count in self._connect().execute(
                "SELECT country, COUNT(*) FROM stations "
                "WHERE country<>'' AND vanished_at IS NULL "
                "GROUP BY country ORDER BY country"
            )
        ]

    def states(self, country: str) -> list[str]:
        return [
            str(state)
            for (state,) in self._connect().execute(
                "SELECT DISTINCT state FROM stations "
                "WHERE country=? AND state<>'' AND vanished_at IS NULL ORDER BY state",
                (country,),
            )
        ]

    def languages(self) -> list[tuple[str, int]]:
        return [
            (str(name), int(count))
            for name, count in self._connect().execute(
                "SELECT language, COUNT(*) FROM stations "
                "WHERE language<>'' AND vanished_at IS NULL "
                "GROUP BY language ORDER BY COUNT(*) DESC LIMIT 400"
            )
        ]

    def codecs(self) -> list[tuple[str, int]]:
        return [
            (str(name), int(count))
            for name, count in self._connect().execute(
                "SELECT codec, COUNT(*) FROM stations "
                "WHERE codec<>'' AND vanished_at IS NULL "
                "GROUP BY codec ORDER BY COUNT(*) DESC"
            )
        ]

    def tags(self, limit: int = 400) -> list[tuple[str, int]]:
        """Distinct tags by frequency. Tags are comma-joined per row, so this
        is computed in Python over one indexed scan - measured acceptable."""
        counts: dict[str, int] = {}
        for (tags,) in self._connect().execute(
            "SELECT tags FROM stations WHERE tags<>'' AND vanished_at IS NULL"
        ):
            for tag in str(tags).split(","):
                if tag:
                    counts[tag] = counts.get(tag, 0) + 1
        ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
        return ranked[:limit]

    _ROW_COLUMNS = (
        "key, name, stream_url, homepage, favicon, country, state, language, "
        "tags, codec, bitrate, votes, source_id, source_record_id"
    )

    def _rows(self, where: str, args: tuple[object, ...], *, limit: int) -> list[StationRow]:
        sql = (
            f"SELECT {self._ROW_COLUMNS} FROM stations "
            f"WHERE vanished_at IS NULL AND {where} "
            f"ORDER BY votes DESC, name LIMIT {int(limit)}"
        )
        return [StationRow(*row) for row in self._connect().execute(sql, args)]

    def by_country(self, country: str, *, state: str = "", limit: int = 2000) -> list[StationRow]:
        if state:
            return self._rows("country=? AND state=?", (country, state), limit=limit)
        return self._rows("country=?", (country,), limit=limit)

    def by_language(self, language: str, *, limit: int = 2000) -> list[StationRow]:
        return self._rows("language=?", (language,), limit=limit)

    def by_codec(self, codec: str, *, limit: int = 2000) -> list[StationRow]:
        return self._rows("codec=?", (codec,), limit=limit)

    def by_tag(self, tag: str, *, limit: int = 2000) -> list[StationRow]:
        needle = tag.strip().lower()
        sql = (
            f"SELECT {self._ROW_COLUMNS} FROM stations "
            "WHERE vanished_at IS NULL AND rowid IN "
            "(SELECT rowid FROM stations_fts WHERE stations_fts MATCH ?) "
            f"ORDER BY votes DESC, name LIMIT {int(limit)}"
        )
        quoted = '"' + needle.replace('"', '""') + '"'
        rows = [StationRow(*row) for row in self._connect().execute(sql, (f"tags:{quoted}",))]
        # FTS tokenizes on word boundaries; keep only exact tag membership so
        # "jazz" does not return "acid jazz fusion"-only stations by accident.
        return [row for row in rows if needle in row.tags.split(",")] or rows

    def by_source(self, source_id: str, *, limit: int = 5000) -> list[StationRow]:
        return self._rows("source_id=?", (source_id,), limit=limit)

    def top_voted(self, *, limit: int = 100) -> list[StationRow]:
        return self._rows("1=1", (), limit=limit)

    def search(
        self,
        query: str,
        *,
        limit: int = 200,
        country: str = "",
        state: str = "",
        language: str = "",
        tag: str = "",
        codec: str = "",
    ) -> list[StationRow]:
        """FTS name search, optionally scoped to one browse axis value --
        the instant answer behind Find on a catalog-served branch."""
        text = " ".join(query.split())
        if not text:
            return []
        quoted = " ".join('"' + part.replace('"', '""') + '"*' for part in text.split())
        where = ["vanished_at IS NULL"]
        params: list[object] = []
        for column, value in (
            ("country", country),
            ("state", state),
            ("language", language),
            ("codec", codec),
        ):
            if value:
                where.append(f"{column} = ? COLLATE NOCASE")
                params.append(value)
        if tag:
            where.append("(',' || tags || ',') LIKE ? COLLATE NOCASE")
            params.append(f"%,{tag},%")
        params.append(quoted)  # the MATCH placeholder is last in the SQL
        sql = (
            f"SELECT {self._ROW_COLUMNS} FROM stations "
            f"WHERE {' AND '.join(where)} AND rowid IN "
            "(SELECT rowid FROM stations_fts WHERE stations_fts MATCH ?) "
            f"ORDER BY votes DESC, name LIMIT {int(limit)}"
        )
        try:
            return [StationRow(*row) for row in self._connect().execute(sql, params)]
        except sqlite3.OperationalError:
            return []  # an unparsable FTS query is "no matches", never a crash

    # -- reads: the library shelf ---------------------------------------------

    def audiobooks(
        self, source: str, *, genre: str = "", limit: int = 3000
    ) -> list[tuple[str, str, str, str]]:
        """(book_id, title, authors, language) rows for one library source."""
        if genre:
            sql = (
                "SELECT book_id, title, authors, language FROM audiobooks "
                "WHERE source=? AND (',' || genres || ',') LIKE ? ORDER BY title LIMIT ?"
            )
            args: tuple[object, ...] = (source, f"%,{genre},%", limit)
        else:
            sql = (
                "SELECT book_id, title, authors, language FROM audiobooks "
                "WHERE source=? ORDER BY title LIMIT ?"
            )
            args = (source, limit)
        return [
            (str(a), str(b), str(c), str(d)) for a, b, c, d in self._connect().execute(sql, args)
        ]

    def audiobook_sections(self, source: str, book_id: str) -> list[tuple[int, str, str]]:
        return [
            (int(i), str(t), str(u))
            for i, t, u in self._connect().execute(
                "SELECT idx, title, url FROM audiobook_sections "
                "WHERE source=? AND book_id=? ORDER BY idx",
                (source, book_id),
            )
        ]

    # -- writes: generation building (refresh and seed import) ----------------

    def begin_generation(self) -> GenerationWriter:  # noqa: F821 - writer module
        """Start building the next generation from a copy of the current one
        (or from an empty schema when none exists)."""
        self._root.mkdir(parents=True, exist_ok=True)
        current = current_generation(self._root)
        next_gen = (current or 0) + 1
        path = _generation_path(self._root, next_gen)
        path.unlink(missing_ok=True)
        if current is not None:
            shutil.copyfile(_generation_path(self._root, current), path)
        con = sqlite3.connect(path)
        con.executescript(_SCHEMA)
        con.execute(
            "INSERT OR REPLACE INTO catalog_meta(key, value) VALUES ('schema_version', ?)",
            (str(SCHEMA_VERSION),),
        )
        from quill.core.radio.catalog.writer import GenerationWriter

        return GenerationWriter(self, con, next_gen, path)

    def _commit_generation(self, generation: int) -> None:
        _set_pointer(self._root, generation)
        self.reopen_if_stale()
