"""The plan-options action in Choose Your AI."""

from __future__ import annotations

from typing import Any

from quill.core.ai import connection_words as words
from quill.core.ai.connection_caps import CHATGPT, CODEX

__all__ = ["PlanOptionsActionMixin"]


class PlanOptionsActionMixin:
    """Open and report the ChatGPT plan options for the selected row."""

    _service: Any
    _hooks: Any

    def _selected_row(self) -> Any: ...

    def _after_change(self, connection: str) -> None: ...

    def plan_options(self) -> None:
        """ChatGPT Plan Options: web search, and Forget on This Computer."""
        from quill.ui.hosted_ai_plan_options import show_plan_options

        row = self._selected_row()
        if row is None or row.connection not in (CHATGPT, CODEX):
            return
        was_in_use = self._service.connection_in_use in (CHATGPT, CODEX)
        agent = self._hooks.app_name
        if not show_plan_options(self, self._service.chatgpt, agent):
            self._hooks.changed()  # a web-search change can alter what the plan offers
            return
        self._service.connection_changed(CHATGPT)
        self._after_change(row.connection)
        lead = words.SIGNED_OUT_IN_USE + " " if was_in_use else ""
        self._hooks.announce(
            f"{lead}Forgotten on this computer. {agent} stays listed under Apps in "
            "ChatGPT's settings until you remove it there."
        )
