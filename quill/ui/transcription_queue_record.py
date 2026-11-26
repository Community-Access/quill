"""Build the durable, non-secret record for one transcription request."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from quill.core.windows_dictation.file_queue import TranscriptionJob


def stored_job(
    job: Any,
    host: Any,
    *,
    batch: str,
    cloud_approved: bool,
) -> TranscriptionJob:
    return TranscriptionJob(
        app=host._dictation_app_name(),  # type: ignore[attr-defined]
        source_path=str(Path(job.path).resolve()),
        model=str(job.model),
        language=str(job.language),
        timestamps=bool(job.timestamps),
        obey_commands=bool(job.obey_commands),
        remove_fillers=bool(job.remove_fillers),
        dash=str(job.dash),
        translate=bool(job.translate),
        keywords=[str(word) for word in job.keywords],
        cloud_approved=cloud_approved,
        batch=batch,
    )


__all__ = ["stored_job"]
