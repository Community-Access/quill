"""A project task's record, as a document with headings (code.md 5.5) -- wx-free.

The transcript is text, so everything QUILL already does for reading works on
it: heading navigation, find, bookmarks, braille, read aloud, export. One
heading per turn and sub-headings for Plan, Changes, Commands and Result, so H
and Shift+H move through it, and heading levels never skip.

It is saved in QUILL's app data (the project's task history), never in the
repository unless the person saves it there themselves.
"""

from __future__ import annotations

from dataclasses import dataclass, field

__all__ = ["TurnLog", "render_markdown", "turn_heading"]


@dataclass
class TurnLog:
    """Everything one turn did, in words."""

    number: int
    instruction: str
    coach: bool = False
    plan: list[str] = field(default_factory=list)
    questions: list[str] = field(default_factory=list)
    pointers: list[str] = field(default_factory=list)
    changes: list[str] = field(default_factory=list)
    commands: list[str] = field(default_factory=list)
    written: list[str] = field(default_factory=list)
    created: list[str] = field(default_factory=list)
    deleted: list[str] = field(default_factory=list)
    rejected: int = 0
    result: str = ""
    answer: str = ""
    #: The engine's own tools on for this turn (decision 4), in words, or "".
    engine_tools: str = ""

    def context_lines(self) -> list[str]:
        """This turn, briefly, for the next turn's engine."""
        lines = [f"Turn {self.number}: the person asked: {self.instruction}"]
        if self.plan:
            lines.append("Plan: " + " ".join(f"{i}. {s}" for i, s in enumerate(self.plan, 1)))
        lines.extend(f"Change: {c}" for c in self.changes)
        lines.extend(f"Command: {c}" for c in self.commands)
        if self.answer:
            lines.append(f"Your summary then: {self.answer[:1500]}")
        return lines


def turn_heading(number: int, coach: bool = False) -> str:
    return f"## Turn {number}: you asked" + (" (coach mode)" if coach else "")


def _title(turns: list[TurnLog]) -> str:
    first = turns[0].instruction.strip().splitlines()[0] if turns else ""
    if len(first) > 70:
        first = first[:67].rstrip() + "..."
    return f"# Project task: {first}" if first else "# Project task"


def render_markdown(project_name: str, turns: list[TurnLog]) -> str:
    """The whole task as Markdown, one heading per turn."""
    out = [_title(turns), "", f"Project: {project_name}", ""]
    for turn in turns:
        out += [turn_heading(turn.number, turn.coach), "", turn.instruction.strip(), ""]
        if turn.plan or turn.engine_tools:
            out += ["### Plan", ""]
            out += [f"{i}. {step}" for i, step in enumerate(turn.plan, 1)]
            if turn.engine_tools:
                out += ([""] if turn.plan else []) + [turn.engine_tools]
            out.append("")
        if turn.questions:
            out += ["### Questions for you", ""] + [f"- {q}" for q in turn.questions] + [""]
        if turn.pointers:
            out += ["### Where to look", ""] + [f"- {p}" for p in turn.pointers] + [""]
        if turn.changes:
            out += ["### Changes", ""] + [f"- {c}" for c in turn.changes] + [""]
        if turn.commands:
            out += ["### Commands", ""] + [f"- {c}" for c in turn.commands] + [""]
        if turn.result or turn.answer:
            out += ["### Result", ""]
            if turn.result:
                out += [turn.result, ""]
            if turn.answer:
                out += [turn.answer.strip(), ""]
    return "\n".join(out).rstrip() + "\n"
