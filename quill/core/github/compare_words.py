"""What is said about a comparison of two branches, tags or commits: words only.

The sentences GHManage's ``compareview.py`` says, moved here so both the
Compare dialog and anything else that reports a comparison say them the same
way, and so they are tested without a window. No ``wx``.

Everything takes a :class:`~quill.core.github.branch_compare.GitHubBranchComparison`.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from quill.core.github.branch_compare import GitHubBranchComparison

__all__ = [
    "ahead_tab_title",
    "behind_tab_title",
    "commits_said",
    "list_said",
    "naming",
    "pull_note",
    "relation",
    "short_ref",
    "summary",
]


def commits_said(n: int) -> str:
    """``1 commit`` or ``1,204 commits``."""
    return f"{n:,} commit{'s' if n != 1 else ''}"


def short_ref(ref: str) -> str:
    """A ref as it is said: a whole SHA cut down as a commit's row has it."""
    return ref[:7] if re.fullmatch(r"[0-9a-f]{12,40}", ref) else ref


def naming(c: GitHubBranchComparison) -> str:
    """Which two these are: ``feature compared with main``."""
    return f"{short_ref(c.head)} compared with {short_ref(c.base)}"


def relation(c: GitHubBranchComparison) -> str:
    """How the two stand, in a sentence."""
    head, base = short_ref(c.head), short_ref(c.base)
    if c.base == c.head:
        return f"{head} is being compared with itself, so there is nothing to show."
    if c.status == "identical" or (not c.ahead_by and not c.behind_by):
        return f"{head} and {base} are identical."
    if c.ahead_by and c.behind_by:
        return (
            f"{head} and {base} have diverged: {head} is {commits_said(c.ahead_by)} "
            f"ahead and {c.behind_by:,} behind."
        )
    if c.ahead_by:
        return f"{head} is {commits_said(c.ahead_by)} ahead of {base}."
    return f"{head} is {commits_said(c.behind_by)} behind {base}."


def pull_note(c: GitHubBranchComparison) -> str:
    """``Pull request #12 is open: Fix the thing.``, or nothing when there is none."""
    if not c.pull_number:
        return ""
    title = f": {c.pull_title}" if c.pull_title else ""
    return f"Pull request #{c.pull_number} is open{title}."


def _files_note(c: GitHubBranchComparison) -> str:
    if not c.files:
        return ""
    added = sum(f.additions for f in c.files)
    removed = sum(f.deletions for f in c.files)
    count = len(c.files)
    return (
        f"{count:,} file{'s' if count != 1 else ''} changed, "
        f"{added:,} line{'s' if added != 1 else ''} added and {removed:,} removed."
    )


def summary(c: GitHubBranchComparison) -> str:
    """The whole comparison in one paragraph, for the top of the window."""
    return " ".join(p for p in (relation(c), _files_note(c), pull_note(c)) if p)


def _tab(name: str, shown: int, total: int) -> str:
    if total > shown:
        return f"{name} ({shown:,} of {total:,}, newest)"
    return f"{name} ({shown:,})"


def ahead_tab_title(c: GitHubBranchComparison) -> str:
    """``Commits Ahead (12)``, or ``(250 of 1,204, newest)`` when GitHub stopped."""
    return _tab("Commits Ahead", len(c.commits), max(c.ahead_by, c.total_commits))


def behind_tab_title(c: GitHubBranchComparison) -> str:
    """``Commits Behind (3)``: what the base has that the head lacks."""
    return _tab("Commits Behind", len(c.behind_commits), c.behind_by)


def list_said(c: GitHubBranchComparison, behind: bool) -> str:
    """A list's name and how many it holds, and if not all, how many of what."""
    name = "Commits behind" if behind else "Commits ahead"
    shown = len(c.behind_commits if behind else c.commits)
    total = c.behind_by if behind else max(c.ahead_by, c.total_commits)
    if total > shown:
        return f"{name}: the newest {shown:,} of {total:,}."
    return f"{name}: {shown:,}."
