"""GitHub remote file browsing and saving for ``MainFrame`` (File-GH-1..GH-5).

Wires the GitHub dialogs to the core provider: check consent, authenticate,
browse a repository, download a file, open it as a normal tab, and on request
commit it back to the same branch with a user-provided message.

Threading contract (same as SSH mixin):
- All PyGithub calls run in daemon threads off the UI thread.
- UI updates use ``self._wx.CallAfter``.
- Dialogs are always shown on the UI thread.
"""

from __future__ import annotations

import contextlib
import hashlib
import threading
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from quill.core.github.consent import load_github_consent_complete, save_github_consent_complete
from quill.core.github.github_provider import GitHubDependencyError, GitHubRemoteProvider
from quill.core.github.models import RemoteOrigin
from quill.core.github.token_store import (
    delete_github_token,
    load_github_token,
    save_github_token,
)
from quill.core.paths import app_data_dir

if TYPE_CHECKING:
    from quill.core.github.models import BrowseResult, RemoteFile


@dataclass(slots=True)
class _GitHubState:
    """Lazily-initialised GitHub runtime state."""

    origins: dict[str, RemoteOrigin]  # local_path -> origin


class GitHubRemoteMixin:
    """Mixin that adds GitHub browse, open, and save-back to ``MainFrame``."""

    # ------------------------------------------------------------------
    # Internal state accessor (lazy init, never crashes on first access)

    def _gh_state(self) -> _GitHubState:
        if not hasattr(self, "_github_state"):
            self._github_state = _GitHubState(origins={})
        return self._github_state

    # ------------------------------------------------------------------
    # Public entry points (called from menu / commands)

    def open_github_repository(self) -> None:
        """File > Open Remote > GitHub Repository..."""
        if not self._ensure_github_ready():
            return
        token = load_github_token()
        provider = GitHubRemoteProvider(token=token or None)
        self._set_status("Connecting to GitHub...")
        self._announce("Connecting to GitHub")
        threading.Thread(
            target=self._github_fetch_identity_for_browse,
            args=(provider,),
            daemon=True,
        ).start()

    def open_github_file_url(self) -> None:
        """File > Open Remote > GitHub File URL..."""
        if not self._ensure_github_ready():
            return
        wx = self._wx
        with wx.TextEntryDialog(
            self.frame,
            "Paste a GitHub file URL (github.com/owner/repo/blob/branch/path):",
            "Open GitHub File URL",
        ) as dlg:
            dlg.SetName("GitHub file URL")
            if self._show_modal_dialog(dlg, "Open GitHub File URL") != wx.ID_OK:
                return
            url = dlg.GetValue().strip()
        if not url:
            return
        parsed = _parse_github_blob_url(url)
        if parsed is None:
            self._show_message_box(
                "Could not parse the URL. Expected format:\n"
                "https://github.com/owner/repo/blob/branch/path/to/file",
                "Open GitHub File URL",
                wx.ICON_ERROR | wx.OK,
            )
            return
        owner_repo, ref, path = parsed
        token = load_github_token()
        provider = GitHubRemoteProvider(token=token or None)
        from quill.core.github.models import BrowseResult, RemoteRepository

        repo_obj = RemoteRepository(provider="github", full_name=owner_repo)
        pseudo_result = BrowseResult(
            repository=repo_obj,
            path=path,
            ref=ref,
            sha="",
            html_url=url,
        )
        self._set_status("Connecting to GitHub...")
        self._announce("Connecting to GitHub")
        threading.Thread(
            target=self._github_fetch_identity_for_url,
            args=(provider, pseudo_result),
            daemon=True,
        ).start()

    def github_save_back(self) -> None:
        """File > Open Remote > Save to GitHub..."""
        path = getattr(self.document, "path", None)
        if path is None:
            self._set_status("No file to save back to GitHub")
            return
        origin = self._gh_state().origins.get(str(path))
        if origin is None:
            self._show_message_box(
                "This document was not opened from GitHub.\n"
                "Use File > Open Remote > GitHub Repository to open a file first.",
                "Save to GitHub",
                self._wx.ICON_INFORMATION | self._wx.OK,
            )
            return
        wx = self._wx
        with wx.TextEntryDialog(
            self.frame,
            f"Commit message for {Path(origin.path).name}:",
            "Save to GitHub",
            value=f"Update {Path(origin.path).name}",
        ) as dlg:
            dlg.SetName("Commit message")
            if self._show_modal_dialog(dlg, "Save to GitHub") != wx.ID_OK:
                return
            message = dlg.GetValue().strip()
        if not message:
            return
        content = self.document.text.encode("utf-8")
        token = load_github_token()
        # #35: pass the provider through contextlib.closing so the worker
        # thread is guaranteed to release the underlying GitHub session
        # even if the user quits mid-save.
        provider = contextlib.closing(GitHubRemoteProvider(token=token or None))
        self._set_status(f"Saving {Path(origin.path).name} to GitHub...")
        self._announce(f"Saving {Path(origin.path).name} to GitHub")
        threading.Thread(  # GATE-40-OK: short-lived save worker.
            target=self._save_back_worker,
            args=(provider, origin, content, message),
            daemon=True,
        ).start()

    def manage_github_accounts(self) -> None:
        """File > Open Remote > Manage GitHub Accounts..."""
        token = load_github_token()
        has_token = bool(token)
        if token:
            threading.Thread(
                target=self._github_fetch_identity_for_manage,
                args=(token, has_token),
                daemon=True,
            ).start()
        else:
            self._github_show_manage_dialog(login=None, has_token=has_token)

    # ------------------------------------------------------------------
    # Background identity helpers (keep get_identity() off UI thread)

    def _github_fetch_identity_for_browse(self, provider: GitHubRemoteProvider) -> None:
        try:
            identity = provider.get_identity()
        except Exception:  # noqa: BLE001
            identity = None
        self._wx.CallAfter(self._github_open_repo_dialog, provider, identity)

    def _github_open_repo_dialog(self, provider: GitHubRemoteProvider, identity: object) -> None:
        identity_label = (
            f"{identity.display_name} ({identity.login})"
            if identity
            else "Anonymous (public repositories only)"
        )
        from quill.ui.github_dialogs import GitHubRepositoryBrowserDialog

        result = GitHubRepositoryBrowserDialog(
            self.frame,
            provider=provider,
            identity_label=identity_label,
            announce_cb=self._announce,
        ).show()
        if result is None:
            self._set_status("GitHub browse cancelled")
            return
        self._github_open_file(provider, result, identity)

    def _github_fetch_identity_for_url(
        self, provider: GitHubRemoteProvider, result: BrowseResult
    ) -> None:
        try:
            identity = provider.get_identity()
        except Exception:  # noqa: BLE001
            identity = None
        self._wx.CallAfter(self._github_open_file, provider, result, identity)

    def _github_fetch_identity_for_manage(self, token: str, has_token: bool) -> None:
        login: str | None = None
        try:
            p = GitHubRemoteProvider(token=token)
            acc = p.get_identity()
            login = acc.login if acc else None
        except Exception:  # noqa: BLE001
            pass
        self._wx.CallAfter(self._github_show_manage_dialog, login=login, has_token=has_token)

    def _github_show_manage_dialog(self, login: str | None, has_token: bool) -> None:
        from quill.ui.github_dialogs import GitHubManageAccountsDialog

        action = GitHubManageAccountsDialog(self.frame, login=login, has_token=has_token).show()
        if action == "remove":
            delete_github_token()
            self._set_status("GitHub account disconnected")
            self._announce("GitHub account disconnected")
        elif action == "add":
            self._github_add_token()

    # ------------------------------------------------------------------
    # Helper: guarantee consent + PyGithub present

    def _ensure_github_ready(self) -> bool:
        try:
            from quill.core.github.github_provider import require_pygithub

            require_pygithub()
        except GitHubDependencyError as exc:
            self._show_message_box(
                str(exc),
                "GitHub Integration",
                self._wx.ICON_INFORMATION | self._wx.OK,
            )
            return False
        if not load_github_consent_complete():
            from quill.ui.github_dialogs import GitHubConsentDialog

            if not GitHubConsentDialog(self.frame).show():
                return False
            save_github_consent_complete()
        return True

    def _github_add_token(self) -> None:
        from quill.ui.github_dialogs import GitHubSignInDialog

        result = GitHubSignInDialog(self.frame).show()
        if result is None:
            return
        if result.token:
            if save_github_token(result.token):
                self._set_status("GitHub token saved")
                self._announce("GitHub token saved")
            else:
                self._show_message_box(
                    "Could not save the token. The Windows Credential Manager "
                    "may not be available.",
                    "GitHub Sign In",
                    self._wx.ICON_WARNING | self._wx.OK,
                )

    # ------------------------------------------------------------------
    # Open flow

    def _github_open_file(
        self,
        provider: GitHubRemoteProvider,
        result: BrowseResult,
        identity: object,
    ) -> None:
        self._set_status(f"Downloading {Path(result.path).name} from GitHub...")
        self._announce(f"Downloading {Path(result.path).name} from GitHub")
        threading.Thread(  # GATE-40-OK: GitHub open worker; bounded by size.
            target=self._open_worker,
            args=(provider, result, identity),
            daemon=True,
        ).start()

    def _open_worker(
        self,
        provider: GitHubRemoteProvider,
        result: BrowseResult,
        identity: object,
    ) -> None:
        wx = self._wx
        try:
            # ``provider`` is a contextlib.closing wrapper so the underlying
            # GitHub session is released on this worker thread once the
            # download completes (finding #35).
            with provider as live_provider:
                remote_file = live_provider.get_file(result.repository, result.path, result.ref)
            wx.CallAfter(self._on_file_fetched, remote_file, result, identity)
        except Exception as exc:  # noqa: BLE001
            wx.CallAfter(self._on_github_error, str(exc), "Open from GitHub")

    def _on_file_fetched(
        self,
        remote_file: RemoteFile,
        result: BrowseResult,
        identity: object,
    ) -> None:
        temp_dir = app_data_dir() / "github-temp"
        slot_key = f"{remote_file.repository.full_name}:{remote_file.ref}:{remote_file.path}"
        slot_hash = hashlib.sha256(slot_key.encode()).hexdigest()[:16]
        slot_dir = temp_dir / slot_hash
        slot_dir.mkdir(parents=True, exist_ok=True)
        local_path = slot_dir / Path(remote_file.path).name
        # Decode as UTF-8 with fallback to Latin-1 for binary/encoded files.
        try:
            text = remote_file.content.decode("utf-8")
        except UnicodeDecodeError as exc:
            self._set_status(f"Refused to open non-UTF-8 file: {exc.reason}")
            self._announce(f"Could not open {Path(remote_file.path).name}: file is not UTF-8 text.")
            self._show_message_box(
                f"{Path(remote_file.path).name} is not a UTF-8 text file.\n"
                "GitHub's API will not let Quill round-trip binary content "
                "safely.  Download the file manually instead.",
                "Open from GitHub",
                self._wx.ICON_ERROR | self._wx.OK,
            )
            return
        local_path.write_text(text, encoding="utf-8", newline="")

        account_id = (
            getattr(identity, "account_id", None) or "github:anonymous"
            if identity
            else "github:anonymous"
        )
        origin = RemoteOrigin(
            provider="github",
            account_id=account_id,
            repository=remote_file.repository.full_name,
            ref=remote_file.ref,
            path=remote_file.path,
            sha=remote_file.sha,
            url=remote_file.html_url,
            opened_at=datetime.now(UTC).isoformat(),
        )
        self._gh_state().origins[str(local_path)] = origin
        self.open_file(local_path)
        label = f"GitHub: {remote_file.repository.full_name} ({remote_file.ref})"
        tab_count = len(self._document_tabs)
        if tab_count:
            tab = self._document_tabs[tab_count - 1]
            tab.source_label = label
            tab.read_only_remote = False
        self._set_status(
            f"Opened {Path(remote_file.path).name} from "
            f"{remote_file.repository.full_name} on {remote_file.ref}"
        )
        self._announce(f"Opened {Path(remote_file.path).name} from GitHub")

    # ------------------------------------------------------------------
    # Save-back flow

    def _save_back_worker(
        self,
        provider: GitHubRemoteProvider,
        origin: RemoteOrigin,
        content: bytes,
        message: str,
    ) -> None:
        wx = self._wx
        try:
            with provider as live_provider:
                new_sha = live_provider.write_file(
                    origin.repository,
                    origin.path,
                    origin.ref,
                    content,
                    origin.sha,
                    message,
                )
            wx.CallAfter(self._on_save_back_done, origin, new_sha)
        except Exception as exc:  # noqa: BLE001
            wx.CallAfter(self._on_github_error, str(exc), "Save to GitHub")

    def _on_save_back_done(self, origin: RemoteOrigin, new_sha: str) -> None:
        path = getattr(self.document, "path", None)
        if path is not None:
            state = self._gh_state()
            old = state.origins.get(str(path))
            if old is not None:
                from dataclasses import replace

                state.origins[str(path)] = replace(old, sha=new_sha)
        msg = f"Committed {Path(origin.path).name} to {origin.repository} ({origin.ref})"
        self._set_status(msg)
        self._announce(msg)

    # ------------------------------------------------------------------
    # Shared error handler

    def _on_github_error(self, message: str, title: str = "GitHub") -> None:
        self._set_status(f"GitHub error: {message}")
        self._announce(f"GitHub error: {message}")
        self._show_message_box(message, title, self._wx.ICON_ERROR | self._wx.OK)

    # ------------------------------------------------------------------
    # Cleanup (finding #32)

    def prune_orphaned_github_temp(self) -> int:
        """Remove GitHub-temp files no longer referenced by an open tab.

        Returns the number of files removed.  Called from
        :meth:`MainFrame._on_close` so a file opened once and never saved
        back to GitHub does not linger in the user's app-data directory
        forever (the original "privacy leak" finding #32).

        The implementation is safe to run repeatedly and silently swallows
        per-file errors so a single permission glitch does not block the
        main shutdown path.
        """
        try:
            temp_dir = app_data_dir() / "github-temp"
        except Exception:  # noqa: BLE001 - paths failure must not crash shutdown
            return 0
        if not temp_dir.exists():
            return 0
        live_paths = {Path(p).resolve() for p in self._gh_state().origins}
        removed = 0
        for entry in temp_dir.iterdir():
            try:
                target = entry.resolve()
            except OSError:
                continue
            if target in live_paths:
                continue
            try:
                if entry.is_file() or entry.is_symlink():
                    entry.unlink()
                else:
                    import shutil

                    shutil.rmtree(entry)
                removed += 1
            except OSError:
                continue
        return removed

    # ------------------------------------------------------------------
    # Bind menu items (called from main_frame_menu._bind_events)

    def _bind_github_menu(self) -> None:
        wx = self._wx
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.open_github_repository(),
            id=self._id_github_repository,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.open_github_file_url(),
            id=self._id_github_file_url,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.github_save_back(),
            id=self._id_github_save_back,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.manage_github_accounts(),
            id=self._id_github_manage_accounts,
        )


# ---------------------------------------------------------------------------
# URL parser


def _parse_github_blob_url(url: str) -> tuple[str, str, str] | None:
    """Parse ``https://github.com/owner/repo/blob/branch/path``.

    Returns ``(owner/repo, branch, path)`` or None.
    Strips query strings (?plain=1), line anchors (#L10), and URL-decodes
    percent-encoded characters in the path — all common when copying from
    the GitHub UI.
    """
    from urllib.parse import unquote, urlparse

    parsed = urlparse(url)
    if parsed.netloc != "github.com":
        return None
    # Drop leading slash; split into up to 5 segments
    rest = parsed.path.lstrip("/")
    parts = rest.split("/", 4)
    if len(parts) < 5 or parts[2] != "blob":
        return None
    owner, repo, _blob, branch, raw_path = parts
    path = unquote(raw_path)
    return f"{owner}/{repo}", branch, path
