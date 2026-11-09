"""The Problem shape, and the sentences a listener hears about problems."""

from __future__ import annotations

from dataclasses import dataclass, field

#: Severities, most serious first. Anything a tool calls something else is
#: folded into the nearest of these by :func:`normalize_severity`.
SEVERITIES = ("error", "warning", "info")


@dataclass(frozen=True, slots=True)
class Problem:
    """One problem: where it is (1-based line and column) and what it is."""

    line: int
    column: int
    severity: str
    message: str
    #: Which checker found it ("JSON", "node", "ruff"...), said in the list.
    source: str = ""
    #: Which open document it is in, when the Problems pane lists them all
    #: ("notes.md"); empty for the document in front of you.
    document: str = ""


@dataclass(frozen=True, slots=True)
class CheckReport:
    """Everything one Check This File found, in document order."""

    language: str
    problems: tuple[Problem, ...] = ()
    #: The checkers that ran, built-in and outside, by name.
    checked_with: tuple[str, ...] = ()
    #: Things worth saying that are not problems in the file: "No checker
    #: installed for Go", "tsc took longer than 15 seconds and was stopped".
    notes: tuple[str, ...] = field(default_factory=tuple)

    @property
    def checked(self) -> bool:
        return bool(self.checked_with)


def normalize_severity(raw: object) -> str:
    """Fold a tool's own word for severity into error, warning or info."""
    word = str(raw or "").strip().lower()
    if word in {"error", "fatal", "fatal error", "parse error", "e", "2", "critical"}:
        return "error"
    if word in {"warning", "warn", "w", "1", "deprecated"}:
        return "warning"
    if word in {"info", "note", "help", "hint", "information", "i", "0", "style"}:
        return "info"
    return "error"


def sort_problems(problems: list[Problem]) -> tuple[Problem, ...]:
    """Document order, and one row per distinct problem."""
    seen: set[tuple[int, int, str]] = set()
    ordered: list[Problem] = []
    for problem in sorted(problems, key=lambda p: (p.line, p.column)):
        key = (problem.line, problem.column, problem.message)
        if key in seen:
            continue
        seen.add(key)
        ordered.append(problem)
    return tuple(ordered)


def offset_for(text: str, line: int, column: int) -> int:
    """The character offset of a 1-based *line* and *column*, clamped to the text."""
    line = max(1, line)
    start = 0
    for _ in range(line - 1):
        newline = text.find("\n", start)
        if newline == -1:
            return len(text)
        start = newline + 1
    end = text.find("\n", start)
    end = len(text) if end == -1 else end
    return min(start + max(0, column - 1), end)


def problem_after(
    problems: tuple[Problem, ...], text: str, caret: int, *, forward: bool
) -> int | None:
    """The index of the problem Next (or Previous) Problem goes to from *caret*.

    Wraps at either end, as a Problems list does: the numbers in the sentence
    ("Problem 1 of 4") say when it has gone round.
    """
    if not problems:
        return None
    offsets = [offset_for(text, p.line, p.column) for p in problems]
    if forward:
        for index, offset in enumerate(offsets):
            if offset > caret:
                return index
        return 0
    for index in range(len(offsets) - 1, -1, -1):
        if offsets[index] < caret:
            return index
    return len(offsets) - 1


def describe_problem(problem: Problem, index: int | None = None, total: int | None = None) -> str:
    """The sentence for one problem: number, place, severity, message."""
    where = f"line {problem.line}, column {problem.column}"
    lead = f"Problem {index + 1} of {total}, " if index is not None and total else ""
    return f"{lead}{where}, {problem.severity}: {problem.message}"


def list_row(problem: Problem) -> str:
    """One row of the Problems list: place first, so arrowing reads in order."""
    source = f" ({problem.source})" if problem.source else ""
    return (
        f"Line {problem.line}, column {problem.column}, {problem.severity}: "
        f"{problem.message}{source}"
    )


def _count(number: int, word: str) -> str:
    return f"{number} {word}" + ("" if number == 1 else "s")


def summarize(report: CheckReport) -> str:
    """What Check This File says when it finishes."""
    notes = " ".join(note.rstrip(".") + "." for note in report.notes)
    if not report.checked:
        return notes or f"No checker for {report.language}."
    if not report.problems:
        head = "No problems found."
    else:
        by_kind = [
            _count(sum(1 for p in report.problems if p.severity == kind), kind)
            for kind in SEVERITIES
            if any(p.severity == kind for p in report.problems)
        ]
        head = f"{_count(len(report.problems), 'problem')}: {', '.join(by_kind)}."
    return f"{head} {notes}".strip()
