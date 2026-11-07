"""Review-thread models shared by the pull-request review client and its mixins.

Split out of :mod:`quill.core.github.pr_review` under GATE-11 when Wave 2 of
the GitHub workbench added reaction counts to review comments: the client
module was at its 600-line cap. :mod:`.pr_review` re-exports every name here,
so callers keep importing from it.

No ``wx`` imports. Strict-typed.
"""

from __future__ import annotations

from dataclasses import dataclass

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
    check_run_id: int = 0  # 0 for a legacy commit status, which cannot be re-requested

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
    side: str = "RIGHT"
    reactions: str = ""  # "3 thumbs up, 1 heart"; empty when nobody reacted


@dataclass(frozen=True, slots=True)
class GitHubReviewThread:
    """A thread: one root review comment plus its replies, in posted order."""

    comments: tuple[GitHubReviewComment, ...]
    node_id: str = ""
    resolved: bool | None = None
    can_resolve: bool = False
    can_unresolve: bool = False
    resolution_error: str = ""

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
        parts.append(
            "resolution unavailable"
            if self.resolved is None
            else "resolved"
            if self.resolved
            else "unresolved"
        )
        return " — ".join(part for part in parts if part)


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


__all__ = [
    "GitHubCheckRun",
    "GitHubReview",
    "GitHubReviewComment",
    "GitHubReviewThread",
    "group_review_threads",
]
