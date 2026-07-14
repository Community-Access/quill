"""Compare Branches: ahead/behind counts, the commits between two refs, and
the changed files (GHManage parity, Ctrl+Shift+B).

Split out of :mod:`quill.core.github.items_provider` to keep that module
under its GATE-11 size budget --
:meth:`~quill.core.github.items_provider.GitHubItemsProvider.compare_branches`
is a thin wrapper around :func:`fetch_branch_comparison` here. The import of
``items_provider`` below is function-local rather than top-level so this
module never participates in a circular import at package load time: by the
time ``compare_branches`` calls in, ``items_provider`` is already fully
loaded (it is the caller).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from quill.core.github.items_provider import GitHubCommit, GitHubPullFile


@dataclass(frozen=True, slots=True)
class GitHubBranchComparison:
    """Ahead/behind counts, the commits between two refs, and the changed
    files -- GHManage's "Compare Branches" (Ctrl+Shift+B)."""

    base: str
    head: str
    ahead_by: int = 0
    behind_by: int = 0
    status: str = ""  # "ahead" / "behind" / "identical" / "diverged"
    total_commits: int = 0
    commits: tuple[GitHubCommit, ...] = ()
    files: tuple[GitHubPullFile, ...] = ()
    permalink_url: str = ""


def fetch_branch_comparison(
    repo: Any,
    base: str,
    head: str,
    *,
    map_commit: Callable[[Any], Any],
    take: Callable[[Any, int], list[Any]],
    limit: int,
) -> GitHubBranchComparison:
    """Fetch and map the two-branch comparison for *repo* (an already-
    resolved PyGithub ``Repository``). *map_commit* and *take* are the
    provider's own commit-mapping and pagination helpers, passed in rather
    than imported so this module stays free of module-load-time coupling.
    Raises whatever PyGithub raises; the caller wraps that in
    :class:`~quill.core.github.items_provider.GitHubItemsError`.
    """
    from quill.core.github.items_provider import GitHubPullFile

    comparison = repo.compare(base, head)
    commit_rows = take(getattr(comparison, "commits", None), limit)
    file_rows = take(getattr(comparison, "files", None), 300)
    return GitHubBranchComparison(
        base=base,
        head=head,
        ahead_by=int(getattr(comparison, "ahead_by", 0) or 0),
        behind_by=int(getattr(comparison, "behind_by", 0) or 0),
        status=str(getattr(comparison, "status", "") or ""),
        total_commits=int(getattr(comparison, "total_commits", 0) or 0),
        commits=tuple(map_commit(row) for row in commit_rows),
        files=tuple(
            GitHubPullFile(
                filename=str(getattr(row, "filename", "") or ""),
                status=str(getattr(row, "status", "") or ""),
                additions=int(getattr(row, "additions", 0) or 0),
                deletions=int(getattr(row, "deletions", 0) or 0),
                changes=int(getattr(row, "changes", 0) or 0),
                previous_filename=str(getattr(row, "previous_filename", "") or ""),
                patch=str(getattr(row, "patch", "") or ""),
            )
            for row in file_rows
        ),
        permalink_url=str(getattr(comparison, "html_url", "") or ""),
    )


__all__ = ["GitHubBranchComparison", "fetch_branch_comparison"]
