from __future__ import annotations

import os
import threading
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from quill.core.paths import app_data_dir
from quill.core.storage import read_json, write_json_atomic


def _validate_session_id(session_id: str) -> None:
    """Raise :class:`ValueError` if ``session_id`` is not a valid UUID string.

    Replaces the previous ``UUID(session_id)`` calls that relied on the
    constructor's exception for control flow.
    """
    UUID(session_id)


@dataclass(frozen=True, slots=True)
class RecoveryOffer:
    session_id: str
    snapshot: Path
    # Cursor position saved at the last autosave (0 = unknown / start of file).
    # Used by the "resume from where I left off" feature (§8.4).
    cursor_position: int = 0
    # How many times the user has dismissed this recovery offer without restoring.
    # The UI shows adaptive messaging when this reaches 3 (M-28 / §8.2).
    dismissal_count: int = 0


# Two layers of synchronization protect the read-modify-write of
# recovery_state.json:
# 1. A process-wide threading.RLock (H-4-core) guards in-process
#    callers from one another.
# 2. An advisory OS file lock (mirroring quill.core.ipc) guards two
#    processes from one another. The IPC primary-instance lock
#    prevents *most* concurrent starts in the same data dir, but
#    on a developer machine with multiple accounts or a
#    misconfigured install, two processes can still race.
_state_lock = threading.RLock()


def _acquire_file_lock() -> int | None:
    """Open the recovery state file with an exclusive OS-level lock.

    Returns the file descriptor if the lock was acquired, else
    ``None`` (caller should fall back to the in-process lock and
    skip the cross-process guarantee, which is rare)."""
    lock_path = _state_path().with_suffix(".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(str(lock_path), os.O_RDWR | os.O_CREAT, 0o644)
    except OSError:
        return None
    if os.name == "nt":
        import msvcrt

        try:
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
        except OSError:
            os.close(fd)
            return None
    else:
        import fcntl

        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)  # type: ignore[attr-defined]
        except OSError:
            os.close(fd)
            return None
    return fd


def _release_file_lock(fd: int) -> None:
    if os.name == "nt":
        import msvcrt

        try:
            msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
        except OSError:
            pass
    else:
        import fcntl

        try:
            fcntl.flock(fd, fcntl.LOCK_UN)  # type: ignore[attr-defined]
        except OSError:
            pass
    os.close(fd)


def begin_session(session_id: str) -> list[RecoveryOffer]:
    _validate_session_id(session_id)
    fd = _acquire_file_lock()
    try:
        with _state_lock:
            state = _load_state()
            offers: list[RecoveryOffer] = []
            previous_session = state.get("last_session_id")
            previous_clean = bool(state.get("clean_exit", True))
            if isinstance(previous_session, str) and previous_session and not previous_clean:
                latest = latest_session_snapshot(previous_session)
                if latest is not None and not _is_offer_dismissed(state, previous_session, latest):
                    cursor_position = _load_cursor_position(state, previous_session)
                    dismissal_count = _load_dismissal_count(state, previous_session)
                    offers.append(
                        RecoveryOffer(
                            session_id=previous_session,
                            snapshot=latest,
                            cursor_position=cursor_position,
                            dismissal_count=dismissal_count,
                        )
                    )
            state["last_session_id"] = session_id
            state["clean_exit"] = False
            _save_state(state)
    finally:
        if fd is not None:
            _release_file_lock(fd)
    return offers


def mark_clean_exit(session_id: str) -> None:
    _validate_session_id(session_id)
    fd = _acquire_file_lock()
    try:
        with _state_lock:
            state = _load_state()
            last_session = state.get("last_session_id")
            if last_session != session_id:
                return
            state["last_session_id"] = session_id
            state["clean_exit"] = True
            _save_state(state)
    finally:
        if fd is not None:
            _release_file_lock(fd)


def mark_recovery_offer_dismissed(offer: RecoveryOffer) -> None:
    _record_offer_outcome(offer, outcome="dismissed")
    _increment_dismissal_count(offer.session_id)


def mark_recovery_offer_recovered(offer: RecoveryOffer) -> None:
    _record_offer_outcome(offer, outcome="recovered")


def latest_session_snapshot(session_id: str) -> Path | None:
    _validate_session_id(session_id)
    root = app_data_dir() / "autosave" / session_id
    if not root.exists():
        return None
    snapshots = sorted(
        [s for s in root.glob("*.snap") if s.stat().st_size > 0],
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    if not snapshots:
        return None
    return snapshots[0]


def read_recovery_snapshot(path: Path) -> tuple[str, bool]:
    """Read *path* and return ``(text, had_replacements)``.

    ``had_replacements`` is True when the file contained bytes that could not
    be decoded as UTF-8 and were substituted with U+FFFD (the Unicode
    replacement character).  The UI surfaces this as a status-bar note in the
    recovery dialog so the user knows to inspect the recovered text.
    """
    text = path.read_text(encoding="utf-8", errors="replace")
    had_replacements = "�" in text
    return text, had_replacements


def save_cursor_position(session_id: str, position: int) -> None:
    """Persist the editor cursor *position* for *session_id*.

    Called from the UI on every autosave so the next session can restore the
    caret to where the user was working ("Resume from where I left off", §8.4).
    """
    _validate_session_id(session_id)
    fd = _acquire_file_lock()
    try:
        with _state_lock:
            state = _load_state()
            positions: dict[str, int] = {}
            raw = state.get("cursor_positions")
            if isinstance(raw, dict):
                positions = {k: v for k, v in raw.items() if isinstance(k, str) and isinstance(v, int)}
            positions[session_id] = int(position)
            state["cursor_positions"] = positions
            _save_state(state)
    finally:
        if fd is not None:
            _release_file_lock(fd)


def _state_path() -> Path:
    return app_data_dir() / "recovery_state.json"


def _load_state() -> dict[str, object]:
    raw = read_json(_state_path(), default={})
    if not isinstance(raw, dict):
        return {}
    return raw


def _save_state(data: dict[str, object]) -> None:
    write_json_atomic(_state_path(), data)


def _record_offer_outcome(offer: RecoveryOffer, *, outcome: str) -> None:
    fd = _acquire_file_lock()
    try:
        with _state_lock:
            state = _load_state()
            state["last_recovery_offer"] = {
                "session_id": offer.session_id,
                "snapshot": str(offer.snapshot),
                "outcome": outcome,
                "recorded_at": datetime.now(UTC).isoformat(),
            }
            _save_state(state)
    finally:
        if fd is not None:
            _release_file_lock(fd)


def _is_offer_dismissed(state: dict[str, object], session_id: str, snapshot: Path) -> bool:
    raw = state.get("last_recovery_offer")
    if not isinstance(raw, dict):
        return False
    outcome = str(raw.get("outcome", "")).strip().lower()
    if outcome != "dismissed":
        return False
    recorded_session = str(raw.get("session_id", "")).strip()
    recorded_snapshot = str(raw.get("snapshot", "")).strip()
    return recorded_session == session_id and recorded_snapshot == str(snapshot)


def _load_cursor_position(state: dict[str, object], session_id: str) -> int:
    positions = state.get("cursor_positions")
    if not isinstance(positions, dict):
        return 0
    raw = positions.get(session_id)
    return int(raw) if isinstance(raw, int) else 0


def _load_dismissal_count(state: dict[str, object], session_id: str) -> int:
    counts = state.get("recovery_dismissal_counts")
    if not isinstance(counts, dict):
        return 0
    raw = counts.get(session_id)
    return int(raw) if isinstance(raw, int) else 0


def _increment_dismissal_count(session_id: str) -> None:
    fd = _acquire_file_lock()
    try:
        with _state_lock:
            state = _load_state()
            counts: dict[str, int] = {}
            raw = state.get("recovery_dismissal_counts")
            if isinstance(raw, dict):
                counts = {k: v for k, v in raw.items() if isinstance(k, str) and isinstance(v, int)}
            counts[session_id] = counts.get(session_id, 0) + 1
            state["recovery_dismissal_counts"] = counts
            _save_state(state)
    finally:
        if fd is not None:
            _release_file_lock(fd)
