"""Compatibility guard for the retired DECtalk download."""

from __future__ import annotations

from pathlib import Path

from quill.core.read_aloud import ReadAloudUnavailableError


def download_dectalk_runtime(target_dir: Path) -> Path:
    """Reject the former download without touching the user's files."""
    raise ReadAloudUnavailableError(
        "QUILL no longer distributes DECtalk because its redistribution rights "
        "have not been confirmed. A separately installed copy can still be used."
    )
