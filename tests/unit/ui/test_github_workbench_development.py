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


class _IssueApi:
    """One issue's body on a fake GitHub; issues made get numbers from 40."""

    def __init__(self, body: str, *, changed_meanwhile: bool = False) -> None:
        self.body, self.reads, self.changed = body, 0, changed_meanwhile
        self.sent: list[tuple[str, str, Any]] = []
        self.next = 40

    def rest(self, method: str, path: str, *, body: Any = None, query: Any = None) -> Any:
        self.sent.append((method, path, body))
        if method == "GET":
            self.reads += 1
            if self.changed and self.reads > 1:
                return SimpleNamespace(data={"body": self.body + "\nedited by someone"})
            return SimpleNamespace(data={"body": self.body})
        if method == "PATCH":
            self.body = body["body"]
        if method == "POST" and path.endswith("/issues"):
            self.next += 1
            return SimpleNamespace(data={"id": 1000 + self.next, "number": self.next})
        return SimpleNamespace(data={})


TASKS = "Plan:\n- [ ] Write the guide\n- [x] Fix the parser\n- [ ] #12\n"


def _task_window(api: _IssueApi, **kwargs: Any) -> _Window:
    window = _Window(**kwargs)
    window.api = api  # type: ignore[assignment]
    window._choose = lambda title, prompt, labels: (  # type: ignore[method-assign]
        window.asked.append((title, " | ".join(labels))) or window.choice
    )
    return window


def test_check_or_uncheck_lists_the_tasks_and_turns_one_over() -> None:
    api = _IssueApi(TASKS)
    window = _task_window(api, choice=1)
    window._do_edit_tasks(REF, ISSUE)
    assert window.asked == [
        ("Tasks in #7", "Not done: Write the guide | Done: Fix the parser | Not done: #12")
    ]
    assert api.body == "Plan:\n- [ ] Write the guide\n- [ ] Fix the parser\n- [ ] #12\n"
    assert window.said == ["Unchecked: Fix the parser.", "(reloaded)"]


def test_an_issue_with_no_task_list_says_so() -> None:
    window = _task_window(_IssueApi("Just prose."))
    window._do_edit_tasks(REF, ISSUE)
    assert window.said == ["#7 has no task list."]


def test_an_edit_made_on_github_meanwhile_is_never_overwritten() -> None:
    api = _IssueApi(TASKS, changed_meanwhile=True)
    window = _task_window(api, choice=0)
    with pytest.raises(Exception, match="changed on GitHub while you chose"):
        window._do_edit_tasks(REF, ISSUE)
    assert not [call for call in api.sent if call[0] == "PATCH"]


def test_convert_makes_sub_issues_and_links_each_line() -> None:
    api = _IssueApi(TASKS)
    window = _task_window(api)
    window._do_convert_tasks(REF, ISSUE)
    assert window.asked[0][0] == "Convert Tasks to Sub-issues"
    assert "Make 2 sub-issues of #7: Write the guide; Fix the parser?" in window.asked[0][1]
    assert api.body == "Plan:\n- [ ] #41\n- [x] #42\n- [ ] #12\n"
    subs = [call[2] for call in api.sent if call[1].endswith("/sub_issues")]
    assert subs == [{"sub_issue_id": 1041}, {"sub_issue_id": 1042}]
    assert window.said == ["Made 2 sub-issues of #7: #41, #42.", "(reloaded)"]


def test_convert_cancelled_sends_nothing() -> None:
    api = _IssueApi(TASKS)
    window = _task_window(api, confirm=False)
    window._do_convert_tasks(REF, ISSUE)
    assert [call[0] for call in api.sent] == ["GET"]
