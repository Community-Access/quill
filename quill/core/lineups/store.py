"""The shared ``lineups.json``: one file, two apps, no lost edits.

Radio and Cast read and write the same file in the family's data folder. Writing
a copy held in memory would let the last save win -- the hazard the survey found
in Radio's old writes to Cast's library -- so every change goes through
:meth:`LineupStore.update`:

1. take a lock file beside ``lineups.json`` (created exclusively; held for the
   few milliseconds of a read-apply-write; considered abandoned after
   :data:`STALE_LOCK_SECONDS`, so a crash mid-write cannot wedge either app);
2. re-read the file;
3. apply the operation (:mod:`quill.core.lineups.ops`) to what was just read;
4. write atomically (``write_json_atomic``) and release the lock.

The other app notices through :meth:`LineupStore.stamp` (the file's size and
modification time) and reloads. Reading never takes the lock: an atomic write
replaces the whole file at once, so a reader sees the old file or the new one.
"""

from __future__ import annotations

import logging
import os
import time
from collections.abc import Callable
from pathlib import Path

from quill.core.error_codes import CodedError
from quill.core.lineups.model import Lineup, LineupBook
from quill.core.lineups.ops import Operation, Outcome

logger = logging.getLogger(__name__)

FILE_NAME = "lineups.json"
STORE_NAME = "lineups"
SCHEMA_VERSION = 1

#: A lock older than this was left by a process that died mid-write.
STALE_LOCK_SECONDS = 10.0
#: How long :meth:`LineupStore.update` waits for the other app's write.
LOCK_WAIT_SECONDS = 3.0


class LineupStoreError(CodedError):
    """The Lineups file could not be written (locked too long, or the disk said no)."""

    code = "QUILL-RADIO-LINEUP-STORE"


def parse(raw: dict[str, object]) -> LineupBook:
    """The book from any shape this store has written (pure)."""
    lineups: list[Lineup] = []
    seen: set[str] = set()
    entries = raw.get("lineups")
    for entry in entries if isinstance(entries, list) else []:
        lineup = Lineup.from_dict(entry)
        if lineup is not None and lineup.id not in seen:
            seen.add(lineup.id)
            lineups.append(lineup)
    try:
        revision = max(0, int(str(raw.get("revision", 0))))
    except (TypeError, ValueError):
        revision = 0
    imported_raw = raw.get("imported")
    imported = tuple(str(x) for x in imported_raw) if isinstance(imported_raw, list) else ()
    return LineupBook(tuple(lineups), revision, imported)


def serialize(book: LineupBook) -> dict[str, object]:
    data: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "revision": book.revision,
        "lineups": [lineup.to_dict() for lineup in book.lineups],
    }
    if book.imported:
        data["imported"] = list(book.imported)
    return data


def is_legacy(raw: dict[str, object]) -> bool:
    version = raw.get("schema_version")
    return not isinstance(version, int) or version < SCHEMA_VERSION


def is_future(raw: dict[str, object]) -> bool:
    version = raw.get("schema_version")
    return isinstance(version, int) and version > SCHEMA_VERSION


class LineupStore:
    """The Lineups file for one data folder."""

    def __init__(
        self, data_dir: Path | None = None, *, clock: Callable[[], float] = time.time
    ) -> None:
        if data_dir is None:
            from quill.core.paths import app_data_dir

            data_dir = app_data_dir()
        self.path = Path(data_dir) / FILE_NAME
        self.lock_path = self.path.with_name(FILE_NAME + ".lock")
        self._clock = clock
        self._future = False

    # -- reading ------------------------------------------------------------------

    def load(self) -> LineupBook:
        """The book on disk; a missing or corrupt file reads as empty (and is kept)."""
        from quill.core.storage import read_json
        from quill.core.versioned_store import load_with_migration

        try:
            raw = read_json(self.path, default=None) if self.path.exists() else None
        except (ValueError, OSError):
            raw = None
        self._future = isinstance(raw, dict) and is_future(raw)
        return load_with_migration(
            self.path,
            store_name=STORE_NAME,
            parse=parse,
            serialize=serialize,
            is_legacy=is_legacy,
            default=LineupBook,
            is_future=is_future,
        )

    def stamp(self) -> tuple[int, int]:
        """``(size, mtime_ns)`` of the file, ``(0, 0)`` when absent: "did it change?"."""
        try:
            info = self.path.stat()
        except OSError:
            return (0, 0)
        return (info.st_size, info.st_mtime_ns)

    @property
    def read_only(self) -> bool:
        """A file a newer build wrote is never rewritten by this one."""
        return self._future

    # -- writing ------------------------------------------------------------------

    def update(self, operation: Operation) -> tuple[LineupBook, Outcome]:
        """Apply *operation* to the file as it is now, under the lock.

        Raises :class:`LineupStoreError` when the lock cannot be had in time or
        the write fails; the file on disk is then unchanged.
        """
        from quill.core.storage import write_json_atomic

        self._acquire()
        try:
            book = self.load()
            if self._future:
                raise LineupStoreError(
                    "These lineups were saved by a newer version, so this one will not change them."
                )
            changed, outcome = operation(book)
            if changed is not book:
                try:
                    write_json_atomic(self.path, serialize(changed))
                except OSError as exc:
                    raise LineupStoreError(f"The lineups could not be saved: {exc}") from exc
            return changed, outcome
        finally:
            self._release()

    def _acquire(self) -> None:
        deadline = self._clock() + LOCK_WAIT_SECONDS
        self.path.parent.mkdir(parents=True, exist_ok=True)
        while True:
            try:
                handle = os.open(self.lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            except FileExistsError:
                if self._lock_is_stale():
                    try:
                        self.lock_path.unlink()
                    except OSError:
                        pass
                    continue
                if self._clock() >= deadline:
                    raise LineupStoreError(
                        "The lineups are being saved by the other app; try again in a moment."
                    ) from None
                time.sleep(0.02)
                continue
            try:
                os.write(handle, str(os.getpid()).encode("ascii"))
            finally:
                os.close(handle)
            return

    def _lock_is_stale(self) -> bool:
        try:
            age = time.time() - self.lock_path.stat().st_mtime
        except OSError:
            return False
        return age > STALE_LOCK_SECONDS

    def _release(self) -> None:
        try:
            self.lock_path.unlink()
        except OSError as exc:
            logger.debug("Could not remove the lineups lock: %s", exc)


__all__ = [
    "FILE_NAME",
    "LOCK_WAIT_SECONDS",
    "SCHEMA_VERSION",
    "STALE_LOCK_SECONDS",
    "LineupStore",
    "LineupStoreError",
    "parse",
    "serialize",
]
