"""Auto-detection of a BRF document's braille code (table).

The user should never have to know whether a file is UEB Grade 2, UEB
Grade 1, legacy American (EBAE) Grade 1/2, or computer braille -- QUILL
back-translates a sample of the document through every candidate table (one
worker launch; see braille_worker's "detect" command) and scores how much
each result looks like English text. The best-scoring table wins and the
detection is announced, so the user learns what their file is instead of
being asked.

Scoring is pure and unit-testable: no subprocess, no liblouis.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

#: Candidate tables tried against every sample, with human-readable labels.
#: Order matters only for tie-breaks: earlier wins a tie, and contracted UEB
#: is by far the most common code for real-world BRF files.
CANDIDATE_TABLES: tuple[tuple[str, str], ...] = (
    ("en-ueb-g2", "UEB Grade 2 (contracted)"),
    ("en-ueb-g1", "UEB Grade 1 (uncontracted)"),
    ("en-us-g2", "Standard American Grade 2 (EBAE, legacy)"),
    ("en-us-g1", "Standard American Grade 1 (EBAE, legacy)"),
    ("en-us-comp8", "Computer braille (8-dot)"),
)

#: How much of the document to sample. Enough lines to be statistically
#: meaningful, small enough that five back-translations stay instant.
_SAMPLE_CHARS = 1600

# ~250 of the highest-frequency English words. Big enough that real English
# scores decisively, small enough to embed. All lowercase.
_COMMON_WORDS = frozenset(
    """
    the be to of and a in that have i it for not on with he as you do at this
    but his by from they we say her she or an will my one all would there
    their what so up out if about who get which go me when make can like time
    no just him know take people into year your good some could them see
    other than then now look only come its over think also back after use two
    how our work first well way even new want because any these give day most
    us is was are been has had were said did having may am shall being
    such where why before through between under never here more very still
    own too old tell ask men call left last long great little own while
    might down should each right went came again off need house home
    world school water room mother father hand eye word side head night
    life man woman child children boy girl book read write page line story
    part place thing name found live away found every another much many
    against three four five six seven eight nine ten hundred thousand
    once always together during without example enough almost began around
    however toward until above along both few those something nothing
    anything everything himself herself itself yourself course rather
    """.split()
)

_WORD_RE = re.compile(r"[a-zA-Z']+")


@dataclass(frozen=True, slots=True)
class BrailleDetection:
    """The winning table plus everything needed to explain the choice."""

    table: str
    label: str
    score: float
    #: (table, label, score) for every candidate that produced output,
    #: best first -- surfaced in logs / detailed announcements.
    ranking: tuple[tuple[str, str, float], ...]


def score_backtranslation(text: str) -> float:
    """Score how much *text* looks like real English prose (0.0 .. 1.0).

    Blend of two signals, both defensible without a dictionary the size of
    a spell checker: the fraction of tokens that are common English words
    (weight 0.7 -- the decisive signal; a wrong-table back-translation
    produces word-shaped garbage that misses this list almost entirely),
    and the fraction of word characters among non-space characters (weight
    0.3 -- punishes outputs full of stray punctuation/symbol noise).
    """
    if not text or not text.strip():
        return 0.0
    tokens = _WORD_RE.findall(text.lower())
    if not tokens:
        return 0.0
    common_hits = sum(1 for token in tokens if token in _COMMON_WORDS)
    word_ratio = common_hits / len(tokens)
    non_space = [ch for ch in text if not ch.isspace()]
    if not non_space:
        return 0.0
    letters = sum(1 for ch in non_space if ch.isalpha() or ch == "'")
    clean_ratio = letters / len(non_space)
    return 0.7 * word_ratio + 0.3 * clean_ratio


def build_sample(brf_text: str, *, limit: int = _SAMPLE_CHARS) -> str:
    """A detection sample: the first *limit* chars of non-blank lines.

    Skips leading blank/decorative lines (title pages are often centered,
    sparse, and full of proper nouns -- poor detection material) in favor of
    running text, but keeps whatever exists when the file is short.
    """
    lines = [line for line in brf_text.splitlines() if line.strip()]
    if not lines:
        return ""
    # Prefer body text: skip the first few lines when there is plenty more.
    start = 4 if len(lines) > 12 else 0
    sample = "\n".join(lines[start:])
    return sample[:limit] if len(sample) > limit else sample


#: Contracted table -> its uncontracted sibling (for the G1-vs-G2 rule below).
_UNCONTRACTED_SIBLING: dict[str, str] = {
    "en-ueb-g2": "en-ueb-g1",
    "en-us-g2": "en-us-g1",
}


def rank_candidates(results: dict[str, str]) -> list[tuple[str, str, float]]:
    """Score every candidate back-translation, best first (pure, testable)."""
    labels = dict(CANDIDATE_TABLES)
    order = {table: i for i, (table, _) in enumerate(CANDIDATE_TABLES)}
    scored = [
        (table, labels.get(table, table), score_backtranslation(text))
        for table, text in results.items()
    ]
    # Higher score first; candidate-list order breaks ties (contracted UEB
    # is the most common real-world code, and it is listed first).
    scored.sort(key=lambda item: (-item[2], order.get(item[0], 99)))
    return scored


def pick_best(results: dict[str, str]) -> tuple[str, str, float, list[tuple[str, str, float]]]:
    """Rank candidates and apply the uncontracted-preference rule.

    Uncontracted (Grade 1) braille is *also* valid input to the Grade 2
    table -- with no contraction cells present, both back-translations come
    out byte-identical and score identically, and a naive tie-break would
    label every Grade 1 file "Grade 2". When the winning table is contracted
    and its uncontracted sibling produced the exact same text, the file is
    effectively uncontracted, and saying so is the honest answer.
    """
    ranking = rank_candidates(results)
    if not ranking:
        return ("", "", 0.0, ranking)
    labels = dict(CANDIDATE_TABLES)
    table, label, score = ranking[0]
    sibling = _UNCONTRACTED_SIBLING.get(table)
    if sibling and results.get(sibling) == results.get(table):
        table, label = sibling, labels.get(sibling, sibling)
    return (table, label, score, ranking)


def detect_braille_table(brf_text: str, *, timeout: float = 30.0) -> BrailleDetection:
    """Detect the braille code of *brf_text* via one worker round trip.

    Raises :class:`quill.core.braille_worker_client.WorkerError` (or a
    subclass) when the worker cannot run or no candidate produced output --
    the same error surface callers already handle for translation itself.
    """
    from quill.core import braille_worker_client as worker

    sample = build_sample(brf_text)
    if not sample:
        raise worker.WorkerError("The document has no text to detect a braille code from.")
    results = worker.detect_backtranslations(
        sample, tables=[table for table, _ in CANDIDATE_TABLES], timeout=timeout
    )
    best_table, best_label, best_score, ranking = pick_best(results)
    if not best_table:
        raise worker.WorkerError("No candidate braille table produced a back-translation.")
    return BrailleDetection(
        table=best_table,
        label=best_label,
        score=best_score,
        ranking=tuple(ranking),
    )
