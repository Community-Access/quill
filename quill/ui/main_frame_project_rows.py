"""QUILL's half of project tasks: the menu rows and the in-place reload (code.md 5.4, 6.4).

No commands of its own. Every handler is the shared
:class:`~quill.ui.project_task_commands.ProjectTaskMixin`'s, the same ones QUILL
Lite's command table names, so the two editors cannot do a project task two
ways (rule 10). What lives here is only what QUILL's frame does differently:

- **The Project Tasks submenu** in the AI menu, built only while the Developer
  profile's ``core.developer`` is on, so nobody else meets a developer row in a
  menu. Each row shows its key through ``_menu_label``.
- **Reloading a file a turn changed** in whichever tab it is open in, without
  switching tabs (a tab switch would move focus), with the cursor kept where
  it was, and one spoken line for all of them. A tab with unsaved edits is
  left alone and named, because overwriting someone's typing is worse than a
  stale view.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

__all__ = ["PROJECT_ROWS", "ProjectRowsMixin"]

#: ``(command id, label, shared handler)``, in menu order. No access keys: the
#: AI menu has spent its letters, and a duplicate is worse than none (GATE-14).
PROJECT_ROWS: tuple[tuple[str, str, str], ...] = (
    ("project.open_folder", "Open Project Folder...", "cmd_open_project_folder"),
    ("project.task", "Do a Project Task...", "cmd_project_task"),
    ("project.stop_agent", "Stop Agent", "cmd_stop_agent"),
    ("project.undo_turn", "Undo Last Agent Turn", "cmd_undo_agent_turn"),
    ("project.explain_turn", "Explain Last Turn", "cmd_explain_agent_turn"),
    ("project.command_output", "Open Command Output", "cmd_open_command_output"),
    ("project.transcript", "Open Task Transcript", "cmd_project_transcript"),
    (
        "project.allowed_commands",
        "Commands Allowed in This Project...",
        "cmd_project_allowed_commands",
    ),
    ("project.engine_tools", "Engine Tools for This Project...", "cmd_project_engine_tools"),
    ("project.close", "Close Project", "cmd_close_project"),
)

#: Suffixes QUILL edits as plain text, and so can reload by setting the text.
_PLAIN = frozenset({"", ".txt", ".md", ".py", ".js", ".ts", ".json", ".toml", ".yml", ".yaml"})


class ProjectRowsMixin:
    """Mixed into QUILL's hosted-AI adapter; adds rows and a reload, never a command."""

    def _project_menu_ids(self) -> dict[str, Any]:
        ids = getattr(self, "_project_row_ids", None)
        if ids is None:
            import wx

            ids = {cid: wx.NewIdRef() for cid, _label, _h in PROJECT_ROWS}
            self._project_row_ids = ids
        return ids

    def _project_rows_visible(self) -> bool:
        features = getattr(self, "features", None)
        check = getattr(features, "is_enabled", None)
        return bool(callable(check) and check("core.developer"))

    def _append_project_rows(self, ai_menu: Any) -> None:
        """The Project Tasks submenu, only in the Developer profile (code.md 6.4)."""
        import wx

        from quill.core.i18n import _

        if not self._project_rows_visible():
            return
        ids = self._project_menu_ids()
        submenu = wx.Menu()
        for command_id, label, _handler in PROJECT_ROWS:
            submenu.Append(ids[command_id], self._menu_label(_(label), command_id))  # type: ignore[attr-defined]
        ai_menu.AppendSubMenu(submenu, _("Project Tasks"))
        if getattr(self, "_project_rows_wired", False):
            return
        self._project_rows_wired = True
        for command_id, label, handler_name in PROJECT_ROWS:
            handler = getattr(self, handler_name)
            self.frame.Bind(wx.EVT_MENU, lambda _e, run=handler: run(), id=ids[command_id])  # type: ignore[attr-defined]
            self.commands.try_register(  # type: ignore[attr-defined]
                command_id,
                label.rstrip("."),
                handler,
                self._binding_for(command_id),  # type: ignore[attr-defined]
            )

    def _refresh_project_cell(self) -> None:
        """The title names the project; the status line says so once (no extra speech)."""
        refresh = getattr(self, "_refresh_title", None)
        if callable(refresh):
            refresh()

    def _reload_agent_changed(self, paths: list[Path]) -> None:
        from quill.core.ai import project_task_words as words

        wanted = {Path(p).resolve() for p in paths}
        updated: list[str] = []
        kept: list[str] = []
        for tab in getattr(self, "_document_tabs", []):
            path = getattr(tab.document, "path", None)
            if path is None or Path(path).resolve() not in wanted:
                continue
            name = Path(path).name
            if getattr(tab.document, "modified", False) or Path(path).suffix.lower() not in _PLAIN:
                kept.append(name)
                continue
            try:
                text = Path(path).read_text("utf-8")
            except (OSError, UnicodeDecodeError):
                kept.append(name)
                continue
            editor = tab.editor
            caret = editor.GetInsertionPoint()
            tab.document.set_text(text)
            editor.ChangeValue(text)
            editor.SetInsertionPoint(max(0, min(caret, editor.GetLastPosition())))
            tab.document.modified = False
            updated.append(name)
        said = words.files_reloaded(updated, kept)
        if said:
            self._announce(said)  # type: ignore[attr-defined]
