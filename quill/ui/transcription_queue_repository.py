"""The one durable queue repository for each transcription data root."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from quill.core.windows_dictation.file_queue import TranscriptionQueue
from quill.ui.transcription_queue_host import durable_host

_REPOSITORIES: dict[Path, TranscriptionQueue] = {}


def repository_for(host: Any) -> TranscriptionQueue:
    owner = durable_host(host)
    root = Path(owner._dictation_data_dir()).resolve()  # type: ignore[attr-defined]
    found = _REPOSITORIES.get(root)
    if found is None:
        found = TranscriptionQueue(root)
        _REPOSITORIES[root] = found
    return found


__all__ = ["repository_for"]
