"""Viewed files in a pull request review, and comments on a whole file."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pytest

from quill.core.github import review_viewed as rv


class PagedApi:
    """Two pages of files, then the mutations recorded."""

    def __init__(self) -> None:
        self.mutations: list[tuple[str, dict[str, object]]] = []

    def rest(self, *_a: Any, **_k: Any) -> Any:
        raise AssertionError("viewed states are GraphQL only")

    def graphql(self, query: str, variables: Mapping[str, object]) -> dict[str, Any]:
        if query.startswith("mutation"):
            self.mutations.append((query.split("{", 2)[1].split("(")[0], dict(variables)))
            return {}
        if variables["i"] == 404:
            return {"repository": {"pullRequest": None}}
        if variables["after"] is None:
            files = {
                "nodes": [
                    {"path": "a.py", "viewerViewedState": "VIEWED"},
                    {"path": "b.py", "viewerViewedState": "UNVIEWED"},
                ],
                "pageInfo": {"hasNextPage": True, "endCursor": "c1"},
            }
        else:
            files = {
                "nodes": [{"path": "c.py", "viewerViewedState": "DISMISSED"}],
                "pageInfo": {"hasNextPage": False},
            }
        return {"repository": {"pullRequest": {"id": "PR1", "files": files}}}


def test_every_page_of_files_is_read_with_its_state() -> None:
    viewed = rv.load_viewed(PagedApi(), "o/r", 7)
    assert viewed.pull_id == "PR1"
    assert viewed.states == {"a.py": "VIEWED", "b.py": "UNVIEWED", "c.py": "DISMISSED"}
    assert [rv.file_label(p, viewed) for p in ("a.py", "b.py", "c.py", "new.py")] == [
        "a.py, viewed",
        "b.py, not viewed",
        "c.py, changed since you viewed it",
        "new.py",
    ]
    assert viewed.sentence() == "1 of 3 files viewed."
    assert viewed.counts(["b.py", "c.py"]) == (0, 2)


def test_a_missing_pull_request_is_said() -> None:
    with pytest.raises(rv.ReviewViewedError, match="no pull request #404"):
        rv.load_viewed(PagedApi(), "o/r", 404)


def test_marking_sends_the_mutation_and_keeps_the_count() -> None:
    api = PagedApi()
    viewed = rv.load_viewed(api, "o/r", 7)
    assert rv.set_viewed(api, viewed, "b.py", True) == "b.py marked as viewed. 2 of 3 files viewed."
    assert rv.set_viewed(api, viewed, "a.py", False) == (
        "a.py marked as not viewed. 1 of 3 files viewed."
    )
    assert api.mutations == [
        ("markFileAsViewed", {"id": "PR1", "path": "b.py"}),
        ("unmarkFileAsViewed", {"id": "PR1", "path": "a.py"}),
    ]


def test_marking_a_file_that_is_not_in_the_pull_request_is_refused() -> None:
    api = PagedApi()
    viewed = rv.load_viewed(api, "o/r", 7)
    with pytest.raises(rv.ReviewViewedError, match="not one of"):
        rv.set_viewed(api, viewed, "elsewhere.py", True)
    with pytest.raises(rv.ReviewViewedError, match="Load the pull request"):
        rv.set_viewed(api, rv.ViewedFiles(), "a.py", True)
    assert api.mutations == []


def test_a_whole_file_comment_is_a_file_subject() -> None:
    assert rv.file_comment_payload("a.py", "Looks right", "abc") == {
        "path": "a.py",
        "body": "Looks right",
        "commit_id": "abc",
        "subject_type": "file",
    }
    with pytest.raises(rv.ReviewViewedError, match="needs some text"):
        rv.file_comment_payload("a.py", "  ", "abc")
    with pytest.raises(rv.ReviewViewedError, match="latest commit"):
        rv.file_comment_payload("a.py", "x", "")
