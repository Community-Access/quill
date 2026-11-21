"""Ask How: answered from the help alone, through the family's AI (PRD D18, GH-R-118)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from quill.core.github import ask_how
from quill.core.github.workbench_window_menu import WINDOW_MENU
from quill.core.workbench.menus import all_rows

ROWS = [(row.command_id, row.label, row.key, row.help) for _spec, row in all_rows(WINDOW_MENU)]


def test_the_question_meets_the_help_that_covers_it() -> None:
    found = ask_how.passages("how do I filter a list", ask_how.corpus(ROWS))
    assert found and any("filter" in p.text().casefold() for p in found)
    assert len(found) <= ask_how.MAX_PASSAGES


def test_nothing_in_the_help_means_no_passages() -> None:
    assert ask_how.passages("zzqx florp", ask_how.corpus(ROWS)) == []
    assert ask_how.passages("how do I", ask_how.corpus(ROWS)) == []


def test_the_prompt_holds_only_the_help_and_says_how_to_not_know() -> None:
    found = [ask_how.Passage("Filter...", "Move to the filter box.", "x")]
    text = ask_how.prompt("how do I filter?", found)
    assert "ONLY the help passages" in text
    assert ask_how.NOT_COVERED in text
    assert "you cannot act" in text
    assert "- Filter...: Move to the filter box." in text
    assert text.rstrip().endswith("Question: how do I filter?")


def test_the_commands_an_answer_names_are_found_in_order() -> None:
    labels = {"a": "&Filter...", "b": "Load &More", "c": "Go"}
    answer = "Press Load More, then use Filter with Ctrl+E. Go is too short to find."
    assert ask_how.commands_named(answer, labels) == [("Load More", "b"), ("Filter", "a")]


class _Provider:
    """The Ask How mixin on a provider-shaped fake."""

    def __init__(self, ai_ask: Any, question: str = "how do I filter a list") -> None:
        from quill.ui.github_workbench_ask_how import GitHubWorkbenchAskHowMixin

        self.mixin = type("P", (GitHubWorkbenchAskHowMixin,), {})()
        self.said: list[str] = []
        self.shown: list[tuple[str, str]] = []
        self.mixin.menu = WINDOW_MENU
        self.mixin.frame = SimpleNamespace(_keys={})
        self.mixin.ai_ask = ai_ask
        self.mixin._say = self.said.append
        self.mixin._ask_text = lambda *_a, **_k: question
        self.mixin._show_ask_how = lambda q, answer, _labels, _helps: self.shown.append((q, answer))


def test_the_ai_gets_the_grounded_prompt_and_its_answer_is_shown() -> None:
    sent: list[str] = []

    def ai_ask(prompt: str, on_answer: Any) -> bool:
        sent.append(prompt)
        on_answer("Press Filter..., Ctrl+E.")
        return True

    provider = _Provider(ai_ask)
    provider.mixin._do_ask_how(None, None)
    assert len(sent) == 1 and "Help passages:" in sent[0]
    assert provider.shown == [("how do I filter a list", "Press Filter..., Ctrl+E.")]


def test_help_that_does_not_cover_it_never_asks_the_ai() -> None:
    sent: list[str] = []
    provider = _Provider(lambda prompt, _done: sent.append(prompt) or True, "zzqx florp")
    provider.mixin._do_ask_how(None, None)
    assert sent == [] and provider.said[0].startswith(ask_how.NOT_COVERED)


def test_without_an_ai_connection_it_is_greyed_with_a_reason(monkeypatch) -> None:
    monkeypatch.delenv("QUILL_SAFE_MODE", raising=False)
    provider = _Provider(None)
    assert not provider.mixin._fits_ask_how(None)
    provider.mixin._do_ask_how(None, None)
    assert "Choose Your AI" in provider.said[0]
    assert _Provider(lambda *_a: True).mixin._fits_ask_how(None)


def test_the_request_goes_through_the_editors_choose_your_ai() -> None:
    from quill.ui.github_workbench_ask_how import ask_through_editor

    asked: list[tuple[str, str, tuple[str, ...]]] = []
    answers: list[str] = []

    class Service:
        def ask(self, feature: str, prompt: str, _ctx: Any, *, on_done, on_error, requires):
            asked.append((feature, prompt, requires))
            on_done(" Ctrl+E. ", None)

    class Editor:
        def __init__(self, ready: bool) -> None:
            self.ready, self.said = ready, []

        def _ai_ready(self) -> bool:
            return self.ready

        def _ai_capable(self, _what: str) -> bool:
            return True

        def _ai_service(self) -> Service:
            return Service()

        def _announce(self, text: str) -> None:
            self.said.append(text)

    assert ask_through_editor(Editor(True), "p", answers.append)
    assert asked == [("ask", "p", ("text",))] and answers == ["Ctrl+E."]
    assert not ask_through_editor(Editor(False), "p", answers.append)
    assert not ask_through_editor(object(), "p", answers.append)
    assert len(asked) == 1
