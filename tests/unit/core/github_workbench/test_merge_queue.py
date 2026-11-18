"""Repository > Merge Queue: the default branch's queue, in order (GH-MR)."""

from __future__ import annotations

from typing import Any

import pytest

from quill.core.github import merge_queue as mq
from quill.core.github.explore_extra_views import EXTRA_REPO_VIEWS
from quill.core.github.workbench_tree import GITHUB_TREE


def _entry(position: int, number: int, state: str) -> dict[str, Any]:
    return {
        "position": position,
        "state": state,
        "enqueuedAt": "2026-11-17T21:05:00Z",
        "enqueuer": {"login": "jeff"},
        "headCommit": {"oid": "abc1234def"},
        "pullRequest": {"number": number, "title": f"Change {number}", "url": f"u/{number}"},
    }


def test_the_queue_is_read_in_order_and_in_words(monkeypatch: pytest.MonkeyPatch) -> None:
    sent: list[dict[str, object]] = []

    def answer(token: Any, query: str, variables: dict[str, object], *, action: str) -> Any:
        sent.append(variables)
        return {
            "repository": {
                "mergeQueue": {
                    "branch": {"name": "main"},
                    "entries": {
                        "nodes": [_entry(10, 7, "QUEUED"), _entry(2, 5, "AWAITING_CHECKS")]
                    },
                }
            }
        }

    monkeypatch.setattr(mq, "graphql_data", answer)
    rows = mq.fetch_merge_queue("t", "o/r", limit=500)
    assert sent == [{"o": "o", "n": "r", "first": 100}]
    assert [row.label for row in rows] == [
        "2. #5 Change 5, running its checks",
        "10. #7 Change 7, waiting",
    ]
    assert rows[0].kind == "pr" and rows[0].key == "5" and rows[0].url == "u/5"
    assert rows[0].detail == (
        "Position 2 in the merge queue for main: #5 Change 5, running its checks. "
        "Queued by jeff at commit abc1234, 2026-11-17 21:05."
    )


def test_no_queue_is_no_rows(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(mq, "graphql_data", lambda *a, **k: {"repository": {"mergeQueue": None}})
    assert mq.fetch_merge_queue("t", "o/r") == []


def test_the_node_is_in_the_tree_and_routed() -> None:
    assert "merge_queue" in EXTRA_REPO_VIEWS
    assert GITHUB_TREE.template_node("repository", "merge_queue").loader == "explore:merge_queue"
