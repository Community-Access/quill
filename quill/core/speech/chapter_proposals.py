"""Chapters proposed from silences, kept honest about being guesses.

Item 42 of the 2026-10-16 checklist ("automatic chapters for local audio").
The silence scan itself is :mod:`quill.core.speech.silence`; this module is
the policy around its answer, wx-free and strict-typed:

* **A guess is labelled a guess.** Every proposed chapter is titled
  "Proposed chapter 1", "Proposed chapter 2" and so on -- never "Chapter 1",
  which is what an author would have written and what the scan used to call
  them. Rename the ones you keep; the word "Proposed" is how a listener
  scrolling the list later can still tell which titles nobody chose.
* **The user's chapters are never silently replaced.** A recording that
  already has chapters of its own (two or more -- a file with no chapter
  marks opens as one chapter spanning the whole file, which is nobody's
  choice) gets :func:`merge_proposals`: every existing chapter kept with its
  title and start, and a proposed boundary added only where it is at least
  :data:`MIN_GAP_MS` from every existing one. Replacing them is the
  Workbench's other answer, and only when asked.
* **A long recording gets time to finish.** :func:`scan_timeout_seconds`
  grows with the recording, because a fixed ten-minute ceiling stopped the
  scan of a long lecture or an all-day recording part-way through.
"""

from __future__ import annotations

from collections.abc import Sequence

from quill.core.speech.chapters import Chapter

__all__ = [
    "MIN_GAP_MS",
    "PROPOSED_TITLE",
    "has_authored_chapters",
    "merge_proposals",
    "retitle_as_proposed",
    "scan_timeout_seconds",
]

#: What a proposed chapter is called until somebody renames it.
PROPOSED_TITLE = "Proposed chapter"

#: A proposed boundary this close to one of the user's own is the same place.
MIN_GAP_MS = 10_000

#: The fixed ceiling the scan used to have, kept as the floor.
_MIN_TIMEOUT_S = 600.0

#: ffmpeg's silencedetect decodes far faster than real time; one tenth of the
#: recording's length is a generous ceiling on a slow machine.
_REALTIME_FRACTION = 0.1


def has_authored_chapters(chapters: Sequence[Chapter]) -> bool:
    """True when the list is somebody's work: two or more chapters."""
    return len(chapters) >= 2


def retitle_as_proposed(
    chapters: Sequence[Chapter], *, title: str = PROPOSED_TITLE
) -> list[Chapter]:
    """The proposal, renumbered from 0 and titled as the guesses they are."""
    return [
        Chapter(index=i, title=f"{title} {i + 1}", start_ms=c.start_ms, end_ms=c.end_ms)
        for i, c in enumerate(chapters)
    ]


def merge_proposals(
    existing: Sequence[Chapter],
    proposed: Sequence[Chapter],
    total_ms: int,
    *,
    min_gap_ms: int = MIN_GAP_MS,
    title: str = PROPOSED_TITLE,
) -> list[Chapter]:
    """Keep every existing chapter; add proposed boundaries that are new.

    Returns a contiguous list over ``[0, total_ms]``: each chapter ends where
    the next begins. Existing titles and starts are untouched; added chapters
    are numbered "Proposed chapter 1, 2, ..." in time order.
    """
    starts = [c.start_ms for c in existing]
    added = sorted({
        p.start_ms
        for p in proposed
        if 0 < p.start_ms < total_ms and all(abs(p.start_ms - s) >= min_gap_ms for s in starts)
    })
    marks: list[tuple[int, str]] = [(c.start_ms, c.title) for c in existing]
    marks.extend((start, f"{title} {n}") for n, start in enumerate(added, start=1))
    marks.sort(key=lambda mark: mark[0])
    merged: list[Chapter] = []
    for i, (start, name) in enumerate(marks):
        end = marks[i + 1][0] if i + 1 < len(marks) else total_ms
        merged.append(Chapter(index=i, title=name, start_ms=start, end_ms=end))
    return merged


def scan_timeout_seconds(total_ms: int) -> float:
    """How long the silence scan may run for a recording *total_ms* long."""
    return max(_MIN_TIMEOUT_S, total_ms / 1000.0 * _REALTIME_FRACTION)
