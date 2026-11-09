"""QUILL's Workbench status cell: "Workbench: owner/name" while the mode is on (2026-11-08).

While GitHub Workbench Mode is on, the status bar carries one more cell, worded
by :func:`quill.core.github.workbench_menu.status_cell_text` -- the repository
the GitHub menu works on, or "Workbench" alone when the document is in none.
QUILL Lite has the same cell (``quill/apps/lite_status_cells.py``), from the
same words.

It comes and goes with the mode, whatever Customize Status Bar says: the item
is in ``STATUS_BAR_ITEMS`` and hidden by default, so it never shows on its own,
and leaving the mode takes it away. It is reached like every other cell, with
F6 and the arrow keys, and it is never announced (GATE-13): entering and
leaving the mode already are, and its text is read when somebody arrives on it.

A base of :class:`quill.ui.main_frame_ai_status.AiStatusCellMixin`, so it sits
ahead of ``StatusBarMixin`` without ``main_frame.py`` gaining a base (GATE-11).
"""

from __future__ import annotations

from quill.core.github import workbench_menu as table

__all__ = ["GitHubWorkbenchStatusCellMixin"]

_KEY = table.STATUS_CELL_KEY


class GitHubWorkbenchStatusCellMixin:
    """The ``workbench`` cell: present only in the mode, and its text."""

    def _statusbar_items(self) -> list[str]:
        items: list[str] = list(super()._statusbar_items())  # type: ignore[misc]
        if not getattr(self, "_github_workbench_mode", False):
            return [item for item in items if item != _KEY]
        if _KEY not in items:
            # Before the message, which stays last for the reason in
            # StatusBarMixin._statusbar_items.
            at = items.index("message") if "message" in items else len(items)
            items.insert(at, _KEY)
        return items

    def _statusbar_text_for_item(self, item: str) -> str:
        if item == _KEY:
            return self.github_workbench_status_text()
        return str(super()._statusbar_text_for_item(item))  # type: ignore[misc]

    def github_workbench_status_text(self) -> str:
        """The cell's text, or ``""`` when the mode is off.

        The repository is looked up once per document path while the mode is
        on: finding it reads ``.git/config`` from disk, and the bar refreshes
        on every pause in typing.
        """
        if not getattr(self, "_github_workbench_mode", False):
            return ""
        path = getattr(getattr(self, "document", None), "path", None)
        cache: dict[str, str] = self.__dict__.setdefault("_github_status_repo_cache", {})
        key = str(path or "")
        if key not in cache:
            find = getattr(self, "_github_items_initial_repo", None)
            cache[key] = str(find()) if callable(find) else ""
        return table.status_cell_text(cache[key])

    def _refresh_github_status_cell(self) -> None:
        """The mode changed: forget the repositories found and redraw the bar."""
        self.__dict__.pop("_github_status_repo_cache", None)
        refresh = getattr(self, "_refresh_statusbar", None)
        if callable(refresh):
            refresh()
