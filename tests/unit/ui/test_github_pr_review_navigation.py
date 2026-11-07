"""Keyboard review navigation distinguishes unresolved and unvisited threads."""

from __future__ import annotations

from types import SimpleNamespace

from quill.ui.github_pr_review_dialog import GitHubPullReviewDialog


class _Outline:
    def __init__(self) -> None:
        self.selected: object | None = None
        self.focused = False

    def SelectItem(self, item: object) -> None:
        self.selected = item

    def SetFocus(self) -> None:
        self.focused = True


def _thread(thread_id: str, *, resolved: bool | None, line: int) -> SimpleNamespace:
    return SimpleNamespace(
        root=SimpleNamespace(
            id=thread_id,
            path="src/app.py",
            line=line,
            author=f"reviewer-{thread_id}",
        ),
        resolved=resolved,
    )


def _dialog(current: int) -> tuple[SimpleNamespace, _Outline, list[str]]:
    outline = _Outline()
    announcements: list[str] = []
    dialog = SimpleNamespace(
        _threads=(
            _thread("one", resolved=True, line=10),
            _thread("two", resolved=False, line=20),
            _thread("three", resolved=None, line=30),
        ),
        _thread_items={0: "node-0", 1: "node-1", 2: "node-2"},
        _visited_thread_ids={"one"},
        _thread_visit_key=lambda index: ("one", "two", "three")[index],
        _node_kind=lambda: ("thread", current),
        _outline=outline,
        _announce=announcements.append,
    )
    return dialog, outline, announcements


def test_next_unresolved_selects_the_next_known_unresolved_thread() -> None:
    dialog, outline, announcements = _dialog(current=0)

    GitHubPullReviewDialog._next_thread(dialog, unresolved_only=True)

    assert outline.selected == "node-1"
    assert outline.focused
    assert "unresolved thread by reviewer-two, line 20" in announcements[-1]


def test_next_unvisited_is_local_and_does_not_mark_github_read() -> None:
    dialog, outline, announcements = _dialog(current=0)

    GitHubPullReviewDialog._next_thread(dialog, unresolved_only=False)

    assert outline.selected == "node-1"
    assert dialog._visited_thread_ids == {"one", "two"}
    assert "unvisited thread by reviewer-two" in announcements[-1]
