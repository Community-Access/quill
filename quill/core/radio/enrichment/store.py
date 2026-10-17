"""The station enrichment store: SQLite, an FTS5 index, migrations, search.

Its own small database beside the station catalog rather than new columns in
it, for two reasons. The catalog is rebuilt from the seed on any schema change
(it treats a version mismatch as "rebuild, never migrate"), and enrichment
arrives on its own schedule from its own signed pack; keeping them apart means
neither can force the other to start over. Joining is by the catalog's own
canonical key (source uuid, else normalized stream URL), with the stream URL
plus name as the fallback.

Derived data, like the catalog: deleting the file loses nothing the listener
owns, and the next pack import rebuilds it.

**Migrations** run forward through ``PRAGMA user_version``; each entry in
:data:`MIGRATIONS` is applied once, in order, inside a transaction. A store
written by a *newer* build is refused (:class:`EnrichmentError`) rather than
guessed at, and the caller recreates it, which is safe because it is derived.

**Import is all or nothing.** A pack replaces the whole table set inside one
transaction, so a failure part way leaves the previous pack's facts in place
-- the property the catalog gets from its generation swap.

**Search** ranks with FTS5's bm25 over weighted columns -- name and identity
(call sign, frequency) highest, then slogan, format and tags, then place, then
description, owner and summary -- and says why each result matched, because
for a screen-reader user that is the difference between trusting a result and
opening five to check. Only when the index finds nothing does a fuzzy match on
names run, so a misspelling is forgiven without polluting good results.
"""

from __future__ import annotations

import difflib
import json
import sqlite3
import threading
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from quill.core.radio.catalog.keys import canonical_key, normalize_stream_url
from quill.core.radio.enrichment import EnrichmentError
from quill.core.radio.enrichment.facts import (
    StationFacts,
    call_sign_tokens,
    frequency_tokens,
    query_terms,
    with_derived_identity,
)
from quill.core.radio.enrichment.pack import SourceCredit, StationPack

DIR_NAME = "radio-enrichment"
FILE_NAME = "stations.db"

_V1 = """
CREATE TABLE pack_meta(
  key   TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
CREATE TABLE pack_sources(
  id          TEXT PRIMARY KEY,
  title       TEXT NOT NULL DEFAULT '',
  terms       TEXT NOT NULL DEFAULT '',
  attribution TEXT NOT NULL DEFAULT ''
);
CREATE TABLE station_facts(
  key         TEXT PRIMARY KEY,
  url_key     TEXT NOT NULL DEFAULT '',
  name        TEXT NOT NULL DEFAULT '',
  stream_url  TEXT NOT NULL DEFAULT '',
  call_sign   TEXT NOT NULL DEFAULT '',
  frequency   TEXT NOT NULL DEFAULT '',
  slogan      TEXT NOT NULL DEFAULT '',
  description TEXT NOT NULL DEFAULT '',
  genre       TEXT NOT NULL DEFAULT '',
  tags        TEXT NOT NULL DEFAULT '',
  city        TEXT NOT NULL DEFAULT '',
  state       TEXT NOT NULL DEFAULT '',
  country     TEXT NOT NULL DEFAULT '',
  language    TEXT NOT NULL DEFAULT '',
  owner       TEXT NOT NULL DEFAULT '',
  homepage    TEXT NOT NULL DEFAULT '',
  summary     TEXT NOT NULL DEFAULT '',
  attribution TEXT NOT NULL DEFAULT '',
  confirmed   TEXT NOT NULL DEFAULT '',
  provenance  TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX idx_sf_url ON station_facts(url_key);
CREATE VIRTUAL TABLE station_facts_fts USING fts5(
  name, ident, slogan, genre, tags, place, description, owner, summary,
  tokenize = 'unicode61 remove_diacritics 2'
);
"""

#: ``(user_version after, script)``, applied in order. Add at the end only.
MIGRATIONS: tuple[tuple[int, str], ...] = ((1, _V1),)
SCHEMA_VERSION = MIGRATIONS[-1][0]

#: bm25 weights, in the FTS column order above.
_WEIGHTS = (10.0, 10.0, 5.0, 4.0, 4.0, 3.0, 2.0, 2.0, 1.0)

_COLUMNS = (
    "key",
    "name",
    "stream_url",
    "call_sign",
    "frequency",
    "slogan",
    "description",
    "genre",
    "tags",
    "city",
    "state",
    "country",
    "language",
    "owner",
    "homepage",
    "summary",
    "attribution",
    "confirmed",
)

#: The fields a "matched:" explanation may name, in the order it checks them,
#: with the words a listener hears.
_EXPLAINED = (
    ("name", "name"),
    ("call_sign", "call sign"),
    ("frequency", "frequency"),
    ("slogan", "slogan"),
    ("genre", "format"),
    ("tags", "tags"),
    ("city", "city"),
    ("state", "state"),
    ("country", "country"),
    ("language", "language"),
    ("description", "description"),
    ("owner", "owner"),
    ("summary", "summary"),
)


@dataclass(frozen=True, slots=True)
class ImportResult:
    """What one pack import changed, for the one spoken outcome."""

    added: int
    changed: int
    removed: int
    total: int


@dataclass(frozen=True, slots=True)
class SearchHit:
    """One search result and why it matched."""

    key: str
    name: str
    #: ``(field words, value)`` pairs, best first; empty for a fuzzy match.
    matched: tuple[tuple[str, str], ...] = ()
    fuzzy: bool = False
    #: Said instead of a match reason, e.g. "playing now".
    note: str = ""

    @property
    def explanation(self) -> str:
        """ "matched slogan: Official home of the Seahawks", or the fuzzy note."""
        if self.note:
            return self.note
        if self.fuzzy:
            return "close spelling of the name"
        if not self.matched:
            return ""
        label, value = self.matched[0]
        if label == "name":
            return "matched name"
        return f"matched {label}: {_clip(value)}"

    @property
    def row_text(self) -> str:
        """The whole row, one sentence for a list."""
        reason = self.explanation
        return f"{self.name}, {reason}" if reason else self.name


def _clip(text: str, limit: int = 80) -> str:
    flat = " ".join(text.split())
    return flat if len(flat) <= limit else flat[: limit - 1].rstrip() + "…"


def store_path(data_dir: Path | str) -> Path:
    return Path(data_dir) / DIR_NAME / FILE_NAME


def migrate(con: sqlite3.Connection) -> int:
    """Bring *con* to :data:`SCHEMA_VERSION`. Returns the version it started at."""
    (start,) = con.execute("PRAGMA user_version").fetchone()
    if start > SCHEMA_VERSION:
        raise EnrichmentError("The station details were written by a newer version of Quill Radio.")
    for version, script in MIGRATIONS:
        if version <= start:
            continue
        try:
            con.execute("BEGIN")
            for statement in _statements(script):
                con.execute(statement)
            con.execute(f"PRAGMA user_version = {int(version)}")
            con.execute("COMMIT")
        except sqlite3.Error as error:
            con.execute("ROLLBACK")
            raise EnrichmentError(f"The station details could not be upgraded: {error}") from error
    return int(start)


def _statements(script: str) -> list[str]:
    """Split a migration script into statements (none of ours contain ';' in text)."""
    return [part.strip() for part in script.split(";") if part.strip()]


class EnrichmentStore:
    """One store file. Thread-safe by a lock; opened lazily on first use."""

    def __init__(self, path: Path | str) -> None:
        self._path = Path(path)
        self._con: sqlite3.Connection | None = None
        self._lock = threading.RLock()

    @classmethod
    def in_data_dir(cls, data_dir: Path | str) -> EnrichmentStore:
        return cls(store_path(data_dir))

    @property
    def path(self) -> Path:
        return self._path

    def _connect(self) -> sqlite3.Connection:
        if self._con is not None:
            return self._con
        self._path.parent.mkdir(parents=True, exist_ok=True)
        try:
            con = sqlite3.connect(self._path, check_same_thread=False, isolation_level=None)
        except sqlite3.Error as error:
            raise EnrichmentError(f"The station details could not be opened: {error}") from error
        try:
            migrate(con)
        except (sqlite3.Error, EnrichmentError) as error:
            con.close()  # or the file stays locked and cannot be recreated
            if isinstance(error, EnrichmentError):
                raise
            raise EnrichmentError(f"The station details could not be opened: {error}") from error
        self._con = con
        return con

    def close(self) -> None:
        with self._lock:
            if self._con is not None:
                self._con.close()
                self._con = None

    def destroy(self) -> None:
        """Delete the store. Loses nothing the listener owns."""
        self.close()
        self._path.unlink(missing_ok=True)

    # -- meta ---------------------------------------------------------------

    def meta(self, key: str) -> str:
        with self._lock:
            row = (
                self
                ._connect()
                .execute("SELECT value FROM pack_meta WHERE key=?", (key,))
                .fetchone()
            )
        return str(row[0]) if row else ""

    def built_at(self) -> str:
        """When the installed pack was built, or "" when none is installed."""
        return self.meta("built_at")

    def count(self) -> int:
        with self._lock:
            (total,) = self._connect().execute("SELECT COUNT(*) FROM station_facts").fetchone()
        return int(total)

    def sources(self) -> list[SourceCredit]:
        with self._lock:
            rows = (
                self
                ._connect()
                .execute("SELECT id, title, terms, attribution FROM pack_sources ORDER BY id")
                .fetchall()
            )
        return [SourceCredit(*map(str, row)) for row in rows]

    # -- import ---------------------------------------------------------------

    def import_pack(self, pack: StationPack) -> ImportResult:
        """Replace everything with *pack*'s facts, in one transaction."""
        # Identity read out of each name, here as in the merge, so a pack built
        # by an older tool still answers "94.9" and "KUOW".
        stations = [
            with_derived_identity(facts, facts.provenance.get("name", "pack"))
            for facts in pack.stations
        ]
        incoming = {facts.key: facts for facts in stations}
        with self._lock:
            con = self._connect()
            existing = {
                str(row[0]): _digest(_facts_from_row(row))
                for row in con.execute(
                    f"SELECT {', '.join(_COLUMNS)}, provenance FROM station_facts"
                )
            }
            added = sum(1 for key in incoming if key not in existing)
            removed = sum(1 for key in existing if key not in incoming)
            changed = sum(
                1
                for key, facts in incoming.items()
                if key in existing and existing[key] != _digest(facts)
            )
            try:
                con.execute("BEGIN")
                con.execute("DELETE FROM station_facts")
                con.execute("DELETE FROM station_facts_fts")
                con.execute("DELETE FROM pack_sources")
                for facts in stations:
                    _insert(con, facts)
                con.executemany(
                    "INSERT OR REPLACE INTO pack_sources(id, title, terms, attribution) "
                    "VALUES (?,?,?,?)",
                    [(c.id, c.title, c.terms, c.attribution) for c in pack.sources],
                )
                for key, value in (("built_at", pack.built_at), ("kind", pack.kind)):
                    con.execute(
                        "INSERT OR REPLACE INTO pack_meta(key, value) VALUES (?, ?)",
                        (key, value),
                    )
                con.execute("COMMIT")
            except sqlite3.Error as error:
                con.execute("ROLLBACK")
                raise EnrichmentError(f"The station pack could not be stored: {error}") from error
        return ImportResult(added=added, changed=changed, removed=removed, total=len(incoming))

    # -- reads ----------------------------------------------------------------

    def details(self, key: str) -> StationFacts | None:
        with self._lock:
            row = (
                self
                ._connect()
                .execute(
                    f"SELECT {', '.join(_COLUMNS)}, provenance FROM station_facts WHERE key=?",
                    (key,),
                )
                .fetchone()
            )
        return _facts_from_row(row) if row else None

    def find_for_station(
        self, station_uuid: str, stream_url: str, name: str = ""
    ) -> StationFacts | None:
        """The facts for a station Radio knows, by key, then by URL and name."""
        for key in (canonical_key(station_uuid, stream_url), normalize_stream_url(stream_url)):
            if key:
                found = self.details(key)
                if found is not None:
                    return found
        url_key = normalize_stream_url(stream_url)
        if not url_key:
            return None
        with self._lock:
            rows = (
                self
                ._connect()
                .execute(
                    f"SELECT {', '.join(_COLUMNS)}, provenance FROM station_facts WHERE url_key=?",
                    (url_key,),
                )
                .fetchall()
            )
        candidates = [_facts_from_row(row) for row in rows]
        folded = " ".join(name.split()).casefold()
        named = [c for c in candidates if " ".join(c.name.split()).casefold() == folded]
        if named:
            return named[0]
        # A shared URL alone never identifies a station (catalog keys.py).
        return candidates[0] if len(candidates) == 1 and not name else None

    def search(
        self, query: str, *, limit: int = 50, home_state: str = "", fuzzy: bool = True
    ) -> list[SearchHit]:
        """Ranked stations for *query*, each saying why it matched.

        ``fuzzy=False`` skips the close-spelling fallback, which reads every
        name: the search-as-you-type path turns it off and asks for it only
        when the listener presses Enter on an empty result.
        """
        terms = query_terms(query)
        if not terms:
            return []
        expression = " ".join('"' + term.replace('"', '""') + '"*' for term in terms)
        weights = ", ".join(str(w) for w in _WEIGHTS)
        sql = (
            "SELECT f.key, f.name, f.call_sign, f.frequency, f.slogan, f.genre, f.tags, "
            "f.city, f.state, f.country, f.language, f.description, f.owner, f.summary "
            "FROM station_facts_fts JOIN station_facts AS f ON f.rowid = station_facts_fts.rowid "
            "WHERE station_facts_fts MATCH ? "
            f"ORDER BY bm25(station_facts_fts, {weights}) "
            "- (CASE WHEN ? <> '' AND f.state = ? COLLATE NOCASE THEN 1.0 ELSE 0.0 END), f.name "
            f"LIMIT {int(limit)}"
        )
        with self._lock:
            con = self._connect()
            try:
                rows = con.execute(sql, (expression, home_state, home_state)).fetchall()
            except sqlite3.OperationalError:
                rows = []  # an unparsable query is "no matches", never a crash
            if rows:
                return [_hit(row, terms) for row in rows]
            if not fuzzy:
                return []
            names = [
                (str(k), str(n)) for k, n in con.execute("SELECT key, name FROM station_facts")
            ]
        return _fuzzy(query, names, limit=limit)


# -- helpers ------------------------------------------------------------------


def _insert(con: sqlite3.Connection, facts: StationFacts) -> None:
    values = [getattr(facts, column) for column in _COLUMNS]
    cursor = con.execute(
        f"INSERT INTO station_facts({', '.join(_COLUMNS)}, url_key, provenance) "
        f"VALUES ({', '.join('?' for _ in _COLUMNS)}, ?, ?)",
        (
            *values,
            normalize_stream_url(facts.stream_url),
            json.dumps(dict(facts.provenance), sort_keys=True),
        ),
    )
    ident = " ".join(
        part
        for part in (
            facts.call_sign,
            call_sign_tokens(facts.call_sign),
            frequency_tokens(facts.frequency),
        )
        if part
    )
    place = " ".join(p for p in (facts.city, facts.state, facts.country, facts.language) if p)
    con.execute(
        "INSERT INTO station_facts_fts(rowid, name, ident, slogan, genre, tags, place, "
        "description, owner, summary) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (
            cursor.lastrowid,
            facts.name,
            ident,
            facts.slogan,
            facts.genre,
            facts.tags.replace(",", " "),
            place,
            facts.description,
            facts.owner,
            facts.summary,
        ),
    )


def _digest(facts: StationFacts) -> str:
    return json.dumps(facts.to_dict(), sort_keys=True)


def _facts_from_row(row: Iterable[object]) -> StationFacts:
    values = list(row)
    try:
        provenance = json.loads(str(values[-1]))
    except ValueError:
        provenance = {}
    data: dict[str, object] = dict(zip(_COLUMNS, values[:-1], strict=True))
    data["provenance"] = provenance if isinstance(provenance, dict) else {}
    return StationFacts.from_dict(data)


def _word_hit(value: str, term: str) -> bool:
    lowered = value.lower()
    return any(
        word.startswith(term) for word in lowered.replace(",", " ").replace("-", " ").split()
    )


def _hit(row: tuple[object, ...], terms: list[str]) -> SearchHit:
    record = dict(
        zip(
            (
                "key",
                "name",
                "call_sign",
                "frequency",
                "slogan",
                "genre",
                "tags",
                "city",
                "state",
                "country",
                "language",
                "description",
                "owner",
                "summary",
            ),
            (str(v or "") for v in row),
            strict=True,
        )
    )
    matched: list[tuple[str, str]] = []
    for column, label in _EXPLAINED:
        value = record.get(column, "")
        if not value:
            continue
        if column == "frequency":
            tokens = frequency_tokens(value).split()
            hit = any(term in tokens for term in terms)
        elif column == "call_sign":
            tokens = call_sign_tokens(value).split()
            hit = any(token.startswith(term) for term in terms for token in tokens)
        else:
            hit = any(_word_hit(value, term) for term in terms)
        if hit:
            matched.append((label, value))
    return SearchHit(key=record["key"], name=record["name"], matched=tuple(matched))


def _fuzzy(query: str, names: list[tuple[str, str]], *, limit: int) -> list[SearchHit]:
    wanted = " ".join(query.split()).casefold()
    if len(wanted) < 3 or not names:
        return []
    folded: dict[str, tuple[str, str]] = {}
    for key, name in names:
        folded.setdefault(name.casefold(), (key, name))
    close = difflib.get_close_matches(wanted, list(folded), n=limit, cutoff=0.75)
    return [SearchHit(key=folded[c][0], name=folded[c][1], fuzzy=True) for c in close]


__all__ = [
    "DIR_NAME",
    "FILE_NAME",
    "MIGRATIONS",
    "SCHEMA_VERSION",
    "EnrichmentStore",
    "ImportResult",
    "SearchHit",
    "migrate",
    "store_path",
]
