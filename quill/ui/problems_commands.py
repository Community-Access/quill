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
from typing import TYPE_CHECKING, Any

from quill.core.problems import (
    CheckReport,
    check_document,
    describe_problem,
    offset_for,
    problem_after,
    summarize,
)
from quill.core.problems.model import Problem, list_row, sort_problems
from quill.core.problems.outside import tools_for
from quill.core.problems.pane import OpenProblemDocument, combine_reports
from quill.core.text_units import native_offset, text_index
from quill.ui.problems_hooks import ProblemsHooksMixin

if TYPE_CHECKING:
    pass

__all__ = ["PAUSE_SECONDS", "ProblemsCommandsMixin"]

#: How long the text must stay still before Check After a Pause checks it.
PAUSE_SECONDS = 1.5


class ProblemsCommandsMixin(ProblemsHooksMixin):
    """The problem commands and the pane. Hooks: :class:`ProblemsHooksMixin`."""

    _problems_report: CheckReport | None = None
    _problems_checked_text: str | None = None
    # The pane's timer (_problems_tick): the change token it saw last time
    # (see _problems_change_token) and the one the last check was made at,
    # when it last changed, whether it was modified, and whether a quiet
    # check is out.
    _problems_seen_token: object = None
    _problems_checked_token: object = None
    _problems_changed_at: float = 0.0
    _problems_was_modified: bool = False
    _problems_auto_running: bool = False
    _problems_last_auto_changed: bool = False
    # The pane's Files chooser, and, in All open files, what each row is.
    _problems_all_files: bool = False
    #: True once this window has shown the pane or been told which files to list.
    _problems_files_chosen: bool = False
    _problems_pane_origins: list[tuple[object, Problem]] | None = None
    #: Bumped on every pane fill, so an All Open Files check that finishes
    #: after a newer fill is dropped rather than shown over it.
    _problems_feed_generation: int = 0

    # -- offsets: the control counts UTF-16 units, the text code points ------ #

    def _problems_go_to_line(self, text: str, line: int, column: int) -> None:
        """The caret to 1-based *line*, *column* of *text*, in the control's units.

        :func:`offset_for` counts code points and the control counts UTF-16
        units, so an emoji earlier in the file would land one short per emoji
        (review 2026-11-09, QUILL 5 and QUILL Lite 7).
        """
        self._problems_go_to(native_offset(text, offset_for(text, line, column)))

    def _problems_caret_index(self, text: str) -> int:
        """The caret as a code-point index into *text*."""
        return text_index(text, self._problems_caret())

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
        text = self._problems_text()
        if self._problems_checked_text == text:
            self._problems_go_to_line(text, problem.line, problem.column)
            return
        # You fixed something since the check, which is the point of a pane
        # that stays open: check again, then go to the same problem where it
        # is now. If the fix removed it, say so rather than land on a stale line.
        self._run_problem_check(lambda fresh: self._go_to_same_problem(fresh, problem))

    def _problems_quick_fix(self, index: int) -> None:
        """Quick Fix on a pane row: the server's fixes for it, chosen from a list."""
        report = self._problems_report
        if report is None:
            return
        origins = self._problems_pane_origins
        if origins is not None:
            if not 0 <= index < len(origins):
                return
            key, problem = origins[index]
            if key != self._problems_document_key():
                self._problems_say("Go to that document first, then ask for a quick fix")
                return
        elif 0 <= index < len(report.problems):
            problem = report.problems[index]
        else:
            return
        ask = getattr(self, "_ls_quick_fixes", None)
        path = self._problems_path()
        text = self._problems_text()
        if not callable(ask) or not ask(
            path, text, problem, lambda fixes: self._offer_quick_fixes(text, fixes, problem)
        ):
            self._problems_say("No quick fix: no language server for this file")

    def _offer_quick_fixes(
        self, text: str, fixes: list[Any] | None, problem: Problem | None = None
    ) -> None:
        from quill.core.lsp.convert import apply_text_edits

        if not fixes:
            self._problems_say("No quick fix for this problem")
            return
        if self._problems_text() != text:
            self._problems_say("The text changed; ask for the quick fix again")
            return
        noun = "quick fix" if len(fixes) == 1 else "quick fixes"
        # Titled Quick Fix and naming the problem: the list is fixes, not
        # problems, and which problem they fix is what the reader cannot see
        # from here (review 2026-11-09, QUILL 13).
        about = ""
        if problem is not None:
            about = f" for line {problem.line}, column {problem.column}: {problem.message}"
        chosen = self._problems_choose(
            f"{len(fixes)} {noun}{about.rstrip('.')}.",
            [fix.title for fix in fixes],
            title="Quick Fix",
        )
        if chosen is None:
            return
        fix = fixes[chosen]
        new_text = apply_text_edits(text, fix.edits)
        start = 0
        while start < min(len(text), len(new_text)) and text[start] == new_text[start]:
            start += 1
        end_old, end_new = len(text), len(new_text)
        while end_old > start and end_new > start and text[end_old - 1] == new_text[end_new - 1]:
            end_old -= 1
            end_new -= 1
        # One span, one undo step: Ctrl+Z takes the whole fix back. The span
        # is in code points; the control counts UTF-16 units.
        self._problems_replace(
            native_offset(text, start), native_offset(text, end_old), new_text[start:end_new]
        )
        self._problems_say(f"Fixed: {fix.title}")
        self._run_problem_check(lambda _report: None, quiet=True)

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
        self._problems_go_to_line(self._problems_text(), nearest.line, nearest.column)

    def _feed_problems_pane(
        self, report: CheckReport, then: Callable[[bool], None] | None = None
    ) -> None:
        """Update the pane, if shown; *then* hears whether the count it shows changed.

        All Open Files checks the other documents on the background runner, as
        Check This File does: their text is read here, on the UI thread, which
        is cheap, and checking twenty of them is not (review 2026-11-09, QUILL
        10 and QUILL Lite 10). A fill that finishes after a newer one began is
        dropped.
        """
        pane = self._problems_pane(create=False)
        self._problems_feed_generation += 1
        generation = self._problems_feed_generation
        if pane is None or not pane.is_shown():
            if then is not None:
                then(False)
            return
        before = pane.count_sentence() if pane.report is not None else None
        if not self._problems_all_files:
            self._problems_pane_origins = None
            pane.show_report(report)
            if then is not None:
                then(before != pane.count_sentence())
            return
        documents = self._problems_open_documents()
        here = self._problems_document_key()

        def work() -> tuple[CheckReport, list[tuple[object, Problem]]]:
            return self._all_open_files_report(report, documents, here)

        def done(result: tuple[CheckReport, list[tuple[object, Problem]]]) -> None:
            if (
                not self._problems_window_alive()
                or generation != self._problems_feed_generation
                or self._problems_document_key() != here
            ):
                if then is not None and self._problems_window_alive():
                    then(False)
                return
            combined, origins = result
            self._problems_pane_origins = origins
            pane.show_report(combined)
            if then is not None:
                then(before != pane.count_sentence())

        self._problems_in_background(work, done)

    def _all_open_files_report(
        self,
        current: CheckReport,
        documents: list[OpenProblemDocument] | None = None,
        here: object = None,
    ) -> tuple[CheckReport, list[tuple[object, Problem]]]:
        """This document's report beside a fresh check of every other open one.

        The others get the built-in checkers only: an outside tool for each of
        twenty tabs is not something to start on a key press. Meant for the
        background runner, so it touches no widget: *documents* and *here* were
        read on the UI thread. Never raises; a document that cannot be checked
        is left out.
        """
        if documents is None:
            documents = self._problems_open_documents()
            here = self._problems_document_key()
        parts: list[tuple[object, str, CheckReport]] = []
        if not any(document.key == here for document in documents):
            parts.append((here, "", current))
        for document in documents:
            if document.key == here:
                parts.append((here, document.name, current))
                continue
            try:
                report = check_document(
                    document.text,
                    language=document.language,
                    path=document.path,
                    modified=document.modified,
                    outside=False,
                )
            except Exception:  # noqa: BLE001 - one bad document never empties the list
                continue
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
        self._feed_problems_pane(report, lambda _changed: self._say_pane_count())

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
        self._problems_go_to_line(self._problems_text(), problem.line, problem.column)

    def _move_to_problem(self, report: CheckReport, *, forward: bool) -> None:
        if not report.problems:
            self._problems_say(summarize(report))
            return
        text = self._problems_text()
        index = problem_after(
            report.problems, text, self._problems_caret_index(text), forward=forward
        )
        if index is None:
            return
        problem = report.problems[index]
        self._problems_go_to_line(text, problem.line, problem.column)
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
        # A cheap token, not the text: copying a large buffer out of the
        # control twice a second is the cost (review 2026-11-09, QUILL 8). The
        # text is read only when a check is actually due.
        token = self._problems_token()
        modified = self._problems_modified()
        if token != self._problems_seen_token:
            self._problems_seen_token = token
            self._problems_changed_at = now
        just_saved = self._problems_was_modified and not modified
        self._problems_was_modified = modified
        if self._problems_auto_running or token == self._problems_checked_token:
            return
        paused = self._problems_pause_enabled() and now - self._problems_changed_at >= PAUSE_SECONDS
        if not (just_saved or paused):
            return
        if self._problems_text() == self._problems_checked_text:
            # Changed and changed back: nothing new to check.
            self._problems_checked_token = token
            return
        self._problems_auto_check()

    def _problems_token(self) -> object:
        """The change token, or the text itself where the host has none."""
        token = self._problems_change_token()
        return self._problems_text() if token is None else token

    def _problems_auto_check(self) -> None:
        self._problems_auto_running = True

        def then(report: CheckReport) -> None:
            self._problems_auto_running = False
            # Only the window in front speaks: with the pane shown in every
            # window, a background one saying its own count after a pause is
            # noise about a file nobody is looking at (review QUILL Lite 6).
            if self._problems_last_auto_changed and self._problems_is_active():
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

        server_problems = getattr(self, "_ls_problems_for", None)
        serves = getattr(self, "_ls_serves", None)
        use_server = callable(server_problems) and callable(serves) and bool(serves(path))

        document = self._problems_document_key()
        token = self._problems_token()

        def work() -> CheckReport:
            # Never raises: a checker or server that fails becomes a note, so
            # ``done`` always runs and a quiet check can never stay "running"
            # for the rest of the session (review 2026-11-09, QUILL 3, Lite 4).
            try:
                return checked()
            except Exception as error:  # noqa: BLE001 - reported, never lost
                return CheckReport(
                    language=language, notes=(f"The check could not finish: {error}",)
                )

        def checked() -> CheckReport:
            report = check_document(
                text, language=language, path=path, modified=modified, outside=outside
            )
            if not use_server:
                return report
            # Layer 4: the language server's problems beside the checkers'.
            found = server_problems(path, text)  # type: ignore[misc]
            if found is None:
                return report
            name = found[0].source if found else "language server"
            return CheckReport(
                language=report.language,
                problems=sort_problems([*report.problems, *found]),
                checked_with=(*report.checked_with, name),
                notes=report.notes,
            )

        def done(report: CheckReport) -> None:
            if not self._problems_window_alive():
                # The window closed while the check ran: nothing of it is left
                # to show the result in (review 2026-11-09, QUILL Lite 3).
                return
            if self._problems_document_key() != document:
                # Another document came to the front while the check ran: its
                # result belongs to a file nobody is looking at, so it is
                # dropped rather than shown against this one (review QUILL 6).
                # Edits to the same document keep it; Go To re-checks then.
                self._problems_auto_running = False
                return
            self._problems_report = report
            self._problems_checked_text = text
            self._problems_checked_token = token

            def fed(changed: bool) -> None:
                self._problems_last_auto_changed = changed
                then(report)

            self._feed_problems_pane(report, fed)

        if use_server or (outside and tools_for(language)):
            # An outside tool can take seconds; the window stays responsive.
            if not quiet:
                self._problems_say("Checking this file")
            self._problems_in_background(work, done)
            return
        done(work())
