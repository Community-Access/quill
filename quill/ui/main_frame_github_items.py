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
        ).show()
        try:
            provider.close()
        except Exception:  # noqa: BLE001 - close is best-effort cleanup
            pass

    def _github_items_initial_repo(self) -> str:
        """Return the current document's ``owner/repo`` origin, or empty."""
        try:
            origins = self._gh_state().origins
        except Exception:  # noqa: BLE001 - _gh_state must never crash the command
            return ""
        path = getattr(self.document, "path", None)
        if not path:
            return ""
        origin = origins.get(path)
        if origin is None or origin.provider != "github":
            return ""
        return origin.repository
