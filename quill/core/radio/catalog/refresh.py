"""Keeping the catalog current: which sources, when, and how carefully.

Orchestration only - fetchers are injected, so every rule here is testable
with no network. The rules, each of which exists because something measured
or shipped demanded it:

- **Staggered, one source per run.** A refresh pass updates the single most
  overdue source, so background freshness is a trickle, never a burst.
  A manual refresh does every due source in one pass, because the listener
  asked and is waiting for an answer.
- **An empty answer from a previously populated source is an outage, not
  truth.** Learned from the live Xiph directory serving a bare shell while
  claiming HTTP 200. The catalog keeps what it has; the source is marked
  stale.
- **A content hash short-circuits.** A full fetch whose payload hashes the
  same as last time writes nothing and counts as "no changes".
- **Tombstones, not deletes.** A station missing from one fetch is marked
  vanished and hidden; it is purged only after a fourteen-day grace window,
  so a source hiccup that drops half its records for an afternoon cannot
  thrash the catalog.
- **Hidden sources are never contacted.** The Choose Browse Sources rule
  extends to refresh: off means off.
- **Failure is per-source.** One source down is one stale source, never a
  failed refresh.
"""

from __future__ import annotations

import hashlib
import logging
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass

from quill.core.radio.catalog.store import CatalogStore, StationRow
from quill.core.radio.catalog.summary import RefreshSummary, SourceOutcome

logger = logging.getLogger(__name__)

#: Default cadence, per source (Jeff, 2026-08-15: "every 24 hours is fine").
DEFAULT_INTERVAL_HOURS = 24

#: A startup refresh is skipped when the catalog is younger than this, so a
#: restart loop never hammers anyone's directory.
STARTUP_FLOOR_HOURS = 6

#: The outage guard: an "empty" answer only counts as an outage when the
#: source previously had at least this many stations. A genuinely tiny source
#: shrinking to zero should be believed.
EMPTY_GUARD_FLOOR = 25


@dataclass(frozen=True, slots=True)
class SourceSpec:
    """One refreshable Class-A source.

    ``fetch_pages`` yields lists of :class:`StationRow` - pages, not the whole
    dump, so refresh memory stays bounded (whole-dump loading measured 217 MB;
    pages cap it in the tens).
    """

    id: str
    label: str
    fetch_pages: Callable[[], Iterable[list[StationRow]]]


def due_sources(
    specs: list[SourceSpec],
    store: CatalogStore,
    *,
    now: float,
    interval_hours: int = DEFAULT_INTERVAL_HOURS,
    enabled_ids: set[str] | None = None,
) -> list[SourceSpec]:
    """The sources old enough to refresh, most overdue first.

    ``enabled_ids`` is the Choose Browse Sources selection; a hidden source is
    not merely skipped, it is never returned, so nothing downstream can
    contact it by accident.
    """
    last: dict[str, float] = {}
    if store.exists():
        for health in store.source_health():
            try:
                last[health.id] = float(health.last_refresh or 0.0)
            except ValueError:
                last[health.id] = 0.0
    horizon = max(1, interval_hours) * 3600
    candidates = [
        spec
        for spec in specs
        if (enabled_ids is None or spec.id in enabled_ids)
        and now - last.get(spec.id, 0.0) >= horizon
    ]
    candidates.sort(key=lambda spec: last.get(spec.id, 0.0))
    return candidates


def refresh(
    specs: list[SourceSpec],
    store: CatalogStore,
    *,
    now: float | None = None,
) -> RefreshSummary:
    """Refresh *specs* into a new generation and swap it in.

    Builds one generation for the whole pass: either every source's outcome
    lands together or (on a crash) none of it does and the old catalog stands.
    """
    moment = now if now is not None else time.time()
    summary = RefreshSummary()
    if not specs:
        return summary
    writer = store.begin_generation()
    changed = False
    try:
        for spec in specs:
            outcome = SourceOutcome(source_id=spec.id, label=spec.label, status="ok")
            summary.outcomes.append(outcome)
            before = _station_count(writer, spec.id)
            seen: set[str] = set()
            hasher = hashlib.sha256()
            added = updated = 0
            try:
                for page in spec.fetch_pages():
                    for row in page:
                        hasher.update(row.key.encode())
                        hasher.update(row.name.encode())
                        hasher.update(row.stream_url.encode())
                    fresh = [row for row in page if row.key not in seen]
                    seen.update(row.key for row in fresh)
                    existing = _existing_keys(writer, [row.key for row in fresh])
                    writer.upsert_stations(spec.id, fresh, now=moment)
                    added += sum(1 for row in fresh if row.key not in existing)
                    updated += sum(1 for row in fresh if row.key in existing)
            except Exception as error:  # noqa: BLE001 - one source down != a failed refresh
                logger.warning("Catalog source %s failed: %s", spec.id, error)
                outcome.status = "stale"
                outcome.error = _plain_reason(error)
                writer.record_source(spec.id, status="stale", error=outcome.error, now=moment)
                continue
            digest = hasher.hexdigest()
            if not seen and before >= EMPTY_GUARD_FLOOR:
                # The Xiph rule: empty from a source that had thousands is an
                # outage wearing a 200 status code.
                outcome.status = "stale"
                outcome.error = "returned no stations; treating that as an outage"
                writer.record_source(spec.id, status="stale", error=outcome.error, now=moment)
                continue
            if digest == writer.source_hash(spec.id):
                outcome.status = "unchanged"
                writer.record_source(spec.id, status="ok", content_hash=digest, now=moment)
                continue
            outcome.added = added
            outcome.updated = updated
            outcome.vanished = writer.tombstone_missing(spec.id, seen, now=moment)
            writer.record_source(spec.id, status="ok", content_hash=digest, now=moment)
            changed = True
        writer.purge_tombstones(now=moment)
        if changed or any(o.status != "skipped" for o in summary.outcomes):
            writer.commit()
        else:
            writer.abandon()
    except Exception:
        writer.abandon()
        raise
    return summary


def write_through(store: CatalogStore, source_id: str, rows: list[StationRow]) -> None:
    """Upsert a slice a live Class-A fetch already returned. Best effort.

    Class A only, by contract - Class B rows must never enter the store
    (iHeart's and TuneIn's terms bar persisting their listings, and keeping
    the rule absolute is what makes it auditable). Failures are swallowed:
    freshness-for-free must never cost the browse that triggered it.
    """
    if not rows:
        return
    try:
        writer = store.begin_generation()
        try:
            writer.upsert_stations(source_id, rows, now=time.time())
            writer.commit()
        except Exception:
            writer.abandon()
            raise
    except Exception:  # noqa: BLE001
        logger.debug("Catalog write-through skipped.", exc_info=True)


def _station_count(writer: object, source_id: str) -> int:
    con = writer.connection  # type: ignore[attr-defined]
    row = con.execute(
        "SELECT COUNT(*) FROM stations WHERE source_id=? AND vanished_at IS NULL",
        (source_id,),
    ).fetchone()
    return int(row[0])


def _existing_keys(writer: object, keys: list[str]) -> set[str]:
    if not keys:
        return set()
    con = writer.connection  # type: ignore[attr-defined]
    found: set[str] = set()
    for start in range(0, len(keys), 500):
        chunk = keys[start : start + 500]
        marks = ",".join("?" * len(chunk))
        for (key,) in con.execute(f"SELECT key FROM stations WHERE key IN ({marks})", chunk):
            found.add(str(key))
    return found


def _plain_reason(error: Exception) -> str:
    text = str(error).strip() or type(error).__name__
    return text[:160]
