"""Compare from a row, and compare links, in the GitHub Workbench (GHManage parity).

Compare With Default (Ctrl+B) and Compare With Previous (Alt+Shift+B) on a
branch, tag, release or commit row go straight to the comparison they are most
often wanted for, without asking for two names the way Compare Branches...
does:

- **With Default:** a branch against the default branch (what it adds); a
  tag, release or commit as the base and the default branch as the head (what
  has happened since).
- **With Previous:** a tag or release against the one listed after it (the
  lists are newest first, drafts skipped); a commit, or a branch's newest
  commit, against its parent (what that one commit changed).

A pasted ``https://github.com/owner/name/compare/a...b`` link opens the same
window wherever the Workbench takes a link: File > Open GitHub Address
(Ctrl+L) and a favorite. Nothing is said on the way (GATE-13); a failure is
said once, through the frame.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.github.items_provider import GitHubBranch, GitHubCommit, GitHubRelease, GitHubTag

__all__ = [
    "COMPARE_REASONS",
    "COMPARE_VERBS",
    "GitHubWorkbenchCompareMixin",
    "compare_with_default_refs",
    "compare_with_previous_refs",
]

_ROWS = frozenset({"branch", "tag", "release", "commit"})

COMPARE_VERBS: dict[str, frozenset[str]] = {
    "compare_default": _ROWS,
    "compare_previous": _ROWS,
}

COMPARE_REASONS: dict[str, str] = {
    "compare_previous": (
        "This is the last one listed, so there is none before it to compare with. "
        "Load more of the list (Ctrl+Shift+Page Down) to reach an older one."
    ),
}


def _ref_name(row: object) -> str:
    """The name a row is compared by: a branch's or tag's name, a release's
    tag, a commit's SHA."""
    if isinstance(row, (GitHubBranch, GitHubTag)):
        return row.name
    if isinstance(row, GitHubRelease):
        return row.tag
    if isinstance(row, GitHubCommit):
        return row.sha
    return ""


def compare_with_default_refs(row: object) -> tuple[str, str]:
    """(base, head) for Compare With Default; ``""`` is the default branch."""
    name = _ref_name(row)
    if isinstance(row, GitHubBranch):
        return "", name
    return name, ""


def compare_with_previous_refs(row: object, rows: list[object]) -> tuple[str, str] | None:
    """(base, head) for Compare With Previous, or None when nothing comes before.

    A tag or release is compared with the next one of its kind in *rows*
    (newest first; a draft release may have no tag yet, so drafts are
    skipped). A commit or a branch is compared with its parent, written
    ``ref^`` and resolved by :func:`quill.core.github.branch_compare.fetch_branch_comparison`.
    """
    name = _ref_name(row)
    if not name:
        return None
    if isinstance(row, (GitHubCommit, GitHubBranch)):
        return f"{name}^", name
    index = next((i for i, other in enumerate(rows) if other is row), -1)
    if index < 0:
        return None
    for older in rows[index + 1 :]:
        if type(older) is not type(row) or getattr(older, "draft", False):
            continue
        previous = _ref_name(older)
        if previous and previous != name:
            return previous, name
    return None


class GitHubWorkbenchCompareMixin:
    """The two row comparisons and compare links, for the GitHub provider."""

    items: Any
    frame: Any
    _say: Callable[[str], None]
    _background: Callable[[str, Callable[[], Any], Callable[[Any], None]], None]
    _repo_for: Callable[[Any], str]
    _parent: Callable[[], Any]

    def _fits_compare_previous(self, row: object) -> bool:
        rows = list(getattr(self.frame, "rows", []) or [])
        return compare_with_previous_refs(row, rows) is not None

    def _do_compare_default(self, ref: Any, row: object) -> None:
        base, head = compare_with_default_refs(row)
        self.open_comparison(self._repo_for(ref), base, head)

    def _do_compare_previous(self, ref: Any, row: object) -> None:
        found = compare_with_previous_refs(row, list(self.frame.rows))
        if found is None:
            self._say(COMPARE_REASONS["compare_previous"])
            return
        self.open_comparison(self._repo_for(ref), *found)

    def open_comparison(self, repo: str, base: str, head: str) -> None:
        """Fetch the comparison off the UI thread, then show it, parented here."""
        if not repo:
            self._say("Open a repository first. Ctrl+L opens one by name or link.")
            return

        def show(comparison: Any) -> None:
            from quill.ui.github_compare_branches_dialog import GitHubCompareBranchesDialog

            GitHubCompareBranchesDialog(
                self._parent(), self.items, repo, comparison, announce_cb=self._say
            ).show()

        self._background(
            "compare them", lambda: self.items.compare_branches(repo, base, head), show
        )

    def open_link(self, text: str) -> bool:
        """A pasted link the Workbench opens itself: a compare link opens the
        comparison. False for anything else, which the caller handles."""
        from quill.core.github.branch_compare import split_compare_ref
        from quill.core.github.references import GitHubReferenceError, parse_github_reference

        try:
            reference = parse_github_reference(text.strip())
        except GitHubReferenceError:
            return False
        if reference.kind != "compare" or not reference.ref:
            return False
        base, head = split_compare_ref(reference.ref)
        if not head:
            return False
        self.open_comparison(reference.repository, base, head)
        return True
