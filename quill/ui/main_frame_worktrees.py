"""Worktree commands for ``MainFrame``: Tools > Local Git > Worktrees.

Why QUILL cares about worktrees at all: checking out a different branch in
place rewrites every file on disk, including the one the user has open. A
sighted user notices the editor redraw; a screen-reader user does not -- the
document under the review cursor quietly becomes a different document with the
same name. A worktree gives each branch a folder of its own, so changing
context is "open a different file" (an action the user takes and hears)
instead of "this file is now a different file" (something that happens to
them). That is the accessibility argument, and it is the reason these
commands exist.

The mixin is the wiring only: it resolves a repository root, confirms git is
available, and hands work to the wx-free engine
(:mod:`quill.core.git_worktree`) and the two dialogs in
:mod:`quill.ui.git_worktree_dialogs`. Listing runs on a background task the
same way every other Local Git command does; the per-row actions run inline
while the modal list is up (as the Uncommitted Changes dialog's stage/unstage
already do), announced before and after so a slow ``git worktree add`` is
never silent.

Depends on :class:`quill.ui.main_frame_local_git.LocalGitMixin` for the shared
``_local_git_ready`` / ``_local_git_repo_root`` / ``_local_git_runner``
helpers; both mixins are in ``MainFrame``'s bases.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Sequence

    from quill.core.git_worktree import WorktreeEntry


class WorktreesMixin:
    """Adds the git worktree command surface to ``MainFrame``."""

    # ------------------------------------------------------------------
    # Commands

    def local_git_worktrees(self) -> None:
        """Tools > Local Git > Worktrees..."""
        if not self._local_git_ready():
            return
        root = self._local_git_repo_root()
        if root is None:
            return

        from quill.core.git_worktree import list_worktrees

        def work(_progress: object) -> object:
            return list_worktrees(self._local_git_runner(), root)

        self._run_background_task(
            "Loading worktrees", work, lambda result: self._on_worktrees_listed(root, result)
        )

    def local_git_new_worktree(self) -> None:
        """Tools > Local Git > New Worktree... (without opening the list first)."""
        if not self._local_git_ready():
            return
        root = self._local_git_repo_root()
        if root is None:
            return
        message = self._worktree_create(root)
        if message:
            self._set_status(message)

    # ------------------------------------------------------------------
    # The list dialog

    def _on_worktrees_listed(self, root: str, result: Any) -> None:
        if not result.ok:
            self._set_status(result.message)
            return
        from quill.ui.git_worktree_dialogs import WorktreesDialog

        WorktreesDialog(
            self.frame,
            list(result.worktrees),
            refresh_provider=lambda: self._worktree_entries(root),
            on_new=lambda: self._worktree_create(root),
            on_open=self._worktree_open,
            on_remove=lambda entry: self._worktree_remove(root, entry),
            on_lock_toggle=lambda entry: self._worktree_lock_toggle(root, entry),
            on_prune=lambda: self._worktree_prune(root),
            announce_cb=self._announce,
        ).show()

    def _worktree_entries(self, root: str) -> Sequence[WorktreeEntry]:
        from quill.core.git_worktree import list_worktrees

        result = list_worktrees(self._local_git_runner(), root)
        return result.worktrees if result.ok else ()

    # ------------------------------------------------------------------
    # Actions

    def _worktree_create(self, root: str) -> str:
        from quill.core.git_worktree import add_worktree
        from quill.ui.git_worktree_dialogs import NewWorktreeDialog

        branches = self._worktree_branch_names(root)
        request = NewWorktreeDialog(
            self.frame,
            branches,
            default_parent_folder=str(Path(root).parent),
            announce_cb=self._announce,
        ).show()
        if request is None:
            return "New worktree cancelled."
        self._announce("Creating the worktree. This can take a moment for a large repository.")
        with self._wx.BusyCursor():
            result = add_worktree(
                self._local_git_runner(),
                root,
                request.path,
                request.branch,
                create_branch=request.create_branch,
                from_ref=request.from_ref,
            )
        return str(result.message)

    def _worktree_branch_names(self, root: str) -> list[str]:
        """Local branches that are not already checked out somewhere."""
        from quill.core.local_git import list_local_branches

        try:
            branches = list_local_branches(root, runner=self._local_git_runner())
        except Exception:  # noqa: BLE001 - an empty chooser is better than no dialog
            return []
        taken = {entry.branch for entry in self._worktree_entries(root) if entry.branch}
        return [b.name for b in branches if b.name not in taken]

    def _worktree_remove(self, root: str, entry: Any) -> str:
        from quill.core.git_worktree import remove_worktree

        if not self._worktree_confirm(
            f"Remove the worktree at {entry.path}?\n\n"
            "The folder and everything in it will be deleted from your disk. "
            "The branch itself stays in the repository.",
            "Remove Worktree",
        ):
            return "Worktree kept."
        result = remove_worktree(self._local_git_runner(), root, entry.path)
        if result.ok or "not committed" not in result.message:
            return str(result.message)
        if not self._worktree_confirm(
            f"{result.message}\n\nDiscard those changes and remove the worktree anyway?",
            "Discard Changes",
        ):
            return "Worktree kept, with its changes."
        forced = remove_worktree(self._local_git_runner(), root, entry.path, force=True)
        return str(forced.message)

    def _worktree_lock_toggle(self, root: str, entry: Any) -> str:
        from quill.core.git_worktree import lock_worktree, unlock_worktree

        runner = self._local_git_runner()
        if entry.is_locked:
            return str(unlock_worktree(runner, root, entry.path).message)
        reason = self._worktree_prompt(
            "Lock Worktree", "Why is this worktree locked? (optional):", ""
        )
        if reason is None:
            return "Lock cancelled."
        return str(lock_worktree(runner, root, entry.path, reason=reason).message)

    def _worktree_prune(self, root: str) -> str:
        from quill.core.git_worktree import prune_worktrees

        return str(prune_worktrees(self._local_git_runner(), root).message)

    # ------------------------------------------------------------------
    # Open in QUILL

    def _worktree_open(self, entry: Any) -> tuple[str, bool]:
        """Open the counterpart of the current document inside *entry*.

        QUILL's file surface opens documents, not folders, so "open this
        worktree" means "open the same file, from over there". When there is
        no counterpart (the file is new on this branch, or nothing is open),
        the user is told so and given a file picker already pointed at the
        worktree folder rather than a dead end.
        """
        counterpart = self._worktree_counterpart(entry.path)
        if counterpart is not None:
            self.open_file(counterpart)
            return (f"Opened {counterpart.name} from {entry.path}.", True)
        chosen = self._worktree_pick_file(entry.path)
        if chosen is None:
            return (f"Nothing opened from {entry.path}.", False)
        self.open_file(chosen)
        return (f"Opened {chosen.name} from {entry.path}.", True)

    def _worktree_counterpart(self, worktree_path: str) -> Path | None:
        path = getattr(getattr(self, "document", None), "path", None)
        if not path:
            return None
        try:
            current = Path(path).resolve()
            source_root = self._local_git_find_root(current)
            if source_root is None:
                return None
            relative = current.relative_to(Path(source_root).resolve())
            candidate = Path(worktree_path) / relative
        except (OSError, ValueError):
            return None
        return candidate if candidate.is_file() else None

    def _worktree_pick_file(self, worktree_path: str) -> Path | None:
        wx = self._wx
        self._announce(
            f"No counterpart of the current document in {worktree_path}. Choose a file to open."
        )
        with wx.FileDialog(
            self.frame,
            "Open a file from this worktree",
            defaultDir=worktree_path,
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as dialog:
            if self._show_modal_dialog(dialog, "Open From Worktree") != wx.ID_OK:
                return None
            return Path(dialog.GetPath())

    # ------------------------------------------------------------------
    # Shared prompts

    def _worktree_confirm(self, message: str, title: str) -> bool:
        wx = self._wx
        dialog = wx.MessageDialog(
            self.frame, message, title, wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING
        )
        try:
            return self._show_modal_dialog(dialog, title) == wx.ID_YES
        finally:
            dialog.Destroy()

    def _worktree_prompt(self, title: str, label: str, value: str = "") -> str | None:
        wx = self._wx
        with wx.TextEntryDialog(self.frame, label, title, value) as dialog:
            if self._show_modal_dialog(dialog, title) != wx.ID_OK:
                return None
            return str(dialog.GetValue()).strip()

    # ------------------------------------------------------------------
    # Command palette registration

    def _register_worktree_commands(self) -> None:
        entries = (
            ("localgit.worktrees", "Local Git: Worktrees...", self.local_git_worktrees),
            ("localgit.new_worktree", "Local Git: New Worktree...", self.local_git_new_worktree),
        )
        for command_id, title, handler in entries:
            self.commands.try_register(command_id, title, handler, self._binding_for(command_id))


__all__ = ["WorktreesMixin"]
