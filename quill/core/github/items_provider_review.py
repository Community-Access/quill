"""Wave 2 pull-request review operations for ``GitHubItemsProvider``.

New line comments on a diff, a review submitted together with its pending
line comments, and "what changed since my last review". Every call goes
through :func:`~quill.core.github.rest_transport.request_json` (api.github.com
only, no redirects followed), and every write reports only what GitHub's
answer confirmed.

:class:`GitHubPullReviewExtrasMixin` gathers this module's mixin with the
reactions, timeline and one-sentence summary mixins (and the later Copilot and
commit-comment mixins), so the provider gains them through one base class
(``items_provider`` has almost no GATE-11 room).

No ``wx`` imports; strict-typed.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from functools import partial
from typing import Any, Protocol

from quill.core.github.commit_comments import GitHubCommitCommentsMixin
from quill.core.github.copilot import GitHubCopilotMixin
from quill.core.github.diff_lines import LineCommentAnchor
from quill.core.github.items_errors import GitHubItemsError
from quill.core.github.line_comment_drafts import PendingLineComment
from quill.core.github.pr_review import REVIEW_EVENTS
from quill.core.github.pr_summary import GitHubPullSummaryMixin
from quill.core.github.reactions import GitHubReactionsMixin
from quill.core.github.rest_transport import (
    GitHubRestError,
    RestResponse,
    request_json,
    rest_failure_message,
)
from quill.core.github.run_actions import repo_path
from quill.core.github.timeline import GitHubTimelineMixin

_MAX_REVIEW_PAGES = 10
_SUBMITTED_STATES = {
    "APPROVE": "APPROVED",
    "REQUEST_CHANGES": "CHANGES_REQUESTED",
    "COMMENT": "COMMENTED",
}


@dataclass(frozen=True, slots=True)
class PostedComment:
    """What GitHub returned for a new review comment."""

    id: int
    url: str = ""


@dataclass(frozen=True, slots=True)
class ChangesSinceReview:
    """The files that changed between the account's last review and the head."""

    reviewed: bool
    reviewed_sha: str = ""
    reviewed_at: str = ""
    files: tuple[str, ...] = ()
    commit_missing: bool = False
    rewritten: bool = False
    truncated: bool = False

    @property
    def date(self) -> str:
        return self.reviewed_at[:10] or "an unknown date"

    def sentence(self) -> str:
        """ "4 files changed since your review on 2026-11-03", or why not."""
        if not self.reviewed:
            return "You have not reviewed this pull request yet, so every file is new to you."
        if self.commit_missing:
            return (
                f"The commit you reviewed on {self.date} ({self.reviewed_sha[:7]}) is no longer "
                "on GitHub; the branch was probably force-pushed. Review every file again."
            )
        if not self.files:
            return f"No files changed since your review on {self.date}."
        count = len(self.files)
        text = f"{count} file{'s' if count != 1 else ''} changed since your review on {self.date}"
        if self.truncated:
            text += "; GitHub listed only the first 300"
        if self.rewritten:
            text += (
                ". The branch was rewritten since then, so this compares your reviewed "
                "commit with the new head"
            )
        return text + "."


class _ReviewAccess(Protocol):
    _token: str | None
    _viewer_login: str

    def _require_write_access(self, action: str) -> None: ...

    def fetch_viewer_login(self) -> str: ...


def _call(action: str, call: Callable[[], RestResponse], expect: tuple[int, ...]) -> RestResponse:
    try:
        response = call()
    except GitHubRestError as exc:
        raise GitHubItemsError(rest_failure_message(action, exc)) from exc
    if response.status not in expect:
        raise GitHubItemsError(
            f"Could not {action}. GitHub answered HTTP {response.status} without confirming it."
        )
    return response


def _pull_path(full_name: str, number: int) -> str:
    if isinstance(number, bool) or not isinstance(number, int) or number <= 0:
        raise GitHubItemsError("Choose a pull request first.")
    return f"{repo_path(full_name)}/pulls/{number}"


def _commit(sha: str) -> str:
    sha = sha.strip()
    if len(sha) < 7 or any(ch not in "0123456789abcdefABCDEF" for ch in sha):
        raise GitHubItemsError("The pull request's head revision is unknown; refresh the review.")
    return sha


class GitHubLineReviewMixin:
    """Line comments, reviews with comments, and changes since a review."""

    _viewer_login: str = ""

    def fetch_viewer_login(self: _ReviewAccess) -> str:
        """The signed-in account's login, read once per provider session."""
        if self._viewer_login:
            return self._viewer_login
        self._require_write_access("identify your account")
        response = _call(
            "identify your GitHub account",
            lambda: request_json(self._token, "GET", "/user"),
            (200,),
        )
        login = response.data.get("login") if isinstance(response.data, Mapping) else None
        if not isinstance(login, str) or not login:
            raise GitHubItemsError("GitHub did not say which account this token belongs to.")
        self._viewer_login = login
        return login

    def post_line_comment(
        self: _ReviewAccess,
        full_name: str,
        number: int,
        anchor: LineCommentAnchor,
        body: str,
        commit_id: str,
    ) -> PostedComment:
        """Post one comment on a line or a range of lines now, outside a review."""
        if not body.strip():
            raise GitHubItemsError("A comment needs some text.")
        self._require_write_access("comment on a line")
        payload: dict[str, object] = {
            **anchor.payload(),
            "body": body,
            "commit_id": _commit(commit_id),
        }
        path = f"{_pull_path(full_name, number)}/comments"
        response = _call(
            f"comment on {anchor.describe()}",
            lambda: request_json(self._token, "POST", path, body=payload),
            (201,),
        )
        data = response.data if isinstance(response.data, Mapping) else {}
        identifier = data.get("id")
        if isinstance(identifier, bool) or not isinstance(identifier, int) or identifier <= 0:
            raise GitHubItemsError("GitHub did not confirm the new comment.")
        return PostedComment(identifier, str(data.get("html_url") or ""))

    def submit_review_with_comments(
        self: _ReviewAccess,
        full_name: str,
        number: int,
        event: str,
        body: str,
        comments: Sequence[PendingLineComment],
        commit_id: str,
    ) -> str:
        """Submit a review and its pending line comments as one GitHub review."""
        api_event = REVIEW_EVENTS.get(event.strip().casefold())
        if api_event is None:
            raise GitHubItemsError(
                f"Unknown review action {event!r}; use approve, request changes, or comment."
            )
        if api_event == "REQUEST_CHANGES" and not body.strip():
            raise GitHubItemsError("GitHub requires a message to request changes.")
        if api_event == "COMMENT" and not body.strip() and not comments:
            raise GitHubItemsError("A comment review needs a message or a line comment.")
        self._require_write_access("submit a review")
        payload: dict[str, object] = {
            "commit_id": _commit(commit_id),
            "event": api_event,
            "body": body,
            "comments": [comment.review_payload() for comment in comments],
        }
        path = f"{_pull_path(full_name, number)}/reviews"
        response = _call(
            "submit the review",
            lambda: request_json(self._token, "POST", path, body=payload),
            (200,),
        )
        data = response.data if isinstance(response.data, Mapping) else {}
        state = data.get("state")
        if state != _SUBMITTED_STATES[api_event]:
            raise GitHubItemsError(
                "GitHub did not confirm the review was submitted"
                + (f"; it reports it as {str(state).casefold()}." if state else ".")
            )
        count = len(comments)
        return f" with {count} line comment{'s' if count != 1 else ''}" if count else ""

    def fetch_changes_since_my_review(
        self: _ReviewAccess, full_name: str, number: int, head_sha: str
    ) -> ChangesSinceReview:
        """Compare the commit of the account's latest review with the current head."""
        login = self.fetch_viewer_login().casefold()
        head = _commit(head_sha)
        latest: Mapping[str, Any] | None = None
        path = f"{_pull_path(full_name, number)}/reviews"
        for page in range(1, _MAX_REVIEW_PAGES + 1):
            response = _call(
                "read your reviews",
                partial(
                    request_json,
                    self._token,
                    "GET",
                    path,
                    query={"per_page": "100", "page": str(page)},
                ),
                (200,),
            )
            rows = response.data if isinstance(response.data, list) else []
            for row in rows:
                if not isinstance(row, Mapping) or row.get("state") == "PENDING":
                    continue
                user = row.get("user")
                author = str(user.get("login") or "") if isinstance(user, Mapping) else ""
                if author.casefold() != login or not row.get("commit_id"):
                    continue
                if latest is None or str(row.get("submitted_at") or "") >= str(
                    latest.get("submitted_at") or ""
                ):
                    latest = row
            if len(rows) < 100:
                break
        if latest is None:
            return ChangesSinceReview(reviewed=False)
        reviewed_sha = str(latest.get("commit_id") or "")
        reviewed_at = str(latest.get("submitted_at") or "")
        if reviewed_sha == head:
            return ChangesSinceReview(True, reviewed_sha, reviewed_at)
        compare = f"{repo_path(full_name)}/compare/{_commit(reviewed_sha)}...{head}"
        try:
            response = request_json(self._token, "GET", compare, query={"per_page": "100"})
        except GitHubRestError as exc:
            if exc.status in (404, 422):
                return ChangesSinceReview(True, reviewed_sha, reviewed_at, commit_missing=True)
            raise GitHubItemsError(rest_failure_message("compare with your review", exc)) from exc
        data = response.data if isinstance(response.data, Mapping) else {}
        files = data.get("files") if isinstance(data.get("files"), list) else []
        names = tuple(
            dict.fromkeys(
                str(row.get("filename") or "")
                for row in files or ()
                if isinstance(row, Mapping) and row.get("filename")
            )
        )
        behind = data.get("behind_by")
        return ChangesSinceReview(
            True,
            reviewed_sha,
            reviewed_at,
            files=names,
            rewritten=isinstance(behind, int) and behind > 0,
            truncated=len(names) >= 300,
        )


class GitHubPullReviewExtrasMixin(
    GitHubLineReviewMixin,
    GitHubReactionsMixin,
    GitHubTimelineMixin,
    GitHubPullSummaryMixin,
    GitHubCopilotMixin,
    GitHubCommitCommentsMixin,
):
    """Everything Wave 2 adds to the provider, in one base class, plus the
    Copilot review and coding-agent calls and commit comments that came after."""


__all__ = [
    "ChangesSinceReview",
    "GitHubLineReviewMixin",
    "GitHubPullReviewExtrasMixin",
    "PostedComment",
]
