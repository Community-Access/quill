"""QUILL's AI status cell: the same cell QUILL Lite has (codex.md decision 19).

"AI: ChatGPT plan", "AI: free" -- the same text Which AI Am I Using (Ctrl+8)
speaks, shortened, read from the shared hosted-AI layer
(:meth:`quill.ui.hosted_ai_choose_commands.ChooseAiMixin.ai_status_text`) so
the two editors cannot word it two ways. Enter on the cell opens Choose Your
AI, as it does in QUILL Lite.

The ``project`` cell lives here too, for the same reason: "Project cli-tool,
main", from the shared project commands
(:meth:`quill.ui.project_task_commands.ProjectTaskMixin.project_status_text`);
Enter opens Do a Project Task.

A mixin of two small overrides rather than two more branches in
:mod:`quill.ui.main_frame_statusbar`, which is at its size budget (GATE-11).
Listed ahead of ``StatusBarMixin`` in ``MainFrame`` so these run first and
hand every other cell on unchanged. The Workbench cell (2026-11-08) is a base of
this one for the same reason: another cell QUILL Lite has with the same words
(:mod:`quill.ui.main_frame_github_status`).
"""

from __future__ import annotations

from quill.ui.main_frame_github_status import GitHubWorkbenchStatusCellMixin

__all__ = ["AiStatusCellMixin"]

_AI = "ai"
_PROJECT = "project"


class AiStatusCellMixin(GitHubWorkbenchStatusCellMixin):
    """The ``ai`` status cell's text and its Enter."""

    def _statusbar_text_for_item(self, item: str) -> str:
        if item == _PROJECT:
            text = getattr(self, "project_status_text", None)
            return str(text()) if callable(text) else ""
        if item == _AI:
            text = getattr(self, "ai_status_text", None)
            return str(text()) if callable(text) else ""
        return super()._statusbar_text_for_item(item)  # type: ignore[misc]

    def _activate_statusbar_cell(self, item: str) -> None:
        if item == _PROJECT:
            self.cmd_project_task()  # type: ignore[attr-defined]
            return
        if item == _AI:
            self.cmd_ai_choose()  # type: ignore[attr-defined]
            return
        super()._activate_statusbar_cell(item)  # type: ignore[misc]
