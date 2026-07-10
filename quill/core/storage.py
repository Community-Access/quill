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
from typing import Any

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


def retry_on_transient_lock[T](
    action: Callable[[], T],
    *,
    max_attempts: int = _REPLACE_MAX_ATTEMPTS,
    delay: float = _REPLACE_RETRY_DELAY,
) -> T:
    """Run ``action``, retrying on a transient Windows file-lock error.

    Shared by :func:`_atomic_replace` (single-file saves) and
    ``core.data_location``'s directory-tree move, both of which can hit a
    destination momentarily held open by an antivirus scanner or backup
    agent.
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
    """
    retry_on_transient_lock(lambda: temp_path.replace(path))


def read_json(path: Path, default: Any) -> Any:
    """Read a JSON file, returning ``default`` when it is missing or unreadable.

    A present-but-corrupt file (malformed JSON, bad encoding, or an I/O error)
    returns ``default`` rather than raising, so one bad config file can never
    crash a load path or startup. The corruption is logged. Callers that hold
    *important* user config (settings, keymap) additionally quarantine the bad
    file before resetting -- see ``quill.core.migration_backup.backup_corrupt_file``.
    """
    if not path.exists():
        return default
    try:
        with path.open("r", encoding="utf-8") as file_handle:
            return json.load(file_handle)
    except (ValueError, OSError) as exc:
        logger.warning("read_json: %s is unreadable (%s); using default", path, exc)
        return default


def write_json_atomic(path: Path, data: Any, *, base: Path | None = None) -> None:
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


def write_text_atomic(
    path: Path,
    text: str,
    *,
    encoding: str = "utf-8",
    newline: str = "",
    base: Path | None = None,
) -> None:
    """Atomically write *text* to *path* (temp file + ``os.replace``).

    The text/binary-document counterpart to :func:`write_json_atomic`. A crash or
    interruption mid-write leaves the previous file intact rather than a
    truncated file at the final path — important both for the user's real
    document (``write_text_document``) and for the autosave snapshot that
    recovery scans as the newest ``.snap`` (``autosave_document``), where a
    partial write would otherwise become the recovery source.

    *newline* is passed straight to the open file (``""`` disables Python's
    universal-newline translation so the caller's already-normalized text is
    written byte-for-byte).
    """
    if base is not None:
        resolve_within(base, path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, raw_temp = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=f".{uuid.uuid4().hex}.tmp",
        dir=path.parent,
    )
    temp_path = Path(raw_temp)
    try:
        with os.fdopen(fd, "w", encoding=encoding, newline=newline) as file_handle:
            file_handle.write(text)
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
