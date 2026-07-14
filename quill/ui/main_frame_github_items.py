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

from quill.core.github.items_provider import (
    GitHubItemsError,
    GitHubItemsProvider,
    refuse_in_safe_mode,
)
from quill.core.github.token_store import load_github_token


class GitHubItemsMixin:
    """Mixin that adds the GitHub items viewer command to ``MainFrame``."""

    def open_github_items_viewer(self) -> None:
        """File > Open Remote > GitHub Items..."""
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
        # Prefill from the current document's GitHub origin when available so a
        # user editing a file from a repo can review that repo's issues in one
        # step instead of retyping owner/repo.
        initial_repo = self._github_items_initial_repo()
        from quill.ui.github_items_dialog import GitHubItemsDialog

        self._announce("Opening GitHub Items")
        GitHubItemsDialog(
            self.frame,
            provider,
            initial_repo=initial_repo,
            announce_cb=self._announce,
            ai_acquire_cb=self._github_ai_summarizer,
        ).show()
        try:
            provider.close()
        except Exception:  # noqa: BLE001 - close is best-effort cleanup
            pass

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
