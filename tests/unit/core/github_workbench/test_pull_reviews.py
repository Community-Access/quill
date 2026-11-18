"""Reviews... on a pull request: read, change, dismiss, submit or delete a review."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from quill.core.github import pull_reviews as pr
from quill.core.github.items_provider import GitHubItem
from quill.ui.github_workbench_pull_reviews import GitHubWorkbenchPullReviewsMixin
from tests.unit.core.github_workbench.test_run_more import Api

P = "/repos/o/r/pulls/7"
REVIEWS = [
    {
        "id": 1,
        "user": {"login": "sam"},
        "state": "APPROVED",
        "body": "Looks good",
        "submitted_at": "2026-11-17T01:00:00Z",
    },
    {"id": 2, "user": {"login": "jeff"}, "state": "PENDING", "body": ""},
]


def test_reviews_read_as_sentences_and_know_what_they_allow() -> None:
    found = pr.reviews(Api({f"GET {P}/reviews": REVIEWS}), "o/r", 7)
    assert found[0].label == "sam approved on 2026-11-17: Looks good"
    assert found[0].dismissable and not found[0].pending
    assert found[1].label == "jeff has a pending review" and found[1].pending


def test_dismiss_submit_delete_and_comments() -> None:
    api = Api({
        f"GET {P}/reviews/1/comments": [{"id": 5, "path": "a.py", "line": 3, "body": "Nit."}]
    })
    review = pr.reviews(Api({f"GET {P}/reviews": REVIEWS}), "o/r", 7)[0]
    assert pr.dismiss(api, "o/r", 7, review, "Outdated") == "Dismissed sam's review."
    assert api.sent[-1] == (
        "PUT",
        f"{P}/reviews/1/dismissals",
        {"message": "Outdated", "event": "DISMISS"},
    )
    with pytest.raises(pr.ReviewError, match="message"):
        pr.dismiss(api, "o/r", 7, review, " ")
    assert pr.submit_pending(api, "o/r", 7, 2, "APPROVE") == "Submitted your review: approve."
    assert pr.delete_pending(api, "o/r", 7, 2).startswith("Deleted your pending review")
    comment = pr.review_comments(api, "o/r", 7, 1)[0]
    assert comment.label == "a.py, line 3: Nit."
    assert pr.edit_comment(api, "o/r", 5, "Nit, fixed.") == "Changed the comment."
    assert api.sent[-1] == ("PATCH", "/repos/o/r/pulls/comments/5", {"body": "Nit, fixed."})


class _Window(GitHubWorkbenchPullReviewsMixin):
    signed_in = True

    def __init__(self, api: Api, answers: list[Any]) -> None:
        self.api, self.answers, self.said = api, list(answers), []
        self.frame = SimpleNamespace()

    def github_api(self) -> Any:
        return self.api

    def _say(self, text: str) -> None:
        self.said.append(text)

    def _background(self, _n: str, work: Any, done: Any) -> None:
        done(work())

    def _choose(self, *_a: Any) -> int:
        return int(self.answers.pop(0))

    def _confirm(self, *_a: Any) -> bool:
        return bool(self.answers.pop(0))

    def _ask_text(self, *_a: Any, **_k: Any) -> str:
        return str(self.answers.pop(0))

    def _show_text(self, *_a: Any) -> None:
        pass


def test_a_pending_review_is_submitted_from_the_pull_request_row() -> None:
    pull = GitHubItem(number=7, title="Fix it", state="open", url="", is_pr=True)
    api = Api({f"GET {P}/reviews": REVIEWS})
    # second review (pending): actions are Read, Change, Submit, Delete -> 2 is Submit
    window = _Window(api, [1, 2, 0, ""])
    assert window._fits_manage_reviews(pull)
    window._do_manage_reviews(SimpleNamespace(instance="o/r"), pull)
    assert api.sent[-1] == ("POST", f"{P}/reviews/2/events", {"event": "COMMENT"})
    assert window.said == ["Submitted your review: comment."]
