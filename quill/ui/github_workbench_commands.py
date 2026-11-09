"""The GitHub menu's own entry points, shared by QUILL and QUILL Lite (2026-11-08).

Workbench mode's GitHub menu opens the views people actually use in one step,
where before they had to open GitHub Items and then pick a view: Inbox (Explore's
attention queue), My Work, Notifications, Issues and Pull Requests, Actions Runs,
Releases, and Explore GitHub itself.

One class, :class:`GitHubWorkbenchCommands`, holds them. It owns no gate: Safe
Mode, the first-use consent and the sign-in check stay in the one opener each
editor already has, and this class only says *which view* to open. QUILL reaches
it through ``quill/ui/main_frame_github_menu.py`` and QUILL Lite through
``quill/apps/lite_github_workbench.py``, the way the hosted free AI is shared
(``quill/ui/hosted_ai_*.py`` with ``main_frame_hosted_ai.py``).

Opening a view says nothing: the window's title and its focused list say it
(GATE-13).
"""

from __future__ import annotations

from collections.abc import Callable

from quill.ui.github_items_view import VIEW_ISSUES, VIEW_RELEASES, VIEW_RUNS

__all__ = ["EXPLORE_VIEWS", "ITEMS_VIEWS", "GitHubWorkbenchCommands"]

#: Explore's view for each Explore row, by QUILL command id.
EXPLORE_VIEWS: dict[str, str | None] = {
    "github.workbench_inbox": "attention",
    "github.workbench_my_work": "my_work",
    "github.view_notifications": "notifications",
    "github.workbench_explore": None,  # Explore's own default
}

#: GitHub Items' view for each Items row, by QUILL command id.
ITEMS_VIEWS: dict[str, str] = {
    "github.workbench_issues": VIEW_ISSUES,
    "github.workbench_actions_runs": VIEW_RUNS,
    "github.workbench_releases": VIEW_RELEASES,
}


class GitHubWorkbenchCommands:
    """The GitHub menu's view rows, over an editor's own two openers.

    *open_items* opens GitHub Items on a view (``"issues"``, ``"runs"``,
    ``"releases"``); *open_explore* opens Explore GitHub on a view, or on its
    default for ``None``. Both run the editor's gates.
    """

    def __init__(
        self,
        open_items: Callable[[str], None],
        open_explore: Callable[[str | None], None],
    ) -> None:
        self._open_items = open_items
        self._open_explore = open_explore

    def run(self, command_id: str) -> None:
        """Run one of the rows above by QUILL's command id."""
        if command_id in ITEMS_VIEWS:
            self._open_items(ITEMS_VIEWS[command_id])
        elif command_id in EXPLORE_VIEWS:
            self._open_explore(EXPLORE_VIEWS[command_id])
        else:
            raise KeyError(command_id)

    def inbox(self) -> None:
        self.run("github.workbench_inbox")

    def my_work(self) -> None:
        self.run("github.workbench_my_work")

    def notifications(self) -> None:
        self.run("github.view_notifications")

    def issues(self) -> None:
        self.run("github.workbench_issues")

    def actions_runs(self) -> None:
        self.run("github.workbench_actions_runs")

    def releases(self) -> None:
        self.run("github.workbench_releases")

    def explore(self) -> None:
        self.run("github.workbench_explore")
