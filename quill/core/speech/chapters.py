"""MP3/ID3 chapter markers, and the operations that reshape a chapter list.

The chapter model and every operation on it now live in
:mod:`quill.core.speech.audio_tags_core`, vendored byte-identical into
podHarvest so the two apps write files the other reads back unchanged (see
``docs/superpowers/specs/ALIGNMENT-audio-tags-and-chapters.md``). This module
is QUILL's face on it: it re-exports the shared pieces, retranslates the
shared module's plain exceptions into :class:`ChapterEditError` so GATE-EC
holds, and keeps the parts only QUILL has -- ``compute_chapters`` and its
``ChapterSection`` input, which turn a batch document-to-speech run's section
durations into chapters, and ``ChapterSettings``, which is how those runs are
configured. The CHAP/CTOC writer began as the sibling BITS project
**ChapterForge**'s (``d:\\code99\\forum``, MIT).

Two behaviours worth restating because callers depend on them:

1. Chapters are **contiguous**: with an inter-article gap, the gap silence is
   the trailing part of the article it follows (``end_ms`` of chapter i equals
   ``start_ms`` of chapter i+1), so every millisecond belongs to a chapter.
   This is a deliberate fix over ChapterForge's ``_chapters_with_gaps``, which
   leaves the gap un-chaptered.
2. Writing **loads the existing ID3 tags** and replaces only the chapter
   frames, rather than building a fresh ``ID3()`` that would discard
   everything else on the file.

Requires ``mutagen`` (the ``quill[mp3]`` extra) to touch a file; it is
imported lazily, so this module loads without it and the write raises a clear
error if it is absent.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from quill.core.error_codes import CodedError
from quill.core.speech import audio_tags_core as _core
from quill.core.speech.audio_tags_core import (
    NUDGE_STEPS_MS as NUDGE_STEPS_MS,
)
from quill.core.speech.audio_tags_core import (
    AudioTagError,
    Chapter,
)

__all__ = [
    "NUDGE_STEPS_MS",
    "Chapter",
    "ChapterEditError",
    "ChapterSection",
    "ChapterSettings",
    "add_chapter",
    "clamp_chapters",
    "compute_chapters",
    "delete_chapter",
    "merge_chapter",
    "nudge_chapter_start",
    "read_mp3_chapters",
    "set_chapter_bounds",
    "set_chapter_start",
    "split_chapter",
    "write_mp3_chapters",
]


class ChapterEditError(CodedError):
    """A chapter edit (add/delete/merge/split/retime) was not possible.

    The message is speakable and says what would have to change. Raised here
    rather than in the shared module because that module is vendored into a
    second repository and cannot import QUILL's error-code base class.
    """

    code = "QUILL-SPEECH-CHAPTER-EDIT"


@dataclass(slots=True)
class ChapterSection:
    """One source section to be chaptered: a heading title and its audio length."""

    title: str
    duration_ms: int


def compute_chapters(sections: list[ChapterSection], gap_ms: int = 0) -> list[Chapter]:
    """Cumulative chapter boundaries from section durations, contiguous with gaps.

    ``gap_ms`` of silence is inserted between articles (never after the last).
    The gap is counted as the **trailing** part of the preceding chapter, so
    chapters are contiguous (``chapters[i].end_ms == chapters[i+1].start_ms``)
    and the whole timeline is covered -- the fix over ChapterForge's gap
    handling.
    """
    chapters: list[Chapter] = []
    cursor = 0
    last = len(sections) - 1
    for i, section in enumerate(sections):
        start = cursor
        trailing_gap = max(0, gap_ms) if i < last else 0
        end = start + max(0, section.duration_ms) + trailing_gap
        chapters.append(Chapter(index=i, title=section.title, start_ms=start, end_ms=end))
        cursor = end
    return chapters


def write_mp3_chapters(
    path: Path,
    chapters: list[Chapter],
    *,
    toc_title: str = "Chapters",
    v2_version: int | None = None,
) -> None:
    """Write ID3 CHAP + CTOC frames onto ``path`` (existing tags preserved).

    Idempotent: existing chapter frames go first, so re-running does not give
    you the chapters twice. ``v2_version`` picks the ID3 minor version the
    whole tag block is saved as; left unset it follows whatever the file's
    existing tags need, so writing chapters can never strand a sort field or a
    full date that was already there (see
    :func:`quill.core.speech.audio_tags.preferred_id3_version`).
    """
    try:
        _core.write_mp3_chapters(Path(path), chapters, toc_title=toc_title, v2_version=v2_version)
    except AudioTagError as exc:
        from quill.core.speech.audio_tags import TagWriteError

        raise TagWriteError(str(exc)) from exc


def read_mp3_chapters(path: Path) -> list[Chapter]:
    """Read chapter frames back from ``path``, ordered by start time."""
    return _core.read_mp3_chapters(Path(path))


def merge_chapter(chapters: list[Chapter], index: int) -> list[Chapter]:
    """Remove the marker at *index*, merging that chapter into its neighbour.

    The first chapter merges into the second and keeps the first's title; any
    other merges into the previous one. Audio is never removed -- only the
    marker goes away.
    """
    try:
        return _core.merge_chapter(chapters, index)
    except _core.ChapterEditError as exc:
        raise ChapterEditError(str(exc)) from exc


def split_chapter(
    chapters: list[Chapter],
    at_ms: int,
    *,
    title: str = "New chapter",
    min_part_ms: int = 1000,
) -> list[Chapter]:
    """Insert a new boundary at *at_ms* -- the split-at-playhead operation.

    The chapter containing *at_ms* is cut in two; the left half keeps the
    original title, the right half gets *title*.
    """
    try:
        return _core.split_chapter(chapters, at_ms, title=title, min_part_ms=min_part_ms)
    except _core.ChapterEditError as exc:
        raise ChapterEditError(str(exc)) from exc


def set_chapter_start(
    chapters: list[Chapter],
    index: int,
    new_start_ms: int,
    *,
    min_part_ms: int = 500,
) -> list[Chapter]:
    """Retime chapter *index*'s start, and the previous chapter's end with it.

    Chapters stay contiguous and ordered; the new start must leave at least
    *min_part_ms* of both the previous chapter and this one.
    """
    try:
        return _core.set_chapter_start(chapters, index, new_start_ms, min_part_ms=min_part_ms)
    except _core.ChapterEditError as exc:
        raise ChapterEditError(str(exc)) from exc


def add_chapter(
    chapters: list[Chapter],
    at_ms: int,
    *,
    title: str = "New chapter",
    min_part_ms: int = 1000,
) -> list[Chapter]:
    """Insert a chapter boundary at *at_ms* -- the explicit "add" operation.

    Inside a chapter this splits it. At or past the last chapter's end the
    marker is appended instead, which is the case :func:`split_chapter`
    refuses outright and the reason "add" is its own verb rather than an
    alias.
    """
    try:
        return _core.add_chapter(chapters, at_ms, title=title, min_part_ms=min_part_ms)
    except _core.ChapterEditError as exc:
        raise ChapterEditError(str(exc)) from exc


def delete_chapter(chapters: list[Chapter], index: int) -> list[Chapter]:
    """Remove chapter *index*'s marker. The audio is never touched.

    Deleting the first chapter pulls the second one's start back to the
    beginning; any other deletion extends the previous chapter over it. Unlike
    :func:`merge_chapter` this is defined for the last chapter too, and it
    keeps the surviving chapter's title rather than the deleted one's.
    """
    try:
        return _core.delete_chapter(chapters, index)
    except _core.ChapterEditError as exc:
        raise ChapterEditError(str(exc)) from exc


def set_chapter_bounds(
    chapters: list[Chapter],
    index: int,
    start_ms: int,
    end_ms: int,
    *,
    min_part_ms: int = 500,
) -> list[Chapter]:
    """Retime both edges of chapter *index*, keeping the list contiguous.

    The neighbours stretch or shrink to meet the new edges. The first
    chapter's start and the last chapter's end are pinned to the file, so a
    different value for either is ignored rather than refused.
    """
    try:
        return _core.set_chapter_bounds(chapters, index, start_ms, end_ms, min_part_ms=min_part_ms)
    except _core.ChapterEditError as exc:
        raise ChapterEditError(str(exc)) from exc


def nudge_chapter_start(
    chapters: list[Chapter],
    index: int,
    delta_ms: int,
    *,
    min_part_ms: int = 500,
) -> tuple[list[Chapter], int]:
    """Move chapter *index*'s start by *delta_ms*, clamped at its neighbours.

    Returns the new list and the delta **actually** applied. This is the one
    chapter edit that clamps rather than raising: a nudge is a held key, and
    running a marker up against its neighbour should stop there, not throw. An
    applied delta of 0 means the marker is already at the wall, which lets the
    caller say so once per run instead of once per keypress.
    """
    try:
        return _core.nudge_chapter_start(chapters, index, delta_ms, min_part_ms=min_part_ms)
    except _core.ChapterEditError as exc:
        raise ChapterEditError(str(exc)) from exc


def clamp_chapters(chapters: list[Chapter], total_ms: int) -> list[Chapter]:
    """Clamp chapters to ``[0, total_ms]``, dropping any that fall entirely outside.

    Guards a plan against a re-encode that shortened the audio (or an imported
    list from a different edit of the file): starts/ends are clamped, empty
    chapters are dropped, and the final chapter is extended to *total_ms* so
    the whole timeline stays covered.
    """
    return _core.clamp_chapters(chapters, total_ms)


@dataclass(slots=True)
class ChapterSettings:
    """Resolved batch chapterization settings (§4.8.8); see core.settings for storage."""

    mode: str = "none"  # none | single | separate
    sound_enabled: bool = False
    sound_id: str = ""
    sound_volume: int = 100  # 0–100
    article_gap_ms: int = 1200
    intro_section_title: str = "Introduction"
    extra: dict[str, str] = field(default_factory=dict)
