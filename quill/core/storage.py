from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

# On Windows os.replace can transiently fail with PermissionError when another
# process (an antivirus scanner, a backup agent, or a screen reader's file hook)
# briefly holds the destination open. Retry a few times with a short backoff
# before giving up so a normal save is not lost to a momentary lock.
_REPLACE_MAX_ATTEMPTS = 5
_REPLACE_RETRY_DELAY = 0.05


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
    """Replace ``path`` with ``temp_path``, retrying transient Windows locks."""

    last_error: PermissionError | None = None
    for attempt in range(_REPLACE_MAX_ATTEMPTS):
        try:
            temp_path.replace(path)
            return
        except PermissionError as error:
            last_error = error
            if attempt + 1 < _REPLACE_MAX_ATTEMPTS:
                time.sleep(_REPLACE_RETRY_DELAY)
    assert last_error is not None
    raise last_error


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as file_handle:
        return json.load(file_handle)


def write_json_atomic(path: Path, data: Any, *, base: Path | None = None) -> None:
    if base is not None:
        resolve_within(base, path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    with temp_path.open("w", encoding="utf-8", newline="\n") as file_handle:
        json.dump(data, file_handle, indent=2, sort_keys=True, ensure_ascii=False)
        file_handle.write("\n")
        file_handle.flush()
        os.fsync(file_handle.fileno())
    _atomic_replace(temp_path, path)
