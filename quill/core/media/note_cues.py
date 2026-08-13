"""Speaking a bookmark's note when playback reaches it (x.md item 4).

Local audio already has positioned, note-bearing marks --
:class:`quill.core.media.bookmarks.MediaBookmark`, one atomic JSON file keyed by
the book's resume key. What it never had is the half that makes them useful
while you are *listening* rather than while you are managing a list: playback
arriving at 14:32 and the note you left there being read to you.

That is the whole of this module. It deliberately adds no storage: a second
store for "notes on local audio" would duplicate the one that already exists,
and the two would drift.

**Why this is not a range check.** The naive version -- "any mark between the
last position and this one" -- behaves correctly during playback and appallingly
everywhere else. Drag the scrubber across an hour and it reads out every note it
passed. Skip back ten seconds and it repeats one you just heard. Pause, and the
repeating position reports announce the same note forever. Each of those turns
the feature into something people switch off, so each is a rule here and a test
beside it.
"""

from __future__ import annotations

from quill.core.media.bookmarks import MediaBookmark

#: A gap larger than this between two position reports is a seek, not playback.
#:
#: The player reports roughly once a second. Two seconds of slack absorbs a
#: dropped tick or a busy moment on the UI thread without ever mistaking a
#: scrubber drag -- which can cross an hour in a single report -- for listening.
MAX_PLAYBACK_ADVANCE_MS = 2_000


def cues_reached(
    marks: list[MediaBookmark],
    previous_ms: int,
    current_ms: int,
    *,
    max_advance_ms: int = MAX_PLAYBACK_ADVANCE_MS,
) -> list[MediaBookmark]:
    """The note-bearing marks playback just crossed, earliest first.

    A mark counts as reached when it sits in ``(previous_ms, current_ms]`` --
    half-open at the start so each is announced exactly once, closed at the end
    so one landing precisely on the current tick is not missed.

    Marks with no note are skipped: a bookmark is a place to jump to, and
    announcing "bookmark" with nothing to say would be noise. Only a mark you
    actually wrote something on has something to speak.

    Returns nothing when playback has not moved forward (covering pause and
    seeking backwards) or when the jump exceeds *max_advance_ms* (a seek).
    """
    if current_ms <= previous_ms:
        return []
    if current_ms - previous_ms > max_advance_ms:
        return []
    crossed = [
        mark for mark in marks if mark.note.strip() and previous_ms < mark.position_ms <= current_ms
    ]
    return sorted(crossed, key=lambda mark: mark.position_ms)


def announcement_for(mark: MediaBookmark) -> str:
    """What a screen reader says when playback reaches *mark*.

    Prefixed with its label when it has one, so a note left on "Chapter 4" says
    so; prefixed with "Note" otherwise, because a bare sentence spoken over an
    audiobook sounds like part of the book.

    No timestamp: you are *at* that moment, so saying it aloud is noise -- and a
    spoken ``14:32`` is ambiguous anyway, which is why the rest of the audio
    stack speaks "3 minutes 10 seconds" rather than "3:10" (rule A-8).
    """
    label = mark.label.strip()
    return f"{label}: {mark.note.strip()}" if label else f"Note: {mark.note.strip()}"
