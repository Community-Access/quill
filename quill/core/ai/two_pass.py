"""Two-pass observe-then-rewrite for small-local-model summarize/describe (#1320).

Idea adopted from HomerScribe: small vision/text models hallucinate less when
you split the work. Pass 1 *observes* -- it extracts concrete facts from the
source. Pass 2 *rewrites* those observations into concise output under an
explicit word budget, **without the source in front of it**, so the model can
only reword what it already extracted rather than inventing interpretation.

Both prompts are pure and unit-tested here; the two backend calls and the
opt-in / local-only gating live in :class:`quill.core.ai.assistant.Assistant`.
A single-pass escape hatch preserves speed on slow CPUs.
"""

from __future__ import annotations

#: Default output ceiling for the rewrite pass. Deliberately modest -- the point
#: of the second pass is a tight, faithful summary, not a long one.
DEFAULT_WORD_BUDGET = 150


def observe_prompt(text: str, *, kind: str = "text") -> str:
    """Pass 1: extract plain observations from the source, no interpretation."""
    return (
        f"Read the following {kind} and list the concrete observations and facts it "
        "contains, one per line, as plain statements. Do not interpret, judge, "
        "summarize, or add anything that is not actually present.\n\n"
        f"{kind.capitalize()}:\n{text}"
    )


def rewrite_prompt(
    observations: str, *, word_budget: int = DEFAULT_WORD_BUDGET, output: str = "summary"
) -> str:
    """Pass 2: rewrite the observations into a budgeted output, source unseen."""
    if word_budget < 1:
        raise ValueError("word_budget must be at least 1")
    return (
        f"Using ONLY the observations below, write a {output} of at most "
        f"{word_budget} words. Include nothing that is not in the observations; do "
        f"not speculate or embellish. Return only the {output}, with no preamble.\n\n"
        f"Observations:\n{observations}"
    )


def word_count(text: str) -> int:
    """Whitespace word count (how the budget is measured)."""
    return len(text.split())


def within_budget(text: str, word_budget: int) -> bool:
    return word_count(text) <= word_budget
