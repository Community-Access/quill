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
* **View > Problems > Show Pane** docks the same problems below the editor, where they
  stay while you work (:mod:`quill.ui.problems_pane`). While it is shown, Check
  This File fills it instead of opening the modal list, and every check keeps
  it current. F6 reaches it; Escape comes back. While it is shown, saving
  checks the file again, and so does a pause in typing when the pane's Check
  After a Pause box is checked (off by default). Those checks are quiet: the
  only thing said is the new count, and only when it changed. Its Files
  chooser lists every open document's problems too (built-in checkers for the
  others), and Enter on one brings that document forward.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

from quill.core.problems import (
    CheckReport,
    check_document,
    describe_problem,
    offset_for,
    problem_after,
    summarize,
)
from quill.core.problems.model import Problem, list_row
from quill.core.problems.outside import tools_for
from quill.core.problems.pane import OpenProblemDocument, combine_reports

if TYPE_CHECKING:
    from quill.ui.problems_pane import ProblemsPane

__all__ = ["PAUSE_SECONDS", "ProblemsCommandsMixin"]

#: How long the text must stay still before Check After a Pause checks it.
PAUSE_SECONDS = 1.5


class ProblemsCommandsMixin:
    """The problem commands and the pane. Hooks: ``_problems_*`` below."""

    _problems_report: CheckReport | None = None
    _problems_checked_text: str | None = None
    # The pane's timer (_problems_tick): what the text was last time, when it
    # last changed, whether it was modified, and whether a quiet check is out.
    _problems_seen_text: str | None = None
    _problems_changed_at: float = 0.0
    _problems_was_modified: bool = False
    _problems_auto_running: bool = False
    _problems_last_auto_changed: bool = False
    # The pane's Files chooser, and, in All open files, what each row is.
    _problems_all_files: bool = False
    #: True once this window has shown the pane or been told which files to list.
    _problems_files_chosen: bool = False
    _problems_pane_origins: list[tuple[object, Problem]] | None = None

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

    def _toggle_problems_pane(self, *, keep_files: bool = False) -> None:
        """View > Problems > Show Pane: show or hide it, and check the file on showing."""
        pane = self._problems_pane(create=True)
        if pane is None:
            return
        if pane.is_shown():
            if pane.has_focus():
                self._problems_back_to_editor()
            self._problems_pane_set_shown(False)
            self._problems_say("Problems pane hidden")
            return
        self._problems_pane_set_shown(True)
        if not self._problems_can_check():
            self._problems_say("Problems pane shown")
            return
        if not keep_files and not self._problems_files_chosen:
            # The first showing in this window starts from the default.
            self._problems_all_files = self._problems_all_files_setting()
        self._problems_files_chosen = True
        pane.set_all_files(self._problems_all_files)
        self._problems_mark_all_files(self._problems_all_files)

        def shown(report: CheckReport) -> None:
            if self._problems_all_files:
                self._problems_say(f"Problems pane shown, all open files. {pane.count_sentence()}")
            else:
                self._problems_say(f"Problems pane shown. {summarize(report)}")

        self._run_problem_check(shown)

    def _problems_pane_go_to(self, index: int) -> None:
        """Enter on a pane row: the caret to that problem, focus to the editor."""
        report = self._problems_report
        if report is None:
            return
        origins = self._problems_pane_origins
        if origins is not None:
            # All open files: the row may be another document's.
            if not 0 <= index < len(origins):
                return
            key, problem = origins[index]
            if key != self._problems_document_key():
                self._problems_go_to_document(key, problem.line, problem.column)
                return
        else:
            if not 0 <= index < len(report.problems):
                return
            problem = report.problems[index]
        if self._problems_checked_text == self._problems_text():
            self._problems_go_to(offset_for(self._problems_text(), problem.line, problem.column))
            return
        # You fixed something since the check, which is the point of a pane
        # that stays open: check again, then go to the same problem where it
        # is now. If the fix removed it, say so rather than land on a stale line.
        self._run_problem_check(lambda fresh: self._go_to_same_problem(fresh, problem))

    def _go_to_same_problem(self, report: CheckReport, wanted: Problem) -> None:
        matches = [
            p
            for p in report.problems
            if (p.message, p.source, p.severity) == (wanted.message, wanted.source, wanted.severity)
        ]
        if not matches:
            self._problems_say(f"That problem is gone. {summarize(report)}")
            return
        nearest = min(matches, key=lambda p: abs(p.line - wanted.line))
        self._problems_go_to(offset_for(self._problems_text(), nearest.line, nearest.column))

    def _feed_problems_pane(self, report: CheckReport) -> bool:
        """Update the pane, if shown; True when the count it shows changed."""
        pane = self._problems_pane(create=False)
        if pane is None or not pane.is_shown():
            return False
        before = pane.count_sentence() if pane.report is not None else None
        if self._problems_all_files:
            combined, origins = self._all_open_files_report(report)
            self._problems_pane_origins = origins
            pane.show_report(combined)
        else:
            self._problems_pane_origins = None
            pane.show_report(report)
        return before != pane.count_sentence()

    def _all_open_files_report(
        self, current: CheckReport
    ) -> tuple[CheckReport, list[tuple[object, Problem]]]:
        """This document's report beside a fresh check of every other open one.

        The others get the built-in checkers only, at once: an outside tool for
        each of twenty tabs is not something to start on a key press.
        """
        here = self._problems_document_key()
        parts: list[tuple[object, str, CheckReport]] = []
        documents = self._problems_open_documents()
        if not any(document.key == here for document in documents):
            parts.append((here, "", current))
        for document in documents:
            if document.key == here:
                parts.append((here, document.name, current))
                continue
            report = check_document(
                document.text,
                language=document.language,
                path=document.path,
                modified=document.modified,
                outside=False,
            )
            if report.problems:
                parts.append((document.key, document.name, report))
        return combine_reports(parts)

    def _problems_choose_files(self, all_files: bool) -> None:
        """View > Problems > This File Only / All Open Files.

        The menu's way to the pane's Files chooser, and the easy one: it also
        shows the pane when it is hidden, because choosing what the pane lists
        and then not seeing it would be a command that did nothing you can hear.
        """
        pane = self._problems_pane(create=True)
        if pane is None:
            return
        pane.set_all_files(all_files)
        if not pane.is_shown():
            self._problems_all_files = all_files
            self._problems_mark_all_files(all_files)
            self._toggle_problems_pane(keep_files=True)
            return
        self._problems_set_all_files(all_files)

    def _problems_switch_files(self) -> None:
        """F in the pane's list: this file, all open files, and back."""
        self._problems_choose_files(not self._problems_all_files)

    def _problems_set_all_files(self, all_files: bool) -> None:
        """The pane's Files chooser: refill, and say the new count.

        A switch for now, not a new default: the default is the
        ``problems_all_open_files`` setting, which each window starts from.
        """
        self._problems_all_files = all_files
        self._problems_files_chosen = True
        self._problems_mark_all_files(all_files)
        pane = self._problems_pane(create=False)
        if pane is not None:
            pane.set_all_files(all_files)
        report = self._problems_report
        if report is None:
            if self._problems_can_check():
                self._run_problem_check(lambda _report: self._say_pane_count())
            return
        self._feed_problems_pane(report)
        self._say_pane_count()

    def _say_pane_count(self) -> None:
        pane = self._problems_pane(create=False)
        if pane is not None:
            self._problems_say(pane.count_sentence())

    def _present_problems(self, report: CheckReport) -> None:
        pane = self._problems_pane(create=False)
        if pane is not None and pane.is_shown():
            # The pane already has the report (``done`` fed it); say what was
            # found and leave focus in the text. F6 reaches the rows.
            self._problems_say(summarize(report))
            return
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

    # -- checking on its own: after a save, and after a pause ---------------- #

    def _problems_tick(self, now: float | None = None) -> None:
        """The pane's timer, twice a second while it is shown.

        Checks the file again, quietly, when it has just been saved, and -- with
        Check After a Pause on -- when you have stopped typing for
        :data:`PAUSE_SECONDS`. Never while you type, never twice for the same
        text, and the only thing ever said is the new count, when it changed.
        """
        pane = self._problems_pane(create=False)
        if pane is None or not pane.is_shown() or not self._problems_can_check():
            return
        now = time.monotonic() if now is None else now
        text = self._problems_text()
        modified = self._problems_modified()
        if text != self._problems_seen_text:
            self._problems_seen_text = text
            self._problems_changed_at = now
        just_saved = self._problems_was_modified and not modified
        self._problems_was_modified = modified
        if self._problems_auto_running or text == self._problems_checked_text:
            return
        paused = self._problems_pause_enabled() and now - self._problems_changed_at >= PAUSE_SECONDS
        if just_saved or paused:
            self._problems_auto_check()

    def _problems_auto_check(self) -> None:
        self._problems_auto_running = True

        def then(report: CheckReport) -> None:
            self._problems_auto_running = False
            if self._problems_last_auto_changed:
                pane = self._problems_pane(create=False)
                if pane is not None:
                    self._problems_say(pane.count_sentence())

        self._run_problem_check(then, quiet=True)

    def _run_problem_check(
        self, then: Callable[[CheckReport], None], *, quiet: bool = False
    ) -> None:
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
            self._problems_last_auto_changed = self._feed_problems_pane(report)
            then(report)

        if outside and tools_for(language):
            # An outside tool can take seconds; the window stays responsive.
            if not quiet:
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

    def _problems_can_check(self) -> bool:
        """False where this document has nothing a checker reads."""
        return True

    def _problems_all_files_setting(self) -> bool:
        """``problems_all_open_files``: the default, set in Settings or Preferences."""
        return False

    def _problems_mark_all_files(self, all_files: bool) -> None:
        """Check the View > Problems row that matches; nothing is saved."""

    def _problems_open_documents(self) -> list[OpenProblemDocument]:
        """Every open document, for the pane's All open files; [] means just this one."""
        return []

    def _problems_document_key(self) -> object:
        """This document's key among :meth:`_problems_open_documents`."""
        return None

    def _problems_go_to_document(self, key: object, line: int, column: int) -> None:
        """Bring another open document forward with its caret at *line*, *column*."""

    def _problems_pause_enabled(self) -> bool:
        """Check After a Pause: the ``problems_check_after_pause`` setting."""
        return False

    def _problems_set_pause_enabled(self, enabled: bool) -> None:
        """The pane's check box: remember the choice."""

    def _problems_pane(self, *, create: bool) -> ProblemsPane | None:
        """The docked pane; built (hidden) on first use when *create*."""
        return None

    def _problems_pane_set_shown(self, shown: bool) -> None:
        """Show or hide the pane, lay the window out, remember the choice."""
        raise NotImplementedError

    def _problems_back_to_editor(self) -> None:
        """Escape in the pane: focus to the text, the caret where it was."""
        raise NotImplementedError

    def _problems_copy(self, text: str) -> None:
        raise NotImplementedError
