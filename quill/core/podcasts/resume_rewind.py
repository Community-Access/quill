"""Playback-only rewind calculation for saved podcast places."""

from __future__ import annotations

from typing import Protocol


class ResumeSettings(Protocol):
    resume_rewind_seconds: int


def apply(
    saved_start_ms: int,
    settings: ResumeSettings,
    resume_ms: int | None,
    automatic_resume: bool,
) -> int:
    """Rewind automatic resumes without changing the saved place."""
    if saved_start_ms <= 0 or (resume_ms is not None and not automatic_resume):
        return saved_start_ms
    seconds = min(300, max(0, int(settings.resume_rewind_seconds)))
    return max(0, saved_start_ms - seconds * 1000)
