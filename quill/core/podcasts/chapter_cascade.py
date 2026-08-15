"""Every tier runs, and the **best** answer wins -- not the first.

The old cascade ran the tiers in cost order and stopped at the first one that
returned anything. That is right for authored sources and wrong for inferred
ones: a weak-but-non-empty transcript segmentation permanently hid a better
silence scan, and nothing could compare two answers because nothing scored one.

So:

* every tier returns a scored :class:`~quill.core.podcasts.chapter_scoring.ChapterAnswer`;
* the cascade runs the tiers the **budget** allows and keeps the best;
* a low-confidence transcript answer no longer suppresses the audio scan;
* below a floor, the honest answer stays "no chapters could be found".

**Authored still beats inferred, always.** A published list, chapter frames in
the file, timestamps in the show notes, or a marked soundbite were written by a
person, and no
heuristic produces titles worth more than that -- so those short-circuit as they
always did, and the scoring only decides between machine-derived answers.

**Nothing here is ever computed twice.** In priority order, stopping at the first
hit: the feed's chapters document, chapter frames in the downloaded file,
timestamps in the show notes, the moments the publisher marked with
``podcast:soundbite``, a cached result from a previous run keyed by
episode *and* the audio file's size and mtime (so replacing the file recomputes
and re-downloading the same file does not). An episode under ``MIN_EPISODE_MS``
never runs anything at all.

wx-free, strict-typed. Every expensive tier is a callable the caller supplies, so
this module never touches the network, ffmpeg or a speech engine itself -- and is
therefore testable with no fixtures beyond a list of chapters.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from quill.core.podcasts.chapter_scoring import (
    SOURCE_FILE_TAGS,
    SOURCE_PUBLISHED,
    SOURCE_SHOW_NOTES,
    SOURCE_SILENCE,
    SOURCE_SOUNDBITES,
    SOURCE_TRANSCRIPT,
    ChapterAnswer,
    apply_scores,
    best,
    score,
)
from quill.core.podcasts.chapters import PodcastChapter
from quill.core.podcasts.inference_budget import InferenceBudget

#: Under ten minutes, an episode does not have chapters worth finding, and the
#: cheapest way to be fast is not to start.
MIN_EPISODE_MS = 10 * 60 * 1000

#: One tier: what it is called, and how to ask it. Every one returns a list of
#: chapters or raises; a raise is "no answer", never a failure worth surfacing,
#: because a tier that cannot run is a tier the cascade simply does without.
Tier = Callable[[], list[PodcastChapter]]


@dataclass(slots=True)
class CascadeInputs:
    """Everything the cascade may ask, as callables it may decline to call.

    Callables rather than values so nothing expensive happens for an episode
    whose answer arrived from a cheaper tier -- which is the overwhelming
    majority of them.
    """

    published: Tier | None = None
    file_tags: Tier | None = None
    show_notes: Tier | None = None
    #: ``podcast:soundbite`` marks from the feed. Authored -- a person chose the
    #: moment and titled it -- so it short-circuits like the three above, but it
    #: is asked last of them because a highlight is not a partition.
    soundbites: Tier | None = None
    cached: Callable[[], ChapterAnswer | None] | None = None
    transcript: Tier | None = None
    fetch_transcript: Tier | None = None
    silence_scan: Tier | None = None
    total_ms: int = 0
    #: How far below its own threshold the segmenter's boundaries sat, where it
    #: reported one -- the only evidence that tier has about its own quality.
    cohesion_margin: float = 0.0
    #: What each tier examined, for the report: "48 minutes of audio".
    examined: dict[str, str] = field(default_factory=dict)


def _try(tier: Tier | None) -> list[PodcastChapter]:
    """Run one tier. Any failure is "no answer" rather than an error."""
    if tier is None:
        return []
    try:
        return [chapter for chapter in tier() if chapter.title]
    except Exception:  # noqa: BLE001 - a tier that cannot run is one we do without
        return []


def _authored(
    inputs: CascadeInputs, source: str, tier: Tier | None, *, floor: int = 2
) -> ChapterAnswer | None:
    """An authored tier's answer, or ``None``. Two chapters is the floor.

    Except for soundbites, where the floor is one: a single marked moment is
    still a place worth jumping to, and the label says it is a highlight rather
    than a chapter list, so nothing is being overclaimed by offering it.
    """
    chapters = _try(tier)
    if len(chapters) < floor:
        return None
    return apply_scores(
        score(
            chapters,
            source,
            total_ms=inputs.total_ms,
            examined=inputs.examined.get(source, ""),
        ),
        total_ms=inputs.total_ms,
    )


def run(inputs: CascadeInputs, budget: InferenceBudget) -> ChapterAnswer:
    """The whole cascade. Returns the best answer the budget allowed."""
    if inputs.total_ms and inputs.total_ms < MIN_EPISODE_MS:
        return ChapterAnswer()

    # 1-4: authored. First hit wins outright -- a person wrote these.
    for source, tier, floor in (
        (SOURCE_PUBLISHED, inputs.published, 2),
        (SOURCE_FILE_TAGS, inputs.file_tags, 2),
        (SOURCE_SHOW_NOTES, inputs.show_notes, 2),
        (SOURCE_SOUNDBITES, inputs.soundbites, 1),
    ):
        answer = _authored(inputs, source, tier, floor=floor)
        if answer is not None:
            return answer

    # 4: a previous run's result. Never recomputed, and the cache itself is
    # keyed on the audio file's stamp, so this cannot outlive its episode.
    if inputs.cached is not None:
        try:
            cached = inputs.cached()
        except Exception:  # noqa: BLE001
            cached = None
        if cached is not None and cached.is_useful:
            return cached

    # 5+: inferred. Every tier the budget allows runs, and the best wins --
    # this is the change. A weak segmentation no longer hides a better scan.
    answers: list[ChapterAnswer] = []

    transcript_chapters = _try(inputs.transcript)
    if not transcript_chapters and budget.may_fetch_transcript:
        # The single biggest gap in the old cascade: an episode that published a
        # perfectly good transcript URL nobody had opened fell straight through
        # to the slow audio scan. The best free answer available was skipped.
        transcript_chapters = _try(inputs.fetch_transcript)
    if transcript_chapters:
        answers.append(
            apply_scores(
                score(
                    transcript_chapters,
                    SOURCE_TRANSCRIPT,
                    total_ms=inputs.total_ms,
                    cohesion_margin=inputs.cohesion_margin,
                    examined=inputs.examined.get(SOURCE_TRANSCRIPT, ""),
                ),
                total_ms=inputs.total_ms,
            )
        )

    if budget.may_scan_audio:
        silence_chapters = _try(inputs.silence_scan)
        if silence_chapters:
            answers.append(
                apply_scores(
                    score(
                        silence_chapters,
                        SOURCE_SILENCE,
                        total_ms=inputs.total_ms,
                        examined=inputs.examined.get(SOURCE_SILENCE, ""),
                    ),
                    total_ms=inputs.total_ms,
                )
            )

    return best(answers)


def announce(answer: ChapterAnswer) -> str:
    """What to say when a scan finishes -- politely, and only once.

    Short on purpose. "12 sections found in this episode" is the whole message;
    the list is there when it is wanted. Never an interruption, and never at all
    if the listener has moved on to something else -- which is the caller's
    judgement, not this function's.
    """
    if not answer.chapters:
        return "No chapters could be found in this episode."
    count = len(answer.chapters)
    if answer.is_authored:
        return f"{count} chapter{'' if count == 1 else 's'} found."
    return f"{count} section{'' if count == 1 else 's'} found in this episode."


def working_label(base: str = "Chapters") -> str:
    """The menu item's text while a scan is running.

    **Disabled and explained beats enabled and does nothing.** A screen reader
    reads the item's own text, so putting the state *in the label* means it is
    heard as part of the item rather than having to be discovered.
    """
    return f"{base} (working them out...)"


MID_SCAN_REPLY = "Chapters are being worked out. I will say when they are ready."
