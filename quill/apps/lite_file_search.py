"""Search in Files and Replace Across Files, in QUILL Lite.

QUILL has had both since 2026-09; QUILL Lite reserved their key
(Ctrl+Alt+Shift+F) and never filled it, so somebody with a hundred files had
to open QUILL for a job the small editor is otherwise right for. Asked for on
QUILLVille by Chris Nova, October 2026.

Everything that decides anything is shared with QUILL: the window
(``quill/ui/file_search_prompt``), the search and the replace
(``quill/core/file_search``), and the reports they write. What is QUILL
Lite's own is only where the answer goes -- a new untitled window, the way
QUILL opens a generated tab -- and running the work on the app's task manager
so a big folder never freezes the window a screen reader is reading.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

__all__ = ["DocumentFileSearchMixin"]


class DocumentFileSearchMixin:
    """``cmd_search_in_files`` and ``cmd_replace_in_files``. On ``DocumentFrame``."""

    app: Any
    path: Path | None

    def _announce(self, text: str, **kwargs: Any) -> None:  # provided by the window
        raise NotImplementedError

    def _file_search_request(self, *, replace: bool) -> Any:
        import wx

        from quill.ui.dialog_contract import show_message_box, show_modal_dialog
        from quill.ui.file_search_prompt import prompt_file_search

        start = Path(self.path).parent if getattr(self, "path", None) else Path.cwd()
        return prompt_file_search(
            parent=self,
            default_root=start,
            replace=replace,
            show_modal=show_modal_dialog,
            show_message=lambda message, caption, style: show_message_box(
                message, caption, style, self
            ),
            wx_module=wx,
        )

    def _run_file_task(
        self, name: str, work: Callable[[], Any], done: Callable[[Any], None]
    ) -> None:
        from quill.apps.lite_window_open import app_task_manager

        def failed(_op: str, error: BaseException) -> None:
            self._announce(f"{name} failed: {error}")

        app_task_manager(self.app).submit(
            name,
            lambda **_kwargs: work(),
            on_success=lambda _op, result: done(result),
            on_failure=failed,
        )

    def _show_report(self, text: str) -> None:
        """The report in a new untitled window, ready to read or save."""
        window = self.app.new_window(getattr(self.app.settings, "default_mode", "plain"))
        window.control.SetValue(text)
        window.control.SetInsertionPoint(0)

    def cmd_search_in_files(self) -> None:
        """Ctrl+Alt+Shift+F: search a folder of files, as QUILL does."""
        from quill.core.file_search import render_search_report, search_files

        request = self._file_search_request(replace=False)
        if request is None:
            return
        self._announce("Searching files.")

        def done(report: Any) -> None:
            self._show_report(render_search_report(report, request.output_mode))
            self._announce(
                f"{report.total_matches} matches in {len(report.entries)} of "
                f"{report.scanned_files} files."
            )

        self._run_file_task(
            "Search in Files",
            lambda: search_files(request.root, request.pattern, request.query, request.options),
            done,
        )

    def cmd_replace_in_files(self) -> None:
        """Ctrl+Shift+R: replace across a folder of files, as QUILL does.

        With Preview before replacing checked -- it is, when the window opens --
        every change is shown first and nothing is written until you say yes.
        """
        from quill.core.file_search import (
            render_replace_preview,
            render_replace_report,
            replace_files,
            search_files,
        )

        request = self._file_search_request(replace=True)
        if request is None:
            return
        replacement = request.replacement or ""

        def write() -> None:
            self._announce("Replacing in files.")

            def written(report: Any) -> None:
                self._show_report(render_replace_report(report))
                self._announce("Replace Across Files finished. The report is in a new window.")

            self._run_file_task(
                "Replace Across Files",
                lambda: replace_files(
                    request.root, request.pattern, request.query, replacement, request.options
                ),
                written,
            )

        if not request.preview_before_replace:
            write()
            return

        def previewed(report: Any) -> None:
            import wx

            from quill.ui.dialog_contract import show_message_box

            self._show_report(render_replace_preview(report, replacement))
            if report.total_matches == 0:
                self._announce("No matches, so nothing would change.")
                return
            answer = show_message_box(
                f"Replace {report.total_matches} matches in {len(report.entries)} files? "
                "The files are changed on disk.",
                "Replace Across Files",
                wx.ICON_QUESTION | wx.YES_NO | wx.NO_DEFAULT,
                self,
            )
            if answer == wx.YES:
                write()
            else:
                self._announce("Nothing was replaced.")

        self._announce("Previewing replacements.")
        self._run_file_task(
            "Replace Across Files preview",
            lambda: search_files(request.root, request.pattern, request.query, request.options),
            previewed,
        )
