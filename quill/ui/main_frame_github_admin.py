"""Repository-lifecycle GitHub commands for ``MainFrame``: create, rename,
change visibility, change default branch, configure branch protection,
fork, delete a branch, and commit multiple files atomically.

The third GitHub UI mixin, alongside :mod:`quill.ui.main_frame_github`
(single-file browse/save) and :mod:`quill.ui.main_frame_github_items`
(issues/PRs/branches viewer). Every command here is a genuine write against
GitHub, so each one follows the same shape:

1. Safe Mode refuses outright (GitHub is a network service).
2. ``_ensure_github_ready()`` (shared with the other two mixins) gates on
   consent + PyGithub being installed.
3. A signed-in token is required -- these are not available anonymously.
   A missing token offers to sign in on the spot rather than just refusing.
4. The repository field prefills from the current document's GitHub origin
   or local git checkout, same as the items viewer (:meth:`_github_items_initial_repo`).
5. The four highest-consequence actions (rename, delete a branch, merge --
   the merge command itself lives in the items dialog -- and flipping
   visibility) go behind :class:`~quill.ui.github_repo_admin_dialogs.TypedConfirmDialog`
   instead of a plain Yes/No, per the design decision recorded in
   ``docs/planning/github.md``.
6. The call itself runs on a background thread via ``_run_background_task``;
   the UI thread is never blocked on the network.

Create-repository and fork both end by offering to wire the result into
QUILL Sync's local-folder flow (:mod:`quill.ui.main_frame_git_sync`) in one
continuous action -- the "create a project without leaving QUILL" flow
described in ``docs/planning/github.md`` section 4.
"""

from __future__ import annotations

import os
from typing import Any

from quill.core.github.repo_admin import GitHubRepoAdminError, GitHubRepoAdminProvider
from quill.core.github.token_store import load_github_token


class GitHubAdminMixin:
    """Adds repository-lifecycle GitHub commands to ``MainFrame``."""

    # ------------------------------------------------------------------
    # Shared gating + small prompt helpers

    def _gh_admin_ready(self) -> str | None:
        """Return a usable token, or None after handling refusal/sign-in.

        Centralizes the four gates every command in this mixin needs: Safe
        Mode, consent + PyGithub, and a signed-in token (offering to sign in
        on the spot rather than just refusing, per "hold the user's hand").
        """
        if os.environ.get("QUILL_SAFE_MODE") == "1":
            self._set_status("GitHub repository actions are disabled in Safe Mode")
            return None
        if not self._ensure_github_ready():
            return None
        token = load_github_token()
        if token:
            return token
        if self._gh_admin_confirm(
            "This action needs a signed-in GitHub account. Sign in now?",
            "GitHub Sign In",
        ):
            self._github_add_token()
            token = load_github_token()
        return token or None

    def _gh_admin_prompt_repo(self, title: str) -> str | None:
        default = self._github_items_initial_repo()
        return self._gh_admin_prompt_single(title, "Repository (owner/repo):", default)

    def _gh_admin_prompt_single(self, title: str, label: str, value: str = "") -> str | None:
        wx = self._wx
        with wx.TextEntryDialog(self.frame, label, title, value) as dialog:
            if self._show_modal_dialog(dialog, title) != wx.ID_OK:
                return None
            text = str(dialog.GetValue()).strip()
            return text or None

    def _gh_admin_confirm(self, message: str, title: str) -> bool:
        wx = self._wx
        dialog = wx.MessageDialog(
            self.frame, message, title, wx.YES_NO | wx.NO_DEFAULT | wx.ICON_INFORMATION
        )
        try:
            return self._show_modal_dialog(dialog, title) == wx.ID_YES
        finally:
            dialog.Destroy()

    def _gh_admin_typed_confirm(self, *, title: str, message: str, expected: str) -> bool:
        from quill.ui.github_repo_admin_dialogs import TypedConfirmDialog

        return TypedConfirmDialog(
            self.frame, title=title, message=message, expected=expected
        ).show()

    def _gh_admin_run(
        self, label: str, work: Any, on_done: Any, *, error_title: str = "GitHub"
    ) -> None:
        """Run *work* in the background, translating ``GitHubRepoAdminError``
        into a status message (already spoken by ``_set_status``) instead of
        letting it crash the worker thread."""

        def guarded(progress: object) -> object:
            try:
                return work(progress)
            except GitHubRepoAdminError as exc:
                return exc

        def done(result: object) -> None:
            if isinstance(result, GitHubRepoAdminError):
                self._set_status(str(result))
                return
            on_done(result)

        self._run_background_task(label, guarded, done)

    # ------------------------------------------------------------------
    # Create repository

    def github_create_repository(self) -> None:
        """Tools > GitHub > Create Repository..."""
        token = self._gh_admin_ready()
        if token is None:
            return
        from quill.ui.github_repo_admin_dialogs import CreateRepositoryDialog

        result = CreateRepositoryDialog(self.frame).show()
        if result is None:
            self._set_status("Repository creation cancelled")
            return

        def work(_progress: object) -> object:
            provider = GitHubRepoAdminProvider(token)
            try:
                return provider.create_repository(
                    result.name,
                    private=result.private,
                    description=result.description,
                    org=result.org,
                )
            finally:
                provider.close()

        self._gh_admin_run(f"Creating {result.name}", work, self._on_github_repo_created)

    def _on_github_repo_created(self, repo: Any) -> None:
        self._set_status(f"Created {repo.full_name} at {repo.html_url}")
        if not self._gh_admin_confirm(
            f"Repository created at {repo.html_url}.\n\nSet up a local folder to sync with it now?",
            "Sync New Repository",
        ):
            return
        folder = self._choose_git_sync_folder()
        if folder is None:
            self._set_status("Local sync skipped — no folder chosen")
            return
        self.settings.git_sync_last_folder = folder
        self._save_settings_quietly()
        clone_url = f"{repo.html_url}.git"

        from quill.core.git_sync import init_repo_with_remote
        from quill.stability.safe_subprocess import run_subprocess_safely

        def work(_progress: object) -> object:
            return init_repo_with_remote(folder, clone_url, runner=run_subprocess_safely)

        def on_done(sync_result: Any) -> None:
            if not sync_result.ok:
                self._set_status(sync_result.message)
                return
            self._run_git_folder_sync(folder)

        self._run_background_task(f"Preparing {folder}", work, on_done)

    # ------------------------------------------------------------------
    # Fork repository

    def github_fork_repository(self) -> None:
        """Tools > GitHub > Fork Repository..."""
        token = self._gh_admin_ready()
        if token is None:
            return
        full_name = self._gh_admin_prompt_repo("Fork Repository")
        if full_name is None:
            return
        org = self._gh_admin_prompt_single(
            "Fork Repository", "Fork into organization (optional; blank = your account):"
        )
        org = org or ""

        def work(_progress: object) -> object:
            provider = GitHubRepoAdminProvider(token)
            try:
                return provider.fork_repository(full_name, org=org)
            finally:
                provider.close()

        self._gh_admin_run(f"Forking {full_name}", work, self._on_github_repo_created)

    # ------------------------------------------------------------------
    # Rename repository

    def github_rename_repository(self) -> None:
        """Tools > GitHub > Rename Repository..."""
        token = self._gh_admin_ready()
        if token is None:
            return
        full_name = self._gh_admin_prompt_repo("Rename Repository")
        if full_name is None:
            return
        new_name = self._gh_admin_prompt_single("Rename Repository", f"New name for {full_name}:")
        if new_name is None:
            return
        if not self._gh_admin_typed_confirm(
            title="Confirm Rename",
            message=(
                f"Rename {full_name} to {new_name!r}? GitHub will redirect the old URL "
                "automatically, but any tooling that hardcodes the old owner/repo name "
                "elsewhere will need updating."
            ),
            expected=full_name,
        ):
            self._set_status("Rename cancelled")
            return

        def work(_progress: object) -> object:
            provider = GitHubRepoAdminProvider(token)
            try:
                return provider.rename_repository(full_name, new_name)
            finally:
                provider.close()

        def on_done(repo: Any) -> None:
            self._set_status(f"Renamed to {repo.full_name}")

        self._gh_admin_run(f"Renaming {full_name}", work, on_done)

    # ------------------------------------------------------------------
    # Change visibility

    def github_change_repository_visibility(self) -> None:
        """Tools > GitHub > Change Repository Visibility..."""
        token = self._gh_admin_ready()
        if token is None:
            return
        full_name = self._gh_admin_prompt_repo("Change Repository Visibility")
        if full_name is None:
            return

        from quill.core.github.github_provider import GitHubRemoteProvider

        def fetch(_progress: object) -> object:
            provider = GitHubRemoteProvider(token=token)
            try:
                return provider.get_repository(full_name)
            finally:
                provider.close()

        self._run_background_task(
            f"Checking {full_name}",
            fetch,
            lambda repo: self._on_github_visibility_checked(token, full_name, repo),
        )

    def _on_github_visibility_checked(self, token: str, full_name: str, repo: Any) -> None:
        make_private = not repo.is_private
        target = "private" if make_private else "public"
        current = "private" if repo.is_private else "public"
        warning = (
            "\n\nMaking a repository public exposes its full history to everyone."
            if make_private is False
            else ""
        )
        if not self._gh_admin_typed_confirm(
            title="Confirm Visibility Change",
            message=(f"{full_name} is currently {current}. Make it {target}?{warning}"),
            expected=full_name,
        ):
            self._set_status("Visibility change cancelled")
            return

        def work(_progress: object) -> object:
            provider = GitHubRepoAdminProvider(token)
            try:
                return provider.set_visibility(full_name, private=make_private)
            finally:
                provider.close()

        def on_done(updated: Any) -> None:
            state = "private" if updated.is_private else "public"
            self._set_status(f"{updated.full_name} is now {state}")

        self._gh_admin_run(f"Updating {full_name}", work, on_done)

    # ------------------------------------------------------------------
    # Change default branch

    def github_change_default_branch(self) -> None:
        """Tools > GitHub > Change Default Branch..."""
        token = self._gh_admin_ready()
        if token is None:
            return
        full_name = self._gh_admin_prompt_repo("Change Default Branch")
        if full_name is None:
            return

        from quill.core.github.items_provider import GitHubItemsProvider

        def fetch(_progress: object) -> object:
            provider = GitHubItemsProvider(token=token)
            try:
                return [b.name for b in provider.fetch_branches(full_name, limit=100)]
            finally:
                provider.close()

        self._run_background_task(
            f"Loading branches for {full_name}",
            fetch,
            lambda names: self._on_github_branches_for_default(token, full_name, names),
        )

    def _on_github_branches_for_default(self, token: str, full_name: str, names: list[str]) -> None:
        if not names:
            self._set_status(f"No branches found on {full_name}")
            return
        wx = self._wx
        with wx.SingleChoiceDialog(
            self.frame, f"New default branch for {full_name}:", "Change Default Branch", names
        ) as dialog:
            if self._show_modal_dialog(dialog, "Change Default Branch") != wx.ID_OK:
                self._set_status("Default branch change cancelled")
                return
            branch = dialog.GetStringSelection()

        def work(_progress: object) -> object:
            provider = GitHubRepoAdminProvider(token)
            try:
                return provider.set_default_branch(full_name, branch)
            finally:
                provider.close()

        def on_done(repo: Any) -> None:
            self._set_status(f"{repo.full_name}'s default branch is now {repo.default_branch}")

        self._gh_admin_run(f"Updating {full_name}", work, on_done)

    # ------------------------------------------------------------------
    # Branch protection

    def github_configure_branch_protection(self) -> None:
        """Tools > GitHub > Configure Branch Protection..."""
        token = self._gh_admin_ready()
        if token is None:
            return
        full_name = self._gh_admin_prompt_repo("Configure Branch Protection")
        if full_name is None:
            return

        from quill.core.github.github_provider import GitHubRemoteProvider
        from quill.core.github.items_provider import GitHubItemsProvider

        def fetch(_progress: object) -> object:
            admin_repo_provider = GitHubRemoteProvider(token=token)
            items = GitHubItemsProvider(token=token)
            try:
                repo = admin_repo_provider.get_repository(full_name)
                names = tuple(b.name for b in items.fetch_branches(full_name, limit=100))
                return (repo.default_branch, names)
            finally:
                admin_repo_provider.close()
                items.close()

        self._run_background_task(
            f"Loading {full_name}",
            fetch,
            lambda pair: self._on_github_branch_protection_loaded(token, full_name, pair),
        )

    def _on_github_branch_protection_loaded(
        self, token: str, full_name: str, pair: tuple[str, tuple[str, ...]]
    ) -> None:
        default_branch, names = pair
        from quill.ui.github_repo_admin_dialogs import BranchProtectionDialog

        result = BranchProtectionDialog(
            self.frame, branches=names, default_branch=default_branch
        ).show()
        if result is None:
            self._set_status("Branch protection unchanged")
            return
        action = (
            f"Remove all protection from {result.branch}"
            if result.remove
            else f"Protect {result.branch} in {full_name}"
        )
        if not self._gh_admin_confirm(f"{action}?", "Confirm Branch Protection"):
            self._set_status("Branch protection unchanged")
            return

        def work(_progress: object) -> object:
            provider = GitHubRepoAdminProvider(token)
            try:
                if result.remove:
                    provider.remove_branch_protection(full_name, result.branch)
                else:
                    provider.set_branch_protection(
                        full_name,
                        result.branch,
                        required_approving_review_count=result.required_approving_review_count,
                        required_status_checks=result.required_status_checks,
                        enforce_admins=result.enforce_admins,
                    )
                return result.branch
            finally:
                provider.close()

        def on_done(branch: Any) -> None:
            verb = "Removed protection from" if result.remove else "Protected"
            self._set_status(f"{verb} {branch} in {full_name}")

        self._gh_admin_run(f"Updating {full_name}", work, on_done)

    # ------------------------------------------------------------------
    # Delete branch

    def github_delete_branch(self) -> None:
        """Tools > GitHub > Delete Branch..."""
        token = self._gh_admin_ready()
        if token is None:
            return
        full_name = self._gh_admin_prompt_repo("Delete Branch")
        if full_name is None:
            return

        from quill.core.github.github_provider import GitHubRemoteProvider
        from quill.core.github.items_provider import GitHubItemsProvider

        def fetch(_progress: object) -> object:
            remote = GitHubRemoteProvider(token=token)
            items = GitHubItemsProvider(token=token)
            try:
                default_branch = remote.get_repository(full_name).default_branch
                names = [b.name for b in items.fetch_branches(full_name, limit=100)]
                return [n for n in names if n != default_branch]
            finally:
                remote.close()
                items.close()

        self._run_background_task(
            f"Loading branches for {full_name}",
            fetch,
            lambda names: self._on_github_branches_for_delete(token, full_name, names),
        )

    def _on_github_branches_for_delete(self, token: str, full_name: str, names: list[str]) -> None:
        if not names:
            self._set_status(f"No deletable branches on {full_name} (default branch excluded)")
            return
        wx = self._wx
        with wx.SingleChoiceDialog(
            self.frame, f"Branch to delete from {full_name}:", "Delete Branch", names
        ) as dialog:
            if self._show_modal_dialog(dialog, "Delete Branch") != wx.ID_OK:
                self._set_status("Branch deletion cancelled")
                return
            branch = dialog.GetStringSelection()
        if not self._gh_admin_typed_confirm(
            title="Confirm Branch Deletion",
            message=(
                f"Delete branch {branch!r} from {full_name}? This cannot be undone from QUILL."
            ),
            expected=branch,
        ):
            self._set_status("Branch deletion cancelled")
            return

        def work(_progress: object) -> object:
            provider = GitHubRepoAdminProvider(token)
            try:
                provider.delete_branch(full_name, branch)
                return branch
            finally:
                provider.close()

        def on_done(deleted: Any) -> None:
            self._set_status(f"Deleted branch {deleted} from {full_name}")

        self._gh_admin_run(f"Deleting {branch}", work, on_done)

    # ------------------------------------------------------------------
    # Multi-file commit

    def github_commit_multiple_files(self) -> None:
        """Tools > GitHub > Commit Multiple Files..."""
        token = self._gh_admin_ready()
        if token is None:
            return
        full_name = self._gh_admin_prompt_repo("Commit Multiple Files")
        if full_name is None:
            return
        wx = self._wx
        with wx.FileDialog(
            self.frame,
            "Choose files to commit",
            style=wx.FD_OPEN | wx.FD_MULTIPLE | wx.FD_FILE_MUST_EXIST,
        ) as dialog:
            if self._show_modal_dialog(dialog, "Commit Multiple Files") != wx.ID_OK:
                self._set_status("Multi-file commit cancelled")
                return
            local_paths = list(dialog.GetPaths())
        if not local_paths:
            return
        branch = self._gh_admin_prompt_single(
            "Commit Multiple Files", "Branch to commit to:", "main"
        )
        if not branch:
            return
        message = self._gh_admin_prompt_single(
            "Commit Multiple Files", "Commit message:", f"Update {len(local_paths)} file(s)"
        )
        if not message:
            return
        listing = "\n".join(f"  {p}" for p in local_paths[:10])
        if len(local_paths) > 10:
            listing += f"\n  and {len(local_paths) - 10} more"
        if not self._gh_admin_confirm(
            f"Commit {len(local_paths)} file(s) to {full_name} on {branch!r}?\n\n{listing}",
            "Confirm Multi-File Commit",
        ):
            self._set_status("Multi-file commit cancelled")
            return

        def work(_progress: object) -> object:
            files: list[tuple[str, bytes]] = []
            for local_path in local_paths:
                from pathlib import Path

                p = Path(local_path)
                repo_path = p.name
                files.append((repo_path, p.read_bytes()))
            provider = GitHubRepoAdminProvider(token)
            try:
                return provider.commit_files(full_name, branch, files, message)
            finally:
                provider.close()

        def on_done(sha: Any) -> None:
            self._set_status(f"Committed {len(local_paths)} file(s) to {full_name} ({sha[:7]})")

        self._gh_admin_run(f"Committing to {full_name}", work, on_done)

    # ------------------------------------------------------------------
    # Command palette registration

    def _register_github_admin_commands(self) -> None:
        self.commands.try_register(
            "github.create_repository",
            "GitHub: Create Repository...",
            self.github_create_repository,
            self._binding_for("github.create_repository"),
        )
        self.commands.try_register(
            "github.fork_repository",
            "GitHub: Fork Repository...",
            self.github_fork_repository,
            self._binding_for("github.fork_repository"),
        )
        self.commands.try_register(
            "github.rename_repository",
            "GitHub: Rename Repository...",
            self.github_rename_repository,
            self._binding_for("github.rename_repository"),
        )
        self.commands.try_register(
            "github.change_repository_visibility",
            "GitHub: Change Repository Visibility...",
            self.github_change_repository_visibility,
            self._binding_for("github.change_repository_visibility"),
        )
        self.commands.try_register(
            "github.change_default_branch",
            "GitHub: Change Default Branch...",
            self.github_change_default_branch,
            self._binding_for("github.change_default_branch"),
        )
        self.commands.try_register(
            "github.configure_branch_protection",
            "GitHub: Configure Branch Protection...",
            self.github_configure_branch_protection,
            self._binding_for("github.configure_branch_protection"),
        )
        self.commands.try_register(
            "github.delete_branch",
            "GitHub: Delete Branch...",
            self.github_delete_branch,
            self._binding_for("github.delete_branch"),
        )
        self.commands.try_register(
            "github.commit_multiple_files",
            "GitHub: Commit Multiple Files...",
            self.github_commit_multiple_files,
            self._binding_for("github.commit_multiple_files"),
        )
