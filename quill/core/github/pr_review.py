"""Pull request review surface: reviews, review threads, checks, and the
review actions (github.md plan section 4.2.1).

The GitHub Items viewer (#924) lists PRs; this module is the *review* model
behind the "Open Review" surface: who approved, which review threads exist
(grouped from GitHub's flat review-comment list), what the checks say, whether
the PR is merge-ready, and the write actions a reviewer takes (approve /
request changes / comment, reply in thread, request reviewers, draft <->
ready, update a stale branch).

Split out of :mod:`quill.core.github.items_provider` to keep that module
under its GATE-11 size budget (the same reason :mod:`.branch_compare` is a
sibling). Unlike ``branch_compare`` this module is called by the *UI*, not by
the provider, so :class:`PullReviewClient` takes the already-constructed
:class:`~quill.core.github.items_provider.GitHubItemsProvider` and leans on
its ``_repo`` resolver and auth state as a deliberate friend module -- one
repo-resolution path, one error style, no second PyGithub session.

Honesty note on thread resolution: GitHub only exposes a review thread's
resolved/unresolved state over GraphQL, and QUILL's GitHub transport is
PyGithub's REST client (the ``gh`` bridge is deliberately Codespaces-only).
So threads here carry the *outdated* flag (REST reports a comment whose hunk
has moved on as ``position = None``) but not a resolved bit; the UI says
"outdated", never guesses "resolved".

No ``wx`` imports. Strict-typed (``mypy quill/core`` scope).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from quill.core.error_codes import CodedError

if TYPE_CHECKING:
    from quill.core.github.items_provider import GitHubItemsProvider

#: Review submission events GitHub accepts, keyed by the verb the UI shows.
REVIEW_EVENTS: dict[str, str] = {
    "approve": "APPROVE",
    "request changes": "REQUEST_CHANGES",
    "comment": "COMMENT",
}

_THREAD_PAGE_LIMIT = 200  # review comments fetched per PR (flat, pre-grouping)
_CHECKS_PAGE_LIMIT = 100


class GitHubReviewError(CodedError):
    """A PR review fetch or action failed (network, auth, API, or refusal)."""

    code = "QUILL-GITHUB-REVIEW-ERROR"


# ---------------------------------------------------------------------------
# Models (frozen, slots)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class GitHubCheckRun:
    """One check run on the PR's head commit (CI job, lint gate, ...)."""

    name: str
    status: str  # "queued" / "in_progress" / "completed"
    conclusion: str  # "" until completed; then "success" / "failure" / ...
    url: str = ""
    summary: str = ""

    @property
    def state_display(self) -> str:
        """One word a list row or announcement can carry."""
        if self.status != "completed":
            return self.status.replace("_", " ") or "queued"
        return self.conclusion or "completed"


@dataclass(frozen=True, slots=True)
class GitHubReview:
    """One submitted review (the approve/request-changes/comment record)."""

    reviewer: str
    state: str  # "APPROVED" / "CHANGES_REQUESTED" / "COMMENTED" / "DISMISSED"
    body: str = ""
    submitted_at: str = ""


@dataclass(frozen=True, slots=True)
class GitHubReviewComment:
    """One review comment, anchored to a file (and usually a line)."""

    id: int
    author: str
    body: str
    path: str = ""
    line: int = 0  # 0 when GitHub reports no current line (outdated hunk)
    created_at: str = ""
    url: str = ""
    outdated: bool = False
    in_reply_to: int = 0  # 0 for a thread root


@dataclass(frozen=True, slots=True)
class GitHubReviewThread:
    """A thread: one root review comment plus its replies, in posted order."""

    comments: tuple[GitHubReviewComment, ...]

    @property
    def root(self) -> GitHubReviewComment:
        return self.comments[0]

    @property
    def path(self) -> str:
        return self.root.path

    @property
    def line(self) -> int:
        return self.root.line

    @property
    def outdated(self) -> bool:
        return self.root.outdated

    @property
    def reply_count(self) -> int:
        return max(len(self.comments) - 1, 0)

    @property
    def header(self) -> str:
        """The list-row line: where, who, how much, and outdated or not."""
        where = self.path or "general"
        if self.line:
            where = f"{where}:{self.line}"
        parts = [where, self.root.author]
        if self.reply_count:
            parts.append(f"{self.reply_count} repl{'y' if self.reply_count == 1 else 'ies'}")
        if self.outdated:
            parts.append("outdated")
        return " — ".join(part for part in parts if part)


@dataclass(frozen=True, slots=True)
class GitHubPullReviewState:
    """Everything the review header bar shows, in one fetch."""

    number: int
    title: str
    state: str  # "open" / "closed"
    draft: bool
    merged: bool
    mergeable: bool | None  # None while GitHub is still computing it
    mergeable_state: str  # "clean" / "dirty" / "behind" / "blocked" / ...
    base_ref: str
    head_ref: str
    head_sha: str
    author: str = ""
    url: str = ""
    requested_reviewers: tuple[str, ...] = ()
    reviews: tuple[GitHubReview, ...] = ()
    checks: tuple[GitHubCheckRun, ...] = ()
    thread_count: int = 0
    outdated_thread_count: int = 0

    @property
    def review_decision(self) -> str:
        """The latest standing review per reviewer, folded to one phrase."""
        latest: dict[str, str] = {}
        for review in self.reviews:  # chronological; later entries win
            if review.state in ("APPROVED", "CHANGES_REQUESTED"):
                latest[review.reviewer] = review.state
            elif review.state == "DISMISSED":
                latest.pop(review.reviewer, None)
        approvals = sum(1 for state in latest.values() if state == "APPROVED")
        blocks = sum(1 for state in latest.values() if state == "CHANGES_REQUESTED")
        if blocks:
            return f"changes requested by {blocks}"
        if approvals:
            return f"approved by {approvals}"
        return "review pending"

    @property
    def checks_summary(self) -> str:
        """ "3 passed, 1 failed, 2 running" — or "no checks"."""
        if not self.checks:
            return "no checks"
        passed = sum(1 for c in self.checks if c.conclusion == "success")
        failed = sum(1 for c in self.checks if c.conclusion in ("failure", "timed_out"))
        running = sum(1 for c in self.checks if c.status != "completed")
        other = len(self.checks) - passed - failed - running
        parts = []
        if passed:
            parts.append(f"{passed} passed")
        if failed:
            parts.append(f"{failed} failed")
        if running:
            parts.append(f"{running} running")
        if other:
            parts.append(f"{other} other")
        return ", ".join(parts)

    @property
    def merge_readiness(self) -> str:
        """Plain language for the header ribbon (plan 4.2.1: no raw states)."""
        if self.merged:
            return "Merged."
        if self.state != "open":
            return "Closed without merging."
        if self.draft:
            return "Draft — not ready for review."
        if self.mergeable_state == "behind":
            return "Branch is behind the base branch; update it before merging."
        if self.mergeable is False or self.mergeable_state == "dirty":
            return "Merge conflicts with the base branch."
        if self.mergeable_state == "blocked":
            return "Blocked — required reviews or checks are not satisfied."
        if self.mergeable is None:
            return "GitHub is still computing mergeability."
        return "Ready to merge."

    def summary_text(self) -> str:
        """The Copy Review Summary text: one readable paragraph block."""
        lines = [
            f"PR #{self.number}: {self.title}",
            f"{self.head_ref} into {self.base_ref}, by {self.author}",
            self.merge_readiness,
            f"Reviews: {self.review_decision}",
            f"Checks: {self.checks_summary}",
            f"Review threads: {self.thread_count}"
            + (f" ({self.outdated_thread_count} outdated)" if self.outdated_thread_count else ""),
        ]
        if self.requested_reviewers:
            lines.append("Awaiting review from: " + ", ".join(self.requested_reviewers))
        if self.url:
            lines.append(self.url)
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Mapping helpers (defensive, mirroring items_provider's conventions)
# ---------------------------------------------------------------------------


def _text(value: object) -> str:
    try:
        return str(value) if value is not None else ""
    except Exception:  # noqa: BLE001 - PyGithub attribute access can raise
        return ""


def _when(value: object) -> str:
    isoformat = getattr(value, "isoformat", None)
    if callable(isoformat):
        try:
            return str(isoformat())
        except Exception:  # noqa: BLE001
            return ""
    return _text(value) if value is not None else ""


def _login(obj: object) -> str:
    return _text(getattr(obj, "login", None))


def _rows(iterable: Any, limit: int) -> list[Any]:
    out: list[Any] = []
    try:
        for item in iterable or ():
            out.append(item)
            if len(out) >= limit:
                break
    except Exception:  # noqa: BLE001 - a partial page beats a blank pane
        pass
    return out


def _map_check_run(row: Any) -> GitHubCheckRun:
    output = getattr(row, "output", None)
    return GitHubCheckRun(
        name=_text(getattr(row, "name", "")),
        status=_text(getattr(row, "status", "")),
        conclusion=_text(getattr(row, "conclusion", "") or ""),
        url=_text(getattr(row, "html_url", "") or ""),
        summary=_text(getattr(output, "title", "") or "") if output is not None else "",
    )


def _map_review(row: Any) -> GitHubReview:
    return GitHubReview(
        reviewer=_login(getattr(row, "user", None)),
        state=_text(getattr(row, "state", "")),
        body=_text(getattr(row, "body", "") or ""),
        submitted_at=_when(getattr(row, "submitted_at", None)),
    )


def _map_review_comment(row: Any) -> GitHubReviewComment:
    position = getattr(row, "position", None)
    line = getattr(row, "line", None) or getattr(row, "original_line", None)
    reply_to = getattr(row, "in_reply_to_id", None)
    return GitHubReviewComment(
        id=int(getattr(row, "id", 0) or 0),
        author=_login(getattr(row, "user", None)),
        body=_text(getattr(row, "body", "")),
        path=_text(getattr(row, "path", "") or ""),
        line=int(line or 0),
        created_at=_when(getattr(row, "created_at", None)),
        url=_text(getattr(row, "html_url", "") or ""),
        outdated=position is None,
        in_reply_to=int(reply_to or 0),
    )


def group_review_threads(
    comments: list[GitHubReviewComment],
) -> tuple[GitHubReviewThread, ...]:
    """Fold GitHub's flat review-comment list into root-plus-replies threads.

    A reply names its root through ``in_reply_to``; a comment whose root was
    deleted (or paged out) is promoted to a root rather than dropped, so the
    pane never silently loses a reviewer's words.
    """
    roots: dict[int, list[GitHubReviewComment]] = {}
    order: list[int] = []
    for comment in comments:
        key = comment.in_reply_to or comment.id
        if key not in roots and comment.in_reply_to and comment.in_reply_to not in roots:
            key = comment.id  # orphaned reply: promote to root
        if key not in roots:
            roots[key] = []
            order.append(key)
        roots[key].append(comment)
    return tuple(GitHubReviewThread(comments=tuple(roots[key])) for key in order)


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class PullReviewClient:
    """Review reads and review actions for one provider session.

    Wraps the viewer's :class:`GitHubItemsProvider` rather than opening a
    second PyGithub session: repository resolution (and its 404/401/403
    error wording) stays in exactly one place. Every method raises
    :class:`GitHubReviewError`.
    """

    def __init__(self, provider: GitHubItemsProvider) -> None:
        self._provider = provider

    # -- plumbing ------------------------------------------------------

    def _pull(self, full_name: str, number: int) -> Any:
        # Friend-module access (see module docstring): one repo resolver.
        repo = self._provider._repo(full_name)  # noqa: SLF001
        try:
            return repo.get_pull(number)
        except Exception as exc:  # noqa: BLE001 - surface as a coded error
            raise GitHubReviewError(f"Could not load pull request #{number}: {exc}") from exc

    def _require_write(self, action: str) -> None:
        if not self._provider.is_authenticated:
            raise GitHubReviewError(
                f"Sign in to GitHub to {action}; the anonymous viewer is read-only."
            )

    # -- reads ---------------------------------------------------------

    def fetch_review_state(self, full_name: str, number: int) -> GitHubPullReviewState:
        """One call for the whole header: PR status, reviews, checks, counts."""
        pull = self._pull(full_name, number)
        try:
            review_rows = _rows(pull.get_reviews(), _THREAD_PAGE_LIMIT)
        except Exception as exc:  # noqa: BLE001
            raise GitHubReviewError(f"Could not load reviews for #{number}: {exc}") from exc
        head = getattr(pull, "head", None)
        head_sha = _text(getattr(head, "sha", "")) if head is not None else ""
        checks = self._checks_for_sha(full_name, head_sha) if head_sha else ()
        threads = self.fetch_review_threads(full_name, number, pull=pull)
        base = getattr(pull, "base", None)
        return GitHubPullReviewState(
            number=number,
            title=_text(getattr(pull, "title", "")),
            state=_text(getattr(pull, "state", "")),
            draft=bool(getattr(pull, "draft", False)),
            merged=bool(getattr(pull, "merged", False)),
            mergeable=getattr(pull, "mergeable", None),
            mergeable_state=_text(getattr(pull, "mergeable_state", "") or ""),
            base_ref=_text(getattr(base, "ref", "")) if base is not None else "",
            head_ref=_text(getattr(head, "ref", "")) if head is not None else "",
            head_sha=head_sha,
            author=_login(getattr(pull, "user", None)),
            url=_text(getattr(pull, "html_url", "") or ""),
            requested_reviewers=tuple(
                _login(user) for user in getattr(pull, "requested_reviewers", ()) or ()
            ),
            reviews=tuple(_map_review(row) for row in review_rows),
            checks=checks,
            thread_count=len(threads),
            outdated_thread_count=sum(1 for thread in threads if thread.outdated),
        )

    def fetch_review_threads(
        self, full_name: str, number: int, *, pull: Any = None
    ) -> tuple[GitHubReviewThread, ...]:
        """The PR's review threads, grouped root-plus-replies per file/line."""
        pull = pull if pull is not None else self._pull(full_name, number)
        try:
            rows = _rows(pull.get_review_comments(), _THREAD_PAGE_LIMIT)
        except Exception as exc:  # noqa: BLE001
            raise GitHubReviewError(f"Could not load review comments: {exc}") from exc
        return group_review_threads([_map_review_comment(row) for row in rows])

    def _checks_for_sha(self, full_name: str, sha: str) -> tuple[GitHubCheckRun, ...]:
        repo = self._provider._repo(full_name)  # noqa: SLF001
        try:
            commit = repo.get_commit(sha)
            rows = _rows(commit.get_check_runs(), _CHECKS_PAGE_LIMIT)
        except Exception as exc:  # noqa: BLE001
            raise GitHubReviewError(f"Could not load checks for {sha[:12]}: {exc}") from exc
        return tuple(_map_check_run(row) for row in rows)

    def fetch_check_runs(self, full_name: str, number: int) -> tuple[GitHubCheckRun, ...]:
        """Check runs on the PR's current head commit."""
        pull = self._pull(full_name, number)
        head = getattr(pull, "head", None)
        sha = _text(getattr(head, "sha", "")) if head is not None else ""
        if not sha:
            return ()
        return self._checks_for_sha(full_name, sha)

    # -- actions -------------------------------------------------------

    def submit_review(self, full_name: str, number: int, event: str, body: str = "") -> None:
        """Submit a review: *event* is a key of :data:`REVIEW_EVENTS`."""
        api_event = REVIEW_EVENTS.get(event.strip().lower())
        if api_event is None:
            raise GitHubReviewError(
                f"Unknown review action {event!r}; use approve, request changes, or comment."
            )
        if api_event in ("REQUEST_CHANGES", "COMMENT") and not body.strip():
            raise GitHubReviewError("GitHub requires a message for this review action.")
        self._require_write("submit a review")
        pull = self._pull(full_name, number)
        try:
            pull.create_review(body=body, event=api_event)
        except Exception as exc:  # noqa: BLE001
            raise GitHubReviewError(f"Could not submit the review: {exc}") from exc

    def reply_to_thread(self, full_name: str, number: int, comment_id: int, body: str) -> None:
        """Reply to the review thread rooted at *comment_id*."""
        if not body.strip():
            raise GitHubReviewError("A reply needs a message.")
        self._require_write("reply to a review thread")
        pull = self._pull(full_name, number)
        try:
            pull.create_review_comment_reply(comment_id, body)
        except Exception as exc:  # noqa: BLE001
            raise GitHubReviewError(f"Could not post the reply: {exc}") from exc

    def request_reviewers(self, full_name: str, number: int, logins: list[str]) -> None:
        """Ask the listed users for review."""
        reviewers = [login.strip().lstrip("@") for login in logins if login.strip()]
        if not reviewers:
            raise GitHubReviewError("Name at least one reviewer to request.")
        self._require_write("request reviewers")
        pull = self._pull(full_name, number)
        try:
            pull.create_review_request(reviewers=reviewers)
        except Exception as exc:  # noqa: BLE001
            raise GitHubReviewError(f"Could not request reviewers: {exc}") from exc

    def set_draft(self, full_name: str, number: int, draft: bool) -> None:
        """Convert to draft (True) or mark ready for review (False)."""
        self._require_write("change the draft state")
        pull = self._pull(full_name, number)
        try:
            if draft:
                pull.convert_to_draft()
            else:
                pull.mark_ready_for_review()
        except Exception as exc:  # noqa: BLE001
            raise GitHubReviewError(f"Could not change the draft state: {exc}") from exc

    def update_branch(self, full_name: str, number: int) -> None:
        """Merge the base branch into a stale PR branch (GitHub's Update branch)."""
        self._require_write("update the branch")
        pull = self._pull(full_name, number)
        try:
            pull.update_branch()
        except Exception as exc:  # noqa: BLE001
            raise GitHubReviewError(f"Could not update the branch: {exc}") from exc


__all__ = [
    "REVIEW_EVENTS",
    "GitHubCheckRun",
    "GitHubPullReviewState",
    "GitHubReview",
    "GitHubReviewComment",
    "GitHubReviewError",
    "GitHubReviewThread",
    "PullReviewClient",
    "group_review_threads",
]
