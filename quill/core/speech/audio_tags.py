"""QUILL's adapter over the shared audio tag model.

The model itself -- the table of 26 tags, how each maps to an ID3 frame and an
MP4 atom, and how they are read and written -- lives in
:mod:`quill.core.speech.audio_tags_core`, which is vendored byte-identical
into podHarvest so the two apps cannot drift. This module is the part that
cannot be shared, and it is deliberately thin:

* **Coded errors.** GATE-EC requires every top-level exception in
  ``quill/core`` to subclass :class:`~quill.core.error_codes.CodedError` with
  its own code, and forbids the ``class X(Exception, CodedError)`` MRO. The
  shared module cannot import ``CodedError``, so it raises plain exceptions
  and they are retranslated here, at the boundary, once.
* **The ``AudioMetadata`` bridge.** ``BookFile``, the M4B re-mux and the batch
  document-to-speech pipeline all speak the seven-field
  :class:`~quill.core.speech.ffmpeg.AudioMetadata`. These converters let the
  full 26-field editor and that seven-field view edit the same file without
  either discarding the other's work.

Everything re-exported below is the shared module's, unchanged. Import from
here rather than from ``audio_tags_core`` so the coded errors are the ones
callers see.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from quill.core.error_codes import CodedError
from quill.core.speech import audio_tags_core as _core
from quill.core.speech.audio_tags_core import (
    GROUPS as GROUPS,
)
from quill.core.speech.audio_tags_core import (
    MAX_COVER_BYTES as MAX_COVER_BYTES,
)
from quill.core.speech.audio_tags_core import (
    TAG_FIELDS as TAG_FIELDS,
)
from quill.core.speech.audio_tags_core import (
    AudioTagError,
    AudioTags,
    CoverArt,
    TagField,
)
from quill.core.speech.audio_tags_core import (
    cover_extension as cover_extension,
)
from quill.core.speech.audio_tags_core import (
    describe_cover as describe_cover,
)
from quill.core.speech.audio_tags_core import (
    field_for as field_for,
)
from quill.core.speech.audio_tags_core import (
    fields_in as fields_in,
)
from quill.core.speech.audio_tags_core import (
    format_time_precise as format_time_precise,
)
from quill.core.speech.audio_tags_core import (
    parse_time as parse_time,
)
from quill.core.speech.audio_tags_core import (
    preferred_id3_version as preferred_id3_version,
)

if TYPE_CHECKING:
    from quill.core.speech.ffmpeg import AudioMetadata

__all__ = [
    "GROUPS",
    "MAX_COVER_BYTES",
    "TAG_FIELDS",
    "AudioTags",
    "CoverArt",
    "TagField",
    "TagReadError",
    "TagWriteError",
    "cover_extension",
    "describe_cover",
    "field_for",
    "fields_in",
    "format_time_precise",
    "load_cover",
    "merge_audio_metadata",
    "parse_time",
    "preferred_id3_version",
    "read_tags",
    "to_audio_metadata",
    "write_tags",
]


class TagReadError(CodedError):
    """A file's tags or cover art could not be read; message is speakable."""

    code = "QUILL-SPEECH-TAG-READ"


class TagWriteError(CodedError):
    """A file's tags could not be written; nothing changed. Message is speakable."""

    code = "QUILL-SPEECH-TAG-WRITE"


def _coded(exc: AudioTagError, write: bool = False) -> CodedError:
    """The coded twin of a shared-module error, carrying the same message."""
    if write or isinstance(exc, _core.TagWriteError):
        return TagWriteError(str(exc))
    return TagReadError(str(exc))


def read_tags(path: Path) -> AudioTags:
    """Every modelled tag on *path* (MP3, or M4A/M4B/MP4).

    A file with no tag block reads as empty tags rather than an error -- an
    untagged file is exactly the one somebody opens the editor to fix.
    """
    try:
        return _core.read_tags(Path(path))
    except AudioTagError as exc:
        raise _coded(exc) from exc


def write_tags(path: Path, tags: AudioTags) -> None:
    """Write every modelled tag onto *path*, leaving everything else alone.

    Load-modify-save, so the chapter CHAP/CTOC frames and anything else this
    editor does not model come through untouched.
    """
    try:
        _core.write_tags(Path(path), tags)
    except AudioTagError as exc:
        raise _coded(exc, write=True) from exc


def load_cover(path: Path) -> CoverArt:
    """Read *path* as cover art, sniffing the real bytes, not the extension."""
    try:
        return _core.load_cover(Path(path))
    except AudioTagError as exc:
        raise _coded(exc) from exc


#: The ``AudioMetadata`` attribute each of the seven core tags corresponds to.
_METADATA_KEYS: tuple[tuple[str, str], ...] = (
    ("title", "title"),
    ("artist", "artist"),
    ("album", "album"),
    ("album_artist", "album_artist"),
    ("genre", "genre"),
    ("year", "year"),
    ("track", "track"),
    ("comment", "comment"),
)


def to_audio_metadata(tags: AudioTags) -> AudioMetadata:
    """The seven-field ``AudioMetadata`` view of *tags*, for ffmpeg and BookFile."""
    from quill.core.speech.ffmpeg import AudioMetadata

    return AudioMetadata(**{attr: tags.get(key) for key, attr in _METADATA_KEYS})


def merge_audio_metadata(tags: AudioTags, meta: AudioMetadata) -> AudioTags:
    """A copy of *tags* with the seven core fields overlaid from *meta*.

    The Chapter Workbench's five quick fields edit an ``AudioMetadata``; this
    is how those edits reach the full tag set without discarding the nineteen
    fields the quick view never shows.
    """
    merged = tags.copy()
    for key, attr in _METADATA_KEYS:
        merged.set(key, str(getattr(meta, attr, "") or ""))
    return merged
