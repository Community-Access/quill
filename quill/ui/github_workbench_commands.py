"""The GitHub menu's own entry points, shared by QUILL and QUILL Lite (2026-11-08).

Workbench mode's GitHub menu is a short list of doors (GitHub PRD section 6,
Phase 4): Open GitHub Workbench, Inbox, This Repository's Issues, This
Repository's Pull Requests and Actions Runs. The rows that left the menu (My
Work, Notifications, Releases, Explore GitHub) keep their command ids, and
every one of them opens the GitHub Workbench window at the matching node
(:data:`WORKBENCH_NODES`) whenever the Workbench is the window in use
(:func:`quill.core.github.workbench_flag.workbench_window_enabled`). The
classic GitHub Items and Explore GitHub windows are no longer entry points.

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
    "ADMIN_DOORS",
    "EXPLORE_VIEWS",
    "ITEMS_VIEWS",
    "WORKBENCH_NODES",
    "GitHubWorkbenchCommands",
    "editor_call",
    "open_in_workbench_window",
    "workbench_takes",
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


#: QUILL's Repository Admin and Codespaces commands, with the Workbench in use:
#: (node to open, what to run there). "sheet:<page>" opens the repository's
#: Properties at that page; a command id runs the editor's own dialog from the
#: Workbench; "" only goes to the node.
ADMIN_DOORS: dict[str, tuple[str, str]] = {
    "github.rename_repository": ("repository", "sheet:general"),
    "github.change_repository_visibility": ("repository", "sheet:danger"),
    "github.change_default_branch": ("repository", "sheet:general"),
    "github.configure_branch_protection": ("repository", "sheet:rules"),
    "github.delete_branch": ("branches", ""),
    "github.create_release": ("releases", "github.create_release"),
    "github.dispatch_workflow": ("workflows", "github.dispatch_workflow"),
    "github.view_security_alerts": ("alerts", ""),
    "github.create_repository": ("repository", "github.create_repository"),
    "github.fork_repository": ("repository", "github.fork_repository"),
    "github.commit_multiple_files": ("repository", "github.commit_multiple_files"),
    "github.browse_organization": ("organizations", ""),
    "github.list_codespaces": ("repository", "github.list_codespaces"),
    "github.create_codespace": ("repository", "github.create_codespace"),
}

_FROM_WORKBENCH: list[str] = []


def workbench_takes(command_id: str) -> bool:
    """Whether *command_id* should open the Workbench and run there, rather than here."""
    from quill.core.github.workbench_flag import workbench_window_enabled

    if command_id not in ADMIN_DOORS or command_id in _FROM_WORKBENCH:
        return False
    return workbench_window_enabled()


def editor_call(run: Callable[[str], None], command_id: str) -> None:
    """Run the editor's own *command_id* for the Workbench, as itself (no door again)."""
    _FROM_WORKBENCH.append(command_id)
    try:
        run(command_id)
    finally:
        _FROM_WORKBENCH.remove(command_id)


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
        if command_id not in WORKBENCH_NODES:
            raise KeyError(command_id)
        if self._open_workbench is None:
            raise RuntimeError("The GitHub Workbench window is not available.")
        self._open_workbench(WORKBENCH_NODES[command_id])

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
    """Open the only GitHub management window after the editor's normal gates."""
    from quill.ui.github_workbench_window import open_github_workbench

    open_github_workbench(
        editor, provider, repository=repository, view=view, announce=announce, **extras
    )
    return True
