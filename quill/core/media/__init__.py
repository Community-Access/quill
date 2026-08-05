"""QUILL Media Player -- core domain layer (``player.md``).

Phase 1: the pure, wx-free foundation -- the :class:`MediaController` state
machine over an injected :class:`PlaybackEngine`, source-agnostic
:class:`MediaItem`/:class:`MediaChapter` models, precise H:M:S seeking
(:mod:`~quill.core.media.timecode`), the backend capability matrix, the player
event stream, the coded ``QUILL-MEDIA-*`` errors, and the ``media_*`` settings
defaults. The DSP chain, DAISY navigation, unified library, and the wx shell
(window, menu bar, tray, Magical Mode) build on this in later phases.
"""

from __future__ import annotations

from quill.core.media.capabilities import EngineCapabilities, capabilities_for
from quill.core.media.config import MEDIA_DEFAULTS, default_config, resolve
from quill.core.media.controller import MediaController, clamp_position
from quill.core.media.daisy import (
    DaisyHeading,
    DaisyParseError,
    first_audio_src,
    parse_ncx,
    resolve_heading_times,
)
from quill.core.media.dsp import (
    EQ_BANDS_HZ,
    EQ_PRESETS,
    DspSettings,
    Equalizer,
    build_audio_filters,
)
from quill.core.media.engine import PlaybackEngine
from quill.core.media.errors import (
    EngineUnavailableError,
    InvalidTimecodeError,
    MediaError,
    NoMediaLoadedError,
)
from quill.core.media.events import (
    CHAPTER_CHANGED,
    ENDED,
    LOADED,
    SEEKED,
    STATE_CHANGED,
    PlayerEvent,
    PlayerListener,
)
from quill.core.media.models import MediaChapter, MediaItem, MediaSource, PlayerState
from quill.core.media.recap import (
    ChapterContext,
    RecapService,
    RecapUnavailable,
    recap_prompt,
)
from quill.core.media.timecode import format_spoken, format_timecode, parse_timecode

__all__ = [
    "CHAPTER_CHANGED",
    "ENDED",
    "EQ_BANDS_HZ",
    "EQ_PRESETS",
    "LOADED",
    "MEDIA_DEFAULTS",
    "SEEKED",
    "STATE_CHANGED",
    "DaisyHeading",
    "DaisyParseError",
    "DspSettings",
    "EngineCapabilities",
    "EngineUnavailableError",
    "Equalizer",
    "InvalidTimecodeError",
    "MediaChapter",
    "MediaController",
    "MediaError",
    "MediaItem",
    "MediaSource",
    "NoMediaLoadedError",
    "PlaybackEngine",
    "ChapterContext",
    "RecapService",
    "RecapUnavailable",
    "recap_prompt",
    "PlayerEvent",
    "PlayerListener",
    "PlayerState",
    "build_audio_filters",
    "capabilities_for",
    "clamp_position",
    "default_config",
    "first_audio_src",
    "format_spoken",
    "format_timecode",
    "parse_ncx",
    "parse_timecode",
    "resolve",
    "resolve_heading_times",
]
