"""Playback fields persisted by :class:`PodcastSettings`."""

from __future__ import annotations

from typing import Protocol

from quill.core.podcasts.models_queue import coerce_int


class PlaybackSettings(Protocol):
    auto_skip_intro_seconds: int
    auto_skip_outro_seconds: int
    finished_within_seconds: int
    resume_rewind_seconds: int


def playback_to_dict(settings: PlaybackSettings) -> dict[str, object]:
    return {
        "auto_skip_intro_seconds": settings.auto_skip_intro_seconds,
        "auto_skip_outro_seconds": settings.auto_skip_outro_seconds,
        "finished_within_seconds": settings.finished_within_seconds,
        "resume_rewind_seconds": settings.resume_rewind_seconds,
    }


def playback_from_dict(data: dict[str, object]) -> dict[str, object]:
    return {
        "auto_skip_intro_seconds": max(0, coerce_int(data.get("auto_skip_intro_seconds"), 0)),
        "auto_skip_outro_seconds": max(0, coerce_int(data.get("auto_skip_outro_seconds"), 0)),
        "finished_within_seconds": min(
            3600, max(0, coerce_int(data.get("finished_within_seconds"), 60))
        ),
        "resume_rewind_seconds": min(300, max(0, coerce_int(data.get("resume_rewind_seconds"), 0))),
    }
