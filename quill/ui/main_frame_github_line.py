"""QUILL's half of GitHub from the editor (GitHub PRD 22.3, 2026-11-17).

The commands are :mod:`quill.ui.github_editor_line`'s, shared with QUILL Lite;
this mixin only says what "the window" means in QUILL's terms (its editor, its
document, its task manager, its clipboard and its GitHub openers) through one
:class:`~quill.ui.github_editor_line.LineHost`. If this class ever grows a
command of its own, the capability has forked.

Who Changed This Line? keeps Local Git's command id,
``localgit.blame_at_cursor``; its old handler there now comes here. The old
one asked the editor for ``GetCurrentLine()``, which QUILL's text control does
not have, so it always answered for line 1; the line now comes from the text,
as Go To Line's does.
"""

from __future__ import annotations

from typing import Any

__all__ = ["LINE_HANDLERS", "GitHubLineCommandsMixin"]

#: The command each From This Line row runs, by QUILL command id.
LINE_HANDLERS: dict[str, str] = {
    "github.copy_line_link": "copy_line_link",
    "localgit.blame_at_cursor": "who_changed_line",
    "github.open_line_pull": "open_line_pull",
    "github.open_line": "open_line",
    "github.issue_from_selection": "issue_from_selection",
    "github.issues_mentioning_file": "issues_mentioning_file",
    "github.comment_on_line": "comment_on_line",
    "github.open_reference_at_cursor": "open_reference_at_cursor",
}

#: Their titles in the command registry and the Command Palette.
LINE_TITLES: dict[str, str] = {
    "github.copy_line_link": "Copy GitHub Link to This Line",
    "localgit.blame_at_cursor": "Who Changed This Line?",
    "github.open_line_pull": "Open the Pull Request for This Line",
    "github.open_line": "Open This Line on GitHub",
    "github.issue_from_selection": "New GitHub Issue from Selection...",
    "github.issues_mentioning_file": "GitHub Issues Mentioning This File",
    "github.comment_on_line": "Comment on This Line in the Open Pull Request...",
    "github.open_reference_at_cursor": "Open the GitHub Reference at the Cursor",
}


class GitHubLineCommandsMixin:
    """GitHub > From This Line, in QUILL."""

    def run_github_line_command(self, command_id: str) -> None:
        """Run a From This Line command by its QUILL command id."""
        from quill.ui import github_editor_line

        getattr(github_editor_line, LINE_HANDLERS[command_id])(self._github_line_host())

    def _github_line_host(self) -> Any:
        from quill.ui.github_editor_line import LineHost

        def run_background(name: str, work: Any, on_done: Any, on_failed: Any) -> None:
            self._task_manager.submit(  # type: ignore[attr-defined]
                name,
                lambda **_kwargs: work(),
                on_success=lambda _op, result: on_done(result),
                on_failure=lambda _op, error: on_failed(error),
            )

        def open_workbench(repository: str, then: str) -> None:
            self.open_github_items_viewer(repository=repository, then=then)  # type: ignore[attr-defined]

        def open_reference(reference: Any, then: str) -> None:
            self.open_github_items_viewer_for(  # type: ignore[attr-defined]
                reference.repository, initial_reference=reference, then=then
            )

        return LineHost(
            parent=self.frame,  # type: ignore[attr-defined]
            announce=self._announce,  # type: ignore[attr-defined]
            run_background=run_background,
            copy_text=self._copy_to_clipboard,  # type: ignore[attr-defined]
            file_path=lambda: str(getattr(getattr(self, "document", None), "path", "") or ""),
            span=self._github_line_span,
            text_and_offset=self._github_line_text_and_offset,
            provider=self._github_line_provider,
            open_workbench=open_workbench,
            open_reference=open_reference,
            show_modal=self._show_modal_dialog,  # type: ignore[attr-defined]
            safe_mode=bool(getattr(self, "_safe_mode", False)),
        )

    def _github_line_text_and_offset(self) -> tuple[str, int]:
        editor = getattr(self, "editor", None)
        if editor is None:
            return "", 0
        return str(editor.GetValue()), int(editor.GetInsertionPoint())

    def _github_line_span(self) -> tuple[int, int, str]:
        """The selection's first and last line (1-based), and its text."""
        editor = getattr(self, "editor", None)
        if editor is None:
            return 1, 1, ""
        text = str(editor.GetValue())
        start, end = editor.GetSelection()
        if end <= start:
            line = text.count("\n", 0, int(editor.GetInsertionPoint())) + 1
            return line, line, ""
        first = text.count("\n", 0, start) + 1
        # A selection that ends at the start of a line does not take that line.
        last = text.count("\n", 0, max(start, end - 1)) + 1
        return first, last, text[start:end]

    def _github_line_provider(self, retry: Any) -> Any:
        """The GitHub gates every QUILL GitHub command passes, then a provider."""
        from quill.core.github.items_provider import (
            GitHubItemsError,
            GitHubItemsProvider,
            refuse_in_safe_mode,
        )
        from quill.core.github.token_store import load_github_token

        wx = self._wx  # type: ignore[attr-defined]
        try:
            refuse_in_safe_mode(bool(getattr(self, "_safe_mode", False)))
        except GitHubItemsError as exc:
            self._show_message_box(str(exc), "GitHub", wx.ICON_INFORMATION | wx.OK)  # type: ignore[attr-defined]
            return None
        if not self._ensure_github_ready():  # type: ignore[attr-defined]
            return None
        token = load_github_token()
        try:
            return GitHubItemsProvider(token=token or None)
        except GitHubItemsError as exc:
            self._show_message_box(str(exc), "GitHub", wx.ICON_INFORMATION | wx.OK)  # type: ignore[attr-defined]
            return None
