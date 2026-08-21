"""Editing a worked-out chapter list -- and what an edit *means*.

The Chapter Review dialog is where a listener checks a set of inferred marks and
fixes the ones that are wrong. These are the operations behind it, kept pure and
wx-free so the rules are testable without a window.

**The rule that matters more than any of the mechanics: a chapter a person edited
is no longer a guess.** Every operation here stamps the row it touches as
:data:`SOURCE_EDITED` with full confidence, because a mark somebody moved to the
right place *is* in the right place, and a list that carried on describing it as
"worked out, 44% sure" would be lying about the best information it has. It also
means the report can say something true and useful -- "nine worked out, three you
corrected" -- which is exactly what somebody wants to know before trusting the
rest.

Two invariants every operation preserves:

* **The list stays sorted and starts at zero.** A chapter list is a partition of
  the episode, not a bag of bookmarks.
* **``end_ms`` is always the next chapter's start**, so "4 of 12, six minutes
  long" stays sayable after an edit, and the last chapter ends with the episode.
"""

from __future__ import annotations

from dataclasses import replace

from quill.core.error_codes import CodedError
from quill.core.podcasts.chapters import PodcastChapter

#: What a chapter's ``source`` becomes once a person has touched it.
SOURCE_EDITED = "edited"

#: How that reads in the list and in the report.
EDITED_LABEL = "you corrected this"

#: Two marks may not be closer together than this. Deliberately small -- this is
#: a hand edit, and somebody who wants a thirty-second chapter has a reason --
#: but not zero, because two marks at the same instant are one mark.
MIN_GAP_MS = 5_000


class ChapterEditError(CodedError):
    """An edit that would leave the list in a state it cannot be in."""

    code = "QUILL-PODCASTS-CHAPTER-EDIT"


def _stamp(chapter: PodcastChapter) -> PodcastChapter:
    """Mark *chapter* as authored by the listener."""
    return replace(chapter, source=SOURCE_EDITED, confidence=1.0, reason=EDITED_LABEL)


def normalise(chapters: list[PodcastChapter], total_ms: int = 0) -> list[PodcastChapter]:
    """Sorted, opening at zero, with every ``end_ms`` following from the next start.

    Called after every operation rather than trusted to callers, because the one
    thing a chapter list cannot survive is being *nearly* ordered.
    """
    rows = sorted((c for c in chapters if c.start_ms >= 0), key=lambda c: c.start_ms)
    if total_ms:
        rows = [c for c in rows if c.start_ms < total_ms]
    if not rows:
        return []
    if rows[0].start_ms != 0:
        rows[0] = replace(rows[0], start_ms=0)
    out: list[PodcastChapter] = []
    for index, chapter in enumerate(rows):
        end = rows[index + 1].start_ms if index + 1 < len(rows) else (total_ms or None)
        out.append(replace(chapter, end_ms=end))
    return out


def retitle(
    chapters: list[PodcastChapter], index: int, title: str, *, total_ms: int = 0
) -> list[PodcastChapter]:
    """Give chapter *index* a new title. An empty title is refused."""
    rows = list(chapters)
    if not 0 <= index < len(rows):
        raise ChapterEditError("No chapter is selected.")
    cleaned = " ".join(title.split())
    if not cleaned:
        raise ChapterEditError("A chapter needs a title.")
    rows[index] = _stamp(replace(rows[index], title=cleaned))
    return normalise(rows, total_ms)


def retime(
    chapters: list[PodcastChapter], index: int, start_ms: int, *, total_ms: int = 0
) -> list[PodcastChapter]:
    """Move chapter *index* to *start_ms*.

    The list is re-sorted afterwards, so dragging a mark past its neighbour
    reorders rather than failing -- somebody who moves a chapter to 40:00 meant
    40:00, and refusing because it is now the fourth rather than the third would
    be pedantry.
    """
    rows = list(chapters)
    if not 0 <= index < len(rows):
        raise ChapterEditError("No chapter is selected.")
    wanted = max(0, int(start_ms))
    if total_ms and wanted >= total_ms:
        raise ChapterEditError("That is past the end of the episode.")
    for position, other in enumerate(rows):
        if position != index and abs(other.start_ms - wanted) < MIN_GAP_MS:
            raise ChapterEditError("There is already a chapter at that point.")
    rows[index] = _stamp(replace(rows[index], start_ms=wanted))
    return normalise(rows, total_ms)


def nudge(
    chapters: list[PodcastChapter], index: int, delta_ms: int, *, total_ms: int = 0
) -> list[PodcastChapter]:
    """Move chapter *index* by *delta_ms*. The common correction, so it is one key.

    An inferred mark is usually *near* right -- the segmenter found the turn and
    put the boundary a few seconds off it. Nudging is how that gets fixed, and it
    has to be cheaper than typing a timestamp or nobody will do it.
    """
    rows = list(chapters)
    if not 0 <= index < len(rows):
        raise ChapterEditError("No chapter is selected.")
    return retime(rows, index, rows[index].start_ms + int(delta_ms), total_ms=total_ms)


def insert(
    chapters: list[PodcastChapter], start_ms: int, title: str, *, total_ms: int = 0
) -> list[PodcastChapter]:
    """Add a chapter at *start_ms*."""
    wanted = max(0, int(start_ms))
    if total_ms and wanted >= total_ms:
        raise ChapterEditError("That is past the end of the episode.")
    if any(abs(c.start_ms - wanted) < MIN_GAP_MS for c in chapters):
        raise ChapterEditError("There is already a chapter at that point.")
    cleaned = " ".join(title.split()) or "New chapter"
    rows = [*chapters, _stamp(PodcastChapter(start_ms=wanted, title=cleaned))]
    return normalise(rows, total_ms)


def remove(
    chapters: list[PodcastChapter], index: int, *, total_ms: int = 0
) -> list[PodcastChapter]:
    """Delete chapter *index*. The opening chapter cannot be deleted, only renamed.

    Because an episode starts whether or not anybody marked it, and a list whose
    first entry is at 6:12 silently claims the first six minutes are not part of
    the programme.
    """
    rows = list(chapters)
    if not 0 <= index < len(rows):
        raise ChapterEditError("No chapter is selected.")
    if len(rows) <= 1:
        raise ChapterEditError("An episode needs at least one chapter.")
    if index == 0:
        raise ChapterEditError("The first chapter cannot be removed, only renamed.")
    del rows[index]
    return normalise(rows, total_ms)


def clock(milliseconds: int) -> str:
    """``1:02:03`` or ``12:34`` -- hours only when there are hours."""
    seconds = max(0, int(milliseconds)) // 1000
    hours, rest = divmod(seconds, 3600)
    minutes, second = divmod(rest, 60)
    return f"{hours}:{minutes:02d}:{second:02d}" if hours else f"{minutes}:{second:02d}"


def parse_clock(text: str) -> int:
    """``12:34`` / ``1:02:03`` / ``754`` -> milliseconds. Raises on anything else."""
    cleaned = text.strip()
    if not cleaned:
        raise ChapterEditError("Enter a time like 12:34 or 1:02:03.")
    parts = cleaned.split(":")
    try:
        numbers = [int(part) for part in parts]
    except ValueError:
        raise ChapterEditError("Enter a time like 12:34 or 1:02:03.") from None
    if any(number < 0 for number in numbers) or len(numbers) > 3:
        raise ChapterEditError("Enter a time like 12:34 or 1:02:03.")
    total = 0
    for number in numbers:
        total = total * 60 + number
    return total * 1000


def preview_window(chapter: PodcastChapter, *, total_ms: int, lead_seconds: int) -> tuple[int, int]:
    """``(from_ms, to_ms)`` to play when checking *chapter*'s mark.

    Symmetrical on purpose. The question a preview answers is "does the
    programme turn *here*", and that can only be judged by hearing the end of
    what came before as well as the start of what comes after -- playing only
    forward from the mark tells you what the section is, not whether the mark is
    in the right place.
    """
    lead = max(1, int(lead_seconds)) * 1000
    start = max(0, chapter.start_ms - lead)
    end = chapter.start_ms + lead
    if total_ms:
        end = min(end, total_ms)
    return start, max(start + 1000, end)


def row_label(chapter: PodcastChapter, index: int, count: int) -> str:
    """One list row, read aloud in full.

    Position, time, length, title, and **how it was arrived at** -- because in a
    list that mixes published marks, worked-out ones and corrections, "which of
    these can I trust" is the first question, and a row that does not answer it
    forces a trip to a properties dialog to find out.
    """
    length = chapter.duration_ms // 1000
    parts = [f"{index + 1} of {count}", clock(chapter.start_ms)]
    if length:
        parts.append(f"{length // 60}m{length % 60:02d}s")
    parts.append(chapter.title or "Untitled")
    if chapter.source == SOURCE_EDITED:
        parts.append(EDITED_LABEL)
    elif chapter.source and chapter.confidence < 1.0:
        parts.append(f"worked out, {round(chapter.confidence * 100)}% sure")
    return " -- ".join(parts)


def summarise(chapters: list[PodcastChapter]) -> str:
    """ "Twelve chapters: nine worked out, three you corrected." """
    if not chapters:
        return "No chapters."
    edited = sum(1 for c in chapters if c.source == SOURCE_EDITED)
    inferred = sum(1 for c in chapters if c.source != SOURCE_EDITED and c.confidence < 1.0)
    authored = len(chapters) - edited - inferred
    bits: list[str] = []
    if authored:
        bits.append(f"{authored} published")
    if inferred:
        bits.append(f"{inferred} worked out")
    if edited:
        bits.append(f"{edited} you corrected")
    count = len(chapters)
    return (
        f"{count} chapter{'' if count == 1 else 's'}: {', '.join(bits)}."
        if bits
        else (f"{count} chapter{'' if count == 1 else 's'}.")
    )
