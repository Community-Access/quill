"""Gist actions in Explore's gists view: new, edit, star, unstar and delete.

The gists view (My gists) used to be read-only. Its context menu now offers New
Gist, which starts from the current document or its selection when Explore was
opened from an editor; and, on a gist row, Edit Gist (description and files:
add, rename, delete, change text), Star Gist, Unstar Gist and Delete Gist. A
delete asks first. Each write runs through the dialog's ``_run_write``, off the
UI thread, and says only what GitHub confirmed; the read Edit Gist waits on
carries a generation token, so a slow answer cannot open an editor after a
newer one. QUILL and QUILL Lite share this through Explore.
"""

from __future__ import annotations

import threading
from typing import Any

from quill.core.github.explore import ExploreRow, GitHubExploreError
from quill.core.github.gists import Gist, GistDraft
from quill.core.github.items_errors import GitHubItemsError
from quill.ui.dialog_contract import dialog_alive

__all__ = ["GitHubExploreGistsMixin"]


def _explore(action: Any) -> Any:
    """Run *action*, turning a gist failure into the error ``_run_write`` says."""
    try:
        return action()
    except GitHubItemsError as exc:
        raise GitHubExploreError(str(exc.args[0]) if exc.args else str(exc)) from exc


class GitHubExploreGistsMixin:
    """Context-menu rows and handlers for gists."""

    def _add_gist_actions(self, add: Any, row: ExploreRow | None) -> None:
        if not self._client._provider.is_authenticated:
            return
        if row is not None and row.kind == "gist" and row.key:
            add("Edit Gist...", lambda: self._edit_gist(row))
            add("Star Gist", lambda: self._star_gist(row, True))
            add("Unstar Gist", lambda: self._star_gist(row, False))
            add("Delete Gist...", lambda: self._delete_gist(row))
        if self._view_key() == "gists":
            add("New Gist...", self._new_gist)

    def _gist_start(self) -> tuple[str, str]:
        source = getattr(self, "_gist_source_cb", None)
        if source is None:
            return "notes.md", ""
        try:
            name, text = source()
        except Exception:  # noqa: BLE001 - a closed editor must not stop New Gist
            return "notes.md", ""
        return (name or "notes.md"), text

    def _new_gist(self) -> None:
        from quill.ui.github_gist_editor_dialog import GitHubGistEditorDialog

        name, text = self._gist_start()
        editor = GitHubGistEditorDialog(
            self.dialog, GistDraft.new(name, text), creating=True, announce_cb=self._announce
        )
        if not editor.show():
            return
        draft, public = editor.draft, editor.public
        kind = "public" if public else "secret"
        self._run_write(
            lambda: _explore(lambda: self._client.create_gist(draft, public=public)),
            f"Created the {kind} gist with {len(draft.files)} file"
            f"{'s' if len(draft.files) != 1 else ''}.",
        )

    def _edit_gist(self, row: ExploreRow) -> None:
        token = getattr(self, "_gist_read_token", 0) + 1
        self._gist_read_token = token
        self._status.SetLabel("Reading the gist from GitHub...")

        def worker() -> None:
            try:
                result: Any = self._client.fetch_gist(row.key)
            except GitHubItemsError as exc:
                result = exc
            except Exception as exc:  # noqa: BLE001 - say it rather than lose it
                result = GitHubItemsError(f"Unexpected error: {exc}")
            self._wx.CallAfter(self._gist_read, token, row.key, result)

        threading.Thread(target=worker, daemon=True).start()  # GATE-40-OK: gist read.

    def _gist_read(self, token: int, gist_id: str, result: Gist | GitHubItemsError) -> None:
        if token != self._gist_read_token or not dialog_alive(self.dialog):
            return
        if isinstance(result, GitHubItemsError):
            message = str(result.args[0]) if result.args else str(result)
            self._status.SetLabel(message)
            self._announce(message)
            return
        self._status.SetLabel(f"Editing the gist {result.description or gist_id}.")
        from quill.ui.github_gist_editor_dialog import GitHubGistEditorDialog

        editor = GitHubGistEditorDialog(
            self.dialog, GistDraft.from_gist(result), creating=False, announce_cb=self._announce
        )
        if not editor.show():
            return
        draft = editor.draft
        summary = draft.summary()
        if summary == "No changes.":
            self._announce("No changes to save; nothing was sent to GitHub.")
            return
        self._run_write(
            lambda: _explore(lambda: self._client.update_gist(gist_id, draft)),
            f"Gist saved. {summary.replace('Save will', 'GitHub confirmed:')}",
        )

    def _star_gist(self, row: ExploreRow, starred: bool) -> None:
        verb = "Starred" if starred else "Unstarred"
        self._run_write(
            lambda: _explore(lambda: self._client.set_gist_starred(row.key, starred)),
            f"{verb} the gist {row.title or row.label}.",
        )

    def _delete_gist(self, row: ExploreRow) -> None:
        name = row.label
        if not self._confirm(
            f"Delete the gist {name}? Its files and history go with it, and QUILL "
            "cannot bring it back.",
            "Delete Gist",
        ):
            return
        self._run_write(
            lambda: _explore(lambda: self._client.delete_gist(row.key)),
            f"Deleted the gist {name}.",
        )
