"""How a chapter is shown and said, everywhere in Cast and Radio.

One house rule, from Jeff (2026-11-27): **the title comes first and the time
follows** -- "Listener mail, 12:34" -- in list rows, show-notes headers, spoken
announcements, Player Information, copied text and file names. A number is a
fact about the list, not about the chapter, so it comes last ("3 of 12"), and a
chapter without a title is "Untitled", never "Chapter 3": a made-up name read
aloud sounds exactly like a real one.

Pure: no wx. The words for a span of time are short on purpose ("4 minutes
10", not "4 minutes and 10 seconds") because they are heard many times an hour.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from quill.core.podcasts.listening_words import clock

__all__ = [
    "UNTITLED",
    "chapter_end_ms",
    "chapter_heading",
    "chapter_index_at",
    "chapter_report_line",
    "chapter_row",
    "chapter_title",
    "position_value",
    "source_phrase",
    "span_words",
    "where_am_i",
]

UNTITLED = "Untitled"

#: A chapter set's source -- either its key or the label Cast keeps -- in the
#: words that follow "from" in a report line.
_SOURCE_PHRASES: dict[str, str] = {
    "published": "from the publisher",
    "published chapters": "from the publisher",
    "file": "from the file",
    "chapters in the file": "from the file",
    "show_notes": "from the show notes",
    "from the show notes": "from the show notes",
    "soundbites": "marked by the podcast",
    "moments this podcast marked": "marked by the podcast",
    "transcript": "from the transcript",
    "from the transcript": "from the transcript",
    "audio": "detected from the audio",
    "detected from the audio": "detected from the audio",
    "suggested": "suggested",
    "published by the uploader": "from the uploader",
}


def chapter_title(chapter: Any) -> str:
    """The chapter's own title, whitespace folded, or "Untitled"."""
    return " ".join(str(getattr(chapter, "title", "") or "").split()) or UNTITLED


def chapter_index_at(chapters: Sequence[Any], position_ms: int) -> int:
    """The index of the chapter playing at *position_ms*, or -1 before the first."""
    current = -1
    for index, chapter in enumerate(chapters):
        if int(getattr(chapter, "start_ms", 0) or 0) <= position_ms:
            current = index
        else:
            break
    return current


def chapter_end_ms(chapters: Sequence[Any], index: int, length_ms: int = 0) -> int:
    """Where chapter *index* ends: its own end, the next start, or the episode's end.

    0 when nothing says (the last chapter of an episode whose length is unknown).
    """
    chapter = chapters[index]
    own = getattr(chapter, "end_ms", None)
    if own:
        return int(own)
    if index + 1 < len(chapters):
        return int(getattr(chapters[index + 1], "start_ms", 0) or 0)
    return max(0, int(length_ms or 0))


def span_words(ms: int) -> str:
    """A length the ear takes in at once: "4 minutes 10", "39 minutes", "50 seconds"."""
    seconds = max(0, int(ms) // 1000)
    hours, rest = divmod(seconds, 3600)
    minutes, secs = divmod(rest, 60)
    if hours:
        words = f"{hours} hour{'s' if hours != 1 else ''}"
        return f"{words} {minutes} minute{'s' if minutes != 1 else ''}" if minutes else words
    if minutes:
        words = f"{minutes} minute{'s' if minutes != 1 else ''}"
        return f"{words} {secs}" if secs else words
    return f"{secs} second{'s' if secs != 1 else ''}"


def chapter_heading(chapter: Any) -> str:
    """ "Listener mail, 12:34": a show-notes header, a copied line, a menu caption."""
    return f"{chapter_title(chapter)}, {clock(int(getattr(chapter, 'start_ms', 0) or 0))}"


def chapter_row(
    chapters: Sequence[Any],
    index: int,
    *,
    length_ms: int = 0,
    playing: bool = False,
    heard: bool = False,
    extra: str = "",
) -> str:
    """ "Listener mail, 12:34, 6 minutes 30, 3 of 12, playing": one list row."""
    chapter = chapters[index]
    parts = [chapter_heading(chapter)]
    end = chapter_end_ms(chapters, index, length_ms)
    start = int(getattr(chapter, "start_ms", 0) or 0)
    if end > start:
        parts.append(span_words(end - start))
    parts.append(f"{index + 1} of {len(chapters)}")
    if playing:
        parts.append("playing")
    if heard:
        parts.append("heard")
    if extra:
        parts.append(extra)
    return ", ".join(parts)


def source_phrase(source: str) -> str:
    """ "from the publisher" for a source key or label; "" when unknown."""
    return _SOURCE_PHRASES.get(" ".join(str(source or "").split()).lower(), "")


def chapter_report_line(chapters: Sequence[Any], index: int, *, source: str = "") -> str:
    """Player Information's line: "Listener mail, 3 of 12, from the publisher"."""
    parts = [chapter_title(chapters[index]), f"{index + 1} of {len(chapters)}"]
    phrase = source_phrase(source)
    if phrase:
        parts.append(phrase)
    return ", ".join(parts)


def position_value(position_ms: int, length_ms: int) -> str:
    """A position slider's spoken value: "12 minutes 34 of 58 minutes"."""
    here = span_words(position_ms)
    if length_ms <= 0:
        return here
    return f"{here} of {span_words(length_ms)}"


def where_am_i(position_ms: int, length_ms: int, chapters: Sequence[Any] = ()) -> str:
    """The where-am-I sentence, chapter first when there is one.

    "Listener mail, 4 minutes 10 into the chapter, 2 minutes 20 left. 18 minutes
    30 of 58 minutes, 39 minutes 30 left."
    """
    sentences: list[str] = []
    index = chapter_index_at(chapters, position_ms) if chapters else -1
    if index >= 0:
        chapter = chapters[index]
        into = position_ms - int(getattr(chapter, "start_ms", 0) or 0)
        words = f"{chapter_title(chapter)}, {span_words(into)} into the chapter"
        end = chapter_end_ms(chapters, index, length_ms)
        if end > position_ms:
            words += f", {span_words(end - position_ms)} left"
        sentences.append(words + ".")
    if length_ms > 0:
        left = max(0, length_ms - position_ms)
        sentences.append(
            f"{span_words(position_ms)} of {span_words(length_ms)}, {span_words(left)} left."
        )
    else:
        sentences.append(f"{span_words(position_ms)} in.")
    return " ".join(sentences)
