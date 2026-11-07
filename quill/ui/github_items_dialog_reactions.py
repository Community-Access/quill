"""Timeline and reactions for the GitHub Items viewer's selected issue or PR."""

from __future__ import annotations

from quill.core.github.items_provider import GitHubItem


class GitHubItemsReactionsMixin:
    """View Timeline, React to the item, and React to the current comment."""

    def _selected_item(self) -> GitHubItem | None:
        index = self._list.GetFirstSelected()
        model = self._rows[index] if 0 <= index < len(self._rows) else None
        return model if isinstance(model, GitHubItem) else None

    def _view_timeline_for_selected(self) -> None:
        item = self._selected_item()
        if item is None:
            self._announce("Select an issue or pull request first.")
            return
        from quill.ui.github_timeline_dialog import GitHubTimelineDialog

        GitHubTimelineDialog(
            self.dialog,
            self._provider,
            self._repo,
            item.number,
            kind="pull request" if item.is_pr else "issue",
            announce_cb=self._announce,
        ).show()

    def _react_to_selected_item(self) -> None:
        item = self._selected_item()
        if item is None:
            self._announce("Select an issue or pull request first.")
            return
        from quill.ui.github_reactions_ui import start_reaction_flow

        start_reaction_flow(
            self.dialog,
            self._provider,
            self._repo,
            "issue",
            item.number,
            what=f"{'pull request' if item.is_pr else 'issue'} #{item.number}",
            announce=self._announce,
        )

    def _react_to_current_comment(self) -> None:
        index = self._current_comment
        if not 0 <= index < len(self._comments):
            self._announce("Move to a comment with Alt+N first.")
            return
        comment = self._comments[index]
        try:
            comment_id = int(comment.get("id", "0") or 0)
        except ValueError:
            comment_id = 0
        from quill.ui.github_reactions_ui import start_reaction_flow

        start_reaction_flow(
            self.dialog,
            self._provider,
            self._repo,
            "issue_comment",
            comment_id,
            what=f"comment {index + 1} by {comment.get('author', 'someone')}",
            announce=self._announce,
        )


__all__ = ["GitHubItemsReactionsMixin"]
