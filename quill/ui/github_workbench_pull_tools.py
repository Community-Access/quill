"""A pull request's exact patch, its revert, and its conflicts in a worktree (GH-PT).

Three commands on a pull request's row:

* **Open Patch in Editor** writes the pull request's whole change as one
  unified diff, ``<repo>-pr-<n>.diff``, and opens it, so the change can be
  read top to bottom with the editor's own find, and saved or applied.
* **Revert Pull Request...** opens a new pull request that undoes a merged
  one, as the web's Revert button does, after asking its title and whether
  it is a draft.
* **Resolve Conflicts in a Worktree...** (QUILL; the editor owns local Git)
  fetches the head and base branches into a new folder beside the checkout,
  merges the base there without committing, and walks the conflicted files
  with Tools > Local Git's Resolve Conflicts. The checkout the person was in
  is never changed.

The work is :mod:`quill.core.github.pull_tools`.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from quill.core.github.items_provider import GitHubItem

__all__ = ["PULL_TOOL_REASONS", "PULL_TOOL_VERBS", "GitHubWorkbenchPullToolsMixin"]

PULL_TOOL_VERBS: dict[str, frozenset[str]] = {
    "open_patch": frozenset({"item"}),
    "revert_pull": frozenset({"item"}),
    "resolve_conflicts": frozenset({"item"}),
}

PULL_TOOL_REASONS: dict[str, str] = {
    "open_patch": "Open Patch is for a pull request.",
    "revert_pull": "Revert is for a merged pull request, while you are signed in.",
    "resolve_conflicts": (
        "Resolve Conflicts in a Worktree is for an open pull request, in QUILL, "
        "which keeps the local Git checkout."
    ),
}


class GitHubWorkbenchPullToolsMixin:
    items: Any
    frame: Any
    signed_in: bool
    resolve_conflicts: Callable[[object, str, int, str, str], None] | None = None
    _open_document: Callable[[Path], None] | None = None
    _say: Callable[[str], None]
    _background: Callable[[str, Callable[[], Any], Callable[[Any], None]], None]
    _ask_text: Callable[..., str]
    _confirm: Callable[[str, str], bool]
    _parent: Callable[[], Any]

    def github_api(self) -> Any:
        raise NotImplementedError

    # -- the exact patch -----------------------------------------------------------

    def _fits_open_patch(self, row: object) -> bool:
        return isinstance(row, GitHubItem) and row.is_pr

    def _do_open_patch(self, ref: Any, row: object) -> None:
        from quill.core.github.pull_tools import patch_file_name, patch_text

        assert isinstance(row, GitHubItem)
        api, repository, number = self.github_api(), ref.instance, row.number
        self._background(
            f"read the patch of #{number}",
            lambda: patch_text(api, repository, number),
            lambda patch: self._patch_landed(repository, number, patch, patch_file_name),
        )

    def _patch_landed(
        self, repository: str, number: int, patch: Any, name_for: Callable[[str, int], str]
    ) -> None:
        from quill.ui.github_workbench_reading import documents_folder

        if not patch.files:
            self._say(f"#{number} changes no files.")
            return
        folder = documents_folder()
        target = folder / name_for(repository, number)
        try:
            folder.mkdir(parents=True, exist_ok=True)
            target.write_text(patch.text, encoding="utf-8", newline="\n")
        except OSError as exc:
            self._say(f"Could not write the patch: {exc}")
            return
        if self._open_document is not None:
            self._open_document(target)
            self._say(f"Opened the patch of #{number}. {patch.sentence}")
        else:
            self._say(f"Saved the patch of #{number} as {target}. {patch.sentence}")

    # -- revert --------------------------------------------------------------------

    def _fits_revert_pull(self, row: object) -> bool:
        return self.signed_in and isinstance(row, GitHubItem) and row.is_pr and row.is_merged

    def _do_revert_pull(self, ref: Any, row: object) -> None:
        from quill.core.github.pull_tools import revert_pull

        assert isinstance(row, GitHubItem)
        title = self._ask_text(
            "Revert Pull Request",
            f"Title of the pull request that undoes #{row.number}:",
            value=f'Revert "{row.title}"',
        )
        if not title:
            return
        target = row.base_branch or "the branch it went into"
        draft = self._confirm(
            "Revert Pull Request",
            f"Open it as a draft? Yes opens a draft, which nobody can merge until it is "
            f"marked ready. No opens it ready for review. Either way it undoes #{row.number} "
            f"on {target} only when it is merged.",
        )
        api, repository, number = self.github_api(), ref.instance, row.number
        self._background(
            f"revert #{number}",
            lambda: revert_pull(api, repository, number, title=title, draft=draft),
            lambda said: (self._say(str(said)), self.frame.reload()),
        )

    # -- conflicts in a worktree ---------------------------------------------------

    def _fits_resolve_conflicts(self, row: object) -> bool:
        return (
            self.resolve_conflicts is not None
            and isinstance(row, GitHubItem)
            and row.is_pr
            and row.state.casefold() == "open"
        )

    def _do_resolve_conflicts(self, ref: Any, row: object) -> None:
        assert isinstance(row, GitHubItem)
        api, repository, number = self.github_api(), ref.instance, row.number

        def work() -> Any:
            return api.rest("GET", f"/repos/{repository}/pulls/{number}").data or {}

        self._background(
            f"read the branches of #{number}",
            work,
            lambda pull: self._branches_landed(repository, number, pull),
        )

    def _branches_landed(self, repository: str, number: int, pull: Any) -> None:
        head = pull.get("head") or {}
        base = pull.get("base") or {}
        head_repo = str((head.get("repo") or {}).get("full_name") or "")
        if head_repo.casefold() != repository.casefold():
            where = head_repo or "a fork that no longer exists"
            self._say(
                f"#{number} comes from {where}, so its branch is not in {repository}. "
                "Resolve its conflicts in a checkout of that fork, or ask its author to."
            )
            return
        start = self.resolve_conflicts
        if start is not None:
            start(self._parent(), repository, number, str(head.get("ref")), str(base.get("ref")))
