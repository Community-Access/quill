"""Repository Files, Milestones, and the batch milestone and assignee changes
in the GitHub Items viewer (Wave 3).

Files... (Alt+F) and Milestones... open their own shared windows; both are also
on the list's context menu. The Batch... menu gains Set Milestone and Add
Assignees beside Close, Reopen and Add Label: each names the exact issues and
asks first, and the result counts only what GitHub confirmed. Split from
``github_items_dialog.py`` to keep it inside GATE-11.
"""

from __future__ import annotations

import threading
from collections.abc import Callable

from quill.core.github.items_errors import GitHubItemsError
from quill.core.github.milestones import GitHubMilestone

__all__ = ["GitHubRepositoryToolsMixin"]


def _message(exc: BaseException) -> str:
    """The error's sentence, without the support code a screen reader would read out."""
    return str(exc.args[0]) if exc.args else str(exc)


class GitHubRepositoryToolsMixin:
    """Files, milestones and the Wave 3 batch actions for ``GitHubItemsDialog``."""

    def _require_repo(self) -> str:
        repo = self._repo
        if not repo or "/" not in repo:
            self._announce("Load a repository first.")
            return ""
        return repo

    def _open_repo_files(self) -> None:
        repo = self._require_repo()
        if not repo:
            return
        from quill.ui.github_repo_files_dialog import GitHubRepoFilesDialog

        ref = self._drill_branch or ""
        GitHubRepoFilesDialog(
            self.dialog,
            self._provider,
            repo=repo,
            ref=ref,
            open_in_editor_cb=self._open_file_reference_cb,
            announce_cb=self._announce,
        ).show()

    def _open_milestones(self) -> None:
        repo = self._require_repo()
        if not repo:
            return
        from quill.ui.github_milestones_dialog import GitHubMilestonesDialog

        GitHubMilestonesDialog(
            self.dialog, self._provider, repo=repo, announce_cb=self._announce
        ).show()

    # -- batch ----------------------------------------------------------------

    def _add_batch_extras(
        self, add: Callable[[str, Callable[[], None]], None], numbers: list[int]
    ) -> None:
        count = len(numbers)
        add(f"Set milestone on {count} selected...", lambda: self._batch_set_milestone(numbers))
        add(f"Add assignees to {count} selected...", lambda: self._batch_add_assignees(numbers))

    def _confirm_batch(self, action: str, numbers: list[int]) -> bool:
        listing = ", ".join(f"#{n}" for n in numbers[:20])
        if len(numbers) > 20:
            listing += f" and {len(numbers) - 20} more"
        question = (
            f"{action} in {self._repo}?\n\n{listing}\n\n"
            "This changes the items on GitHub for everyone watching them."
        )
        if self._confirm_action(question, "Confirm batch change"):
            return True
        self._announce("Batch change cancelled.")
        return False

    def _run_batch_work(self, requested: int, work: Callable[[], list[str]]) -> None:
        wx = self._wx

        def worker() -> None:
            try:
                errors = work()
            except GitHubItemsError as exc:
                wx.CallAfter(self._set_status, f"Error: {_message(exc)}")
                return
            wx.CallAfter(self._on_batch_done, requested, errors)

        threading.Thread(target=worker, daemon=True).start()  # GATE-40-OK: consented batch write.

    def _batch_set_milestone(self, numbers: list[int]) -> None:
        repo = self._require_repo()
        if not repo:
            return
        self._set_status("Loading milestones...", announce=False)

        def worker() -> None:
            try:
                milestones = self._provider.fetch_milestones(repo, state="open")
            except GitHubItemsError as exc:
                self._wx.CallAfter(self._set_status, f"Could not load milestones: {_message(exc)}")
                return
            self._wx.CallAfter(self._choose_batch_milestone, numbers, milestones)

        threading.Thread(target=worker, daemon=True).start()  # GATE-40-OK: milestone read.

    def _choose_batch_milestone(
        self, numbers: list[int], milestones: list[GitHubMilestone]
    ) -> None:
        wx = self._wx
        from quill.ui.dialog_contract import dialog_alive

        if not dialog_alive(self.dialog):
            return
        choices = [m.label() for m in milestones] + ["No milestone (clear it)"]
        with wx.SingleChoiceDialog(
            self.dialog,
            f"Milestone for the {len(numbers)} selected item(s):",
            "Set Milestone",
            choices,
        ) as picker:
            if self._show_modal(picker, "Set Milestone") != wx.ID_OK:
                self._announce("Batch change cancelled.")
                return
            index = picker.GetSelection()
        chosen = milestones[index] if 0 <= index < len(milestones) else None
        action = (
            f"Set milestone {chosen.title!r} on {len(numbers)} item(s)"
            if chosen
            else f"Clear the milestone on {len(numbers)} item(s)"
        )
        if not self._confirm_batch(action, numbers):
            return
        self._set_status(f"{action}...")
        repo, number = self._repo, chosen.number if chosen else None
        self._run_batch_work(
            len(numbers), lambda: self._provider.assign_milestone(repo, numbers, number)
        )

    def _batch_add_assignees(self, numbers: list[int]) -> None:
        wx = self._wx
        with wx.TextEntryDialog(
            self.dialog,
            "GitHub usernames to assign, separated by commas:",
            "Add Assignees",
        ) as entry:
            if self._show_modal(entry, "Add Assignees") != wx.ID_OK:
                self._announce("Batch change cancelled.")
                return
            typed = entry.GetValue()
        logins = [part for part in typed.replace(" ", ",").split(",") if part.strip()]
        if not logins:
            self._announce("Type at least one GitHub username.")
            return
        action = f"Assign {', '.join(logins)} to {len(numbers)} item(s)"
        if not self._confirm_batch(action, numbers):
            return
        self._set_status(f"{action}...")
        repo = self._repo
        self._run_batch_work(
            len(numbers), lambda: self._provider.add_assignees(repo, numbers, logins)
        )
