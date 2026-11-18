"""Viewed files, and comments on a whole file, in the pull request review window (GH-D).

Each changed file in the review outline carries its viewed state for you, as
GitHub keeps it: "viewed", "not viewed", or "changed since you viewed it". A
file's context menu marks it viewed or not, the same mark GitHub's Files tab
shows, and **Show Only Files Not Viewed** hides the ones you have done, so a
long review can be worked through and picked up again. **Comment on This
File...** opens the comment composer for a comment on the whole file rather
than a line. The states load after the review, in the background; a failure
leaves the outline as it was and says why on the status line. The work is
:mod:`quill.core.github.review_viewed`.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any

from quill.core.github.review_viewed import (
    ViewedFiles,
    file_comment_payload,
    load_viewed,
    set_viewed,
)

__all__ = ["GitHubPullReviewViewedMixin"]


class GitHubPullReviewViewedMixin:
    _viewed: ViewedFiles | None = None
    _unviewed_only: bool = False
    _file_paths: list[str]
    _client: Any
    _repo: str
    _number: int
    _diff: Any
    _state: Any
    _wx: Any
    dialog: Any
    _status: Any
    _announce: Callable[[str], None]
    _render_outline: Callable[..., None]
    _node_kind: Callable[[], tuple[str, int]]

    def _api(self) -> Any:
        from quill.core.github.workbench_api import TokenApi

        return TokenApi(getattr(self._client._provider, "token", None))  # noqa: SLF001

    def _in_background(self, work: Callable[[], Any], done: Callable[[Any], None]) -> None:
        wx = self._wx

        def run() -> None:
            try:
                result = work()
            except Exception as exc:  # noqa: BLE001 - said on the UI thread
                wx.CallAfter(self._viewed_failed, str(exc))
                return
            wx.CallAfter(done, result)

        threading.Thread(target=run, daemon=True).start()  # GATE-40-OK: one GitHub request.

    def _viewed_failed(self, message: str) -> None:
        self._status.SetLabel(f"Viewed files: {message}")
        self._announce(message)

    # -- loading ---------------------------------------------------------------------

    def _load_viewed(self) -> None:
        """Read each file's viewed state, then name it in the outline."""
        if not self._client.can_write:
            return
        api, repo, number = self._api(), self._repo, self._number
        self._in_background(lambda: load_viewed(api, repo, number), self._viewed_landed)

    def _viewed_landed(self, viewed: ViewedFiles) -> None:
        self._viewed = viewed
        self._render_outline()
        self._status.SetLabel(f"Review loaded. {viewed.sentence(self._shown_all_paths())}")

    def _shown_all_paths(self) -> list[str]:
        diff = self._diff
        return [file.filename for file in diff.files] if diff is not None else []

    # -- the selection -----------------------------------------------------------------

    def _selected_file_path(self) -> str:
        """The path of the file node selected, or "" (labels carry a state, so never parse them)."""
        kind, index = self._node_kind()
        paths = getattr(self, "_file_paths", [])
        return paths[index] if kind == "file" and 0 <= index < len(paths) else ""

    def _file_state_sentence(self, path: str) -> str:
        word = self._viewed.word(path) if self._viewed is not None else ""
        return f"For you: {word}." if word else ""

    def _keep_file(self, path: str) -> bool:
        """Whether *path* shows under Show Only Files Not Viewed."""
        viewed = self._viewed
        return not (self._unviewed_only and viewed is not None and viewed.is_viewed(path))

    # -- the commands --------------------------------------------------------------------

    def _viewed_menu_rows(self, add: Callable[..., None]) -> None:
        path = self._selected_file_path()
        viewed = self._viewed
        known = viewed is not None and path in viewed.states
        on = known and viewed is not None and viewed.is_viewed(path)
        add(
            "Mark as Not Viewed" if on else "Mark as Viewed",
            self._toggle_viewed,
            enabled=known and self._client.can_write,
        )
        add(
            "Comment on This File...",
            self._comment_on_file,
            enabled=self._client.can_write and bool(path),
        )
        self._show_only_row(add)

    def _show_only_row(self, add: Callable[..., None]) -> None:
        add(
            "Show All Files" if self._unviewed_only else "Show Only Files Not Viewed",
            self._toggle_unviewed_only,
            enabled=self._viewed is not None,
        )

    def _toggle_viewed(self, _event: object = None) -> None:
        path, viewed = self._selected_file_path(), self._viewed
        if not path or viewed is None:
            return
        on = not viewed.is_viewed(path)
        api = self._api()

        def done(said: str) -> None:
            self._render_outline()
            self._announce(said)

        self._in_background(lambda: set_viewed(api, viewed, path, on), done)

    def _toggle_unviewed_only(self, _event: object = None) -> None:
        if self._viewed is None:
            return
        self._unviewed_only = not self._unviewed_only
        self._render_outline()
        paths = self._shown_all_paths()
        left = sum(1 for path in paths if not self._viewed.is_viewed(path))
        self._announce(
            f"Showing only the {left} files not viewed."
            if self._unviewed_only
            else f"Showing all {len(paths)} files."
        )

    def _comment_on_file(self, _event: object = None) -> None:
        from quill.ui.dialog_contract import show_modal_dialog
        from quill.ui.github_comment_composer import compose_comment

        path = self._selected_file_path()
        head = str(getattr(self._diff, "head_sha", "") or getattr(self._state, "head_sha", ""))
        if not path:
            return
        api = self._api()

        def background(_name: str, work: Callable[[], Any], done: Callable[[Any], None]) -> None:
            self._in_background(work, done)

        body = compose_comment(
            self.dialog,
            show_modal_dialog,
            title=f"Comment on {path}",
            api=api,
            repository=self._repo,
            background=background,
            say=self._announce,
        )
        if not body:
            return
        number, repo = self._number, self._repo

        def post() -> str:
            api.rest(
                "POST",
                f"/repos/{repo}/pulls/{number}/comments",
                body=file_comment_payload(path, body, head),
            )
            return f"Comment posted on {path}."

        self._in_background(post, self._announce)
