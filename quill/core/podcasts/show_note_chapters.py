"""Reading chapter timestamps out of show notes, the way people actually write them.

**The biggest unclaimed win in the whole chapter cascade**, and it costs nothing:
a publisher who bothered to write chapter timestamps has *already done the work*,
and the words beside each timestamp are a **title a person wrote**. That makes
this the only cheap tier whose titles are authored -- worth more than anything
inferred, at no cost and no delay.

The previous reader recognised one shape: ``12:34 Topic`` at the start of a line.
Real show notes are far more various than that, and every shape it missed was a
free, authored chapter list thrown away:

* ``00:00``, ``0:00:00``, ``1:02:03``, and the same inside ``(...)`` or ``[...]``
* ``12.34`` -- a point instead of a colon, which is common
* ``1h05m``, ``1 hr 5 min``, ``5m30s``
* a leading index or bullet: ``1. 00:00 Introduction``
* **the timestamp at the end of the line**: ``Introduction — 00:00`` is at least
  as common as the other way round, and was previously invisible
* **HTML**, since show notes usually arrive as markup rather than text

Three rules that keep it honest:

* **The words next to the timestamp are the title.** Not the opening words of the
  section's transcript -- an actual title, written by a person, describing what
  the part is about.
* **A list that does not look like a chapter list is refused.** Fewer than two,
  implausibly many, starting an hour in, or mostly out of order: each of those
  is a page that merely *contains* times, and returning it would be a confident
  wrong answer.
* **One bad mark loses that mark, not the list.** This is the rule the previous
  reader got wrong, and it was expensive. Double Tap ends every episode with a
  "Contact Us" sign-off about twenty seconds from the end; an all-or-nothing
  minimum-gap check therefore threw away all ten of its authored chapters over
  the last one. A row that cannot be part of a chapter list is dropped and the
  rest are kept -- but only while the great majority survive, because a list
  that needs most of itself repaired was never a chapter list.

wx-free, strict-typed, pure.
"""

from __future__ import annotations

import html
import re

from quill.core.podcasts.chapters import PodcastChapter

#: The most marks a real chapter list has. Beyond this it is a transcript, a
#: tracklist with per-second cues, or a page of times that is not a chapter list.
MAX_MARKS = 120

#: Two marks closer together than this are not two chapters. Half a minute --
#: the same floor the old reader used, deliberately: the defect there was never
#: this number, it was that failing it discarded the *whole list* instead of the
#: one offending mark. Keeping the floor strict and dropping only the bad row
#: rejects "00:00 One / 00:05 Two / 00:10 Three" (which is not a chapter list)
#: while keeping a ten-chapter list whose last entry is a twenty-second outro.
MIN_GAP_MS = 30_000

#: A chapter list that does not begin near the beginning is not this episode's
#: chapter list -- it is a schedule, a set of references, or somebody's notes.
MAX_FIRST_MARK_MS = 20 * 60 * 1000

#: How much of a list may be repaired before it stops being a list at all.
#: Dropping the odd unusable row is tidying; dropping a third of them means the
#: page was never a chapter list and the survivors are a coincidence.
MIN_MARK_RETENTION = 0.8

#: ``1:02:03`` / ``12:34`` / ``12.34`` -- colon or point separated.
_CLOCK = r"(?:(?P<h>\d{1,2})[:.])?(?P<m>\d{1,2})[:.](?P<s>\d{2})"

#: ``1h05m``, ``1 hr 5 min``, ``5m30s``, ``90s`` -- the spelled-out forms.
_SPELLED = (
    r"(?:(?P<sh>\d{1,2})\s*(?:h|hr|hrs|hour|hours)\s*)?"
    r"(?:(?P<sm>\d{1,3})\s*(?:m|min|mins|minute|minutes)\s*)?"
    r"(?:(?P<ss>\d{1,2})\s*(?:s|sec|secs|second|seconds))?"
)

_LEAD = r"^[\s\-\*•–—>]*(?:\d{1,3}[\.\)]\s*)?[\[\(]?"
_TRAIL = r"[\]\)]?"
_SEP = r"(?:\s*[-–—:\|]\s*|\s+)"

#: Timestamp first: "00:00 Introduction", "1. [1:02:03] - The interview".
_LEADING = re.compile(_LEAD + _CLOCK + _TRAIL + _SEP + r"(?P<title>\S.*?)\s*$")
_LEADING_SPELLED = re.compile(_LEAD + _SPELLED + _TRAIL + _SEP + r"(?P<title>\S.*?)\s*$")

#: Timestamp last: "Introduction — 00:00", "The interview (1:02:03)".
_TRAILING = re.compile(
    r"^[\s\-\*•–—>]*(?P<title>.*?\S)" + _SEP + r"[\[\(]?" + _CLOCK + r"[\]\)]?\s*$"
)


def _clock_ms(hours: str | None, minutes: str, seconds: str) -> int:
    return ((int(hours or 0) * 60 + int(minutes)) * 60 + int(seconds)) * 1000


def _spelled_ms(hours: str | None, minutes: str | None, seconds: str | None) -> int:
    if not any((hours, minutes, seconds)):
        return -1
    return ((int(hours or 0) * 60 + int(minutes or 0)) * 60 + int(seconds or 0)) * 1000


def strip_markup(notes: str) -> str:
    """Show notes as lines of text, whether they arrived as HTML or as text.

    Show notes are *usually* markup, and a reader that only handled text was
    skipping most of the internet. Block tags become line breaks so a
    ``<li>00:00 Intro</li>`` list reads as one timestamp per line, which is what
    the line-oriented matching below assumes.
    """
    if "<" not in notes:
        return notes
    text = re.sub(r"(?i)<\s*br\s*/?>", "\n", notes)
    text = re.sub(r"(?i)</\s*(p|div|li|tr|h[1-6])\s*>", "\n", text)
    text = re.sub(r"(?i)<\s*(p|div|li|tr|h[1-6])[^>]*>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    return html.unescape(text)


def _mark_from_line(line: str) -> tuple[int, str] | None:
    """``(start_ms, title)`` for one line, or ``None``.

    Leading timestamps are tried before trailing ones: a line with a time at both
    ends is far more likely to be "00:00 Intro (2 min)" than a title ending in a
    time, and the leading form is the one that means what it looks like.
    """
    stripped = line.strip()
    if not stripped:
        return None
    for pattern in (_LEADING, _TRAILING):
        match = pattern.match(stripped)
        if match is None:
            continue
        title = (match.group("title") or "").strip(" -–—:|\t.")
        if not title:
            continue
        return _clock_ms(match.group("h"), match.group("m"), match.group("s")), title
    match = _LEADING_SPELLED.match(stripped)
    if match is not None:
        milliseconds = _spelled_ms(match.group("sh"), match.group("sm"), match.group("ss"))
        title = (match.group("title") or "").strip(" -–—:|\t.")
        if milliseconds >= 0 and title:
            return milliseconds, title
    return None


def parse_marks(notes: str) -> list[tuple[int, str]]:
    """Every timestamped line in *notes*, in the order written. No validation."""
    if not notes or not notes.strip():
        return []
    marks: list[tuple[int, str]] = []
    for line in strip_markup(notes).replace("\r", "\n").split("\n"):
        mark = _mark_from_line(line)
        if mark is not None:
            marks.append(mark)
    return marks


def usable_marks(marks: list[tuple[int, str]], *, total_ms: int = 0) -> list[tuple[int, str]]:
    """The marks that can be this episode's chapters, or ``[]`` for none.

    Rows are dropped, not the list: a mark that runs past the end of the
    episode, or that arrives too soon after the one before it, is discarded and
    the rest are kept. That single change is worth more than every pattern this
    module recognises -- an outro sign-off twenty seconds from the end used to
    cost a publisher all ten of their authored chapters.

    The whole list is still refused when it was never a chapter list: fewer than
    two usable marks, implausibly many, a first mark an hour in, or so much
    repair needed that the survivors are a coincidence rather than a structure.
    """
    if len(marks) < 2 or len(marks) > MAX_MARKS:
        return []
    if marks[0][0] > MAX_FIRST_MARK_MS:
        return []

    kept: list[tuple[int, str]] = []
    for start_ms, title in marks:
        if total_ms and start_ms >= total_ms:
            continue
        # Strictly after the last mark kept, and far enough after it to be a
        # different chapter. This drops both an out-of-order row and a crammed
        # one, which are the same defect seen from two directions.
        if kept and start_ms - kept[-1][0] < MIN_GAP_MS:
            continue
        kept.append((start_ms, title))

    if len(kept) < 2 or len(kept) < MIN_MARK_RETENTION * len(marks):
        return []
    return kept


def looks_like_a_chapter_list(marks: list[tuple[int, str]], *, total_ms: int = 0) -> bool:
    """Whether these marks are this episode's chapters rather than merely times.

    Each refusal has a page behind it: a set of references with times, a
    schedule, a transcript with per-line cues. Returning any of them as chapters
    would be a confident wrong answer, which is the one output this refuses to
    produce.
    """
    return bool(usable_marks(marks, total_ms=total_ms))


def chapters_from_notes(*sources: str, total_ms: int = 0) -> list[PodcastChapter]:
    """Chapters from the first of *sources* that yields a real chapter list.

    Several sources on purpose: the description, the summary, and any structured
    notes an episode carries are all places publishers put this, and reading only
    one field was throwing away lists that were right there.
    """
    from quill.core.podcasts.chapter_scoring import SOURCE_SHOW_NOTES, reason_for

    for notes in sources:
        marks = usable_marks(parse_marks(notes or ""), total_ms=total_ms)
        if not marks:
            continue
        rows: list[PodcastChapter] = []
        for index, (start_ms, title) in enumerate(marks):
            end_ms = marks[index + 1][0] if index + 1 < len(marks) else (total_ms or None)
            rows.append(
                PodcastChapter(
                    start_ms=start_ms,
                    title=title,
                    end_ms=end_ms,
                    source=SOURCE_SHOW_NOTES,
                    confidence=1.0,
                    reason=reason_for(SOURCE_SHOW_NOTES),
                )
            )
        return rows
    return []
