"""MP3/ID3 chapter markers for batch document-to-speech (§4.8.4).

wx-free, strict-typed. Computes chapter boundaries from per-section durations and
writes ID3v2.3 CHAP + CTOC frames (the format Apple Podcasts, Overcast, VLC,
foobar2000, … navigate). The CHAP/CTOC writer is borrowed from the sibling BITS
project **ChapterForge** (``d:\\code99\\forum``, MIT) — ``core.Chapter`` /
``core.compute_chapters`` / ``core.write_tags_and_chapters`` — with two
deliberate fixes over the borrowed logic (see ``docs/planning`` §4.8.4 notes):

1. Chapters are **contiguous**: with an inter-article gap, the gap silence is the
   trailing part of the article it follows (``end_ms`` of chapter i equals
   ``start_ms`` of chapter i+1), so every millisecond belongs to a chapter.
   ChapterForge's ``_chapters_with_gaps`` leaves the gap un-chaptered.
2. Writing **loads existing ID3 tags** and only replaces the chapter frames,
   instead of building a fresh ``ID3()`` that discards other metadata.

Requires ``mutagen`` (the ``quill[mp3]`` extra); imported lazily so this module
loads without it and ``write_mp3_chapters`` raises a clear error if it is absent.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path


@dataclass(slots=True)
class Chapter:
    """A computed chapter boundary (ms), mirroring ChapterForge's ``Chapter``."""

    index: int
    title: str
    start_ms: int
    end_ms: int
    #: Podcasting 2.0 extras: an optional link and image for this chapter.
    #: Round-tripped through the ``…chapters.json`` sidecar; empty = omitted.
    url: str = ""
    image: str = ""

    @property
    def duration_ms(self) -> int:
        return self.end_ms - self.start_ms


@dataclass(slots=True)
class ChapterSection:
    """One source section to be chaptered: a heading title and its audio length."""

    title: str
    duration_ms: int


def compute_chapters(sections: list[ChapterSection], gap_ms: int = 0) -> list[Chapter]:
    """Cumulative chapter boundaries from section durations, contiguous with gaps.

    ``gap_ms`` of silence is inserted between articles (never after the last). The
    gap is counted as the **trailing** part of the preceding chapter, so chapters
    are contiguous (``chapters[i].end_ms == chapters[i+1].start_ms``) and the whole
    timeline is covered — the fix over ChapterForge's gap handling.
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


def write_mp3_chapters(path: Path, chapters: list[Chapter], *, toc_title: str = "Chapters") -> None:
    """Write ID3v2.3 CHAP + CTOC frames onto ``path`` (existing tags preserved).

    Idempotent: any existing CHAP/CTOC frames are removed first so re-running does
    not duplicate chapters. Raises ``RuntimeError`` when mutagen is unavailable.
    """
    try:
        from mutagen.id3 import CHAP, CTOC, ID3, TIT2, CTOCFlags, ID3NoHeaderError
    except ImportError as exc:  # pragma: no cover - exercised only without the extra
        raise RuntimeError(
            "MP3 chapter markers require the 'mutagen' package (quill[mp3])."
        ) from exc

    try:
        tags = ID3(str(path))
    except ID3NoHeaderError:
        tags = ID3()

    tags.delall("CHAP")
    tags.delall("CTOC")

    element_ids: list[str] = []
    for chapter in chapters:
        element_id = f"chp{chapter.index:04d}"
        element_ids.append(element_id)
        tags.add(
            CHAP(
                element_id=element_id,
                start_time=int(chapter.start_ms),
                end_time=int(chapter.end_ms),
                start_offset=0xFFFFFFFF,  # 0xFFFFFFFF = "use time, ignore byte offset"
                end_offset=0xFFFFFFFF,
                sub_frames=[TIT2(encoding=3, text=[chapter.title])],
            )
        )
    if element_ids:
        tags.add(
            CTOC(
                element_id="toc",
                flags=CTOCFlags.TOP_LEVEL | CTOCFlags.ORDERED,
                child_element_ids=element_ids,
                sub_frames=[TIT2(encoding=3, text=[toc_title])],
            )
        )
    tags.save(str(path), v2_version=3)


def read_mp3_chapters(path: Path) -> list[Chapter]:
    """Read CHAP frames back from ``path`` (ordered by start time). For verification."""
    from mutagen.id3 import ID3

    tags = ID3(str(path))
    frames = sorted(tags.getall("CHAP"), key=lambda f: f.start_time)
    chapters: list[Chapter] = []
    for index, frame in enumerate(frames):
        title = ""
        title_frame = frame.sub_frames.get("TIT2")
        if title_frame is not None and title_frame.text:
            title = str(title_frame.text[0])
        chapters.append(
            Chapter(
                index=index,
                title=title,
                start_ms=int(frame.start_time),
                end_ms=int(frame.end_time),
            )
        )
    return chapters


class ChapterEditError(ValueError):
    """A chapter edit (merge/split/retime) was not possible; message is speakable."""


def _renumber(chapters: list[Chapter]) -> list[Chapter]:
    return [replace(c, index=i) for i, c in enumerate(chapters)]


def merge_chapter(chapters: list[Chapter], index: int) -> list[Chapter]:
    """Remove the marker at *index*, merging that chapter into its neighbour.

    The first chapter merges into the second (the first title is kept); any
    other chapter merges into the previous one. Audio is never removed — only
    the marker goes away. Ported from ChapterForge's editor.
    """
    n = len(chapters)
    if n < 2:
        raise ChapterEditError("There must be at least two chapters to merge.")
    if not 0 <= index < n:
        raise ChapterEditError("No chapter is selected.")
    if index == 0:
        merged = replace(chapters[0], end_ms=chapters[1].end_ms)
        result = [merged, *chapters[2:]]
    else:
        prev = replace(chapters[index - 1], end_ms=chapters[index].end_ms)
        result = [*chapters[: index - 1], prev, *chapters[index + 1 :]]
    return _renumber(result)


def split_chapter(
    chapters: list[Chapter],
    at_ms: int,
    *,
    title: str = "New chapter",
    min_part_ms: int = 1000,
) -> list[Chapter]:
    """Insert a new boundary at *at_ms* — the split-at-playhead operation.

    The chapter containing *at_ms* is cut in two; the left half keeps the
    original title, the right half gets *title*. Raises
    :class:`ChapterEditError` when the point is not inside a chapter or would
    leave a sliver shorter than *min_part_ms* on either side.
    """
    for i, c in enumerate(chapters):
        if c.start_ms < at_ms < c.end_ms:
            if at_ms - c.start_ms < min_part_ms or c.end_ms - at_ms < min_part_ms:
                raise ChapterEditError("That split point is too close to a chapter boundary.")
            left = replace(c, end_ms=at_ms)
            right = Chapter(
                index=i + 1, title=title or "New chapter", start_ms=at_ms, end_ms=c.end_ms
            )
            return _renumber([*chapters[:i], left, right, *chapters[i + 1 :]])
    raise ChapterEditError("The split point is not inside a chapter.")


def set_chapter_start(
    chapters: list[Chapter],
    index: int,
    new_start_ms: int,
    *,
    min_part_ms: int = 500,
) -> list[Chapter]:
    """Retime chapter *index*'s start (and the previous chapter's end).

    Chapters stay contiguous and ordered; the new start must leave at least
    *min_part_ms* of both the previous chapter and this one.
    """
    if not 0 <= index < len(chapters):
        raise ChapterEditError("No chapter is selected.")
    if index == 0:
        raise ChapterEditError("The first chapter must start at the beginning.")
    lo = chapters[index - 1].start_ms + min_part_ms
    hi = chapters[index].end_ms - min_part_ms
    if not lo <= new_start_ms <= hi:
        from quill.core.speech.chapter_io import format_timestamp

        raise ChapterEditError(
            f"Start must be between {format_timestamp(lo)} and {format_timestamp(hi)}."
        )
    prev = replace(chapters[index - 1], end_ms=new_start_ms)
    cur = replace(chapters[index], start_ms=new_start_ms)
    return _renumber([*chapters[: index - 1], prev, cur, *chapters[index + 1 :]])


def clamp_chapters(chapters: list[Chapter], total_ms: int) -> list[Chapter]:
    """Clamp chapters to ``[0, total_ms]``, dropping any that fall entirely outside.

    Guards a plan against a re-encode that shortened the audio (or an imported
    list from a different edit of the file): starts/ends are clamped, empty
    chapters are dropped, and the final chapter is extended to *total_ms* so
    the whole timeline stays covered.
    """
    if total_ms <= 0:
        return []
    kept: list[Chapter] = []
    for c in chapters:
        start = max(0, min(c.start_ms, total_ms))
        end = max(0, min(c.end_ms, total_ms))
        if end > start:
            kept.append(replace(c, start_ms=start, end_ms=end))
    if kept:
        kept[-1] = replace(kept[-1], end_ms=total_ms)
    return _renumber(kept)


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
