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

The reader itself now lives in :mod:`quill.core.speech.reuse_core`, which
is vendored byte-identical into podHarvest so both apps recognise the same
show-note shapes. Everything below is the Cast-shaped face on it: the same
names, re-exported, plus the one function that builds a
:class:`PodcastChapter` with Cast's source and confidence. Fixing a shape
here means fixing it for both apps, which is the point.

wx-free, strict-typed, pure.
"""

from __future__ import annotations

from quill.core.podcasts.chapters import PodcastChapter

#: The most marks a real chapter list has. Beyond this it is a transcript, a
#: tracklist with per-second cues, or a page of times that is not a chapter list.
from quill.core.speech.reuse_core import (
    MAX_FIRST_MARK_MS as MAX_FIRST_MARK_MS,
)
from quill.core.speech.reuse_core import (
    MAX_MARKS as MAX_MARKS,
)
from quill.core.speech.reuse_core import (
    MIN_GAP_MS as MIN_GAP_MS,
)
from quill.core.speech.reuse_core import (
    MIN_MARK_RETENTION as MIN_MARK_RETENTION,
)
from quill.core.speech.reuse_core import (
    looks_like_a_chapter_list as looks_like_a_chapter_list,
)
from quill.core.speech.reuse_core import (
    parse_marks as parse_marks,
)
from quill.core.speech.reuse_core import (
    strip_markup as strip_markup,
)
from quill.core.speech.reuse_core import (
    usable_marks as usable_marks,
)


def chapters_from_notes(*sources: str, total_ms: int = 0) -> list[PodcastChapter]:
    """Chapters from the first of *sources* that yields a real chapter list.

    Several sources on purpose: the description, the summary, and any
    structured notes an episode carries are all places publishers put this, and
    reading only one field was throwing away lists that were right there.
    """
    from quill.core.podcasts.chapter_scoring import SOURCE_SHOW_NOTES, reason_for
    from quill.core.speech.reuse_core import marks_from_notes

    for notes in sources:
        marks = marks_from_notes(notes or "", total_ms=total_ms)
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
