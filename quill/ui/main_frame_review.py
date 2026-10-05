"""QUILL's half of Toggle Task Done and Export as HTML.

Both commands are shared with QUILL Lite (:mod:`quill.ui.task_list_commands`,
:mod:`quill.ui.html_export_commands`) and both came from reviewing plans the
way PlanCake (Andre of Oire Software) does: tick a task, and hand somebody a
page. This mixin registers them under QUILL's command ids, puts Toggle Task
Done in **Insert > List** beside Task, and gives Export as HTML a Pandoc path.

* ``format.toggle_task_done`` -- Ctrl+Alt+Enter, the same in both editors.
* ``file.export_html`` -- Ctrl+Alt+Shift+End, File > Export > HTML. It ran
  Pandoc without ``--standalone`` (a fragment, not a page) and had no key.

Pandoc, when installed, renders Markdown with ``--standalone``, the document's
title and language, and the shared stylesheet; without it, or for HTML and
plain text, QUILL's own renderer writes the page, as it does in QUILL Lite.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from quill.ui.html_export_commands import HtmlExportCommandsMixin
from quill.ui.main_frame_editor_host import QuillEditorHostMixin
from quill.ui.task_list_commands import TaskListCommandsMixin

__all__ = ["ReviewToolsMixin"]


class ReviewToolsMixin(QuillEditorHostMixin, TaskListCommandsMixin, HtmlExportCommandsMixin):
    """Registration, one menu row and the Pandoc override. No commands of its own."""

    def register_review_commands(self) -> None:
        self.commands.try_register(
            "format.toggle_task_done",
            "Toggle Task Done",
            self.cmd_toggle_task_done,
            self._binding_for("format.toggle_task_done"),
        )
        self.commands.try_register(
            "file.export_html",
            "Export as HTML",
            self.cmd_export_html,
            self._binding_for("file.export_html"),
        )

    def _task_toggle_menu_id(self) -> Any:
        menu_id = getattr(self, "_id_toggle_task_done", None)
        if menu_id is None:
            import wx

            menu_id = wx.NewIdRef()
            self._id_toggle_task_done = menu_id
        return menu_id

    def _append_task_toggle_row(self, list_menu: Any) -> None:
        """Insert > List > Toggle Task Done, after Task."""
        import wx

        from quill.core.i18n import _

        menu_id = self._task_toggle_menu_id()
        list_menu.Append(
            menu_id, self._menu_label(_("Toggle Task &Done"), "format.toggle_task_done")
        )
        if not getattr(self, "_task_toggle_wired", False):
            self._task_toggle_wired = True
            self.frame.Bind(wx.EVT_MENU, lambda _e: self.cmd_toggle_task_done(), id=menu_id)

    def _command_to_menu_id_map(self) -> dict[str, int]:
        mapping: dict[str, int] = super()._command_to_menu_id_map()  # type: ignore[misc]
        mapping["format.toggle_task_done"] = self._task_toggle_menu_id()
        if getattr(self, "_id_export_html", None) is not None:
            mapping["file.export_html"] = self._id_export_html
        return mapping

    def _write_html_export(
        self, target: Path, text: str, kind: str, title: str, include_notes: bool
    ) -> None:
        """Pandoc for Markdown when it is installed; QUILL's renderer otherwise."""
        from quill.core.external_tools import get_external_tool_status
        from quill.io.html_page import pandoc_html_args, prepare_for_pandoc, style_block
        from quill.io.pandoc import PandocConversionError, convert_file_with_pandoc

        if kind != "markdown" or not get_external_tool_status("pandoc").installed:
            super()._write_html_export(target, text, kind, title, include_notes)
            return
        with tempfile.TemporaryDirectory(prefix="quill-html-") as folder:
            source = Path(folder) / "document.md"
            header = Path(folder) / "style.html"
            source.write_text(prepare_for_pandoc(text, include_notes), encoding="utf-8")
            header.write_text(style_block(), encoding="utf-8")
            try:
                convert_file_with_pandoc(
                    source,
                    target,
                    from_format="gfm+hard_line_breaks",
                    to_format="html",
                    extra_args=pandoc_html_args(title, self._host_language(), str(header)),
                )
            except PandocConversionError:
                # Pandoc refused this document; the page still gets written.
                super()._write_html_export(target, text, kind, title, include_notes)
