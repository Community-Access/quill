"""Navigate > Code in QUILL Lite: blocks, indent changes and the problem keys.

The same rows, letters and keys as QUILL's Navigate > Code
(``quill/ui/main_frame_code_nav.py``), over the same shared code:
:mod:`quill.core.navigation` for blocks and indentation, and
:class:`quill.ui.problems_commands.ProblemsCommandsMixin` over
:mod:`quill.core.problems` for Check This File.

QUILL Lite's languages are plain text, Markdown and HTML, so that is what it
uses them for. A block in Markdown or plain text is a paragraph and in HTML is a
heading or landmark element -- QUILL's HTML pattern, read from the same profile.
Check This File checks Markdown and HTML with the built-in checkers and never
starts an outside tool; QUILL, which knows many more languages, checks those
too. That keeps QUILL Lite level with QUILL rather than ahead of it (rule 10).
"""

from __future__ import annotations

from pathlib import Path

from quill.ui.problems_commands import ProblemsCommandsMixin

__all__ = ["DocumentCodeNavMixin"]


class DocumentCodeNavMixin(ProblemsCommandsMixin):
    """Next / Previous Block and Indent Change, Check This File, the problem keys."""

    # -- blocks ------------------------------------------------------------- #

    def _lite_block_pattern(self) -> str:
        if self.markup_surface() != "html":
            return ""
        from quill.core.language_profile import get_profile_by_name

        profile = get_profile_by_name("HTML")
        return profile.block_pattern if profile is not None else ""

    def cmd_next_block(self) -> None:
        """Next Block: the next paragraph, or in HTML the next heading or landmark."""
        self._walk_block(forward=True)

    def cmd_previous_block(self) -> None:
        """Previous Block: as Next Block, backwards."""
        self._walk_block(forward=False)

    def _walk_block(self, *, forward: bool) -> None:
        from quill.core.navigation import next_block_start, previous_block_start

        text = self.control.GetValue()
        caret = int(self.control.GetInsertionPoint())
        finder = next_block_start if forward else previous_block_start
        target = finder(text, caret, self._lite_block_pattern())
        if target is None:
            self._announce("No next block" if forward else "No previous block")
            return
        # The screen reader reads the line the caret lands on; nothing to add.
        self._go_to(target)

    # -- indent changes ------------------------------------------------------ #

    def cmd_next_indent(self) -> None:
        """Next Indent Change: the next line, skipping blanks, indented differently."""
        self._walk_indent(forward=True)

    def cmd_previous_indent(self) -> None:
        """Previous Indent Change: as Next Indent Change, backwards."""
        self._walk_indent(forward=False)

    def _walk_indent(self, *, forward: bool) -> None:
        from quill.core.navigation import describe_indent, indent_change_target

        text = self.control.GetValue()
        target = indent_change_target(text, int(self.control.GetInsertionPoint()), forward=forward)
        if target is None:
            self._announce("No change of indent below" if forward else "No change of indent above")
            return
        self._go_to(target)
        # The reader says the line; how deep it sits is the part it may not.
        self._announce(describe_indent(text, target).capitalize())

    # -- Check This File and the problem keys --------------------------------- #

    def cmd_check_this_file(self) -> None:
        """Check This File: every problem in a Markdown or HTML document, as a list."""
        if self._problems_surface() is None:
            self._announce(_NOTHING_TO_CHECK)
            return
        self._check_this_file()

    def cmd_next_problem(self) -> None:
        """Next Problem: move to the next problem and say what it is."""
        if self._problems_surface() is None:
            self._announce(_NOTHING_TO_CHECK)
            return
        self._step_problem(forward=True)

    def cmd_previous_problem(self) -> None:
        """Previous Problem: as Next Problem, backwards."""
        if self._problems_surface() is None:
            self._announce(_NOTHING_TO_CHECK)
            return
        self._step_problem(forward=False)

    def _problems_surface(self) -> str | None:
        return self.markup_surface()

    def _problems_text(self) -> str:
        return str(self.control.GetValue())

    def _problems_caret(self) -> int:
        return int(self.control.GetInsertionPoint())

    def _problems_language(self) -> str:
        return self._problems_surface() or "plain"

    def _problems_path(self) -> Path | None:
        return getattr(self, "path", None)

    def _problems_modified(self) -> bool:
        return bool(getattr(self, "modified", True))

    def _problems_go_to(self, offset: int) -> None:
        self._go_to(offset)

    def _problems_say(self, message: str) -> None:
        self._announce(message)

    def _problems_choose(self, summary: str, rows: list[str]) -> int | None:
        from quill.apps.lite_dialogs import choose_from_rows

        chosen = choose_from_rows(
            self,
            title="Problems",
            label=f"{summary} &Problems:",
            help_text=(
                "Every problem Check This File found, in document order, with its "
                "line and column. Press Enter to go to the one selected; Escape "
                "closes the list. Next Problem and Previous Problem walk the same "
                "list from the document without opening it."
            ),
            rows=[(index, row) for index, row in enumerate(rows)],
        )
        if chosen is None:
            self.control.SetFocus()
            return None
        return int(chosen) if isinstance(chosen, int) else None


_NOTHING_TO_CHECK = (
    "Nothing to check: QUILL Lite checks Markdown and HTML documents. "
    "QUILL checks code and data files too."
)
