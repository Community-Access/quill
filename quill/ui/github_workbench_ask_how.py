"""Help > Ask How...: a question in plain words, answered from the help (PRD D18, GH-R-118).

The grounding, the request's words and the commands an answer names are
:mod:`quill.core.github.ask_how`; this asks the question, sends the one
request through the editor's Choose Your AI (``ai_ask``, given by the editor
that opened the window), and shows the answer with a Do It row for each
command it names. Nothing runs until the person chooses a row, and then
with that command's own preview.

Off without an AI connection: the editor's AI says so and offers Choose Your
AI. When the help holds nothing on the question, the AI is not asked.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

__all__ = ["ASK_HOW_REASONS", "ASK_HOW_VERBS", "GitHubWorkbenchAskHowMixin", "ask_through_editor"]

ASK_HOW_VERBS: dict[str, frozenset[str]] = {"ask_how": frozenset({"view"})}
ASK_HOW_REASONS: dict[str, str] = {
    "ask_how": "Ask How needs an AI connection: choose one with Choose Your AI in the editor, "
    "and it is off in Safe Mode.",
}
_TITLE = "Ask How"


class GitHubWorkbenchAskHowMixin:
    frame: Any
    menu: Any
    ai_ask: Callable[[str, Callable[[str], None]], bool] | None
    _say: Callable[[str], None]
    _ask_text: Callable[..., str]

    def _fits_ask_how(self, _row: object) -> bool:
        import os

        return (
            getattr(self, "ai_ask", None) is not None and os.environ.get("QUILL_SAFE_MODE") != "1"
        )

    def _menu_help_rows(self) -> list[tuple[str, str, str, str]]:
        """Every menu row as (command id, label, key, help), keys as bound now."""
        from quill.core.workbench.menus import all_rows

        keys = getattr(self.frame, "_keys", {}) if self.frame is not None else {}
        return [
            (row.command_id, row.label, keys.get(row.command_id, row.key), row.help)
            for _spec, row in all_rows(getattr(self, "menu", ()))
        ]

    def _do_ask_how(self, _ref: Any, _row: object) -> None:
        from quill.core.github import ask_how

        question = self._ask_text(
            _TITLE, "Ask how to do something in the GitHub Workbench, in your own words:"
        )
        if not question:
            return
        rows = self._menu_help_rows()
        found = ask_how.passages(question, ask_how.corpus(rows))
        if not found:
            self._say(f"{ask_how.NOT_COVERED} Search Help, Ctrl+Shift+F1, looks by single words.")
            return
        asker = getattr(self, "ai_ask", None)
        labels = {command_id: label for command_id, label, _key, _help in rows}
        helps = {command_id: help_text for command_id, _label, _key, help_text in rows}
        if asker is None:
            self._say(ASK_HOW_REASONS["ask_how"])
            return
        # False when the editor's AI refused (Safe Mode, no connection): it said why.
        asker(
            ask_how.prompt(question, found),
            lambda answer: self._show_ask_how(question, answer, labels, helps),
        )

    def _show_ask_how(
        self, question: str, answer: str, labels: dict[str, str], helps: dict[str, str]
    ) -> None:
        from quill.core.github import ask_how
        from quill.ui.workbench_help_dialogs import ActionChoice, ActionListDialog

        words = answer.strip() or ask_how.NOT_COVERED
        choices = [ActionChoice(f"Answer: {words}", True, lambda: self._say(words), words)]
        if words != ask_how.NOT_COVERED:
            for label, command_id in ask_how.commands_named(words, labels):
                choices.append(
                    ActionChoice(
                        f"Do It: {label}",
                        True,
                        lambda c=command_id: self.frame.run(c),
                        helps.get(command_id, "") + " It runs with its own preview, if it has one.",
                    )
                )
        ActionListDialog(self.frame.frame, _TITLE, f"You asked: {question}", choices).show()


def ask_through_editor(owner: Any, prompt: str, on_answer: Callable[[str], None]) -> bool:
    """Ask How's one request through *owner*'s Choose Your AI; True if it was sent.

    *owner* is the editor (QUILL's main frame or a QUILL Lite window), both of
    which carry the shared hosted-AI mixin: its readiness check (Safe Mode, the
    agreement, a connection) and the capability gate run first and say why
    when they refuse, as for every other AI request (GATE-CAPS).
    """
    ready = getattr(owner, "_ai_ready", None)
    capable = getattr(owner, "_ai_capable", None)
    service = getattr(owner, "_ai_service", None)
    if not (callable(ready) and callable(capable) and callable(service)):
        return False
    if not ready() or not capable("text"):
        return False
    announce = getattr(owner, "_announce", None)
    if callable(announce):
        announce("Asking your AI.")
    service().ask(
        "ask",
        prompt,
        None,
        on_done=lambda text, _quota: on_answer(str(text or "").strip()),
        on_error=lambda sentence: announce(sentence) if callable(announce) else None,
        requires=("text",),
    )
    return True
