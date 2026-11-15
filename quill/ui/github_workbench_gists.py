"""The GitHub Workbench's gist commands: New, Edit, Star or Unstar, Delete.

Explore GitHub did these before the Workbench replaced it; the Workbench's
action table (:mod:`quill.core.github.item_actions`) kept the rows and Ctrl+N
on My Gists kept pointing at ``new_gist``, but nothing answered them. These
use the calls Explore made (:class:`quill.core.github.gists.GitHubGistsMixin`
through the Explore client), so there is no new network call, and the same
gist editor dialog.

A new gist starts from the editor that opened the Workbench -- its selection,
else its whole document -- through *gist_source*, the callback both editors
already had for Explore (``_github_gist_source``). Without one it starts blank.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.github.explore_models import ExploreRow

__all__ = ["GitHubWorkbenchGistsMixin"]


class GitHubWorkbenchGistsMixin:
    """New, Edit, Star or Unstar, Delete for gists; helpers are the router's."""

    frame: Any
    _gist_source: Callable[[], tuple[str, str]] | None
    _say: Callable[[str], None]
    _confirm: Callable[[str, str], bool]
    _background: Callable[[str, Callable[[], Any], Callable[[Any], None]], None]
    _explore_client: Callable[[], Any]
    _announce: Callable[[str], None]

    def _gist_start(self) -> tuple[str, str]:
        source = getattr(self, "_gist_source", None)
        if source is None:
            return "notes.md", ""
        try:
            name, text = source()
        except Exception:  # noqa: BLE001 - a closed editor must not stop New Gist
            return "notes.md", ""
        return (name or "notes.md"), text

    def _do_new_gist(self, _ref: Any, _row: object) -> None:
        from quill.core.github.gists import GistDraft
        from quill.ui.github_gist_editor_dialog import GitHubGistEditorDialog

        name, text = self._gist_start()
        editor = GitHubGistEditorDialog(
            self.frame.frame, GistDraft.new(name, text), creating=True, announce_cb=self._announce
        )
        if not editor.show():
            return
        draft, public = editor.draft, editor.public
        kind = "public" if public else "secret"
        count = len(draft.files)
        client = self._explore_client()
        self._background(
            "create the gist",
            lambda: client.create_gist(draft, public=public),
            lambda _gist: (
                self._say(f"Created the {kind} gist with {count} file{'s' if count != 1 else ''}."),
                self.frame.reload(),
            ),
        )

    def _do_edit_gist(self, _ref: Any, row: object) -> None:
        assert isinstance(row, ExploreRow)
        client = self._explore_client()
        self._background(
            "read the gist",
            lambda: client.fetch_gist(row.key),
            lambda gist: self._edit_read(row, gist),
        )

    def _edit_read(self, row: ExploreRow, gist: Any) -> None:
        from quill.core.github.gists import GistDraft
        from quill.ui.github_gist_editor_dialog import GitHubGistEditorDialog

        if self.frame is None:
            return
        editor = GitHubGistEditorDialog(
            self.frame.frame, GistDraft.from_gist(gist), creating=False, announce_cb=self._announce
        )
        if not editor.show():
            return
        draft = editor.draft
        summary = draft.summary()
        if summary == "No changes.":
            self._say("No changes to save; nothing was sent to GitHub.")
            return
        client = self._explore_client()
        self._background(
            "save the gist",
            lambda: client.update_gist(row.key, draft),
            lambda _gist: (
                self._say(f"Gist saved. {summary.replace('Save will', 'GitHub confirmed:')}"),
                self.frame.reload(),
            ),
        )

    def _do_star_gist(self, _ref: Any, row: object) -> None:
        assert isinstance(row, ExploreRow)
        client = self._explore_client()
        name = row.title or row.label

        def toggle() -> bool:
            starred = not client.is_gist_starred(row.key)
            client.set_gist_starred(row.key, starred)
            return starred

        self._background(
            "star or unstar the gist",
            toggle,
            lambda starred: self._say(f"{'Starred' if starred else 'Unstarred'} the gist {name}."),
        )

    def _do_delete_gist(self, _ref: Any, row: object) -> None:
        assert isinstance(row, ExploreRow)
        name = row.label
        if not self._confirm(
            "Delete Gist",
            f"Delete the gist {name}? Its files and history go with it, and QUILL "
            "cannot bring it back.",
        ):
            return
        client = self._explore_client()
        self._background(
            "delete the gist",
            lambda: client.delete_gist(row.key),
            lambda _result: (self._say(f"Deleted the gist {name}."), self.frame.reload()),
        )
