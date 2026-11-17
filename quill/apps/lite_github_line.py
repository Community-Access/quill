"""QUILL Lite's half of GitHub from the editor (GitHub PRD 22.3, 2026-11-17).

The commands are :mod:`quill.ui.github_editor_line`'s, shared with QUILL; this
mixin only says what "the window" means in QUILL Lite's terms (its control,
its path, its task manager, its clipboard and its GitHub opener) through one
:class:`~quill.ui.github_editor_line.LineHost`. If this class ever grows a
command of its own, the capability has forked.

Mixed into :class:`~quill.apps.lite_window_tools.DocumentToolsMixin`, beside
the other GitHub mixins, so only a document window has these commands: the
empty window has no line to ask about.
"""

from __future__ import annotations

from typing import Any

__all__ = ["GitHubLineLiteMixin"]


class GitHubLineLiteMixin:
    """GitHub > From This Line, in a QUILL Lite document window."""

    app: Any
    path: Any
    control: Any

    def _github_line_host(self) -> Any:
        from quill.apps.lite_window_open import app_task_manager
        from quill.ui.dialog_contract import show_modal_dialog
        from quill.ui.github_editor_line import LineHost

        def run_background(name: str, work: Any, on_done: Any, on_failed: Any) -> None:
            app_task_manager(self.app).submit(
                name,
                lambda **_kwargs: work(),
                on_success=lambda _op, result: on_done(result),
                on_failure=lambda _op, error: on_failed(error),
            )

        return LineHost(
            parent=self,
            announce=self._announce,  # type: ignore[attr-defined]
            run_background=run_background,
            copy_text=self._set_clipboard_text,  # type: ignore[attr-defined]
            file_path=lambda: str(self.path or ""),
            span=self._github_line_span,
            text_and_offset=lambda: (
                str(self.control.GetValue()),
                int(self.control.GetInsertionPoint()),
            ),
            provider=lambda retry: self._github_provider(retry),  # type: ignore[attr-defined]
            open_workbench=lambda _repository, then: self.open_github_items(  # type: ignore[attr-defined]
                then=then
            ),
            open_reference=lambda reference, then: self.open_github_items(  # type: ignore[attr-defined]
                reference=reference, then=then
            ),
            show_modal=lambda dialog, label: show_modal_dialog(dialog, label),
            safe_mode=bool(getattr(self.app, "safe_mode", False)),
        )

    def _github_line_span(self) -> tuple[int, int, str]:
        """The selection's first and last line (1-based), and its text."""
        text = str(self.control.GetValue())
        start, end = self.control.GetSelection()
        if end <= start:
            caret = int(self.control.GetInsertionPoint())
            line = text.count("\n", 0, caret) + 1
            return line, line, ""
        first = text.count("\n", 0, start) + 1
        # A selection that ends at the start of a line does not take that line.
        last = text.count("\n", 0, max(start, end - 1)) + 1
        return first, last, text[start:end]

    def cmd_github_copy_line_link(self) -> None:
        from quill.ui.github_editor_line import copy_line_link

        copy_line_link(self._github_line_host())

    def cmd_github_who_changed_line(self) -> None:
        from quill.ui.github_editor_line import who_changed_line

        who_changed_line(self._github_line_host())

    def cmd_github_open_line_pull(self) -> None:
        from quill.ui.github_editor_line import open_line_pull

        open_line_pull(self._github_line_host())

    def cmd_github_open_line(self) -> None:
        from quill.ui.github_editor_line import open_line

        open_line(self._github_line_host())

    def cmd_github_issue_from_selection(self) -> None:
        from quill.ui.github_editor_line import issue_from_selection

        issue_from_selection(self._github_line_host())

    def cmd_github_issues_mentioning_file(self) -> None:
        from quill.ui.github_editor_line import issues_mentioning_file

        issues_mentioning_file(self._github_line_host())

    def cmd_github_comment_on_line(self) -> None:
        from quill.ui.github_editor_line import comment_on_line

        comment_on_line(self._github_line_host())

    def cmd_github_open_reference_at_cursor(self) -> None:
        from quill.ui.github_editor_line import open_reference_at_cursor

        open_reference_at_cursor(self._github_line_host())
