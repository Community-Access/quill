"""Close an issue for its reason, and Create Branch for This Issue, in the Workbench window."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from quill.core.github.items_provider import GitHubItem
from quill.ui.github_workbench_development import GitHubWorkbenchDevelopmentMixin
from quill.ui.github_workbench_writes import GitHubWorkbenchWritesMixin
from tests.unit.core.github.test_issue_development import FakeApi

ISSUE = GitHubItem(
    number=7,
    title="Fix the parser",
    state="open",
    author="jeff",
    url="https://x/o/r/issues/7",
    is_pr=False,
)
PULL = GitHubItem(
    number=8,
    title="A pull",
    state="open",
    author="jeff",
    url="https://x/o/r/pull/8",
    is_pr=True,
)


class _Window(GitHubWorkbenchDevelopmentMixin, GitHubWorkbenchWritesMixin):
    signed_in = True

    def __init__(self, *, choice: int = -1, typed: str = "", confirm: bool = True) -> None:
        self.api = FakeApi()
        self.said: list[str] = []
        self.asked: list[tuple[str, str]] = []
        self.choice, self.typed, self.confirm = choice, typed, confirm
        self.updated: list[tuple[Any, ...]] = []
        self.frame = SimpleNamespace(reload=lambda: self.said.append("(reloaded)"))
        self.items = SimpleNamespace(
            update_items=lambda repo, numbers, state=None: self.updated.append((
                repo,
                numbers,
                state,
            ))
        )

    def github_api(self) -> Any:
        return self.api

    def _say(self, text: str) -> None:
        self.said.append(text)

    def _choose(self, title: str, prompt: str, labels: list[str]) -> int:
        self.asked.append((title, prompt))
        assert labels == ["Completed", "Not planned", "Duplicate of another issue..."]
        return self.choice

    def _ask_text(
        self, title: str, prompt: str, *, multiline: bool = False, value: str = ""
    ) -> str:
        self.asked.append((title, value))
        return self.typed

    def _confirm(self, title: str, question: str) -> bool:
        self.asked.append((title, question))
        return self.confirm

    def _background(self, _name: str, work: Any, done: Any) -> None:
        done(work())


REF = SimpleNamespace(instance="o/r")


def test_closing_an_issue_asks_why_and_cancel_sends_nothing() -> None:
    window = _Window(choice=-1)
    window._do_close_reopen(REF, ISSUE)
    assert window.asked == [("Close #7", "Close #7, Fix the parser, as:")]
    assert window.api.calls == [] and window.updated == []


def test_not_planned_is_sent_and_said() -> None:
    window = _Window(choice=1)
    window._do_close_reopen(REF, ISSUE)
    assert window.api.calls == [
        ("PATCH", "/repos/o/r/issues/7", {"state": "closed", "state_reason": "not_planned"})
    ]
    assert window.said == ["Closed #7 as not planned.", "(reloaded)"]


def test_a_duplicate_asks_for_the_original_by_number() -> None:
    window = _Window(choice=2, typed="#3")
    window._do_close_reopen(REF, ISSUE)
    assert window.said[0] == "Closed #7 as a duplicate of #3, Original."


@pytest.mark.parametrize(
    ("typed", "said"), [("", []), ("three", ["three is not an issue number."])]
)
def test_a_duplicate_without_a_number_sends_nothing(typed: str, said: list[str]) -> None:
    window = _Window(choice=2, typed=typed)
    window._do_close_reopen(REF, ISSUE)
    assert window.said == said and window.api.calls == []


def test_a_pull_request_keeps_the_plain_question() -> None:
    window = _Window()
    window._do_close_reopen(REF, PULL)
    assert window.asked == [("Close #8", "Close #8, A pull?")]
    assert window.updated == [("o/r", [8], "closed")]


def test_create_branch_suggests_githubs_name_and_links_it() -> None:
    window = _Window(typed="7-fix-the-parser")
    window._do_create_branch(REF, ISSUE)
    assert window.asked == [("Create Branch for This Issue", "7-fix-the-parser")]
    assert window.said == [
        "Made branch 7-fix-the-parser from main, linked to #7. "
        "To work on it: git fetch, then git switch 7-fix-the-parser."
    ]


@pytest.mark.parametrize(("typed", "said"), [("", []), ("has space", None)])
def test_create_branch_cancel_or_a_bad_name_sends_nothing(
    typed: str, said: list[str] | None
) -> None:
    window = _Window(typed=typed)
    window._do_create_branch(REF, ISSUE)
    assert window.api.calls == []
    if said is not None:
        assert window.said == said
    else:
        assert "cannot be a branch name" in window.said[0]


def test_create_branch_fits_an_issue_only_and_only_signed_in() -> None:
    window = _Window()
    assert window._fits_create_branch(ISSUE) and not window._fits_create_branch(PULL)
    window.signed_in = False
    assert not window._fits_create_branch(ISSUE)
