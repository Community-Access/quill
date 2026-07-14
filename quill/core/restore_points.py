"""Content-addressed restore points for saved documents.

The first shipped slice of the QUILL Sync plan (docs/planning/quill-sync-plan.md,
section 7): every successful save records a snapshot of the document's canonical
text, and ``File > Restore Previous Version`` lists and restores them. Restore
points work entirely offline and involve no sync engine; they are the
cross-session safety layer above ``core.backups`` (one pre-save ``.bak``) and
persistent undo (in-session).

Storage layout, under the QUILL data dir::

    restore_points/<doc-key>/index.json          # entry list, atomic writes
    restore_points/<doc-key>/blobs/<sha256>.txt  # content, one file per version

Blobs are content-addressed per document, so saving unchanged text costs
nothing (the entry is skipped) and pruning one document's history never has to
reference-count against another's. Everything here is wx-free and best-effort
by contract at the call site: recording a restore point must never be the
reason a save fails, so the UI wraps :func:`record_restore_point` in a guard.
"""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from quill.core.paths import app_data_dir
from quill.core.storage import read_json, write_json_atomic

__all__ = [
    "MAX_TEXT_BYTES",
    "RestorePoint",
    "list_restore_points",
    "prune_restore_points",
    "read_restore_point",
    "record_restore_point",
]

#: Documents larger than this are not snapshotted (the retention cap would be
#: consumed by a handful of saves). 20 MB of UTF-8 text is far beyond any
#: ordinary manuscript.
MAX_TEXT_BYTES = 20 * 1024 * 1024

#: The newest versions of a document are always kept, whatever their age.
_KEEP_MIN = 5

_SCHEMA_VERSION = 1


@dataclass(frozen=True, slots=True)
class RestorePoint:
    """One recorded version of one document."""

    content_hash: str
    saved_at: str  # ISO-8601 UTC, e.g. "2026-07-04T21:14:09+00:00"
    word_count: int
    size_bytes: int
    source: str  # "save" | "restore" | "import"

    @property
    def saved_at_local(self) -> datetime:
        return datetime.fromisoformat(self.saved_at).astimezone()


def _store_root() -> Path:
    return app_data_dir() / "restore_points"


def _document_key(path: Path) -> str:
    seed = str(path.resolve())
    return hashlib.sha1(seed.encode("utf-8")).hexdigest()


def _doc_dir(path: Path) -> Path:
    return _store_root() / _document_key(path)


def _load_index(doc_dir: Path) -> dict[str, object]:
    data = read_json(doc_dir / "index.json", {})
    if not isinstance(data, dict) or not isinstance(data.get("entries"), list):
        return {"schema_version": _SCHEMA_VERSION, "path": "", "entries": []}
    return data


def _entries(index: dict[str, object]) -> list[dict[str, object]]:
    entries = index.get("entries")
    return entries if isinstance(entries, list) else []


def record_restore_point(path: Path, text: str, *, source: str = "save") -> RestorePoint | None:
    """Snapshot ``text`` as the newest restore point for ``path``.

    Returns the new :class:`RestorePoint`, or ``None`` when nothing was
    recorded (unchanged content, or text over :data:`MAX_TEXT_BYTES`).
    """
    payload = text.encode("utf-8")
    if len(payload) > MAX_TEXT_BYTES:
        return None
    content_hash = hashlib.sha256(payload).hexdigest()
    doc_dir = _doc_dir(path)
    index = _load_index(doc_dir)
    entries = _entries(index)
    if entries and entries[-1].get("content_hash") == content_hash:
        return None  # unchanged since the last snapshot

    blob = doc_dir / "blobs" / f"{content_hash}.txt"
    blob.parent.mkdir(parents=True, exist_ok=True)
    if not blob.exists():
        temp = blob.with_suffix(".tmp")
        temp.write_bytes(payload)
        temp.replace(blob)

    point = RestorePoint(
        content_hash=content_hash,
        saved_at=datetime.now(UTC).isoformat(),
        word_count=len(text.split()),
        size_bytes=len(payload),
        source=source,
    )
    entries.append(asdict(point))
    index["schema_version"] = _SCHEMA_VERSION
    index["path"] = str(path)
    index["entries"] = entries
    write_json_atomic(doc_dir / "index.json", index)
    return point


def list_restore_points(path: Path) -> list[RestorePoint]:
    """All restore points for ``path``, newest first. Corrupt entries skipped."""
    doc_dir = _doc_dir(path)
    points: list[RestorePoint] = []
    for raw in _entries(_load_index(doc_dir)):
        try:
            points.append(
                RestorePoint(
                    content_hash=str(raw["content_hash"]),
                    saved_at=str(raw["saved_at"]),
                    word_count=int(str(raw.get("word_count", 0))),
                    size_bytes=int(str(raw.get("size_bytes", 0))),
                    source=str(raw.get("source", "save")),
                )
            )
        except (KeyError, TypeError, ValueError):
            continue
    return list(reversed(points))


def read_restore_point(path: Path, content_hash: str) -> str | None:
    """The stored text for one restore point, or ``None`` if its blob is gone."""
    if not content_hash or any(ch in content_hash for ch in "/\\."):
        return None  # defensive: hashes are hex, never path fragments
    blob = _doc_dir(path) / "blobs" / f"{content_hash}.txt"
    try:
        return blob.read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def _thin(points: list[RestorePoint], now: datetime) -> set[str]:
    """Content hashes to KEEP under the age policy (newest-first input).

    Keep the newest :data:`_KEEP_MIN` unconditionally; everything from the
    last 7 days; one per day for 30 days; one per week beyond that.
    """
    keep: set[str] = set()
    seen_days: set[str] = set()
    seen_weeks: set[str] = set()
    for position, point in enumerate(points):
        try:
            saved = datetime.fromisoformat(point.saved_at)
        except ValueError:
            continue  # unparseable entries are pruned
        age = now - saved
        if position < _KEEP_MIN or age <= timedelta(days=7):
            keep.add(point.content_hash)
            continue
        day = saved.strftime("%Y-%m-%d")
        week = saved.strftime("%G-W%V")
        if age <= timedelta(days=30):
            if day not in seen_days:
                seen_days.add(day)
                keep.add(point.content_hash)
            continue
        if week not in seen_weeks:
            seen_weeks.add(week)
            keep.add(point.content_hash)
    return keep


def prune_restore_points(path: Path, *, max_total_mb: int = 200) -> int:
    """Apply the retention policy to ``path``'s history; return versions removed.

    Age thinning first (see :func:`_thin`), then a size cap: while the
    document's blob store exceeds ``max_total_mb``, the oldest survivors are
    removed — but the newest :data:`_KEEP_MIN` are never touched, so a size cap
    can bound disk usage yet never erase recent history.
    """
    doc_dir = _doc_dir(path)
    points = list_restore_points(path)
    if not points:
        return 0
    keep = _thin(points, datetime.now(UTC))
    survivors = [p for p in points if p.content_hash in keep]

    total = sum(p.size_bytes for p in survivors)
    limit = max_total_mb * 1024 * 1024
    while total > limit and len(survivors) > _KEEP_MIN:
        oldest = survivors.pop()  # newest-first list: pop() is the oldest
        total -= oldest.size_bytes

    kept_hashes = {p.content_hash for p in survivors}
    removed = len(points) - len(survivors)
    if removed == 0:
        return 0

    index = _load_index(doc_dir)
    index["entries"] = [
        raw for raw in _entries(index) if str(raw.get("content_hash", "")) in kept_hashes
    ]
    write_json_atomic(doc_dir / "index.json", index)
    blob_dir = doc_dir / "blobs"
    if blob_dir.is_dir():
        for blob in blob_dir.glob("*.txt"):
            if blob.stem not in kept_hashes:
                try:
                    blob.unlink()
                except OSError:
                    pass  # a locked blob is disk waste, not a failure
    return removed
