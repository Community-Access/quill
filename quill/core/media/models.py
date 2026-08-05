"""Core data models for the media player (source-agnostic, wx-free).

A :class:`MediaItem` is what the controller plays, regardless of where it came
from (local file, QUILL library download, podcast, or a BARD title). Chapters are
a light :class:`MediaChapter` list so this module stays dependency-free; the UI
maps richer chapter objects (``quill/core/speech/chapters.py``) onto it.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class MediaSource(StrEnum):
    """Where a media item came from."""

    LOCAL = "local"
    LIBRARY = "library"
    PODCAST = "podcast"
    BARD = "bard"
    DAISY = "daisy"
    STREAM = "stream"


class PlayerState(StrEnum):
    """The controller's transport state."""

    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"
    ENDED = "ended"


@dataclass(frozen=True, slots=True)
class MediaChapter:
    """One chapter/heading marker within a media item."""

    index: int
    title: str
    start_ms: int
    end_ms: int | None = None


@dataclass(frozen=True, slots=True)
class MediaItem:
    """A playable item and its metadata."""

    path: str
    title: str = ""
    source: MediaSource = MediaSource.LOCAL
    author: str = ""
    fmt: str = ""
    duration_ms: int = 0
    chapters: tuple[MediaChapter, ...] = ()
    #: Stable key for resume/bookmark storage (defaults to the path).
    resume_key: str = ""

    @property
    def key(self) -> str:
        return self.resume_key or self.path

    @property
    def has_chapters(self) -> bool:
        return len(self.chapters) > 0


__all__ = ["MediaChapter", "MediaItem", "MediaSource", "PlayerState"]
