"""Why Can't I Merge?, Auto-Merge... and the merge queue on a pull request's row (GH-MR)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from quill.core.github import merge_automation as auto
from quill.core.github import merge_readiness as mr
from quill.core.github.items_provider import GitHubItem
from quill.ui.github_workbench_development import DEVELOPMENT_REASONS, DEVELOPMENT_VERBS
from quill.ui.github_workbench_merge import GitHubWorkbenchMergeMixin

PULL = GitHubItem(number=4, title="Add it", state="open", url="u", is_pr=True)
REF = SimpleNamespace(instance="o/r")


class _Window(GitHubWorkbenchMergeMixin):
    signed_in = True

    def __init__(self, *, choice: int = 0, confirm: bool = True) -> None:
        self.said: list[str] = []
        self.asked: list[tuple[str, str]] = []
        self.choice, self.confirm = choice, confirm
        self.items = object()
        self.frame = SimpleNamespace(reload=lambda: self.said.append("(reloaded)"))

    def github_api(self) -> Any:
        return "API"

    def _say(self, text: str) -> None:
        self.said.append(text)

    def _choose(self, title: str, prompt: str, labels: list[str]) -> int:
        self.asked.append((title, prompt))
        return self.choice

    def _confirm(self, title: str, question: str) -> bool:
        self.asked.append((title, question))
        return self.confirm

    def _background(self, _name: str, work: Any, done: Any) -> None:
        done(work())


@pytest.fixture
def ready(monkeypatch: pytest.MonkeyPatch) -> list[mr.Readiness]:
    holder = [
        mr.Readiness(
            number=4,
            head="abc1234def",
            base="main",
            merge_state="BLOCKED",
            review="REVIEW_REQUIRED",
        )
    ]
    monkeypatch.setattr(mr, "load_readiness", lambda api, repo, number: holder[0])
    return holder


@pytest.fixture
def sent(monkeypatch: pytest.MonkeyPatch) -> list[tuple[Any, ...]]:
    calls: list[tuple[Any, ...]] = []
    for name in (
        "enable_auto_merge",
        "disable_auto_merge",
        "enqueue_pull_request",
        "dequeue_pull_request",
    ):
        monkeypatch.setattr(
            auto, name, lambda *a, _n=name: (calls.append((_n, *a[1:])), f"{_n} done")[1]
        )
    return calls


def test_verbs_and_reasons_are_registered() -> None:
    for verb in ("why_cant_merge", "auto_merge", "merge_queue"):
        assert verb in DEVELOPMENT_VERBS and verb in DEVELOPMENT_REASONS


def test_fits_an_open_pull_only() -> None:
    window = _Window()
    assert window._fits_why_cant_merge(PULL) and window._fits_auto_merge(PULL)
    closed = GitHubItem(number=4, title="x", state="closed", url="u", is_pr=True)
    issue = GitHubItem(number=5, title="x", state="open", url="u", is_pr=False)
    assert not window._fits_why_cant_merge(closed) and not window._fits_merge_queue(issue)
    window.signed_in = False
    assert window._fits_why_cant_merge(PULL) and not window._fits_auto_merge(PULL)


def test_why_cant_merge_says_the_reasons_and_the_commit(ready: Any) -> None:
    window = _Window()
    window._do_why_cant_merge(REF, PULL)
    assert window.said == [
        "#4 cannot merge yet, as of commit abc1234. It needs an approving review."
    ]


def test_auto_merge_on_asks_the_method_and_says_what_it_waits_for(ready: Any, sent: Any) -> None:
    window = _Window(choice=1)
    window._do_auto_merge(REF, PULL)
    assert "It needs an approving review." in window.asked[0][1]
    assert sent == [("enable_auto_merge", "o/r", 4, "Squash and merge")]
    assert window.said == ["enable_auto_merge done", "(reloaded)"]


def test_auto_merge_already_on_offers_to_turn_it_off(ready: Any, sent: Any) -> None:
    ready[0] = mr.Readiness(number=4, head="a", base="main", auto_merge="REBASE")
    window = _Window()
    window._do_auto_merge(REF, PULL)
    assert "to rebase it" in window.asked[0][1]
    assert sent == [("disable_auto_merge", "o/r", 4)]


def test_auto_merge_when_it_can_merge_now_sends_nothing(ready: Any, sent: Any) -> None:
    ready[0] = mr.Readiness(number=4, head="a", base="main", merge_state="CLEAN")
    window = _Window()
    window._do_auto_merge(REF, PULL)
    assert sent == [] and "nothing to wait for" in window.said[0]


def test_merge_queue_adds_or_removes(ready: Any, sent: Any) -> None:
    window = _Window()
    window._do_merge_queue(REF, PULL)
    assert "as of commit abc1234" in window.asked[0][1]
    ready[0] = mr.Readiness(number=4, head="a", base="main", queue_position=3)
    window._do_merge_queue(REF, PULL)
    assert "position 3. Take it out?" in window.asked[1][1]
    assert [call[0] for call in sent] == ["enqueue_pull_request", "dequeue_pull_request"]


def test_no_means_nothing_is_sent(ready: Any, sent: Any) -> None:
    window = _Window(confirm=False, choice=-1)
    window._do_merge_queue(REF, PULL)
    window._do_auto_merge(REF, PULL)
    assert sent == []
