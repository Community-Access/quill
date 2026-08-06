"""Deterministic output-quality shaping for small local models (#1319).

QUILL's free-AI-for-everyone path leans on small on-device models (llama.cpp,
Apple Foundation Models) whose failure modes are consistent and cheap to catch
without a second model call:

* **hedging** ("it seems", "arguably") that softens prose into mush,
* **editorializing** ("clearly", "obviously") that a rewrite/summary should not
  add, and
* **filler openers** ("In today's world", "It is important to note") that pad
  without informing.

Two complementary techniques, both pure text — no provider or model changes,
consistent with the no-hardcoded-model-lists rule:

1. :func:`negative_examples_block` — a few *wrong then corrected* pairs to put
   in the prompt. The HomerScribe finding QUILL adopts here: on small models,
   examples beat instructions ("He looks furious." -> "He clenches his fist.").
2. :func:`find_quality_issues` + :func:`retry_instruction` — a deterministic
   post-filter over the model's own output; a hit names the offending phrases
   for a single, cheap retry, with no second model call needed to *judge*.

Everything here is pure and unit-tested; the wiring (local-backend gate, one
retry) lives in :mod:`quill.core.ai.assistant`.
"""

from __future__ import annotations

import re

#: Hedges that drain confidence from generated prose. Distinctive phrases only
#: -- bare common words like "may"/"might" are excluded to avoid false hits on
#: legitimate source content.
HEDGING_PHRASES: tuple[str, ...] = (
    "it seems",
    "it appears that",
    "arguably",
    "it could be argued",
    "one could argue",
    "one might argue",
    "somewhat",
    "kind of",
    "sort of",
)

#: Editorializing / judgment adverbs a neutral rewrite or summary must not add.
JUDGMENT_WORDS: tuple[str, ...] = (
    "clearly",
    "obviously",
    "of course",
    "undoubtedly",
    "certainly",
    "surely",
    "needless to say",
)

#: Padding openers that announce writing instead of doing it.
FILLER_OPENERS: tuple[str, ...] = (
    "in today's world",
    "in this day and age",
    "it is important to note",
    "it's important to note",
    "it is worth noting",
    "it's worth noting",
    "as we all know",
    "at the end of the day",
    "first and foremost",
    "when it comes to",
)

#: Wrong -> corrected pairs that teach the same lessons by example (small models
#: learn more from these than from bare rules).
NEGATIVE_EXAMPLE_PAIRS: tuple[tuple[str, str], ...] = (
    ("He looks furious.", "He clenches his fist."),
    ("In today's world, technology is important.", "Technology shapes daily life."),
    ("It seems that the results were positive.", "The results were positive."),
    ("Clearly, this is the best approach.", "This is the best approach."),
    ("It is important to note that the deadline is Friday.", "The deadline is Friday."),
)


def _all_terms() -> tuple[str, ...]:
    return HEDGING_PHRASES + JUDGMENT_WORDS + FILLER_OPENERS


def _pattern_for(term: str) -> re.Pattern[str]:
    # Word-boundary match so "surely" never fires inside "surely" != "insurely"
    # and multi-word phrases match across a single run of whitespace.
    escaped = r"\s+".join(re.escape(word) for word in term.split())
    return re.compile(rf"(?<!\w){escaped}(?!\w)", re.IGNORECASE)


_COMPILED: tuple[tuple[str, re.Pattern[str]], ...] = tuple(
    (term, _pattern_for(term)) for term in _all_terms()
)


def find_quality_issues(text: str) -> list[str]:
    """Return the distinctive low-quality phrases present in *text*.

    Deterministic and case-insensitive; each offending term is reported once,
    in a stable order (hedging, then judgment, then filler). "" when clean.
    """
    if not text or not text.strip():
        return []
    found: list[str] = []
    for term, pattern in _COMPILED:
        if pattern.search(text) and term not in found:
            found.append(term)
    return found


def retry_instruction(issues: list[str]) -> str:
    """A one-line instruction naming the offending phrases, for a single retry.

    Empty when there is nothing to fix, so the caller can treat "" as "no
    retry needed".
    """
    if not issues:
        return ""
    quoted = ", ".join(f'"{issue}"' for issue in issues)
    return (
        "Revise your previous answer to remove these weakening words and phrases: "
        f"{quoted}. Keep the same meaning and roughly the same length -- just cut "
        "the hedging, editorializing, and filler. Return only the revised text."
    )


def negative_examples_block() -> str:
    """A compact prompt block of wrong -> corrected pairs (teach by example)."""
    lines = ["Follow the style of these corrections (avoid the 'weak' form):"]
    for weak, better in NEGATIVE_EXAMPLE_PAIRS:
        lines.append(f'- Weak: "{weak}"  Better: "{better}"')
    return "\n".join(lines)
