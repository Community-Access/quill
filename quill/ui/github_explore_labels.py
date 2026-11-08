"""Label actions in Explore's Repository labels view (create, edit, delete, find issues).

Moved out of :mod:`quill.ui.github_explore_dialog` on 2026-11-07 (GATE-11) to
make room for Wave 4. Each write goes through the dialog's ``_run_write``,
which asks GitHub off the UI thread and says only what it confirmed.
"""

from __future__ import annotations

from quill.core.github.explore import ExploreRow

__all__ = ["GitHubExploreLabelsMixin"]


class GitHubExploreLabelsMixin:
    """Create, edit and delete a label, and search for the issues that carry one."""

    def _find_label_issues(self, row: ExploreRow) -> None:
        self._query.SetValue(f'repo:{row.repo} is:issue label:"{row.key}"')
        self._view.SetSelection(0)
        self._load(None)

    def _create_label(self) -> None:
        name = self._prompt("Label name:", "Create Label")
        if not name:
            return
        color = self._prompt("Six-digit color without #:", "Create Label", "ededed")
        if color is None:
            return
        description = self._prompt("Description (optional):", "Create Label")
        if description is None:
            return
        repo = self._repo.GetValue().strip()
        self._run_write(
            lambda: self._client.create_label(repo, name, color, description),
            f"Created label {name}.",
        )

    def _delete_label(self, row: ExploreRow) -> None:
        if self._confirm(f"Delete label {row.key} from {row.repo}?", "Delete Label"):
            self._run_write(
                lambda: self._client.delete_label(row.repo, row.key), f"Deleted label {row.key}."
            )

    def _edit_label(self, row: ExploreRow) -> None:
        detail_lines = row.detail.splitlines()
        current_color = (
            detail_lines[1].removeprefix("Color: #") if len(detail_lines) > 1 else "ededed"
        )
        current_description = detail_lines[2] if len(detail_lines) > 2 else ""
        name = self._prompt("Label name:", "Edit Label", row.key)
        if not name:
            return
        color = self._prompt("Six-digit color without #:", "Edit Label", current_color)
        if color is None:
            return
        description = self._prompt("Description (optional):", "Edit Label", current_description)
        if description is None:
            return
        self._run_write(
            lambda: self._client.edit_label(row.repo, row.key, name, color, description),
            f"Updated label {row.key}.",
        )
