"""Walk Me Through It: a help task said one step at a time (GitHub PRD D12, GH-R-107).

A Do Something task is written as a short paragraph of steps ("Press
Ctrl+Shift+1 for Issues, then Ctrl+N. Type a title, press Enter, ...").
Read as one paragraph it has to be held in memory while the keys are pressed.
A walk says the first step, waits until a command has been run, and then
says the next one. F1 says the step again, Shift+F1 lists all of them, and
Escape stops the walk.

The steps are cut from the task's own words, at sentence ends, semicolons
and the joins "and" and "then" after a comma, so the walk and the help topic
can never say different things. No ``wx``; strict-typed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

__all__ = ["Walk", "steps_of"]

_CUTS = re.compile(r"(?<=[.;])\s+|,\s+(?:and|then)\s+|;\s*")


def steps_of(text: str) -> tuple[str, ...]:
    """*text*'s steps, each a sentence starting with a capital and ending with a stop."""
    steps: list[str] = []
    for part in _CUTS.split(text.strip()):
        words = part.strip().rstrip(".;,").strip()
        if not words:
            continue
        steps.append(words[0].upper() + words[1:] + ".")
    return tuple(steps)


@dataclass(slots=True)
class Walk:
    """One walk through a task: its title, its steps and the step it is on."""

    title: str
    steps: tuple[str, ...]
    index: int = 0

    @property
    def finished(self) -> bool:
        return self.index >= len(self.steps)

    def current(self) -> str:
        """The step it is on, with where that is in the walk."""
        if self.finished:
            return f"{self.title}: done."
        return f"Step {self.index + 1} of {len(self.steps)}: {self.steps[self.index]}"

    def opening(self) -> str:
        return (
            f"Walking through {self.title}. {self.current()} "
            "F1 says the step again, Shift+F1 lists the steps, Escape stops."
        )

    def advance(self) -> str:
        """Move on after a command was run; what to say next.

        A step that only moves the selection ("Arrow down the list") runs no
        command, so the command after it shows it was done: it is passed over
        with the step the command finished.
        """
        while not self.finished and self.steps[self.index].casefold().startswith("arrow "):
            self.index += 1
        self.index += 1
        if self.finished:
            return f"That was the last step of {self.title}."
        return self.current()

    def listing(self) -> str:
        """Every step, the current one marked."""
        lines = [f"{self.title}, {len(self.steps)} steps."]
        for number, step in enumerate(self.steps, 1):
            here = ", you are here" if number - 1 == self.index else ""
            lines.append(f"Step {number}{here}: {step}")
        return " ".join(lines)
