"""Help > Practice on GitHub... (GitHub PRD 22.8)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from quill.ui.github_workbench_development import DEVELOPMENT_VERBS
from quill.ui.github_workbench_practice import GitHubWorkbenchPracticeMixin
from tests.unit.core.github_workbench.test_practice_repository import FakeApi


class _Window(GitHubWorkbenchPracticeMixin):
    signed_in = True

    def __init__(self, api: FakeApi, *, choice: int = 0, yes: bool = True) -> None:
        self.api, self.choice, self.yes = api, choice, yes
        self.said: list[str] = []
        self.went: list[str] = []
        self.asked: list[str] = []

    def github_api(self) -> Any:
        return self.api

    def _explore_client(self) -> Any:
        return SimpleNamespace(account_login=lambda: "me")

    def _go_repository(self, repository: str) -> None:
        self.went.append(repository)

    def _say(self, text: str) -> None:
        self.said.append(text)

    def _choose(self, title: str, prompt: str, labels: list[str]) -> int:
        self.asked.append(prompt)
        return self.choice

    def _confirm(self, title: str, question: str) -> bool:
        self.asked.append(question)
        return self.yes

    def _background(self, _name: str, work: Any, done: Any) -> None:
        done(work())


def test_registered() -> None:
    assert "practice" in DEVELOPMENT_VERBS


def test_the_first_time_asks_then_makes_and_opens_it() -> None:
    window = _Window(FakeApi())
    window._do_practice(None, None)
    assert "Make a private repository, me/quill-practice" in window.asked[0]
    assert window.went == ["me/quill-practice"]
    assert window.said[-1].endswith("Opening it.")


def test_no_makes_nothing() -> None:
    api = FakeApi()
    _Window(api, yes=False)._do_practice(None, None)
    assert not any(method == "POST" for method, _p, _b in api.sent)


def test_when_it_exists_open_or_start_over() -> None:
    window = _Window(FakeApi(exists=True), choice=0)
    window._do_practice(None, None)
    assert window.went == ["me/quill-practice"]
    api = FakeApi(exists=True)
    again = _Window(api, choice=1)
    again._do_practice(None, None)
    assert "cannot be undone. Then QUILL makes a fresh one." in again.asked[-1]
    assert ("DELETE", "/repos/me/quill-practice") in [(m, p) for m, p, _b in api.sent]
    assert again.said[0] == "Deleted me/quill-practice."
