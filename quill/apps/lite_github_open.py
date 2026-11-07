"""Open a GitHub file from the GitHub Workbench in QUILL Lite.

QUILL opens a file from Repository Files (or a file link in GitHub Items) through
File, Open Remote, GitHub File URL. QUILL Lite has no remote documents to save
back to, so it opens the same file's text in a new untitled window: everything a
reader or editor needs, and Save As keeps it. Saying so plainly is the honest
version of the same command, rather than leaving the Open in Editor button dead
in one editor and alive in the other.
"""

from __future__ import annotations

import threading

import wx

from quill.core.github.items_errors import GitHubItemsError
from quill.core.github.references import GitHubReferenceError, parse_github_reference
from quill.ui.richedit_editing import PLAIN

__all__ = ["GitHubFileOpenMixin"]


def _message(exc: BaseException) -> str:
    """The error's sentence, without the support code a screen reader would read out."""
    return str(exc.args[0]) if exc.args else str(exc)


class GitHubFileOpenMixin:
    """``_open_github_file_reference``: the Lite end of the shared open-file callback."""

    def _open_github_file_reference(self, url: str) -> None:
        try:
            reference = parse_github_reference(url)
        except GitHubReferenceError as exc:
            self._announce(_message(exc))
            return
        if reference.kind != "file" or not reference.path:
            self._announce("That link is not a GitHub file.")
            return
        from quill.core.github.items_provider import GitHubItemsProvider
        from quill.core.github.token_store import load_github_token

        repo, ref, path = reference.repository, reference.ref, reference.path
        self._announce(f"Opening {path} from GitHub")

        def worker() -> None:
            try:
                provider = GitHubItemsProvider(token=load_github_token() or None)
                try:
                    text = provider.fetch_repo_file_text(repo, path, ref)
                finally:
                    provider.close()
            except GitHubItemsError as exc:
                wx.CallAfter(self._announce, _message(exc))
                return
            wx.CallAfter(self._show_github_file_text, path, text)

        threading.Thread(target=worker, daemon=True).start()  # GATE-40-OK: one file read.

    def _show_github_file_text(self, path: str, text: str) -> None:
        frame = self.app.new_window(PLAIN)
        frame.control.SetValue(text)
        frame.control.SetInsertionPoint(0)
        frame._announce(
            f"{path.rpartition('/')[2]} from GitHub, opened as a new untitled document. "
            "Save As keeps a copy."
        )
