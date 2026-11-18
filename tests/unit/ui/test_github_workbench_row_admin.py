"""Row commands ask before anything that cannot be undone."""

from __future__ import annotations

from typing import Any

import pytest

from quill.core.github import row_admin
from quill.core.github.explore_models import ExploreRow
from quill.core.github.items_provider import GitHubBranch, GitHubRelease
from quill.ui.github_workbench_row_admin import GitHubWorkbenchRowAdminMixin


class _Host(GitHubWorkbenchRowAdminMixin):
    def __init__(self, answers: list[Any]) -> None:
        self.answers, self.said, self.signed_in = answers, [], True
        self.frame = type("F", (), {"reload": lambda self: None})()
        self._say = self.said.append  # type: ignore[assignment]
        self._background = lambda _w, work, done: done(work())  # type: ignore[assignment]
        self._choose = lambda *a, **k: self.answers.pop(0)  # type: ignore[assignment]
        self._confirm = lambda *a, **k: self.answers.pop(0)  # type: ignore[assignment]
        self._ask_text = lambda *a, **k: self.answers.pop(0)  # type: ignore[assignment]
        self._repo_for = lambda _ref: "o/r"  # type: ignore[assignment]

    def github_api(self) -> Any:
        return object()


def test_cancel_deletes_nothing_and_the_choice_decides_the_tag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, bool]] = []
    monkeypatch.setattr(
        row_admin,
        "delete_release",
        lambda _a, _r, tag, delete_tag: calls.append((tag, delete_tag)) or "ok",
    )
    release = GitHubRelease(tag="v1", name="One")
    _Host([-1])._do_delete_release(None, release)
    assert calls == []
    _Host([1])._do_delete_release(None, release)
    assert calls == [("v1", True)]


def test_merge_into_asks_and_a_milestone_delete_asks(monkeypatch: pytest.MonkeyPatch) -> None:
    merged: list[tuple[str, str]] = []
    monkeypatch.setattr(
        row_admin,
        "merge_branch",
        lambda _a, _r, base, head: merged.append((base, head)) or "merged",
    )
    branch = GitHubBranch(name="topic", commit_sha="abc", default_branch="main")
    _Host(["main", False])._do_merge_into(None, branch)
    assert merged == []
    _Host(["main", True])._do_merge_into(None, branch)
    assert merged == [("main", "topic")]
    gone: list[str] = []
    monkeypatch.setattr(
        row_admin, "delete_milestone", lambda _a, _r, title: gone.append(title) or "ok"
    )
    milestone = ExploreRow("Spring", "d", "u", "o/r", "milestone", "Spring")
    _Host([False])._do_delete_milestone(None, milestone)
    _Host([True])._do_delete_milestone(None, milestone)
    assert gone == ["Spring"]
