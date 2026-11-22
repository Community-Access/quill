"""Narration from Scribe for Documents: chapter markers from the DAISY navigation (PRD 8.5).

QUILL Studio's "Narration from Scribe for Documents..." asks Scribe for MP3
audio and DAISY (text and audio). The DAISY book's navigation says where each
heading starts in its audio; when the book has one audio file, and it is as
long as the MP3 (Scribe makes both from the same speech), those times become
chapter markers written into the MP3 itself (ID3 CHAP frames, in place: the
audio is not touched). The marked file is the one the Scribe library records,
so My Scribe Documents and Beacon still find it.

When the markers cannot be trusted -- several DAISY audio files, a length that
does not match, a navigation that cannot be read -- nothing is written, and
the reason is a phrase the one result sentence carries ("with no chapter
markers, because the DAISY book has 4 audio files"), never a second message.

wx-free.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from quill.core.speech.chapters import Chapter

#: How far the DAISY audio's length may differ from the MP3's and still be
#: the same speech: two seconds, or one percent of a long book.
_SLACK_MS = 2_000
_SLACK_SHARE = 0.01


@dataclass(frozen=True, slots=True)
class Markers:
    """What :func:`mark_narration` did: how many chapters, or why none."""

    count: int = 0
    reason: str = ""

    @property
    def phrase(self) -> str:
        """For the result sentence: ``with 12 chapter markers``."""
        if self.count:
            noun = "chapter marker" if self.count == 1 else "chapter markers"
            return f"with {self.count} {noun}"
        return f"with no chapter markers, because {self.reason}" if self.reason else ""


def daisy_chapters(ncx: Path) -> tuple[list[Chapter], list[str]]:
    """The DAISY book's headings as chapters of its one audio file, and every
    audio file it names (in reading order). Chapters are empty when the book
    has more or fewer than one audio file."""
    from quill.core.media import parse_ncx, resolve_heading_times

    root = ncx.parent

    def load_smil(name: str) -> str | None:
        candidate = root / name
        if not candidate.is_file():
            return None
        return candidate.read_text(encoding="utf-8", errors="replace")

    headings = parse_ncx(ncx.read_text(encoding="utf-8", errors="replace"))
    resolved = resolve_heading_times(headings, load_smil)
    timed = [h for h in resolved if h.time_ms is not None and h.audio_src]
    files: list[str] = []
    for heading in timed:
        if heading.audio_src not in files:
            files.append(heading.audio_src)
    if len(files) != 1:
        return [], files
    ordered = sorted(timed, key=lambda h: int(h.time_ms or 0))
    chapters: list[Chapter] = []
    for index, heading in enumerate(ordered):
        start = int(heading.time_ms or 0)
        end = int(ordered[index + 1].time_ms or start) if index + 1 < len(ordered) else start
        title = " ".join((heading.title or "").split()) or f"Heading {index + 1}"
        chapters.append(Chapter(index=index, title=title, start_ms=start, end_ms=end))
    return chapters, files


def mark_narration(mp3: Path, ncx: Path) -> Markers:
    """Write the DAISY book's headings into *mp3* as chapter markers.

    Idempotent: an MP3 that already carries more than one chapter is left as
    it is and its count is reported.
    """
    from quill.core.speech.book_file import BookReadError, read_book, save_mp3_book
    from quill.core.speech.ffmpeg import probe_duration_ms

    try:
        book = read_book(mp3)
    except BookReadError:
        return Markers(reason="the MP3 could not be read")
    if len(book.chapters) > 1:
        return Markers(count=len(book.chapters))
    try:
        chapters, files = daisy_chapters(ncx)
    except Exception:  # noqa: BLE001 - a navigation we cannot read gives no markers
        return Markers(reason="its DAISY navigation could not be read")
    if len(files) > 1:
        return Markers(reason=f"the DAISY book has {len(files)} audio files")
    if len(chapters) < 2:
        return Markers(reason="the DAISY book has no headings with times")
    try:
        daisy_ms = probe_duration_ms(ncx.parent / files[0])
    except Exception:  # noqa: BLE001 - no length to compare means no trust
        daisy_ms = 0
    total = book.total_ms
    if total <= 0 or daisy_ms <= 0 or abs(daisy_ms - total) > max(_SLACK_MS, total * _SLACK_SHARE):
        return Markers(reason="the DAISY timings do not match the MP3")
    last = chapters[-1]
    chapters[-1] = Chapter(index=last.index, title=last.title, start_ms=last.start_ms, end_ms=total)
    book.chapters = [c for c in chapters if c.start_ms < total]
    try:
        save_mp3_book(book)
    except Exception:  # noqa: BLE001 - said in the sentence, never raised into the queue
        return Markers(reason="the markers could not be written")
    return Markers(count=len(book.chapters))


__all__ = ["Markers", "daisy_chapters", "mark_narration"]
