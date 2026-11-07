"""Check This File, the Problems list, and Next / Previous Problem.

Shared by QUILL and QUILL Lite, so the two cannot drift on what a problem is,
what is said about it or where the caret goes. The checking itself is
:mod:`quill.core.problems`; this is the part with a caret and a voice. Each
editor's window supplies the hooks at the bottom of the class and nothing else.

What a listener gets, and why:

* **Check This File** checks the whole document and, when it finds something,
  opens the Problems list -- every problem, one row each, line and column first
  so arrowing reads them in order. Enter goes to the one chosen. With nothing
  found it only says so: there is no empty list to dismiss.
* **Next Problem** and **Previous Problem** walk the same problems without the
  list, moving the caret and saying the problem's number, place and message --
  which the screen reader cannot know. They check again first whenever the
  text has changed since the last check, so the line numbers are never stale.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from quill.core.problems import (
    CheckReport,
    check_document,
    describe_problem,
    offset_for,
    problem_after,
    summarize,
)
from quill.core.problems.model import list_row
from quill.core.problems.outside import tools_for

__all__ = ["ProblemsCommandsMixin"]


class ProblemsCommandsMixin:
    """The three problem commands. Hooks: ``_problems_*`` below."""

    _problems_report: CheckReport | None = None
    _problems_checked_text: str | None = None

    # -- the commands ------------------------------------------------------- #

    def _check_this_file(self) -> None:
        self._run_problem_check(self._present_problems)

    def _step_problem(self, *, forward: bool) -> None:
        text = self._problems_text()
        if self._problems_report is not None and self._problems_checked_text == text:
            self._move_to_problem(self._problems_report, forward=forward)
            return
        self._run_problem_check(lambda report: self._move_to_problem(report, forward=forward))

    # -- what happens with a report ----------------------------------------- #

    def _present_problems(self, report: CheckReport) -> None:
        if not report.problems:
            self._problems_say(summarize(report))
            return
        rows = [list_row(problem) for problem in report.problems]
        chosen = self._problems_choose(summarize(report), rows)
        if chosen is None:
            return
        problem = report.problems[chosen]
        self._problems_go_to(offset_for(self._problems_text(), problem.line, problem.column))

    def _move_to_problem(self, report: CheckReport, *, forward: bool) -> None:
        if not report.problems:
            self._problems_say(summarize(report))
            return
        text = self._problems_text()
        index = problem_after(report.problems, text, self._problems_caret(), forward=forward)
        if index is None:
            return
        problem = report.problems[index]
        self._problems_go_to(offset_for(text, problem.line, problem.column))
        self._problems_say(describe_problem(problem, index, len(report.problems)))

    # -- running the check -------------------------------------------------- #

    def _run_problem_check(self, then: Callable[[CheckReport], None]) -> None:
        text = self._problems_text()
        language = self._problems_language()
        path = self._problems_path()
        modified = self._problems_modified()
        outside = self._problems_outside_allowed()

        def work() -> CheckReport:
            return check_document(
                text, language=language, path=path, modified=modified, outside=outside
            )

        def done(report: CheckReport) -> None:
            self._problems_report = report
            self._problems_checked_text = text
            then(report)

        if outside and tools_for(language):
            # An outside tool can take seconds; the window stays responsive.
            self._problems_say("Checking this file")
            self._problems_in_background(work, done)
            return
        done(work())

    # -- hooks each editor supplies ------------------------------------------ #

    def _problems_text(self) -> str:
        raise NotImplementedError

    def _problems_caret(self) -> int:
        raise NotImplementedError

    def _problems_language(self) -> str:
        """A :func:`quill.core.problems.language_key`."""
        raise NotImplementedError

    def _problems_path(self) -> Path | None:
        raise NotImplementedError

    def _problems_modified(self) -> bool:
        return True

    def _problems_outside_allowed(self) -> bool:
        return False

    def _problems_go_to(self, offset: int) -> None:
        raise NotImplementedError

    def _problems_say(self, message: str) -> None:
        raise NotImplementedError

    def _problems_choose(self, summary: str, rows: list[str]) -> int | None:
        """Show the Problems list; the index chosen, or ``None`` on Escape."""
        raise NotImplementedError

    def _problems_in_background(
        self, work: Callable[[], CheckReport], done: Callable[[CheckReport], None]
    ) -> None:
        done(work())
