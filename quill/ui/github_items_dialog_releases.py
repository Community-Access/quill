"""Release-specific draft actions for the shared GitHub Items viewer."""

from __future__ import annotations

from quill.core.github.items_provider import GitHubRelease


class GitHubItemsReleaseMixin:
    """Create a local, editable release-notes preview for an explicit tag range."""

    def _draft_release_notes(self) -> None:
        from quill.ui.github_release_notes_dialog import GitHubReleaseNotesDialog

        selected = self._selected_indices()
        previous_tag = ""
        if len(selected) == 1 and 0 <= selected[0] < len(self._rows):
            selected_release = self._rows[selected[0]]
            if isinstance(selected_release, GitHubRelease):
                previous_tag = selected_release.tag
        GitHubReleaseNotesDialog(
            self.dialog,
            self._provider,
            self._repo,
            previous_tag=previous_tag,
            announce_cb=self._announce,
        ).show()


__all__ = ["GitHubItemsReleaseMixin"]
