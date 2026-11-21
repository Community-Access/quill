"""An issue's or pull request's comments, under its description in the Workbench's details pane.

The pane said "Comments: 2" and showed none of them: the Workbench built the
details with an empty thread and never read it.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from quill.core.github.items_provider import GitHubItem
from quill.ui.github_workbench_item_comments import READING, detail_with_comments

ISSUE = GitHubItem(12, "Crash", "open", "https://github.com/o/r/issues/12", False, comments=2)
QUIET = GitHubItem(13, "Typo", "open", "https://github.com/o/r/issues/13", False)
THREAD = [
    {"author": "ann", "created_at": "2026-11-20T10:00:00Z", "body": "It crashes for me too."},
    {"author": "bob", "created_at": "2026-11-21T09:00:00Z", "body": "Fixed in #14."},
]


class _Details:
    def __init__(self) -> None:
        self.value, self.point = "", (0, 0)

    def ChangeValue(self, text: str) -> None:  # noqa: N802 - wx's name
        self.value, self.point = text, (0, 0)

    def GetSelection(self) -> tuple[int, int]:  # noqa: N802
        return self.point

    def SetSelection(self, start: int, end: int) -> None:  # noqa: N802
        self.point = (start, end)


class _Items:
    def __init__(self) -> None:
        self.asked: list[tuple[str, int]] = []

    def fetch_issue_comments(self, repo: str, number: int) -> list[dict[str, str]]:
        self.asked.append((repo, number))
        return THREAD


def _provider(selected: object, *, in_pane: bool = False) -> Any:
    pending: list[Any] = []
    said: list[str] = []
    details = _Details()
    focus = SimpleNamespace(Window=SimpleNamespace(FindFocus=lambda: details if in_pane else None))
    frame = SimpleNamespace(
        details=details,
        selected_row=lambda: selected,
        _run_background=lambda _n, work, done, _failed: pending.append((work, done)),
        _wx=focus,
        _say=said.append,
        said=said,
    )
    provider = SimpleNamespace(items=_Items(), frame=frame, pending=pending)
    provider.detail = lambda row: detail_with_comments(provider, row)
    return provider


def test_the_thread_is_read_once_and_lands_in_the_pane_without_moving_the_caret() -> None:
    provider = _provider(ISSUE)
    first = detail_with_comments(provider, ISSUE)
    assert first.endswith(READING) and "Comment 1 of 2" not in first
    assert detail_with_comments(provider, ISSUE).endswith(READING)
    assert len(provider.pending) == 1  # a second look while reading starts no second read
    provider.frame.details.point = (7, 9)
    work, done = provider.pending.pop()
    done(work())
    shown = provider.frame.details.value
    assert "Comment 1 of 2 - ann (2026-11-20):" in shown and "Fixed in #14." in shown
    assert READING not in shown and provider.frame.details.point == (7, 9)
    assert provider.frame.said == []  # the pane was not focused: nothing to say
    assert provider.items.asked == [("o/r", 12)]
    assert "Comment 2 of 2" in detail_with_comments(provider, ISSUE)
    assert provider.pending == []


def test_an_item_without_comments_reads_nothing() -> None:
    provider = _provider(QUIET)
    assert READING not in detail_with_comments(provider, QUIET)
    assert provider.pending == []


def test_a_thread_that_arrives_after_you_moved_on_waits_for_you() -> None:
    provider = _provider(QUIET)
    detail_with_comments(provider, ISSUE)
    work, done = provider.pending.pop()
    done(work())
    assert provider.frame.details.value == ""  # QUIET is selected now: its pane is left alone


def test_in_the_pane_you_hear_once_that_the_comments_arrived() -> None:
    provider = _provider(ISSUE, in_pane=True)
    detail_with_comments(provider, ISSUE)
    work, done = provider.pending.pop()
    done(work())
    assert provider.frame.said == ["2 comments read; they follow the description."]
