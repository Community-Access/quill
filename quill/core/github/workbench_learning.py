"""Help and Learning's Tutorials and Tips nodes (GitHub PRD D11 and D16, GH-R-106).

**Tutorials** lists the GitHub lessons with where you are in each ("done",
"step 3 of 7"), and how many are done. They are the same lessons as Help >
Tutorials in the editor (:mod:`quill.core.tutorials.github_lessons`), so the
two can never teach different things.

**Tips** are QUILLBert's: one short thing worth trying each, held in a list
and never pushed at you. Every key a tip names is one the Workbench binds;
a test checks that, so a tip cannot teach a key that does nothing.

No ``wx``; strict-typed.
"""

from __future__ import annotations

from collections.abc import Sequence

from quill.core.tutorials.model import KeyLookup, Tutorial, key_phrase
from quill.core.tutorials.progress import TutorialProgressStore

__all__ = ["TIPS", "TUTORIAL_PREFIX", "lesson_steps", "tip_rows", "tutorial_rows", "tutorials_note"]

TUTORIAL_PREFIX = "tutorial:"

TIPS: tuple[str, ...] = (
    "Select several rows and press Alt+Enter once: one sheet changes them all, with a "
    "preview first.",
    "Ctrl+Enter is OK in a sheet from anywhere, even in the middle of a long text box.",
    "F9 says the last result again, and Shift+F9 explains what it means and what to do next.",
    "Alt+1 to Alt+9 say where you are, the counts, your access and the hourly allowance, "
    "and move nothing.",
    "Ctrl+L takes owner/name, #42, owner/name#42 or any GitHub link, and goes there.",
    "When a list stops short, Load More, Alt+PageDown, reads the next page.",
    "Shift+F1 says why a command is greyed, and lists Why? first when something happened "
    "on its own.",
    "Ctrl+Alt+K turns on the Key Describer: keys say what they do here instead of doing it, "
    "until Escape.",
    "Do Something's tasks can walk you through, one step at a time: Walk Me Through It, "
    "on the context menu.",
    "A watch tells you when a run finishes or a release appears, and never marks a "
    "notification read. Ctrl+N in Watches adds one.",
    "Ctrl+Alt+P makes quill-practice, a private repository with issues, a pull request and "
    "a failing run, to learn on without worrying.",
)


def tip_rows() -> list[tuple[str, str]]:
    """Each tip as a row: its words, and its detail."""
    return [(tip, f"QUILLBert's tip {n} of {len(TIPS)}: {tip}") for n, tip in enumerate(TIPS, 1)]


def _where(lesson: Tutorial, store: TutorialProgressStore | None) -> str:
    if store is not None and store.is_done(lesson.slug):
        return "done"
    step = store.step_of(lesson.slug) if store is not None else 0
    if step:
        return f"step {step + 1} of {len(lesson.steps)}"
    return f"{lesson.minutes} minutes, not started"


def tutorial_rows(
    lessons: Sequence[Tutorial], store: TutorialProgressStore | None
) -> list[tuple[str, str, str]]:
    """Each lesson as a row: "Title: where you are", its summary, and its target."""
    return [
        (
            f"{lesson.title}: {_where(lesson, store)}",
            f"{lesson.summary} {len(lesson.steps)} steps. Enter opens it; Walk Me Through "
            "It, on the context menu, says it here one step at a time.",
            f"{TUTORIAL_PREFIX}{lesson.slug}",
        )
        for lesson in lessons
    ]


def tutorials_note(lessons: Sequence[Tutorial], store: TutorialProgressStore | None) -> str:
    """ "2 of 6 done": what the node says about itself."""
    done = sum(1 for lesson in lessons if store is not None and store.is_done(lesson.slug))
    return f"{done} of {len(lessons)} done."


def lesson_steps(lesson: Tutorial, key_for: KeyLookup) -> tuple[str, ...]:
    """A lesson as walk steps: each step's words, its keys as bound now, what you hear.

    *key_for* gives the key a command has now, so a rebound key is the one the
    walk teaches, as in the Tutorials window (:func:`key_phrase`).
    """
    steps: list[str] = []
    for step in lesson.steps:
        text = f"{step.title}. {step.body}".replace("..", ".")
        keys = key_phrase(step, key_for)
        if keys:
            text += f" Keys: {keys}."
        if step.hear:
            text += f" You should hear: {step.hear}"
        steps.append(text)
    return tuple(steps)
