"""How good is a chapter list, and which of two answers is better?

The missing primitive in the chapter cascade. Until now the tiers ran in cost
order and the **first** one to return anything won -- so a weak-but-non-empty
transcript segmentation permanently hid a better silence scan, and nothing could
compare two answers because nothing scored one.

This is the score. Three things it has to be:

* **Cheap**, because it runs on every answer from every tier.
* **Explainable**, because the *"How were these found?"* report says what the
  confidence was and a number nobody can account for is worse than no number.
* **Conservative**, because the honest answer for a bad segmentation is "no
  chapters could be found", and a scorer that flatters its input removes the
  ability to say that.

Published chapters are 1.0 by definition -- a person wrote them, and no
heuristic gets to second-guess that. Everything else earns its number.

wx-free, strict-typed, pure.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from quill.core.podcasts.chapters import PodcastChapter

#: Where each tier's answer comes from. Carried on every chapter and reported.
SOURCE_PUBLISHED = "published"
SOURCE_FILE_TAGS = "file tags"
SOURCE_SHOW_NOTES = "show notes"
#: ``podcast:soundbite`` -- the moments the publisher marked as worth hearing.
#: Authored, because a person chose them and wrote their titles, but ranked
#: below the three above because soundbites are *highlights, not a partition*:
#: two of them in an hour is a complete and correct answer to "what is the good
#: bit" and a poor answer to "how is this episode laid out". Which is why they
#: only win when nothing better was published.
SOURCE_SOUNDBITES = "soundbites"
#: The publisher's own running order, matched to where each topic arrives in
#: the words. The *titles* were written by a person and the *times* were
#: worked out, which is why it sits below the four sources that carry both
#: and above the two that carry neither.
SOURCE_NOTE_ANCHORS = "show notes and audio"
SOURCE_TRANSCRIPT = "transcript"
SOURCE_SILENCE = "silence scan"

#: How each source is described to a listener. Full sentences, because these
#: appear in the report and in the chapter list's own labelling.
SOURCE_LABELS: dict[str, str] = {
    SOURCE_PUBLISHED: "published by the podcast",
    SOURCE_FILE_TAGS: "read from the audio file's own chapter marks",
    SOURCE_SHOW_NOTES: "read from timestamps in the show notes",
    SOURCE_SOUNDBITES: "the moments this podcast marked as worth hearing",
    SOURCE_NOTE_ANCHORS: (
        "matched from the running order in the show notes to where each topic starts"
    ),
    SOURCE_TRANSCRIPT: "worked out from the transcript, where the topic changed",
    SOURCE_SILENCE: "worked out by listening for pauses in the audio",
}

#: Confidence a tier's answer starts from, before the shape of the answer
#: adjusts it. Authored sources sit at the top because a person wrote them.
BASE_CONFIDENCE: dict[str, float] = {
    SOURCE_PUBLISHED: 1.0,
    SOURCE_FILE_TAGS: 0.95,
    SOURCE_SHOW_NOTES: 0.9,
    SOURCE_SOUNDBITES: 0.85,
    SOURCE_NOTE_ANCHORS: 0.7,
    SOURCE_TRANSCRIPT: 0.5,
    SOURCE_SILENCE: 0.35,
}

#: Below this, an answer is not worth showing at all. "No chapters could be
#: found" is a good answer, and the code already says it well.
MIN_USEFUL_CONFIDENCE = 0.2


@dataclass(frozen=True, slots=True)
class ChapterAnswer:
    """One tier's answer: what it found, where from, and how sure it is."""

    chapters: tuple[PodcastChapter, ...] = ()
    source: str = ""
    confidence: float = 0.0
    #: What was examined to produce it, for the report -- "48 minutes of audio",
    #: "1,240 transcript lines". Empty when the tier has nothing to say.
    examined: str = ""

    @property
    def is_useful(self) -> bool:
        return bool(self.chapters) and self.confidence >= MIN_USEFUL_CONFIDENCE

    @property
    def is_authored(self) -> bool:
        """Whether a person wrote these titles, rather than a machine deriving them."""
        return self.source in {
            SOURCE_PUBLISHED,
            SOURCE_FILE_TAGS,
            SOURCE_SHOW_NOTES,
            SOURCE_SOUNDBITES,
            SOURCE_NOTE_ANCHORS,
        }


def evenness(chapters: Sequence[PodcastChapter], total_ms: int) -> float:
    """How evenly spaced the boundaries are, 0.0 to 1.0.

    Not because even chapters are better -- a real episode has an eight-minute
    interview and a forty-second ad read -- but because a **wildly** uneven
    answer is the signature of a bad segmentation: one enormous section and six
    slivers is what a scan produces when it found noise rather than structure.
    """
    if len(chapters) < 2 or total_ms <= 0:
        return 0.0
    starts = [c.start_ms for c in chapters]
    lengths = [b - a for a, b in zip(starts, [*starts[1:], total_ms], strict=True)]
    lengths = [max(0, length) for length in lengths]
    if not lengths or not any(lengths):
        return 0.0
    mean = sum(lengths) / len(lengths)
    if mean <= 0:
        return 0.0
    variance = sum((length - mean) ** 2 for length in lengths) / len(lengths)
    spread = float(variance) ** 0.5
    # Coefficient of variation, inverted and clamped: 0 spread is 1.0, and a
    # spread as large as the mean is 0.0.
    return float(max(0.0, min(1.0, 1.0 - (spread / mean))))


def score(
    chapters: Sequence[PodcastChapter],
    source: str,
    *,
    total_ms: int = 0,
    cohesion_margin: float = 0.0,
    examined: str = "",
) -> ChapterAnswer:
    """Turn one tier's chapters into a scored answer.

    *cohesion_margin* is how far below its own threshold the transcript
    segmenter's accepted boundaries sat -- it already computes the mean and the
    spread, so this costs it nothing to return, and it is the only evidence that
    tier has about whether it found real structure or noise.
    """
    rows = [c for c in chapters if c is not None]
    if not rows:
        return ChapterAnswer(source=source, confidence=0.0, examined=examined)

    confidence = BASE_CONFIDENCE.get(source, 0.3)

    if source in {SOURCE_TRANSCRIPT, SOURCE_SILENCE}:
        # An inferred answer is judged on its shape. A single boundary in a long
        # episode says almost nothing; a hundred says the detector was chasing
        # noise. The sweet spot is deliberately wide, because real episodes vary.
        count = len(rows)
        if count < 2:
            confidence *= 0.4
        elif count > 40:
            confidence *= 0.6
        confidence *= 0.7 + 0.3 * evenness(rows, total_ms)
        # The segmenter's own margin, where it has one: boundaries that sat well
        # below the cohesion threshold are boundaries it was confident about.
        confidence *= 1.0 + max(0.0, min(0.5, cohesion_margin))

    confidence = max(0.0, min(1.0, confidence))
    return ChapterAnswer(
        chapters=tuple(rows), source=source, confidence=confidence, examined=examined
    )


def apply_scores(answer: ChapterAnswer, *, total_ms: int = 0) -> ChapterAnswer:
    """Stamp source, confidence, end and reason onto every chapter in *answer*.

    So a chapter carries its own provenance wherever it ends up -- a set that
    was merged, filtered or handed to a UI keeps knowing where each row came
    from, which is what the report reads.
    """
    rows = list(answer.chapters)
    if not rows:
        return answer
    stamped: list[PodcastChapter] = []
    for index, chapter in enumerate(rows):
        end_ms = rows[index + 1].start_ms if index + 1 < len(rows) else (total_ms or None)
        stamped.append(
            PodcastChapter(
                start_ms=chapter.start_ms,
                title=chapter.title,
                image_url=chapter.image_url,
                link_url=chapter.link_url,
                end_ms=chapter.end_ms if chapter.end_ms is not None else end_ms,
                source=chapter.source or answer.source,
                confidence=(
                    chapter.confidence
                    if chapter.source and chapter.source != answer.source
                    else answer.confidence
                ),
                reason=chapter.reason or reason_for(answer.source),
            )
        )
    return ChapterAnswer(
        chapters=tuple(stamped),
        source=answer.source,
        confidence=answer.confidence,
        examined=answer.examined,
    )


def reason_for(source: str) -> str:
    """Why a chapter is where it is, in words."""
    return SOURCE_LABELS.get(source, "worked out from the episode")


def best(answers: Sequence[ChapterAnswer]) -> ChapterAnswer:
    """The best of several answers -- **not** the first.

    This is the whole point of scoring. An authored answer always beats an
    inferred one however confident the inference is, because a person wrote the
    titles and no heuristic produces titles worth more than that. Among answers
    of the same kind, confidence decides.
    """
    usable = [answer for answer in answers if answer.is_useful]
    if not usable:
        return ChapterAnswer()
    return max(usable, key=lambda a: (a.is_authored, a.confidence, len(a.chapters)))


def describe(answer: ChapterAnswer) -> str:
    """The *"How were these found?"* report, in sentences rather than a table.

    For this audience the transparency matters more than most: an inferred
    chapter list is a claim, and this is how somebody checks it. Never a chart.
    """
    if not answer.chapters:
        return "No chapters could be found for this episode."
    count = len(answer.chapters)
    how = SOURCE_LABELS.get(answer.source, "worked out from the episode")
    lines = [
        f"{count} chapter{'' if count == 1 else 's'}, {how}.",
    ]
    if answer.examined:
        lines.append(f"Examined: {answer.examined}.")
    if answer.source == SOURCE_NOTE_ANCHORS:
        lines.append(
            "The titles come from the running order this podcast published, so a person "
            "wrote them. Where each one starts was worked out from the words."
        )
    elif answer.is_authored:
        lines.append("A person wrote these titles, so they say what each part is about.")
    else:
        lines.append(
            f"Confidence {round(answer.confidence * 100)}%. "
            "These were worked out rather than published, so the titles describe "
            "the words used rather than the subject."
        )
    return " ".join(lines)
