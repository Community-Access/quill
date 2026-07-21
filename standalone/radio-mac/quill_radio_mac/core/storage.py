"""Atomic JSON persistence for Quill Radio for Mac.

Ported from upstream ``quill.core.storage``, trimmed to what the radio
modules actually use: :func:`write_json_atomic` plus its supporting
pieces (:func:`retry_on_transient_lock`, :func:`resolve_within`, and the
:class:`PathEscapeError` guard). The favorites store, history store,
recording settings, recording schedule, and wake timer all persist
through :func:`write_json_atomic`; they do their own reads with plain
``json.loads`` (a corrupt file resets to defaults in each store, exactly
as upstream).

Write strategy: dump to a UUID-named temp file in the destination
directory, ``fsync``, then ``os.replace`` over the target. A crash or
interruption mid-write leaves the previous file intact rather than a
truncated JSON file -- important because these files hold the user's
favorites and preferences.

Threading contract: functions here are safe to call from any thread
(the task manager's workers, the recorder thread, the scheduler thread).
Concurrent writers to the *same* path last-writer-wins at the
``os.replace`` boundary, which is atomic on both POSIX and NTFS; the
UUID temp names mean concurrent writers can never collide on the temp
file itself.

macOS notes: ``os.replace`` is atomic on APFS. The transient-lock retry
loop exists for Windows (antivirus or backup agents briefly holding the
destination open); on macOS the first attempt simply succeeds and the
loop is a no-op, so the shared code path stays identical on both
platforms.
"""

from __future__ import annotations

import errno
import json
import logging
import os
import tempfile
import time
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

# On Windows os.replace can transiently fail with PermissionError when another
# process (an antivirus scanner, a backup agent, or a screen reader's file hook)
# briefly holds the destination open. Retry a few times with a short backoff
# before giving up so a normal save is not lost to a momentary lock.
_REPLACE_MAX_ATTEMPTS = 5
_REPLACE_RETRY_DELAY = 0.05

_TRANSIENT_LOCK_ERRNOS = frozenset({
    errno.EACCES,
    errno.EAGAIN,
    errno.EBUSY,
    getattr(errno, "EWOULDBLOCK", errno.EAGAIN),
})

# Upstream declares this with PEP 695 syntax (``def f[T](...)``), which
# needs Python 3.12; this port's floor is 3.11, so a classic TypeVar is
# used instead. Behavior is identical.
T = TypeVar("T")


def retry_on_transient_lock(
    action: Callable[[], T],
    *,
    max_attempts: int = _REPLACE_MAX_ATTEMPTS,
    delay: float = _REPLACE_RETRY_DELAY,
) -> T:
    """Run ``action``, retrying on a transient Windows file-lock error.

    Retries ``PermissionError`` and ``OSError`` with the transient
    sharing-violation / lock-violation errnos; anything else propagates
    immediately. After ``max_attempts`` the last error is re-raised so
    the caller still sees the real failure.
    """
    last_error: OSError | None = None
    for attempt in range(max_attempts):
        try:
            return action()
        except OSError as error:
            if not isinstance(error, PermissionError) and error.errno not in _TRANSIENT_LOCK_ERRNOS:
                raise
            last_error = error
            if attempt + 1 < max_attempts:
                time.sleep(delay)
    assert last_error is not None
    raise last_error


class PathEscapeError(ValueError):
    """Raised when a write target resolves outside its permitted base directory."""


def resolve_within(base: Path, candidate: Path) -> Path:
    """Resolve ``candidate`` and confirm it stays inside ``base``.

    Returns the resolved candidate path. Raises :class:`PathEscapeError` when the
    candidate would escape ``base`` (for example through a ``..`` segment or an
    absolute path), so persistence writers can never be tricked into writing
    outside the application data area.
    """

    base_resolved = base.resolve()
    candidate_resolved = candidate.resolve()
    if candidate_resolved != base_resolved and base_resolved not in candidate_resolved.parents:
        raise PathEscapeError(f"Refusing to write outside {base_resolved}: {candidate_resolved}")
    return candidate_resolved


def _atomic_replace(temp_path: Path, path: Path) -> None:
    """Replace ``path`` with ``temp_path``, retrying transient Windows locks.

    On Windows the destination can be briefly held open by an antivirus
    scanner, a backup agent, or a screen reader's file hook. We retry on
    ``PermissionError`` and on ``OSError`` with the transient sharing-
    violation / lock-violation errnos (ERROR_SHARING_VIOLATION,
    ERROR_LOCK_VIOLATION) so a normal save is not lost to a momentary lock.
    On macOS/APFS the first attempt succeeds and no retry ever happens.
    """
    retry_on_transient_lock(lambda: temp_path.replace(path))


def write_json_atomic(path: Path, data: Any, *, base: Path | None = None) -> None:
    """Atomically write ``data`` as pretty-printed JSON to ``path``.

    The parent directory is created if missing. The JSON is written with
    ``indent=2, sort_keys=True, ensure_ascii=False`` and a trailing
    newline -- byte-identical formatting to the Windows app, so files
    diff cleanly across platforms. When ``base`` is given the target is
    first validated with :func:`resolve_within` so a crafted relative
    path can never write outside the app data area.

    Uses a UUID-named temp file in the same directory so concurrent
    writers cannot collide on a fixed name like ``path.suffix + ".tmp"``;
    the temp file is always removed on failure, so no ``*.tmp`` litter is
    ever left beside the target.
    """
    if base is not None:
        resolve_within(base, path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Use a UUID-named temp file in the same directory so concurrent writers
    # cannot collide on a fixed name like path.suffix + ".tmp".
    fd, raw_temp = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=f".{uuid.uuid4().hex}.tmp",
        dir=path.parent,
    )
    temp_path = Path(raw_temp)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as file_handle:
            json.dump(data, file_handle, indent=2, sort_keys=True, ensure_ascii=False)
            file_handle.write("\n")
            file_handle.flush()
            os.fsync(file_handle.fileno())
    except BaseException:
        temp_path.unlink(missing_ok=True)
        raise
    try:
        _atomic_replace(temp_path, path)
    except BaseException:
        temp_path.unlink(missing_ok=True)
        raise
