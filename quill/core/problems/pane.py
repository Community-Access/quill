"""What the Problems pane shows, and the one sentence it says.

The pane itself is :mod:`quill.ui.problems_pane`; this is the part with no
``wx``: which rows survive the filter row, what each row reads, and what is said
when the count changes. Both editors' panes read it, so QUILL and QUILL Lite
cannot drift on what "errors only" means or on how a count is worded.

The filter row has two choosers:

* **Show** -- every problem, errors and warnings, or errors only. Severities
  are the three in :data:`quill.core.problems.model.SEVERITIES`, so "errors
  and warnings" drops only ``info``.
* **Source** -- every checker, or one of the checkers that found something in
  this report (the built-in JSON checker, ``ruff``, ``node``...). The choices
  are built from the report, so the list never offers a source with nothing in
  it.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

from quill.core.problems.model import CheckReport, Problem

__all__ = [
    "ALL_SOURCES",
    "SCOPE_CHOICES",
    "SHOW_CHOICES",
    "OpenProblemDocument",
    "combine_reports",
    "PaneFilter",
    "count_sentence",
    "filter_problems",
    "pane_row",
    "source_choices",
]

#: The Show chooser, in order: ``(key, label)``. The first is the default.
SHOW_CHOICES: tuple[tuple[str, str], ...] = (
    ("all", "All problems"),
    ("warnings", "Errors and warnings"),
    ("errors", "Errors only"),
)

#: The Files chooser, in order: ``(key, label)``. The first is the default.
SCOPE_CHOICES: tuple[tuple[str, str], ...] = (
    ("this", "This file"),
    ("open", "All open files"),
)

#: The Source chooser's first row, which means "do not filter by source".
ALL_SOURCES = "All sources"

#: What a source with no name is called in the chooser and the row.
_UNNAMED_SOURCE = "Checker"

_SHOWN_SEVERITIES: dict[str, frozenset[str]] = {
    "all": frozenset({"error", "warning", "info"}),
    "warnings": frozenset({"error", "warning"}),
    "errors": frozenset({"error"}),
}


@dataclass(frozen=True, slots=True)
class OpenProblemDocument:
    """One open document, as the pane's All open files needs it."""

    #: Whatever the editor uses to bring it to the front (a tab index, a window).
    key: object
    name: str
    text: str
    language: str
    path: Path | None = None
    modified: bool = True


def combine_reports(
    parts: list[tuple[object, str, CheckReport]],
) -> tuple[CheckReport, list[tuple[object, Problem]]]:
    """One report from several documents' reports, and what each row came from.

    Each problem keeps its own line and column and gains its document's name,
    which the row reads first. The second value lists, row by row, the
    document key and the problem as that document's report has it, so Go To
    can bring the right document forward.
    """
    problems: list[Problem] = []
    origins: list[tuple[object, Problem]] = []
    checked: list[str] = []
    for key, name, report in parts:
        for problem in report.problems:
            problems.append(replace(problem, document=name))
            origins.append((key, problem))
        checked.extend(tool for tool in report.checked_with if tool not in checked)
    combined = CheckReport(
        language=parts[0][2].language if parts else "",
        problems=tuple(problems),
        checked_with=tuple(checked),
    )
    return combined, origins


@dataclass(frozen=True, slots=True)
class PaneFilter:
    """The filter row's two answers."""

    show: str = "all"
    source: str = ALL_SOURCES


def _source_name(problem: Problem) -> str:
    return problem.source or _UNNAMED_SOURCE


def source_choices(report: CheckReport | None) -> tuple[str, ...]:
    """The Source chooser: All sources, then each source found, in first-seen order."""
    seen: list[str] = []
    for problem in report.problems if report is not None else ():
        name = _source_name(problem)
        if name not in seen:
            seen.append(name)
    return (ALL_SOURCES, *seen)


def filter_problems(
    problems: tuple[Problem, ...], pane_filter: PaneFilter
) -> tuple[tuple[int, Problem], ...]:
    """The problems the pane shows, each with its index in the report.

    The index is kept so Go To and Next Problem agree on which problem is
    which, whatever is hidden.
    """
    shown = _SHOWN_SEVERITIES.get(pane_filter.show, _SHOWN_SEVERITIES["all"])
    return tuple(
        (index, problem)
        for index, problem in enumerate(problems)
        if problem.severity in shown
        and (pane_filter.source == ALL_SOURCES or _source_name(problem) == pane_filter.source)
    )


def pane_row(problem: Problem) -> str:
    """One row: the document (in All open files), severity, place, message, source.

    Severity first because the pane is a list you scan for errors; the modal
    list puts the place first because it is read in document order.
    """
    where = f"{problem.document}: " if problem.document else ""
    return (
        f"{where}{problem.severity.capitalize()}, line {problem.line}, "
        f"column {problem.column}: {problem.message} ({_source_name(problem)})"
    )


def count_sentence(total: int, shown: int | None = None) -> str:
    """The one sentence said when the count changes: "3 problems".

    When the filter hides some, it says how many are showing as well, because
    a count that disagrees with the rows you then arrow through reads as a bug.
    """
    head = "No problems" if total == 0 else f"{total} problem" + ("" if total == 1 else "s")
    if shown is None or shown == total:
        return head
    return f"{head}, {shown} shown"
