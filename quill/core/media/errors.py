"""Coded errors for the media player core (``player.md`` Section 15).

All inherit :class:`quill.core.error_codes.CodedError` with unique
``QUILL-MEDIA-*`` codes so a pasted message names the failing branch (GATE-EC).
"""

from __future__ import annotations

from quill.core.error_codes import CodedError


class MediaError(CodedError):
    """Base for media-player failures."""

    code = "QUILL-MEDIA-CORE-FAILED"


class InvalidTimecodeError(MediaError):
    """A timecode string could not be parsed into a position."""

    code = "QUILL-MEDIA-TIMECODE-INVALID"


class EngineUnavailableError(MediaError):
    """No playback engine is available (or it failed to load the media)."""

    code = "QUILL-MEDIA-ENGINE-UNAVAILABLE"


class NoMediaLoadedError(MediaError):
    """A transport action was requested with nothing loaded."""

    code = "QUILL-MEDIA-NONE-LOADED"


__all__ = [
    "EngineUnavailableError",
    "InvalidTimecodeError",
    "MediaError",
    "NoMediaLoadedError",
]
