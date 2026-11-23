"""Narration from Scribe for Documents: chapter markers from the DAISY navigation (PRD 8.5).

QUILL Studio's "Narration from Scribe for Documents..." asks Scribe for MP3
audio and DAISY (text and audio). The DAISY book's navigation says where each
heading starts in its audio, and those times become chapter markers written
into the MP3 itself (ID3 CHAP frames, in place: the audio is not touched). The
marked file is the one the Scribe library records, so My Scribe Documents and
Beacon still find it.

**One audio file.** A heading's time is its time in the MP3, when that file
is as long as the MP3 (Scribe makes both from the same speech).

**Split audio** (what Scribe writes: one MP3 per paragraph or section, F3).
The MP3 is those files played one after another, so a heading starts at the
length of every file before its own plus its time in its own file. Each
file's length is the end of its last clip in the SMIL, in the book's reading
order (the OPF spine). Scribe's MP3 leaves out the spoken title the DAISY
book starts with (its first audio file, the ``docTitle``): measured on
Pneuma's corpus, 4 books of 4, the MP3 is exactly that much shorter and starts
with the second file. So both readings are tried, with and without the first
file, and the one whose length matches the MP3 is used; a heading in the
left-out file starts at the beginning.

When the markers cannot be trusted -- a length that matches neither reading,
a navigation that cannot be read -- nothing is written, and the reason is a
phrase the one result sentence carries ("with no chapter markers, because the
DAISY timings do not match the MP3"), never a second message.

wx-free.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

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


def _timed_headings(ncx: Path) -> list[Any]:
    """The book's headings that resolve to an audio file and a time."""
    from quill.core.media import parse_ncx, resolve_heading_times

    root = ncx.parent

    def load_smil(name: str) -> str | None:
        candidate = root / name
        if not candidate.is_file():
            return None
        return candidate.read_text(encoding="utf-8", errors="replace")

    headings = parse_ncx(ncx.read_text(encoding="utf-8", errors="replace"))
    resolved = resolve_heading_times(headings, load_smil)
    return [h for h in resolved if h.time_ms is not None and h.audio_src]


def _audio_files(timed: list[Any]) -> list[str]:
    files: list[str] = []
    for heading in timed:
        if heading.audio_src not in files:
            files.append(heading.audio_src)
    return files


def _chapters(starts: list[tuple[int, str]], total_ms: int) -> list[Chapter]:
    """Chapters from ``(start, title)``, in time order. Two headings at one
    time are one chapter, named by the later (the more particular) heading."""
    by_time: dict[int, str] = {}
    for start, title in sorted(starts, key=lambda item: item[0]):
        by_time[start] = title
    ordered = sorted(by_time.items())
    chapters: list[Chapter] = []
    for index, (start, title) in enumerate(ordered):
        end = ordered[index + 1][0] if index + 1 < len(ordered) else max(start, total_ms)
        name = " ".join((title or "").split()) or f"Heading {index + 1}"
        chapters.append(Chapter(index=index, title=name, start_ms=start, end_ms=end))
    return chapters


def daisy_chapters(ncx: Path) -> tuple[list[Chapter], list[str]]:
    """The DAISY book's headings as chapters of its one audio file, and every
    audio file it names (in reading order). Chapters are empty when the book
    has more or fewer than one audio file: :func:`split_offsets` places those."""
    timed = _timed_headings(ncx)
    files = _audio_files(timed)
    if len(files) != 1:
        return [], files
    starts = [(int(h.time_ms or 0), h.title) for h in timed]
    ordered = sorted(starts, key=lambda item: item[0])
    last = ordered[-1][0] if ordered else 0
    return _chapters(starts, last), files


# -- split audio ---------------------------------------------------------------


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _smil_order(ncx: Path, timed: list[Any]) -> list[str]:
    """The SMIL files in reading order: the OPF spine, else the navigation's order."""
    from quill.core.safe_xml import fromstring

    for opf in sorted(ncx.parent.glob("*.opf")):
        try:
            root = fromstring(opf.read_bytes())
        except Exception:  # noqa: BLE001 - an unreadable package falls back to the navigation
            continue
        hrefs = {
            str(el.get("id", "")): str(el.get("href", ""))
            for el in root.iter()
            if _local(el.tag) == "item"
        }
        spine = [
            hrefs.get(str(el.get("idref", "")), "")
            for el in root.iter()
            if _local(el.tag) == "itemref"
        ]
        smils = [href for href in spine if href.lower().endswith(".smil")]
        if smils:
            return smils
    order: list[str] = []
    for heading in timed:
        name = heading.src.partition("#")[0]
        if name and name not in order:
            order.append(name)
    return order


def _file_lengths(ncx: Path, smils: list[str]) -> list[tuple[str, int]]:
    """Every audio file the book plays, in reading order, with its length:
    the end of its last clip."""
    from quill.core.media.daisy import parse_clip_ms
    from quill.core.safe_xml import fromstring

    lengths: dict[str, int] = {}
    for name in smils:
        root = fromstring((ncx.parent / name).read_bytes())
        for el in root.iter():
            if _local(el.tag) != "audio":
                continue
            src = str(el.get("src", "") or "")
            end = parse_clip_ms(str(el.get("clipEnd") or el.get("clip-end") or ""))
            if not src or end is None:
                continue
            lengths[src] = max(lengths.get(src, 0), end)
    return list(lengths.items())


def split_offsets(ncx: Path, timed: list[Any], total_ms: int) -> dict[str, int] | None:
    """Where each audio file starts in the MP3 of *total_ms*, or ``None`` when
    the DAISY lengths match it neither with nor without the first file."""
    sequence = _file_lengths(ncx, _smil_order(ncx, timed))
    if not sequence or total_ms <= 0:
        return None
    whole = sum(length for _name, length in sequence)
    first = sequence[0][1]
    readings = [(abs(whole - total_ms), 0)]
    if len(sequence) > 1:
        readings.append((abs(whole - first - total_ms), first))
    error, skipped = min(readings)
    if error > max(_SLACK_MS, total_ms * _SLACK_SHARE):
        return None
    offsets: dict[str, int] = {}
    elapsed = 0
    for name, length in sequence:
        offsets[name] = max(0, elapsed - skipped)
        elapsed += length
    return offsets


def _single_file_chapters(ncx: Path, timed: list[Any], total: int) -> list[Chapter] | str:
    """One audio file: its times, when it is as long as the MP3. A reason if not."""
    from quill.core.speech.ffmpeg import probe_duration_ms

    try:
        daisy_ms = probe_duration_ms(ncx.parent / timed[0].audio_src)
    except Exception:  # noqa: BLE001 - no length to compare means no trust
        daisy_ms = 0
    if total <= 0 or daisy_ms <= 0 or abs(daisy_ms - total) > max(_SLACK_MS, total * _SLACK_SHARE):
        return "the DAISY timings do not match the MP3"
    return _chapters([(int(h.time_ms or 0), h.title) for h in timed], total)


def mark_narration(mp3: Path, ncx: Path) -> Markers:
    """Write the DAISY book's headings into *mp3* as chapter markers.

    Idempotent: an MP3 that already carries more than one chapter is left as
    it is and its count is reported.
    """
    from quill.core.speech.book_file import BookReadError, read_book, save_mp3_book

    try:
        book = read_book(mp3)
    except BookReadError:
        return Markers(reason="the MP3 could not be read")
    if len(book.chapters) > 1:
        return Markers(count=len(book.chapters))
    total = book.total_ms
    try:
        timed = _timed_headings(ncx)
        if len({h.time_ms for h in timed}) < 2 and len(_audio_files(timed)) < 2:
            return Markers(reason="the DAISY book has no headings with times")
        if len(_audio_files(timed)) == 1:
            placed = _single_file_chapters(ncx, timed, total)
        else:
            offsets = split_offsets(ncx, timed, total)
            placed = "the DAISY timings do not match the MP3"
            if offsets is not None and all(h.audio_src in offsets for h in timed):
                starts = [(offsets[h.audio_src] + int(h.time_ms or 0), h.title) for h in timed]
                placed = _chapters(starts, total)
    except Exception:  # noqa: BLE001 - a navigation we cannot read gives no markers
        return Markers(reason="its DAISY navigation could not be read")
    if isinstance(placed, str):
        return Markers(reason=placed)
    chapters = [c for c in placed if c.start_ms < total]
    if len(chapters) < 2:
        return Markers(reason="the DAISY book has no headings with times")
    book.chapters = chapters
    try:
        save_mp3_book(book)
    except Exception:  # noqa: BLE001 - said in the sentence, never raised into the queue
        return Markers(reason="the markers could not be written")
    return Markers(count=len(book.chapters))


__all__ = ["Markers", "daisy_chapters", "mark_narration", "split_offsets"]
