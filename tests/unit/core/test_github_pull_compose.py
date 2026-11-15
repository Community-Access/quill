"""New Pull Request's prefill, kept drafts and existing-PR check (pull_compose.py)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from quill.core.github import pull_compose as pc


@pytest.fixture(autouse=True)
def _no_kept_drafts():
    pc._KEPT.clear()
    yield
    pc._KEPT.clear()


def test_one_commit_gives_its_subject_and_body() -> None:
    draft = pc.prefill("o/r", "main", "fix/crash", ["Fix the crash\n\nIt divided by zero."])
    assert (draft.title, draft.body) == ("Fix the crash", "It divided by zero.")


def test_several_commits_give_the_branch_in_words() -> None:
    draft = pc.prefill("o/r", "main", "feature/login-page_2", ["a", "b"])
    assert (draft.title, draft.body) == ("Login page 2", "")


def test_cancel_keeps_the_draft_and_sending_drops_it() -> None:
    pc.keep_draft(pc.PullDraft("O/R", "main", "f", "Mine", "typed", draft=True))
    again = pc.prefill("o/r", "main", "f", ["ignored"])
    assert (again.title, again.body, again.draft) == ("Mine", "typed", True)
    pc.drop_draft("o/r", "main", "f")
    assert pc.prefill("o/r", "main", "f", ["New"]).title == "New"
    pc.keep_draft(pc.PullDraft("o/r", "main", "g"))  # nothing typed: nothing kept
    assert pc.kept_draft("o/r", "main", "g") is None


def test_refusals_say_why() -> None:
    assert "same branch" in pc.describe_refusal("main", "main", ahead_by=3)
    assert "nothing to propose" in pc.describe_refusal("main", "f", ahead_by=0)
    assert pc.describe_refusal("main", "f", ahead_by=None) == ""
    assert pc.describe_refusal("main", "f", ahead_by=2) == ""


def test_the_existing_pull_is_found_by_owner_qualified_head() -> None:
    asked: list[dict[str, Any]] = []

    class _Repo:
        owner = SimpleNamespace(login="octo")

        def get_pulls(self, **kw: Any) -> list[Any]:
            asked.append(kw)
            return [SimpleNamespace(number=7)]

    assert pc.find_open_pull(_Repo(), "main", "f").number == 7
    assert asked == [{"state": "open", "base": "main", "head": "octo:f"}]
