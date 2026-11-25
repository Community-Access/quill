"""A lock file, for the read-modify-write two processes can both be inside.

QUILL and QUILL Lite are separate processes that share files when the listener
asks them to -- one personal dictionary (``share_quill_dictionary``), one
abbreviation library (``share_quill_abbreviations``). Every one of those is
read-modify-write: load the list, add an entry, write the list back. Two apps
open at once, two words taught within a moment of each other, and one of them is
simply gone, because the second read happened before the first write and the
second write put back a list that never had the first word in it (bad.md S10).

A lock *file* rather than a lock object, because the two are separate processes
and an in-process lock is invisible across that boundary.
``O_CREAT | O_EXCL`` is the one thing every filesystem agrees is atomic.

**It never blocks forever.** The original shared-dictionary callers proceed
after the timeout and say so in the log: losing one taught word to a race is a
smaller failure than an editor that will not let you teach one at all. Durable
queues opt into ``require_lock=True`` instead, so they report contention rather
than commit an unlocked read-modify-write. Both paths can discard a lock old
enough to be from a crashed process.
"""

from __future__ import annotations

import logging
import os
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path

__all__ = ["DEFAULT_LOCK_TIMEOUT_S", "guarded_write"]

logger = logging.getLogger(__name__)

#: How long to wait for another process to finish before going ahead anyway.
#: Two seconds is far longer than any of these writes takes and short enough
#: that a stale lock is not a hang somebody has to diagnose.
DEFAULT_LOCK_TIMEOUT_S = 2.0

#: How often to look again while waiting. Short enough that the common case --
#: the other process finishing immediately -- costs nothing measurable.
_POLL_S = 0.02


@contextmanager
def guarded_write(
    path: Path,
    *,
    timeout_s: float = DEFAULT_LOCK_TIMEOUT_S,
    lock_path: Path | None = None,
    stale_after_s: float | None = None,
    clock: Callable[[], float] = time.time,
    require_lock: bool = False,
) -> Iterator[None]:
    """Hold a lock beside *path* for the duration of the block.

    Read and write must both happen *inside* the block, not either side of it:
    the point is that nothing else rewrites the file between the two.

    Most callers retain the original best-effort behaviour after
    *timeout_s*. A durable queue can set ``require_lock=True`` so it reports
    contention instead of writing without the cross-process lock. Durable
    callers may also name their historical lock file and discard it only after
    ``stale_after_s``; the lock file is otherwise never removed by a waiter.
    """
    lock_path = lock_path or path.with_name(path.name + ".lock")
    handle: int | None = None
    deadline = time.monotonic() + timeout_s
    while True:
        try:
            lock_path.parent.mkdir(parents=True, exist_ok=True)
            handle = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            break
        except FileExistsError:
            if stale_after_s is not None:
                try:
                    if clock() - lock_path.stat().st_mtime > stale_after_s:
                        lock_path.unlink(missing_ok=True)
                        continue
                except OSError:
                    pass
            if time.monotonic() >= deadline:
                if require_lock:
                    raise TimeoutError(f"timed out waiting for the lock at {lock_path}") from None
                logger.warning("Lock %s is stale; writing anyway", lock_path)
                break
            time.sleep(_POLL_S)
        except OSError:
            # An unwritable folder is the caller's problem to report, not one to
            # turn into a hang here.
            if require_lock:
                raise
            break
    try:
        yield
    finally:
        if handle is not None:
            try:
                os.close(handle)
                lock_path.unlink(missing_ok=True)
            except OSError:
                pass
