"""The show notes say *what* the sections are; the audio says *where*.

The two halves of the problem have been solved by different sources all along
and nothing joined them up.

* The **transcript** knows where the vocabulary turns. It does not know how many
  turns to expect, and it cannot name them -- so it over-produces and labels
  every section with a quotation from itself.
* The **show notes** name the segments and give their order, written by a
  person. What they almost never give is *times*, which is why
  :func:`quill.core.podcasts.chapter_sources.parse_show_notes_chapters` -- which
  only reads timestamps -- finds nothing at all in most feeds.

Main Menu is the case in point. Not one of its 512 episodes carries a timestamp,
so the authored tier is empty every time. But the descriptions read like this:

    "high school student Tyler Juranek begins a series of short reviews he calls
    Techie Tidbits ... Next, we visit with Gerry Chevalier about the newest
    release of HumanWare's Victor Reader Stream ... After that, we talk with
    Jerry Munden, Vice President of Prodigy ... Finally, Matt Roberts brings us
    part one of a demonstration on accessing DVR from Dish Network"

That is a running order: four segments, named, in sequence. It is worth more
than any heuristic, and it was being thrown away because it had no colons in it.

**The method.** Take each topic phrase from the notes, find where in the
transcript its distinctive words actually *arrive*, and put the boundary there.
Phrases are aligned **in order** -- the notes are written in the order the
programme runs -- which is a sequence-alignment problem, so it is solved with a
monotonic dynamic-programming pass rather than by taking each phrase's best
match independently and hoping they come out sorted.

**Two things this fixes at once:**

* **Over-production.** The notes say how many segments there are. Four described
  segments means four or five chapters, not fourteen.
* **Titles.** Each chapter is named by the phrase that found it -- **written by
  a person**, which is worth more than anything a model would produce and needs
  no model at all. It is the only route to authored titles that involves no AI.

Measured on the hand-referenced episodes in ``labs/chapter-poc``: anchors landed
within 9 and 15 seconds of the true section starts. Where the notes describe two
or more segments the rule is **use them and stop** -- padding the anchors out
with lexical boundaries measurably made the list worse, for the same reason the
cascade short-circuits on an authored source instead of blending it.

wx-free, strict-typed, pure. No network, no ffmpeg, no model.
"""

from __future__ import annotations

import html
import re
from collections.abc import Sequence

from quill.core.podcasts.chapter_inference import TimedCue, _content_words
from quill.core.podcasts.chapters import PodcastChapter

__all__ = [
    "MIN_ANCHORS",
    "anchored_chapters",
    "topic_phrases",
]

#: Lines that are never a topic. Every feed carries some of this, and a phrase
#: matched out of the boilerplate would anchor on the disclaimer read at the top
#: of the hour.
_BOILERPLATE = re.compile(
    r"(?i)(subscribe|follow us|email us|contact us|get in touch|opinions expressed|"
    r"endorsement|@|https?://|www\.|call \d|toll.?free|patreon|donate|"
    r"copyright|all rights reserved)"
)

#: A phrase needs this many usable words before it can be looked for. One
#: content word is a heading, not a description, and it matches everywhere.
_MIN_PHRASE_WORDS = 2

#: More phrases than this and the description is a transcript, an episode index
#: or a sponsor list -- not a running order. Aligning them all is quadratic in an
#: input somebody else controls, so it is bounded.
_MAX_PHRASES = 40

#: How wide a window is scored when looking for a phrase, and how far apart the
#: scoring positions are.
_WINDOW_MS = 180_000
_STEP_MS = 15_000

#: Sections cannot be closer together than this, whatever the notes imply.
_MIN_GAP_MS = 180_000

#: Fewer rows than this is not a running order, and one anchor with nothing
#: after it is not a chapter list worth showing.
MIN_ANCHORS = 2

#: The opening section, which the notes never describe because it is the bit
#: before the first thing they mention.
_OPENING_TITLE = "Opening"

#: A title is the phrase's first words: long enough to say what the segment is,
#: short enough to hear in a list.
_TITLE_WORDS = 10


def topic_phrases(description: str) -> list[str]:
    """The notes as an ordered list of topic phrases.

    Split on sentence ends *and* on the connectives a running order is written
    with -- "next", "after that", "finally", "in the second hour" -- because one
    sentence often carries two segments.
    """
    text = re.sub(r"(?i)<\s*br\s*/?>", "\n", description or "")
    text = re.sub(r"(?i)</\s*(p|div|li|tr|h[1-6])\s*>", "\n", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text)

    pieces = re.split(
        r"(?i)(?<=[.!?])\s+|\s*[\r\n]+\s*|"
        r"\s+(?=next,|then,|after that,|finally,|later,|also,|"
        r"in (?:the|our) (?:second|first) hour)",
        text,
    )
    phrases: list[str] = []
    for piece in pieces:
        cleaned = piece.strip(" \t*-–—•")
        if not cleaned or _BOILERPLATE.search(cleaned):
            continue
        if len(_content_words(cleaned)) < _MIN_PHRASE_WORDS:
            continue
        phrases.append(cleaned)
        if len(phrases) >= _MAX_PHRASES:
            break
    return phrases


def _episode_frequency(cues: Sequence[TimedCue]) -> tuple[dict[str, int], int]:
    counts: dict[str, int] = {}
    for cue in cues:
        for word in _content_words(cue.text):
            counts[word] = counts.get(word, 0) + 1
    return counts, sum(counts.values())


def _phrase_scores(
    phrase: str,
    cues: Sequence[TimedCue],
    positions: Sequence[int],
    frequency: dict[str, int],
    corpus_total: int,
) -> list[float]:
    """Where *phrase*'s subject **starts**, scored at each position.

    The obvious version of this -- score how strongly the phrase matches inside
    a window and take the best -- was measurably wrong, and wrong in a way worth
    recording. A thirty-five minute interview mentions its guest most often in
    the *middle*, so matching on density anchored one episode's main segment at
    30:00 when it actually began at 1:09. Density finds where a topic **is**; a
    chapter needs where it **begins**.

    So the score is a difference: how much of the phrase appears in the window
    *after* a position, minus how much appears in the window *before* it. That
    peaks exactly at the moment the subject arrives, and it is near zero both in
    the middle of the segment and everywhere the subject is absent.

    Words are weighted by how rare they are in this episode, so "Victor Reader
    Stream" carries the match and "the new release" contributes nothing. A word
    counts once per window however often it repeats -- five mentions of one name
    should not outweigh three different names all being present.
    """
    wanted = {word for word in _content_words(phrase) if frequency.get(word, 0) > 0}
    if not wanted:
        return []
    weights = {
        word: 1.0 / (frequency.get(word, 1) / max(1, corpus_total) + 1e-5) for word in wanted
    }

    def _presence(low: int, high: int) -> float:
        present: set[str] = set()
        for cue in cues:
            if cue.start_ms < low:
                continue
            if cue.start_ms >= high:
                break
            present.update(word for word in _content_words(cue.text) if word in wanted)
        return sum(weights[word] for word in present)

    scores: list[float] = []
    for start in positions:
        after = _presence(start, start + _WINDOW_MS)
        before = _presence(max(0, start - _WINDOW_MS), start)
        scores.append(after - before)
    return scores


def _align(
    phrases: Sequence[str], cues: Sequence[TimedCue], total_ms: int
) -> list[tuple[int, str, float]]:
    """Assign each phrase a position, **in order**, maximising the total match.

    A monotonic alignment rather than independent best matches: the notes are
    written in running order, so an assignment that puts phrase three before
    phrase two is wrong however well the words match.

    **Ties go to the later position.** The onset score is flat across every
    position whose window straddles the moment the subject arrives -- up to a
    whole window's worth of them -- and the earliest of those is a boundary
    placed before a single word of the segment has been spoken. A chapter that
    starts early makes the previous section run past its own end, which is the
    worse of the two errors to hear.
    """
    frequency, corpus_total = _episode_frequency(cues)
    if not frequency:
        return []
    positions = list(range(0, max(1, total_ms - _WINDOW_MS), _STEP_MS))
    rows: list[list[float]] = []
    kept: list[str] = []
    for phrase in phrases:
        scored = _phrase_scores(phrase, cues, positions, frequency, corpus_total)
        if scored:
            rows.append(scored)
            kept.append(phrase)
    if not rows:
        return []

    count = len(positions)
    gap = max(1, _MIN_GAP_MS // _STEP_MS)
    unset = float("-inf")
    best = [[unset] * count for _ in rows]
    back = [[-1] * count for _ in rows]
    best[0] = list(rows[0])
    for row in range(1, len(rows)):
        running_best = unset
        running_arg = -1
        for index in range(count):
            candidate = index - gap
            if candidate >= 0:
                value = best[row - 1][candidate]
                if value != unset and value >= running_best:
                    running_best = value
                    running_arg = candidate
            if running_arg >= 0:
                best[row][index] = rows[row][index] + running_best
                back[row][index] = running_arg

    top = max(best[-1])
    if top == unset:
        return []
    last = max(index for index, value in enumerate(best[-1]) if value == top)
    chain = [last]
    for row in range(len(rows) - 1, 0, -1):
        last = back[row][last]
        if last < 0:
            return []
        chain.append(last)
    chain.reverse()
    return [(positions[index], kept[row], rows[row][index]) for row, index in enumerate(chain)]


def _title_for(phrase: str) -> str:
    return " ".join(phrase.split()[:_TITLE_WORDS])


def anchored_chapters(
    description: str, cues: Sequence[TimedCue], total_ms: int
) -> list[PodcastChapter]:
    """Chapters whose *titles* the publisher wrote and whose *times* were found.

    Returns an empty list -- never a partial answer -- unless the notes describe
    at least :data:`MIN_ANCHORS` segments and each of them lands somewhere the
    words actually support. An empty list is the honest reading of "these notes
    are a paragraph about the show, not a running order".
    """
    if total_ms <= 0 or not cues:
        return []
    phrases = topic_phrases(description)
    if len(phrases) < MIN_ANCHORS:
        return []
    anchored = _align(phrases, cues, total_ms)
    if not anchored:
        return []

    rows: list[PodcastChapter] = [PodcastChapter(start_ms=0, title=_OPENING_TITLE)]
    for start_ms, phrase, phrase_score in anchored:
        if phrase_score <= 0 or start_ms - rows[-1].start_ms < _MIN_GAP_MS:
            continue
        rows.append(PodcastChapter(start_ms=start_ms, title=_title_for(phrase)))
    if len(rows) < MIN_ANCHORS:
        return []
    return rows
