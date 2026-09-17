"""A lock file, for the read-modify-write two processes can both be inside.

QUILL and QuillLite are separate processes that share files when the listener
asks them to -- one personal dictionary (``share_quill_dictionary``), one
abbreviation library (``share_quill_abbreviations``). Every one of those is
read-modify-write: load the list, add an entry, write the list back. Two apps
open at once, two words taught within a moment of each other, and one of them is
simply gone, because the second read happened before the first write and the
second write put back a list that never had the first word in it (bad.md S10).

A lock *file* rather than a lock object, because the two are separate processes
and an in-process lock is invisible across that boundary.
``O_CREAT | O_EXCL`` is the one thing every filesystem agrees is atomic.

**It never blocks forever.** After the timeout it proceeds anyway and says so in
the log. Losing one taught word to a race is a smaller failure than an editor
that will not let you teach one at all -- and without the fall-through, a stale
lock left by a process that crashed would be permanent, which is the worst
outcome of the three.
"""

from __future__ import annotations

import logging
import os
import time
from collections.abc import Iterator
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
def guarded_write(path: Path, *, timeout_s: float = DEFAULT_LOCK_TIMEOUT_S) -> Iterator[None]:
    """Hold a lock beside *path* for the duration of the block.

    Read and write must both happen *inside* the block, not either side of it:
    the point is that nothing else rewrites the file between the two.
    """
    lock_path = path.with_name(path.name + ".lock")
    handle: int | None = None
    deadline = time.monotonic() + timeout_s
    while True:
        try:
            lock_path.parent.mkdir(parents=True, exist_ok=True)
            handle = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            break
        except FileExistsError:
            if time.monotonic() >= deadline:
                logger.warning("Lock %s is stale; writing anyway", lock_path)
                break
            time.sleep(_POLL_S)
        except OSError:
            # An unwritable folder is the caller's problem to report, not one to
            # turn into a hang here.
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
