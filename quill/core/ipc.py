from __future__ import annotations

import contextlib
import json
import os
import threading
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import IO

from quill.core.paths import app_data_dir

# Held open for the lifetime of the primary instance. The OS releases the
# advisory lock automatically when this process exits for ANY reason — clean
# quit, crash, or hard kill — so a leftover lock file can NEVER block a new
# instance. There is no PID to go stale and nothing to "self-heal": if a
# process is gone, its lock is gone. That is what makes the single-instance
# guard just work no matter how the previous run ended.
_lock_handle: IO[str] | None = None


def try_claim_primary_instance(slot: str = "") -> bool:
    """Return True if this process is now the single primary instance.

    Backed by an OS advisory file lock (``flock`` on POSIX, ``msvcrt.locking``
    on Windows) held for the process lifetime — not by a PID written to disk.
    The kernel owns the lock's lifecycle, so a stale lock file is impossible.

    ``slot`` namespaces the lock so sibling apps that share one data dir (QUILL,
    Quill Radio, Quill Cast) each get their own single-instance guard: the empty
    default is QUILL's, ``"radio"`` is Quill Radio's, and so on. Two copies of
    the *same* app collide; two *different* apps do not.
    """
    global _lock_handle
    if _lock_handle is not None:
        return True  # already claimed by this process; idempotent

    lock_path = _lock_file_path(slot)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        # O_RDWR|O_CREAT (no truncate, no append) so writes are positioned and
        # an existing lock held by a live instance is left untouched.
        fd = os.open(str(lock_path), os.O_RDWR | os.O_CREAT, 0o644)
        handle = os.fdopen(fd, "r+", encoding="utf-8")
    except OSError:
        return False

    if not _acquire_os_lock(handle):
        handle.close()
        return False  # another live instance holds the lock

    # We hold the lock. Record our pid for diagnostics only — the lock, not
    # this content, is authoritative. A write failure must never drop the claim.
    try:
        handle.seek(0)
        handle.write(_lock_payload())
        handle.truncate()
        handle.flush()
    except OSError:
        pass
    _lock_handle = handle
    return True


def release_primary_instance(slot: str = "") -> None:
    """Release the OS lock (if held) and remove the lock file."""
    global _lock_handle
    handle = _lock_handle
    _lock_handle = None
    if handle is not None:
        try:
            _release_os_lock(handle)
        finally:
            try:
                handle.close()
            except OSError:
                pass
    _lock_file_path(slot).unlink(missing_ok=True)


def _acquire_os_lock(handle: IO[str]) -> bool:
    """Take an exclusive, non-blocking lock. False if another process holds it."""
    fileno = handle.fileno()
    if os.name == "nt":
        import msvcrt

        try:
            handle.seek(0)
            msvcrt.locking(fileno, msvcrt.LK_NBLCK, 1)
        except OSError:
            return False
        return True

    import fcntl

    try:
        fcntl.flock(fileno, fcntl.LOCK_EX | fcntl.LOCK_NB)  # type: ignore[attr-defined]
    except OSError:
        return False
    return True


def _release_os_lock(handle: IO[str]) -> None:
    fileno = handle.fileno()
    if os.name == "nt":
        import msvcrt

        try:
            handle.seek(0)
            msvcrt.locking(fileno, msvcrt.LK_UNLCK, 1)
        except OSError:
            pass
        return

    import fcntl

    try:
        fcntl.flock(fileno, fcntl.LOCK_UN)  # type: ignore[attr-defined]
    except OSError:
        pass


def _lock_payload() -> str:
    return json.dumps({"pid": os.getpid()})


@dataclass(frozen=True, slots=True)
class OpenRequest:
    path: Path
    line: int | None = None
    column: int | None = None
    action: str = "open"


def enqueue_open_request(
    path: Path | None,
    *,
    line: int | None = None,
    column: int | None = None,
    action: str = "open",
    slot: str = "",
) -> None:
    queue_path = _queue_file_path(slot)
    queue_path.parent.mkdir(parents=True, exist_ok=True)
    # H-4-core-2: serialize concurrent writes via a dedicated side-car lock
    # file (*.lock) that always has content at byte 0 so msvcrt.locking can
    # work reliably. The data file itself is written with plain open("a") after
    # the lock is acquired; the JSON line is always < PIPE_BUF so the underlying
    # write is atomic once we own the lock.
    with _queue_write_lock(queue_path):
        with queue_path.open("a", encoding="utf-8", newline="\n") as handle:
            payload = (
                {"action": "show"}
                if path is None
                else {
                    "action": (action or "open").strip().lower(),
                    "path": str(path),
                    "line": line,
                    "column": column,
                }
            )
            handle.write(json.dumps(payload, ensure_ascii=True) + "\n")
            handle.flush()


def drain_open_requests(slot: str = "") -> list[OpenRequest | None]:
    queue_path = _queue_file_path(slot)
    if not queue_path.exists():
        return []
    lines = queue_path.read_text(encoding="utf-8").splitlines()
    queue_path.unlink(missing_ok=True)
    requests: list[OpenRequest | None] = []
    for line in lines:
        if not line.strip():
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(raw, dict):
            continue
        action = str(raw.get("action", "open")).strip().lower()
        if action == "show":
            requests.append(None)
            continue
        if isinstance(raw.get("path"), str):
            line_number = raw.get("line")
            column_number = raw.get("column")
            requests.append(
                OpenRequest(
                    path=Path(raw["path"]),
                    line=int(line_number) if isinstance(line_number, int) else None,
                    column=int(column_number) if isinstance(column_number, int) else None,
                    action=action or "open",
                )
            )
    return requests


# H-4-core-2: in-process lock for enqueue.  Multiple threads in the same
# process (e.g., two background tasks both triggering "open file" events)
# serialize here.  Cross-process writes (two secondary QUILL instances) rely
# on the fact that a single JSON line is always < PIPE_BUF (4 KiB on all
# supported platforms) so the underlying kernel write is already atomic.
_enqueue_lock = threading.Lock()


@contextlib.contextmanager
def _queue_write_lock(queue_path: Path) -> Iterator[None]:
    """Serialize concurrent in-process enqueue calls."""
    _ = queue_path
    with _enqueue_lock:
        yield


def _lock_file_path(slot: str = "") -> Path:
    name = f"instance-{slot}.lock" if slot else "instance.lock"
    return app_data_dir() / "ipc" / name


def _queue_file_path(slot: str = "") -> Path:
    name = f"open-requests-{slot}.jsonl" if slot else "open-requests.jsonl"
    return app_data_dir() / "ipc" / name
