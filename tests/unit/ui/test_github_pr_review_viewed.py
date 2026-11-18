"""Viewed files and whole-file comments in the pull request review window."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from quill.core.github.review_viewed import ViewedFiles
from quill.ui.github_pr_review_viewed import GitHubPullReviewViewedMixin


class _Api:
    def __init__(self) -> None:
        self.sent: list[tuple[str, Any]] = []

    def graphql(self, query: str, variables: Any) -> dict[str, Any]:
        self.sent.append((query.split("{", 2)[1].split("(")[0], dict(variables)))
        return {}

    def rest(self, method: str, path: str, *, body: Any = None, query: Any = None) -> Any:
        self.sent.append((f"{method} {path}", body))
        return SimpleNamespace(data={})


class _Review(GitHubPullReviewViewedMixin):
    def __init__(self, *, signed_in: bool = True) -> None:
        self.api = _Api()
        self.said: list[str] = []
        self.rendered = 0
        self.selection = ("file", 0)
        self._file_paths = ["a.py", "b.py"]
        self._viewed = ViewedFiles("PR1", {"a.py": "VIEWED", "b.py": "UNVIEWED"})
        self._unviewed_only = False
        self._client = SimpleNamespace(can_write=signed_in, _provider=SimpleNamespace(token="t"))
        self._repo, self._number = "o/r", 7
        self._diff = SimpleNamespace(
            head_sha="abc",
            files=[SimpleNamespace(filename="a.py"), SimpleNamespace(filename="b.py")],
        )
        self._state = None
        self.dialog = None
        self._status = SimpleNamespace(SetLabel=lambda text: self.said.append(f"[status] {text}"))

    def _api(self) -> Any:
        return self.api

    def _in_background(self, work: Any, done: Any) -> None:
        done(work())

    def _announce(self, text: str) -> None:
        self.said.append(text)

    def _render_outline(self, *_a: Any) -> None:
        self.rendered += 1

    def _node_kind(self) -> tuple[str, int]:
        return self.selection


def _rows(review: _Review) -> list[tuple[str, bool]]:
    rows: list[tuple[str, bool]] = []
    review._viewed_menu_rows(lambda label, _handler, enabled=True: rows.append((label, enabled)))
    return rows


def test_the_selected_file_comes_from_the_node_never_its_label() -> None:
    review = _Review()
    assert review._selected_file_path() == "a.py"
    review.selection = ("thread", 0)
    assert review._selected_file_path() == ""
    review.selection = ("file", 9)
    assert review._selected_file_path() == ""


def test_the_menu_offers_the_opposite_of_the_files_state() -> None:
    review = _Review()
    assert _rows(review) == [
        ("Mark as Not Viewed", True),
        ("Comment on This File...", True),
        ("Show Only Files Not Viewed", True),
    ]
    review.selection = ("file", 1)
    assert _rows(review)[0] == ("Mark as Viewed", True)


def test_signed_out_the_writes_are_greyed() -> None:
    assert [enabled for _label, enabled in _rows(_Review(signed_in=False))] == [False, False, True]


def test_marking_sends_githubs_mutation_and_says_the_count() -> None:
    review = _Review()
    review.selection = ("file", 1)
    review._toggle_viewed()
    assert review.api.sent == [("markFileAsViewed", {"id": "PR1", "path": "b.py"})]
    assert review.said == ["b.py marked as viewed. 2 of 2 files viewed."]
    assert review.rendered == 1


def test_show_only_files_not_viewed_hides_the_viewed_and_says_how_many_are_left() -> None:
    review = _Review()
    review._toggle_unviewed_only()
    assert review.said == ["Showing only the 1 files not viewed."]
    assert not review._keep_file("a.py") and review._keep_file("b.py")
    review._toggle_unviewed_only()
    assert review.said[-1] == "Showing all 2 files." and review._keep_file("a.py")


def test_a_file_comment_goes_through_the_composer_as_a_file_subject(monkeypatch) -> None:
    titles: list[str] = []
    monkeypatch.setattr(
        "quill.ui.github_comment_composer.compose_comment",
        lambda *_a, title, **_k: titles.append(title) or "Looks right",
    )
    review = _Review()
    review._comment_on_file()
    assert titles == ["Comment on a.py"]
    assert review.api.sent == [
        (
            "POST /repos/o/r/pulls/7/comments",
            {"path": "a.py", "body": "Looks right", "commit_id": "abc", "subject_type": "file"},
        )
    ]
    assert review.said == ["Comment posted on a.py."]


@pytest.mark.parametrize("answer", ["", None])
def test_leaving_the_composer_sends_nothing(monkeypatch, answer: str | None) -> None:
    monkeypatch.setattr(
        "quill.ui.github_comment_composer.compose_comment", lambda *_a, **_k: answer or ""
    )
    review = _Review()
    review._comment_on_file()
    assert review.api.sent == [] and review.said == []


def test_the_states_land_in_the_outline_and_the_status_line() -> None:
    review = _Review()
    review._viewed_landed(ViewedFiles("PR1", {"a.py": "VIEWED", "b.py": "DISMISSED"}))
    assert review.rendered == 1
    assert review.said == ["[status] Review loaded. 1 of 2 files viewed."]
    assert review._file_state_sentence("b.py") == "For you: changed since you viewed it."
