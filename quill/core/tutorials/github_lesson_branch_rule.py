"""D8's branch rule lesson: protect a branch, read its rules, clear it (GH-R-105).

It runs on ``quill-practice``, between giving someone access and the API
Console. The rule is made with Configure Branch Protection, the row Enter runs
in the repository's Settings > Branch Protection place, and read back on the
branch's own Protection page and in Settings > Rulesets. The last step takes
the rule off, so the practice repository is as it was. GitHub protects a
private repository's branches only on a paid plan, so the Apply step says
what a refusal means.
"""

from __future__ import annotations

from quill.core.github.practice_repository import PRACTICE_NAME
from quill.core.tutorials.github_lessons import (
    GITHUB_TRACK_ID,
    _go_practice,
    _open_workbench,
    _wb,
)
from quill.core.tutorials.model import Step, Tutorial

__all__ = ["branch_rule_lesson"]

_SURFACES = ("GitHub Workbench",)


def branch_rule_lesson() -> Tutorial:
    """D8's branch rule: protect main on the practice repository, then clear it."""
    return Tutorial(
        slug="github-branch-rule",
        title="Protect a branch",
        track=GITHUB_TRACK_ID,
        minutes=6,
        surfaces=_SURFACES,
        summary=(
            "Make a rule that main takes changes only through a reviewed pull request, "
            "read the rules a branch has, and take the rule off again."
        ),
        steps=(
            _open_workbench(),
            _go_practice(),
            _wb(
                "go_settings",
                title="Go to Settings",
                body=(
                    "Settings holds the repository's own rules. You can change them because "
                    "the practice repository is yours."
                ),
                hear="Settings.",
            ),
            Step(
                title="Open Branch Protection",
                body=(
                    "Arrow down to Branch Protection and press Enter. Its list starts with "
                    "Configure Branch Protection; press Enter on that."
                ),
                keys=("Down", "Enter"),
                hear="Configure Branch Protection, Branch, main.",
            ),
            Step(
                title="Choose the branch and the rule",
                body=(
                    "Focus starts on Branch, already main. Tab past the Remove check box to "
                    "Required approving reviews, and press Up to make it 1. Leave the rest."
                ),
                keys=("Tab", "Tab", "Up"),
                hear="Required approving reviews, 1.",
            ),
            Step(
                title="Apply it",
                body=(
                    f"Tab to Apply and press Enter. QUILL asks first: Protect main in "
                    f"your-name/{PRACTICE_NAME}? Say Yes."
                ),
                keys=("Tab", "Enter"),
                hear=f"The status bar says Protected main in your-name/{PRACTICE_NAME}.",
                note=(
                    "On a free plan GitHub protects branches only in public repositories, so "
                    "it may refuse here and say so. Nothing has changed; read on to know the "
                    "steps."
                ),
            ),
            _wb(
                "properties",
                title="Read the rules on main",
                body=(
                    "Arrow to Branches, under Code, then to main, and press Alt+Enter. "
                    "Ctrl+Tab to the Protection page: Rules that apply says each rule in words."
                ),
                hear="Branch main, on the General page.",
            ),
            Step(
                title="Look at Rulesets",
                body=(
                    "Close the properties with Escape, press Ctrl+Shift+9 for Settings, and "
                    "arrow down to Rulesets. It lists any rulesets, each as a sentence. "
                    "Alt+Enter on one opens its sheet; its Summary page reads every rule."
                ),
                keys=("Escape", "Ctrl+Shift+9", "Down"),
                hear="Rulesets, and how many it has.",
                note="The practice repository has none, so the list is empty.",
            ),
            Step(
                title="Take the rule off",
                body=(
                    "Arrow up to Branch Protection and press Enter on Configure Branch "
                    "Protection again. Tab to Remove all protection from this branch "
                    "instead, press Space, then Apply, and say Yes."
                ),
                keys=("Up", "Enter", "Tab", "Space"),
                hear=(
                    "The status bar says Removed protection from main in "
                    f"your-name/{PRACTICE_NAME}."
                ),
            ),
        ),
        closing=(
            "You can now protect a branch and read the rules on it. In the editor, "
            "Configure Branch Protection is under Tools > Git and GitHub > GitHub."
        ),
        then=("github-api-console",),
    )
