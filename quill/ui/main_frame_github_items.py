"""GitHub items viewer entry point for ``MainFrame`` (#924).

Adds the ``File > Open Remote > GitHub Items...`` command: a read-only,
screen-reader-first browser for a repository's issues, PRs, branches, commits,
tags, releases, and workflow runs, modeled on GHManage
(https://github.com/kellylford/GHManage).

The dialog itself (:mod:`quill.ui.github_items_dialog`) is wx-only; this mixin
is the glue that enforces the same gates every other GitHub entry point uses:

- Safe Mode refuses (#924 refuses_in_safe_mode).
- Consent + dependency check via ``_ensure_github_ready`` (shared with the
  browse/open/save-back flow in :mod:`quill.ui.main_frame_github`).
- Token from the OS credential store; the provider is constructed here and
  handed to the dialog so the dialog itself never touches secrets or consent.
- The current document's GitHub origin (if any) pre-fills the repository field.
"""

from __future__ import annotations

from pathlib import Path

from quill.core.github.references import (
    GitHubReference,
    GitHubReferenceError,
    parse_github_reference,
)
from quill.core.github.token_store import load_github_token


class GitHubItemsMixin:
    """Mixin that adds the GitHub items viewer command to ``MainFrame``."""

    def start_github_issue_worktree(
        self,
        parent: object,
        repository: str,
        number: int,
        title: str,
        is_pr: bool = False,
    ) -> None:
        from quill.ui.github_issue_worktree import start_issue_worktree

        start_issue_worktree(self, parent, repository, number, title, is_pr)

    def open_github_reference(self) -> None:
        """Open a pasted GitHub URL in the best available QUILL view."""
        wx = self._wx
        with wx.TextEntryDialog(
            self.frame,
            "Paste a GitHub URL or enter owner/repo:",
            "Open GitHub Reference",
        ) as dialog:
            dialog.SetName("GitHub URL or owner and repository")
            if self._show_modal_dialog(dialog, "Open GitHub Reference") != wx.ID_OK:
                return
            raw_reference = dialog.GetValue().strip()
        try:
            reference = parse_github_reference(raw_reference)
        except GitHubReferenceError as exc:
            self._show_message_box(
                str(exc),
                "Open GitHub Reference",
                wx.ICON_ERROR | wx.OK,
            )
            return

        if reference.kind == "file" and reference.supports_native_view:
            self.open_github_file_url(reference.url)
            return
        if reference.supports_native_view:
            self.open_github_items_viewer_for(
                reference.repository,
                initial_reference=reference,
            )
            return
        self._open_github_reference_in_browser(reference)

    def _open_github_reference_in_browser(self, reference: GitHubReference) -> None:
        """Explain a native-view gap before opening a link in the browser."""
        import webbrowser

        wx = self._wx
        kind = reference.kind.replace("_", " ")
        message = (
            f"QUILL does not have a native view for this {kind} link yet.\n\n"
            "Open the GitHub link in your default browser? QUILL will not attach "
            "your GitHub token to this browser request."
        )
        dialog = wx.MessageDialog(
            self.frame,
            message,
            "Open GitHub Reference in Browser",
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_INFORMATION,
        )
        try:
            if self._show_modal_dialog(dialog, "Open GitHub Reference in Browser") != wx.ID_YES:
                return
        finally:
            dialog.Destroy()
        if webbrowser.open(reference.url, new=2):
            self._announce(f"Opened {kind} in your browser.")
        else:
            self._set_status("Could not open the GitHub link in your default browser.")

    def open_github_items_viewer(self, initial_view: str = "", node: str = "") -> None:
        """File > Open Remote > GitHub Items..., and the GitHub menu's doors.

        *initial_view* is the Items view to open on (``"runs"``, ``"releases"``);
        empty for the issues view, as it always opened. *node* is the GitHub
        Workbench node a door opens (``"inbox"``, ``"pulls"``), when the
        Workbench is the window in use.
        """
        # items_provider pulls the GitHub request stack (urllib); it is only
        # needed when the viewer is opened, so keep it off the cold-start path.
        from quill.core.github.items_provider import (
            GitHubItemsError,
            GitHubItemsProvider,
            refuse_in_safe_mode,
        )

        # Safe Mode disables all GitHub network services, including this one.
        try:
            refuse_in_safe_mode(self._safe_mode)
        except GitHubItemsError as exc:
            self._show_message_box(
                str(exc),
                "GitHub Items",
                self._wx.ICON_INFORMATION | self._wx.OK,
            )
            return
        # Consent + PyGithub availability -- same gate as browse/open/save-back.
        if not self._ensure_github_ready():
            return
        token = load_github_token()
        try:
            provider = GitHubItemsProvider(token=token or None)
        except GitHubItemsError as exc:
            self._show_message_box(
                str(exc),
                "GitHub Items",
                self._wx.ICON_INFORMATION | self._wx.OK,
            )
            return
        self._watch_github_token_expiry(token)  # main_frame_github_accounts
        # Prefill from the current document's GitHub origin when available so a
        # user editing a file from a repo can review that repo's issues in one
        # step instead of retyping owner/repo.
        initial_repo = self._github_items_initial_repo()
        from quill.ui.github_workbench_commands import open_in_workbench_window

        # The Workbench window, behind its developer flag (both editors, one call).
        if open_in_workbench_window(
            self.frame,
            provider,
            repository=initial_repo,
            view=initial_view,
            announce=self._announce,
            node=node,
            editor_command=self._github_editor_command,
            editor_command_available=self._github_editor_has,
            open_file_url=self.open_github_file_url,
        ):
            return
        from quill.ui.github_items_dialog import GitHubItemsDialog

        # Nothing said on the way in: the dialog's title and its focused list
        # are what the screen reader says next (GATE-13).
        GitHubItemsDialog(
            self.frame,
            provider,
            initial_repo=initial_repo,
            initial_view=initial_view,
            open_file_reference_cb=self.open_github_file_url,
            announce_cb=self._announce,
            ai_acquire_cb=self._github_ai_summarizer,
            start_issue_worktree_cb=self.start_github_issue_worktree,
            gist_source_cb=self._github_gist_source,
        ).show()
        try:
            provider.close()
        except Exception:  # noqa: BLE001 - close is best-effort cleanup
            pass

    def open_github_items_viewer_for(
        self,
        full_name: str,
        *,
        initial_reference: GitHubReference | None = None,
    ) -> None:
        """Open the shared Items dialog pre-filled with a selected repository."""
        from quill.core.github.items_provider import (
            GitHubItemsError,
            GitHubItemsProvider,
            refuse_in_safe_mode,
        )

        try:
            refuse_in_safe_mode(self._safe_mode)
        except GitHubItemsError as exc:
            self._show_message_box(
                str(exc), "GitHub Items", self._wx.ICON_INFORMATION | self._wx.OK
            )
            return
        if not self._ensure_github_ready():
            return
        token = load_github_token()
        try:
            provider = GitHubItemsProvider(token=token or None)
        except Exception as exc:  # noqa: BLE001
            self._set_status(f"Could not open {full_name}: {exc}")
            return
        self._watch_github_token_expiry(token)
        from quill.ui.github_items_dialog import GitHubItemsDialog

        GitHubItemsDialog(
            self.frame,
            provider,
            initial_repo=full_name,
            initial_reference=initial_reference,
            open_file_reference_cb=self.open_github_file_url,
            announce_cb=self._announce,
            start_issue_worktree_cb=self.start_github_issue_worktree,
            gist_source_cb=self._github_gist_source,
        ).show()
        try:
            provider.close()
        except Exception:  # noqa: BLE001 - close is best-effort cleanup
            pass

    def _github_gist_source(self) -> tuple[str, str]:
        """(file name, text) a new gist starts from: the selection, else the document."""
        editor = getattr(self, "editor", None)
        text = editor.GetStringSelection() if editor is not None else ""
        if not text and editor is not None:
            text = editor.GetValue()
        path = getattr(getattr(self, "document", None), "path", None)
        return (Path(path).name if path else "notes.md"), text

    def _github_ai_summarizer(self):
        """Resolve QUILL's AI connection for a thread summary, on demand.

        Called by the dialog on the UI thread when the user presses Summarize
        — never earlier, so opening the viewer alone can never prompt for AI
        setup. Returns a ``summarize(text) -> str`` closure that is safe to
        run off-thread (one bounded completion through the same connection
        and consent gates as every other keyed AI feature), or None when AI
        is off/declined.
        """
        result = self._ai_require_connection()
        if result is None:
            return None
        connection, api_key = result

        def summarize(thread_text: str) -> str:
            from quill.core.github.thread_summary import summarize_thread

            return summarize_thread(connection, api_key, thread_text)

        return summarize

    def _github_items_initial_repo(self) -> str:
        """The current document's ``owner/repo``, from either origin source.

        Prefers the tracked Open-from-GitHub origin; falls back to the
        document's own git checkout (local git sync — a file opened from disk
        inside a clone with a GitHub ``origin`` remote prefills too).
        """
        path = getattr(getattr(self, "document", None), "path", None)
        try:
            origins = self._gh_state().origins
            if path:
                origin = origins.get(path)
                if origin is not None and origin.provider == "github":
                    return origin.repository
        except Exception:  # noqa: BLE001 - _gh_state must never crash the command
            pass
        try:
            from quill.core.github.local_repo import detect_github_repo

            return detect_github_repo(path)
        except Exception:  # noqa: BLE001 - detection is best-effort
            return ""
