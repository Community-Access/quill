"""QUILL's half of project tasks: where the rows sit, and the in-place reload (code.md 5.4, 6.4).

No commands of its own. Every handler is the shared
:class:`~quill.ui.project_task_commands.ProjectTaskMixin`'s, the same ones QUILL
Lite's command table names, so the two editors cannot do a project task two
ways (rule 10). What lives here is only what QUILL's frame does differently:

- **Where the rows are.** Each Developer command sits where people already
  look for that kind of command (Jeff, 2026-11-04), the same menus as QUILL
  Lite: Open Project Folder and Close Project in File, above Exit; Undo Last
  Agent Turn and Stop Agent in Edit > Agent Work; the task's transcript and
  command output in View; Commands Allowed in This Project in Tools; and Do a
  Project Task, Explain Last Turn and Engine Tools in the AI menu's second
  group, what the AI does (``quill/core/ai/ai_menu_layout.py``). The rows are
  built only while ``core.developer`` is on, so nobody outside the Developer
  profile meets one. Each shows its key through ``_menu_label``; none takes an
  access letter, because these menus have spent theirs and a duplicate is
  worse than none (GATE-14).
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

#: ``menu -> ((command id, label, shared handler), ...)``, in menu order.
PROJECT_ROWS: dict[str, tuple[tuple[str, str, str], ...]] = {
    "file": (
        ("project.open_folder", "Open Project Folder...", "cmd_open_project_folder"),
        ("project.close", "Close Project", "cmd_close_project"),
    ),
    "edit": (
        ("project.undo_turn", "Undo Last Agent Turn", "cmd_undo_agent_turn"),
        ("project.stop_agent", "Stop Agent", "cmd_stop_agent"),
    ),
    "view": (
        ("project.transcript", "Agent Task Transcript", "cmd_project_transcript"),
        ("project.command_output", "Agent Command Output", "cmd_open_command_output"),
    ),
    "tools": (
        (
            "project.allowed_commands",
            "Commands Allowed in This Project...",
            "cmd_project_allowed_commands",
        ),
    ),
    "ai": (
        ("project.task", "Do a Project Task...", "cmd_project_task"),
        ("project.explain_turn", "Explain Last Turn", "cmd_explain_agent_turn"),
        ("project.engine_tools", "Engine Tools for This Project...", "cmd_project_engine_tools"),
    ),
}

#: Suffixes QUILL edits as plain text, and so can reload by setting the text.
_PLAIN = frozenset({"", ".txt", ".md", ".py", ".js", ".ts", ".json", ".toml", ".yml", ".yaml"})


class ProjectRowsMixin:
    """Mixed into QUILL's hosted-AI adapter; places rows and reloads, never a command."""

    def _project_menu_ids(self) -> dict[str, Any]:
        ids = getattr(self, "_project_row_ids", None)
        if ids is None:
            import wx

            ids = {cid: wx.NewIdRef() for rows in PROJECT_ROWS.values() for cid, _l, _h in rows}
            self._project_row_ids = ids
        return ids

    def _project_rows_visible(self) -> bool:
        features = getattr(self, "features", None)
        check = getattr(features, "is_enabled", None)
        return bool(callable(check) and check("core.developer"))

    def _project_row(self, menu: Any, row: tuple[str, str, str], *, position: int = -1) -> None:
        import wx

        from quill.core.i18n import _

        command_id, label, handler_name = row
        menu_id = self._project_menu_ids()[command_id]
        text = self._menu_label(_(label), command_id)  # type: ignore[attr-defined]
        if position >= 0:
            menu.Insert(position, menu_id, text)
        else:
            menu.Append(menu_id, text)
        wired: set[str] = self.__dict__.setdefault("_project_rows_wired", set())
        if command_id in wired:
            return
        wired.add(command_id)
        handler = getattr(self, handler_name)
        self.frame.Bind(wx.EVT_MENU, lambda _e, run=handler: run(), id=menu_id)  # type: ignore[attr-defined]
        self.commands.try_register(  # type: ignore[attr-defined]
            command_id,
            label.rstrip("."),
            handler,
            self._binding_for(command_id),  # type: ignore[attr-defined]
        )

    def _append_project_rows(self, ai_menu: Any) -> None:
        """The AI menu's project rows, in its second group (ai_menu_layout.py)."""
        if not self._project_rows_visible():
            return
        for row in PROJECT_ROWS["ai"]:
            self._project_row(ai_menu, row)

    def _place_project_rows(
        self, *, file_menu: Any, edit_menu: Any, view_menu: Any, tools_menu: Any
    ) -> None:
        """File, Edit, View and Tools rows, the Developer profile only (code.md 6.4)."""
        import wx

        from quill.core.i18n import _

        if not self._project_rows_visible():
            return
        # File: above Exit and the separator before it, which stays last.
        exit_at = next(
            (i for i, item in enumerate(file_menu.GetMenuItems()) if item.GetId() == wx.ID_EXIT),
            file_menu.GetMenuItemCount(),
        )
        items = file_menu.GetMenuItems()
        if exit_at > 0 and items[exit_at - 1].IsSeparator():
            exit_at -= 1
        file_menu.InsertSeparator(exit_at)
        for offset, row in enumerate(PROJECT_ROWS["file"]):
            self._project_row(file_menu, row, position=exit_at + offset)
        agent = wx.Menu()
        for row in PROJECT_ROWS["edit"]:
            self._project_row(agent, row)
        edit_menu.AppendSeparator()
        edit_menu.AppendSubMenu(agent, _("Agent Work"))
        view_menu.AppendSeparator()
        for row in PROJECT_ROWS["view"]:
            self._project_row(view_menu, row)
        for row in PROJECT_ROWS["tools"]:
            self._project_row(tools_menu, row)

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
