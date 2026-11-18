"""The Relationships window: add a sub-issue, block, remove, move (GitHub Workbench)."""

from __future__ import annotations

from typing import Any

import pytest

pytest.importorskip("wx")

from quill.core.github.issue_relations import IssueRef, Relations  # noqa: E402
from quill.core.github.items_errors import GitHubItemsError  # noqa: E402
from quill.ui import github_issue_relations_dialog as module  # noqa: E402
from quill.ui.github_issue_relations_dialog import IssueRelationsDialog, removable  # noqa: E402
from tests.wx_session import patch_call_after, shared_wx_app  # noqa: E402

SIX = IssueRef(id=106, number=6, title="Six", repo="o/r")
TWO = IssueRef(id=102, number=2, title="Two", repo="o/r")
ONE = IssueRef(id=101, number=1, title="One", repo="o/r")


class _Thread:
    def __init__(self, *, target: Any, daemon: bool) -> None:
        self._target = target

    def start(self) -> None:
        self._target()


class _Api:
    def __init__(self) -> None:
        self.calls: list[tuple[str, Any]] = []
        self.state = Relations(parent=ONE, sub_issues=(SIX,), blocked_by=(TWO,))
        self.parent_conflict = False

    def issue_ref(self, text: str, here: str) -> IssueRef:
        return {"#6": SIX, "#2": TWO, "#5": IssueRef(id=105, number=5, title="Me", repo="o/r")}[
            text
        ]

    def relations(self, repo: str, number: int) -> Relations:
        return self.state

    def add_sub_issue(self, repo: str, number: int, child: IssueRef, *, move: bool = False) -> None:
        if self.parent_conflict and not move:
            raise GitHubItemsError("Could not add: the issue already has a parent issue.")
        self.calls.append(("add_sub", (child.number, move)))

    def remove_sub_issue(self, repo: str, number: int, child: IssueRef) -> None:
        self.calls.append(("remove_sub", child.number))

    def add_blocked_by(self, repo: str, number: int, blocker: IssueRef) -> None:
        self.calls.append(("add_blocked", blocker.number))

    def remove_blocked_by(self, repo: str, number: int, blocker: IssueRef) -> None:
        self.calls.append(("remove_blocked", blocker.number))


@pytest.fixture
def window(monkeypatch: pytest.MonkeyPatch):
    shared_wx_app()
    patch_call_after(monkeypatch)
    monkeypatch.setattr(module.threading, "Thread", _Thread)
    api = _Api()
    answers: dict[str, Any] = {"text": "#6", "confirm": True}
    said: list[str] = []
    dialog = IssueRelationsDialog(
        None,
        api,  # type: ignore[arg-type]
        repo="o/r",
        number=5,
        relations=api.state,
        announce_cb=said.append,
        ask_text=lambda _t, _p: answers["text"],
        confirm=lambda _t, _m: answers["confirm"],
    )
    yield dialog, api, answers, said
    dialog.dialog.Destroy()


def test_rows_start_with_what_they_are(window) -> None:
    dialog, _api, _answers, _said = window
    assert list(dialog._list.GetStrings()) == [
        "Parent: #1 One (open)",
        "Sub-issue: #6 Six (open)",
        "Blocked by: #2 Two (open)",
    ]


def test_add_sub_issue_and_blocked_by(window) -> None:
    dialog, api, answers, said = window
    dialog.add_sub_issue()
    answers["text"] = "#2"
    dialog.add_blocked_by()
    assert api.calls == [("add_sub", (6, False)), ("add_blocked", 2)]
    assert said[-1] == "#5 is now blocked by #2."


def test_an_issue_cannot_link_to_itself(window) -> None:
    dialog, api, answers, said = window
    answers["text"] = "#5"
    dialog.add_blocked_by()
    assert api.calls == [] and said[-1] == "An issue cannot block itself."


def test_one_with_a_parent_is_moved_only_after_asking(window) -> None:
    dialog, api, answers, said = window
    api.parent_conflict = True
    answers["confirm"] = False
    dialog.add_sub_issue()
    assert api.calls == [] and said[-1] == "#6 was left where it is."
    answers["confirm"] = True
    dialog.add_sub_issue()
    assert api.calls == [("add_sub", (6, True))]


def test_remove_only_what_this_issue_owns(window) -> None:
    dialog, api, _answers, said = window
    dialog._list.SetSelection(0)  # the parent
    dialog.remove_selected()
    assert api.calls == [] and "changed from that other issue" in said[-1]
    dialog._list.SetSelection(2)  # blocked by #2
    dialog.remove_selected()
    assert api.calls == [("remove_blocked", 2)]
    assert removable(api.state, 1) == ("sub", SIX)
