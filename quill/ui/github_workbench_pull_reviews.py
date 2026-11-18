"""Reviews... on a pull request: read, change, dismiss, submit or delete a review (PRD section 19).

The code is in :mod:`quill.core.github.pull_reviews`; this mixin asks and says.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.github.items_provider import GitHubItem

__all__ = ["PULL_REVIEW_REASONS", "PULL_REVIEW_VERBS", "GitHubWorkbenchPullReviewsMixin"]

PULL_REVIEW_VERBS: dict[str, frozenset[str]] = {"manage_reviews": frozenset({"item"})}

PULL_REVIEW_REASONS: dict[str, str] = {
    "manage_reviews": "Reviews is for a pull request, while you are signed in.",
}


class GitHubWorkbenchPullReviewsMixin:
    frame: Any
    signed_in: bool
    _say: Callable[[str], None]
    _background: Callable[[str, Callable[[], Any], Callable[[Any], None]], None]
    _choose: Callable[[str, str, list[str]], int]
    _confirm: Callable[[str, str], bool]
    _ask_text: Callable[..., str]
    _show_text: Callable[[str, str], None]

    def github_api(self) -> Any:
        raise NotImplementedError

    def _fits_manage_reviews(self, row: object) -> bool:
        return self.signed_in and isinstance(row, GitHubItem) and row.is_pr

    def _do_manage_reviews(self, ref: Any, row: object) -> None:
        from quill.core.github.pull_reviews import reviews

        if not isinstance(row, GitHubItem):
            return
        api, repo, number = self.github_api(), ref.instance, row.number
        title = f"Reviews of #{number}"

        def listed(found: Any) -> None:
            found = list(found)
            if not found:
                self._say(f"Pull request #{number} has no reviews yet.")
                return
            picked = self._choose(title, "Which review?", [one.label for one in found])
            if picked >= 0:
                self._review_actions(api, repo, number, found[picked])

        self._background(
            f"list the reviews of #{number}", lambda: reviews(api, repo, number), listed
        )

    def _review_actions(self, api: Any, repo: str, number: int, review: Any) -> None:
        title = f"{review.author}'s review"
        actions: list[tuple[str, Callable[[], None]]] = [
            ("Read its comments...", lambda: self._review_comments(api, repo, number, review)),
            ("Change its summary...", lambda: self._review_summary(api, repo, number, review)),
        ]
        if review.dismissable:
            actions.append((
                "Dismiss it...",
                lambda: self._review_dismiss(api, repo, number, review),
            ))
        if review.pending:
            actions.append(("Submit it...", lambda: self._review_submit(api, repo, number, review)))
            actions.append(("Delete it...", lambda: self._review_delete(api, repo, number, review)))
        picked = self._choose(title, review.label, [words for words, _act in actions])
        if picked >= 0:
            actions[picked][1]()

    def _review_comments(self, api: Any, repo: str, number: int, review: Any) -> None:
        from quill.core.github import pull_reviews as pr

        def listed(found: Any) -> None:
            found = list(found)
            if not found:
                self._say("This review has no line comments.")
                return
            title = f"Comments in {review.author}'s review"
            picked = self._choose(title, "Which comment?", [one.label for one in found])
            if picked < 0:
                return
            comment = found[picked]
            act = self._choose(title, comment.label, ["Read it", "Change it...", "Delete it..."])
            if act == 0:
                self._show_text(title, f"{comment.path}, line {comment.line}\n\n{comment.body}")
            elif act == 1:
                body = self._ask_text(
                    "Change Comment", "The comment:", multiline=True, value=comment.body
                )
                if body:
                    self._background(
                        "change the comment",
                        lambda: pr.edit_comment(api, repo, comment.id, body),
                        lambda said: self._say(str(said)),
                    )
            elif act == 2 and self._confirm("Delete Comment", f"Delete: {comment.label}"):
                self._background(
                    "delete the comment",
                    lambda: pr.delete_comment(api, repo, comment.id),
                    lambda said: self._say(str(said)),
                )

        self._background(
            "read the review's comments",
            lambda: pr.review_comments(api, repo, number, review.id),
            listed,
        )

    def _review_summary(self, api: Any, repo: str, number: int, review: Any) -> None:
        from quill.core.github.pull_reviews import change_summary

        body = self._ask_text(
            "Change Summary", "The review's summary:", multiline=True, value=review.body
        )
        if body:
            self._background(
                "change the summary",
                lambda: change_summary(api, repo, number, review.id, body),
                lambda said: self._say(str(said)),
            )

    def _review_dismiss(self, api: Any, repo: str, number: int, review: Any) -> None:
        from quill.core.github.pull_reviews import dismiss

        message = self._ask_text("Dismiss Review", f"Why dismiss {review.author}'s review?")
        if message:
            self._background(
                "dismiss the review",
                lambda: dismiss(api, repo, number, review, message),
                lambda said: self._say(str(said)),
            )

    def _review_submit(self, api: Any, repo: str, number: int, review: Any) -> None:
        from quill.core.github.pull_reviews import SUBMIT_EVENTS, submit_pending

        picked = self._choose(
            "Submit Review", "Submit it as:", [words for _e, words in SUBMIT_EVENTS]
        )
        if picked < 0:
            return
        event = SUBMIT_EVENTS[picked][0]
        body = self._ask_text("Submit Review", "A summary (optional):", multiline=True)
        self._background(
            "submit the review",
            lambda: submit_pending(api, repo, number, review.id, event, body),
            lambda said: self._say(str(said)),
        )

    def _review_delete(self, api: Any, repo: str, number: int, review: Any) -> None:
        from quill.core.github.pull_reviews import delete_pending

        if not self._confirm(
            "Delete Pending Review", "Delete your pending review and its comments?"
        ):
            return
        self._background(
            "delete the pending review",
            lambda: delete_pending(api, repo, number, review.id),
            lambda said: self._say(str(said)),
        )
