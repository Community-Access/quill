"""QUILL's AI status cell: the same cell QUILL Lite has (codex.md decision 19).

"AI: ChatGPT plan", "AI: free" -- the same text Which AI Am I Using (Ctrl+8)
speaks, shortened, read from the shared hosted-AI layer
(:meth:`quill.ui.hosted_ai_choose_commands.ChooseAiMixin.ai_status_text`) so
the two editors cannot word it two ways. Enter on the cell opens Choose Your
AI, as it does in QUILL Lite.

A mixin of two small overrides rather than two more branches in
:mod:`quill.ui.main_frame_statusbar`, which is at its size budget (GATE-11).
Listed ahead of ``StatusBarMixin`` in ``MainFrame`` so these run first and
hand every other cell on unchanged.
"""

from __future__ import annotations

__all__ = ["AiStatusCellMixin"]

_AI = "ai"


class AiStatusCellMixin:
    """The ``ai`` status cell's text and its Enter."""

    def _statusbar_text_for_item(self, item: str) -> str:
        if item == _AI:
            text = getattr(self, "ai_status_text", None)
            return str(text()) if callable(text) else ""
        return super()._statusbar_text_for_item(item)  # type: ignore[misc]

    def _activate_statusbar_cell(self, item: str) -> None:
        if item == _AI:
            self.cmd_ai_choose()  # type: ignore[attr-defined]
            return
        super()._activate_statusbar_cell(item)  # type: ignore[misc]
