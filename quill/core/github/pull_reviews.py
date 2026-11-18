"""One pull request's reviews: read, change, dismiss, submit or delete one (GitHub PRD section 19).

The review window writes a new review and replies to threads; this module is
for the reviews already there. :func:`reviews` lists them as sentences; a
review's own comments can be read, a review comment of yours edited or
deleted, your review's summary changed, someone's approval or change request
dismissed with a message, and your pending review submitted or deleted.
wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from quill.core.error_codes import CodedError
from quill.core.github.rest_transport import GitHubRestError
from quill.core.github.workbench_api import GitHubApi

__all__ = [
    "Review",
    "ReviewComment",
    "ReviewError",
    "SUBMIT_EVENTS",
    "change_summary",
    "delete_comment",
    "delete_pending",
    "dismiss",
    "edit_comment",
    "review_comments",
    "reviews",
    "submit_pending",
]

#: What a pending review can be submitted as: (GitHub's event, the words for it).
SUBMIT_EVENTS: tuple[tuple[str, str], ...] = (
    ("COMMENT", "Comment"),
    ("APPROVE", "Approve"),
    ("REQUEST_CHANGES", "Request changes"),
)

_STATE_WORDS = {
    "APPROVED": "approved",
    "CHANGES_REQUESTED": "asked for changes",
    "COMMENTED": "commented",
    "DISMISSED": "was dismissed",
    "PENDING": "has a pending review",
}


class ReviewError(CodedError):
    code = "QUILL-GITHUB-REVIEW-REFUSED"


@dataclass(frozen=True)
class Review:
    id: int
    author: str
    state: str
    body: str
    submitted: str

    @property
    def label(self) -> str:
        when = f" on {self.submitted}" if self.submitted else ""
        summary = f": {self.body.splitlines()[0][:80]}" if self.body.strip() else ""
        return f"{self.author} {_STATE_WORDS.get(self.state, self.state.lower())}{when}{summary}"

    @property
    def pending(self) -> bool:
        return self.state == "PENDING"

    @property
    def dismissable(self) -> bool:
        return self.state in ("APPROVED", "CHANGES_REQUESTED")


@dataclass(frozen=True)
class ReviewComment:
    id: int
    path: str
    line: int
    body: str

    @property
    def label(self) -> str:
        where = f"{self.path}, line {self.line}" if self.line else self.path or "the change"
        return f"{where}: {self.body.strip().splitlines()[0][:100] if self.body.strip() else ''}"


def _pull(repo: str, number: int) -> str:
    return f"/repos/{repo}/pulls/{int(number)}"


def _refused(exc: GitHubRestError, doing: str) -> ReviewError:
    if exc.status in (401, 403):
        return ReviewError(f"GitHub refused to {doing}. It needs write access to the repository.")
    if exc.status == 404:
        return ReviewError(f"GitHub found nothing to {doing}.")
    if exc.status == 422:
        return ReviewError(f"GitHub could not {doing}: {exc}")
    return ReviewError(f"Could not {doing}: {exc}")


def reviews(api: GitHubApi, repo: str, number: int) -> list[Review]:
    try:
        data = api.rest("GET", f"{_pull(repo, number)}/reviews", query={"per_page": "100"}).data
    except GitHubRestError as exc:
        raise _refused(exc, "list the reviews") from exc
    found = []
    for raw in data or ():
        if not isinstance(raw, Mapping) or not raw.get("id"):
            continue
        user = raw.get("user")
        found.append(
            Review(
                int(raw["id"]),
                str(user.get("login") or "someone") if isinstance(user, Mapping) else "someone",
                str(raw.get("state") or ""),
                str(raw.get("body") or ""),
                str(raw.get("submitted_at") or "")[:10],
            )
        )
    return found


def _comment(raw: Mapping[str, Any]) -> ReviewComment:
    line = raw.get("line") or raw.get("original_line") or 0
    return ReviewComment(
        int(raw["id"]), str(raw.get("path") or ""), int(line), str(raw.get("body") or "")
    )


def review_comments(api: GitHubApi, repo: str, number: int, review_id: int) -> list[ReviewComment]:
    try:
        data = api.rest(
            "GET",
            f"{_pull(repo, number)}/reviews/{int(review_id)}/comments",
            query={"per_page": "100"},
        ).data
    except GitHubRestError as exc:
        raise _refused(exc, "read the review's comments") from exc
    return [_comment(raw) for raw in data or () if isinstance(raw, Mapping) and raw.get("id")]


def change_summary(api: GitHubApi, repo: str, number: int, review_id: int, body: str) -> str:
    try:
        api.rest("PUT", f"{_pull(repo, number)}/reviews/{int(review_id)}", body={"body": body})
    except GitHubRestError as exc:
        raise _refused(exc, "change the review's summary") from exc
    return "Changed the review's summary."


def dismiss(api: GitHubApi, repo: str, number: int, review: Review, message: str) -> str:
    if not message.strip():
        raise ReviewError("GitHub needs a message saying why the review is dismissed.")
    try:
        api.rest(
            "PUT",
            f"{_pull(repo, number)}/reviews/{review.id}/dismissals",
            body={"message": message.strip(), "event": "DISMISS"},
        )
    except GitHubRestError as exc:
        raise _refused(exc, f"dismiss {review.author}'s review") from exc
    return f"Dismissed {review.author}'s review."


def submit_pending(
    api: GitHubApi, repo: str, number: int, review_id: int, event: str, body: str = ""
) -> str:
    payload: dict[str, object] = {"event": event}
    if body.strip():
        payload["body"] = body.strip()
    try:
        api.rest("POST", f"{_pull(repo, number)}/reviews/{int(review_id)}/events", body=payload)
    except GitHubRestError as exc:
        raise _refused(exc, "submit the review") from exc
    words = dict(SUBMIT_EVENTS).get(event, event.lower())
    return f"Submitted your review: {words.lower()}."


def delete_pending(api: GitHubApi, repo: str, number: int, review_id: int) -> str:
    try:
        api.rest("DELETE", f"{_pull(repo, number)}/reviews/{int(review_id)}")
    except GitHubRestError as exc:
        raise _refused(exc, "delete the pending review") from exc
    return "Deleted your pending review and its comments."


def edit_comment(api: GitHubApi, repo: str, comment_id: int, body: str) -> str:
    if not body.strip():
        raise ReviewError("Type the comment's new words.")
    try:
        api.rest("PATCH", f"/repos/{repo}/pulls/comments/{int(comment_id)}", body={"body": body})
    except GitHubRestError as exc:
        raise _refused(exc, "change the comment") from exc
    return "Changed the comment."


def delete_comment(api: GitHubApi, repo: str, comment_id: int) -> str:
    try:
        api.rest("DELETE", f"/repos/{repo}/pulls/comments/{int(comment_id)}")
    except GitHubRestError as exc:
        raise _refused(exc, "delete the comment") from exc
    return "Deleted the comment."
