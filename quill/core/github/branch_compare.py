"""Compare Branches: ahead/behind counts, the commits each way between two
refs, the changed files and the open pull request (GHManage parity,
Ctrl+Shift+B). The sentences said about one are in :mod:`.compare_words`.

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


#: What GitHub's compare call returns at most, however it is paged.
MAX_COMPARE_COMMITS = 250


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
    #: What *base* has that *head* lacks, newest first (the comparison turned round).
    behind_commits: tuple[GitHubCommit, ...] = ()
    #: The open pull request of *head* into *base*; 0 when there is none or GitHub did not say.
    pull_number: int = 0
    pull_title: str = ""
    pull_url: str = ""

    @property
    def commits_cut_short(self) -> bool:
        """Whether GitHub has more commits between the two than ``commits`` holds."""
        return self.total_commits > len(self.commits)

    def commits_tab_title(self) -> str:
        """ "Commits (12)", or "Commits (250 of 1,204, newest)" when cut short."""
        shown = len(self.commits)
        if self.commits_cut_short:
            return f"Commits ({shown} of {self.total_commits:,}, newest)"
        return f"Commits ({shown})"


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

    # An empty side is the repository's default branch ("Compare With Default").
    if not base or not head:
        default = str(getattr(repo, "default_branch", "") or "main")
        base, head = base or default, head or default
    # ``ref^`` is the commit before *ref* ("Compare With Previous"), asked for
    # by SHA rather than trusted to survive a URL path.
    base, head = _parent_sha(repo, base), _parent_sha(repo, head)
    comparison = repo.compare(base, head)
    # GitHub lists a comparison's commits oldest first, and the compare call
    # returns at most 250 of them. Taking the first *limit* showed the oldest
    # few under a "newest first" label; take all GitHub gives, newest first,
    # and let the caller say "N of total" when that is not all of them.
    commit_rows = take(getattr(comparison, "commits", None), max(limit, MAX_COMPARE_COMMITS))
    commit_rows = list(reversed(commit_rows))
    file_rows = take(getattr(comparison, "files", None), 300)
    behind_by = int(getattr(comparison, "behind_by", 0) or 0)
    behind_rows: list[Any] = []
    if behind_by:
        # GitHub lists only what head adds; what base has that head lacks is
        # the same comparison the other way round. Worth showing without it.
        try:
            back = repo.compare(head, base)
            behind_rows = list(reversed(take(getattr(back, "commits", None), MAX_COMPARE_COMMITS)))
        except Exception:  # noqa: BLE001 - the ahead half still stands
            behind_rows = []
    pull = open_pull_between(repo, base, head)
    return GitHubBranchComparison(
        base=base,
        head=head,
        ahead_by=int(getattr(comparison, "ahead_by", 0) or 0),
        behind_by=behind_by,
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
        behind_commits=tuple(map_commit(row) for row in behind_rows),
        pull_number=int(getattr(pull, "number", 0) or 0) if pull is not None else 0,
        pull_title=str(getattr(pull, "title", "") or "") if pull is not None else "",
        pull_url=str(getattr(pull, "html_url", "") or "") if pull is not None else "",
    )


def _parent_sha(repo: Any, ref: str) -> str:
    """*ref* itself, or, for ``name^``, the SHA of that commit's first parent."""
    if not ref.endswith("^"):
        return ref
    parents = getattr(repo.get_commit(ref[:-1]), "parents", None) or ()
    if not parents:
        raise ValueError(f"{ref[:-1]} has no commit before it")
    return str(getattr(parents[0], "sha", "") or ref)


def open_pull_between(repo: Any, base: str, head: str) -> Any | None:
    """The open pull request of *head* into *base*, or None. GitHub filters
    by OWNER:BRANCH, and *head* may already name another owner's branch. A
    tag or a commit has no pull request, and a failure here never costs the
    comparison."""
    full_name = str(getattr(repo, "full_name", "") or "")
    owner = full_name.split("/", 1)[0]
    named = head if ":" in head or not owner else f"{owner}:{head}"
    try:
        for pull in repo.get_pulls(state="open", base=base, head=named):
            return pull
    except Exception:  # noqa: BLE001 - the comparison is worth showing without it
        return None
    return None


def split_compare_ref(text: str) -> tuple[str, str]:
    """``main...feature`` as ``("main", "feature")``, from a compare link's
    path. Two dots work too; a lone ref is the head against the default
    branch, so its base is ``""``. A ``?`` or ``#`` tail is not part of it."""
    spec = text.split("?", 1)[0].split("#", 1)[0].strip().strip("/")
    for dots in ("...", ".."):
        if dots in spec:
            base, _sep, head = spec.partition(dots)
            return base.strip(), head.strip()
    return "", spec


__all__ = [
    "MAX_COMPARE_COMMITS",
    "GitHubBranchComparison",
    "fetch_branch_comparison",
    "open_pull_between",
    "split_compare_ref",
]
