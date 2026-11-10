"""The GitHub menu's own entry points, shared by QUILL and QUILL Lite (2026-11-08).

Workbench mode's GitHub menu is a short list of doors (GitHub PRD section 6,
Phase 4): Open GitHub Workbench, Inbox, This Repository's Issues, This
Repository's Pull Requests and Actions Runs. The rows that left the menu (My
Work, Notifications, Releases, Explore GitHub) keep their command ids, and
every one of them opens the GitHub Workbench window at the matching node
(:data:`WORKBENCH_NODES`) whenever the Workbench is the window in use
(:func:`quill.core.github.workbench_flag.workbench_window_enabled`); with the
classic windows chosen they open GitHub Items or Explore GitHub on their view,
as before.

One class, :class:`GitHubWorkbenchCommands`, holds them. It owns no gate: Safe
Mode, the first-use consent and the sign-in check stay in the one opener each
editor already has, and this class only says *where* to open. QUILL reaches
it through ``quill/ui/main_frame_github_menu.py`` and QUILL Lite through
``quill/apps/lite_github_workbench.py``, the way the hosted free AI is shared
(``quill/ui/hosted_ai_*.py`` with ``main_frame_hosted_ai.py``).

Opening a place says nothing: the window's title and its focused tree say it
(GATE-13).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.ui.github_items_view import VIEW_ISSUES, VIEW_RELEASES, VIEW_RUNS

__all__ = [
    "EXPLORE_VIEWS",
    "ITEMS_VIEWS",
    "WORKBENCH_NODES",
    "GitHubWorkbenchCommands",
    "open_in_workbench_window",
]

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
    "github.workbench_pulls": VIEW_ISSUES,
    "file.open_github_items": "",
    "github.workbench_actions_runs": VIEW_RUNS,
    "github.workbench_releases": VIEW_RELEASES,
}


#: The Workbench node each door opens, by QUILL command id ("" is the
#: person's own choice in Workbench Options: Inbox, Start Here or the last place).
WORKBENCH_NODES: dict[str, str] = {
    "file.open_github_items": "",
    "github.workbench_inbox": "inbox",
    "github.workbench_my_work": "attention",
    "github.view_notifications": "notifications",
    "github.workbench_issues": "issues",
    "github.workbench_pulls": "pulls",
    "github.workbench_actions_runs": "runs",
    "github.workbench_releases": "releases",
    "github.workbench_explore": "search",
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
        open_workbench: Callable[[str], None] | None = None,
    ) -> None:
        self._open_items = open_items
        self._open_explore = open_explore
        self._open_workbench = open_workbench

    def run(self, command_id: str) -> None:
        """Run one of the rows above by QUILL's command id."""
        from quill.core.github.workbench_flag import workbench_window_enabled

        if self._open_workbench is not None and workbench_window_enabled():
            self._open_workbench(WORKBENCH_NODES[command_id])
        elif command_id in ITEMS_VIEWS:
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

    def pulls(self) -> None:
        self.run("github.workbench_pulls")

    def workbench(self) -> None:
        self.run("file.open_github_items")

    def actions_runs(self) -> None:
        self.run("github.workbench_actions_runs")

    def releases(self) -> None:
        self.run("github.workbench_releases")

    def explore(self) -> None:
        self.run("github.workbench_explore")


def open_in_workbench_window(
    editor: object,
    provider: object,
    *,
    repository: str = "",
    view: str = "",
    announce: Callable[[str], None] | None = None,
    **extras: Any,
) -> bool:
    """Open the GitHub Workbench window instead of GitHub Items (the default).

    Both editors' GitHub Items openers call this after their own gates (Safe
    Mode, consent, sign-in) have made *provider*. It returns False only when
    the person chose the classic windows in Workbench Options (or a developer
    forced them, :mod:`quill.core.github.workbench_flag`), so the opener goes
    on to GitHub Items exactly as before. When it returns True the window
    owns *provider* and closes it with itself.
    """
    from quill.core.github.workbench_flag import workbench_window_enabled

    if not workbench_window_enabled():
        return False
    from quill.ui.github_workbench_window import open_github_workbench

    open_github_workbench(
        editor, provider, repository=repository, view=view, announce=announce, **extras
    )
    return True
