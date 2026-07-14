"""Sync Folder with GitHub (QUILL Sync, Beta 3) — the general-purpose half.

Adds one command, ``Tools > Sync > Sync Folder with GitHub...``: point it at
any folder, and QUILL commits, pulls, and pushes it over that folder's own
git remote. The engine is :mod:`quill.core.git_sync`, which itself delegates
to the exact same commit/pull/push implementation Accessible Vault's "Sync
Vault" already ships — one sync engine in the tree, two entry points. See
``quill.core.git_sync`` for why this exists instead of a bespoke QUILL sync
service: git already does structured, conflict-aware sync well, so QUILL
reuses it rather than reinventing it.

The other half of "QUILL Sync" — relocating QUILL's own settings/snippets/
data folder onto a folder a cloud client (OneDrive, Dropbox, Drive, iCloud)
already mirrors — is :mod:`quill.core.data_location`, reachable from
Preferences and the first-run wizard; nothing new was needed there beyond
documentation, since the mechanism already existed.

Consent and safety, matching the Vault Sync precedent exactly:

- Disabled outright in Safe Mode (git push/pull is network activity).
- A folder that is not yet a git repository, or has no remote configured,
  is never silently initialized — the user sees exactly what will happen
  (``git init`` and/or ``git remote add origin <url>``) and confirms before
  anything is written or any network call is made.
- Conflicts are listed by name (never auto-resolved) using the same
  accessible list dialog Vault Sync's conflict report already uses.
- Relies on the user's own git installation and its own credential handling
  (SSH key or the system git credential manager) — QUILL does not store or
  inject a separate token for these subprocess calls.
"""

from __future__ import annotations

import os
from typing import Any


class GitSyncMixin:
    """Adds the general-purpose folder-sync-via-GitHub command to MainFrame."""

    def _git_sync_prompt_single(self, title: str, label: str, value: str = "") -> str | None:
        wx = self._wx
        with wx.TextEntryDialog(self.frame, label, title, value) as dialog:
            if self._show_modal_dialog(dialog, title) != wx.ID_OK:
                return None
            return str(dialog.GetValue()).strip()

    def _git_sync_confirm(self, message: str, title: str) -> bool:
        wx = self._wx
        dialog = wx.MessageDialog(
            self.frame, message, title, wx.YES_NO | wx.NO_DEFAULT | wx.ICON_INFORMATION
        )
        try:
            return self._show_modal_dialog(dialog, title) == wx.ID_YES
        finally:
            dialog.Destroy()

    def _choose_git_sync_folder(self) -> str | None:
        wx = self._wx
        default = str(getattr(self.settings, "git_sync_last_folder", "") or "")
        if not default:
            path = getattr(getattr(self, "document", None), "path", None)
            default = str(path.parent) if path is not None else ""
        with wx.DirDialog(
            self.frame,
            "Choose a folder to sync with GitHub",
            defaultPath=default,
            style=wx.DD_DEFAULT_STYLE,
        ) as dialog:
            if self._show_modal_dialog(dialog, "Choose Folder") != wx.ID_OK:
                return None
            return str(dialog.GetPath())

    def sync_folder_with_github(self) -> None:
        """Tools > Sync > Sync Folder with GitHub..."""
        if os.environ.get("QUILL_SAFE_MODE") == "1":
            self._set_status("Folder sync is disabled in Safe Mode")
            return
        folder = self._choose_git_sync_folder()
        if folder is None:
            self._set_status("Folder sync cancelled")
            return
        self.settings.git_sync_last_folder = folder
        self._save_settings_quietly()

        from quill.core.git_sync import check_repo_status
        from quill.stability.safe_subprocess import run_subprocess_safely

        def work(_progress: object) -> object:
            return check_repo_status(folder, runner=run_subprocess_safely)

        self._run_background_task(
            f"Checking {folder}",
            work,
            lambda status: self._on_git_sync_status_checked(folder, status),
        )

    def _save_settings_quietly(self) -> None:
        from quill.core.settings import save_settings

        try:
            save_settings(self.settings)
        except Exception:  # noqa: BLE001 - remembering the folder is best-effort
            pass

    def _on_git_sync_status_checked(self, folder: str, status: Any) -> None:
        if status.ready:
            self._run_git_folder_sync(folder)
            return
        self._prepare_git_sync_folder(folder, status)

    def _prepare_git_sync_folder(self, folder: str, status: Any) -> None:
        if not status.is_git_repo:
            message = (
                f"'{folder}' is not a git repository yet. QUILL can set it up: this runs "
                "'git init' in the folder, then adds the remote repository you provide as "
                "'origin'. Continue?"
            )
        else:
            message = (
                f"'{folder}' is a git repository but has no remote configured yet. QUILL can "
                "add one: this runs 'git remote add origin <the URL you provide>'. Continue?"
            )
        if not self._git_sync_confirm(message, "Set Up Folder for GitHub Sync"):
            self._set_status("Folder sync cancelled")
            return
        remote_url = self._git_sync_prompt_single(
            "Set Up Folder for GitHub Sync",
            "GitHub repository URL (for example, https://github.com/you/your-repo.git):",
        )
        if not remote_url:
            self._set_status("Folder sync cancelled — no repository URL given")
            return

        from quill.core.git_sync import init_repo_with_remote
        from quill.stability.safe_subprocess import run_subprocess_safely

        def work(_progress: object) -> object:
            return init_repo_with_remote(folder, remote_url, runner=run_subprocess_safely)

        def on_done(result: Any) -> None:
            if not result.ok:
                self._set_status(result.message)  # _set_status already speaks it
                return
            self._run_git_folder_sync(folder)

        self._run_background_task(f"Preparing {folder}", work, on_done)

    def _run_git_folder_sync(self, folder: str) -> None:
        from quill.core.git_sync import sync_folder_via_git
        from quill.stability.safe_subprocess import run_subprocess_safely

        def work(_progress: object) -> object:
            return sync_folder_via_git(folder, runner=run_subprocess_safely)

        self._run_background_task(f"Syncing {folder}", work, self._on_git_folder_sync_done)

    def _on_git_folder_sync_done(self, result: Any) -> None:
        if getattr(result, "conflicts", ()):
            from quill.ui.vault_dialogs import show_vault_list_modal

            show_vault_list_modal(
                self,
                "Sync conflicts — resolve, then sync again",
                [(path, None) for path in result.conflicts],
                on_activate=lambda _payload: None,
            )
        self._set_status(result.message)  # _set_status already speaks it

    def _register_git_sync_commands(self) -> None:
        self.commands.try_register(
            "sync.sync_folder",
            "Sync Folder with GitHub...",
            self.sync_folder_with_github,
            self._binding_for("sync.sync_folder"),
        )
