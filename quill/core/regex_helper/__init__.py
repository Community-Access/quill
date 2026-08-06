"""Regular Expression Helper -- the wx-free core (issue #1328, P1).

Regular expressions are uniquely hostile to screen-reader users: a pattern is
dense punctuation with no words to latch onto, and most regex tools explain it
with diagrams. This package is the accessible alternative -- a recipe catalog
with spoken explanations (:mod:`catalog`), a deterministic plain-language
explain engine (:mod:`explain`), and a bounded, never-raising test runner
(:mod:`runner`) that reports matches by line and column the way a person
navigates a document.

No wx, no network, no AI; strict-typed and safe to call from any thread.
"""

from __future__ import annotations

from quill.core.regex_helper.catalog import (
    CATEGORIES,
    RECIPES,
    RegexRecipe,
    recipes_by_category,
)
from quill.core.regex_helper.explain import ExplainResult, explain_pattern
from quill.core.regex_helper.runner import (
    MatchInfo,
    RunResult,
    preview_replace,
    run_pattern,
)

__all__ = [
    "CATEGORIES",
    "RECIPES",
    "ExplainResult",
    "MatchInfo",
    "RegexRecipe",
    "RunResult",
    "explain_pattern",
    "preview_replace",
    "recipes_by_category",
    "run_pattern",
]
