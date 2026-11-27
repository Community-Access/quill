"""My GitHub's two rows in the Workbench window's menu bar (kept out of GATE-11's budget).

Go > My GitHub is the front door's key; View > My GitHub View Options... asks what
the list shows and how it is ordered. Both are put into the bar by
:mod:`quill.core.github.workbench_window_menu`.
"""

from __future__ import annotations

from quill.core.workbench.menus import MenuRow

__all__ = ["GO_MY_GITHUB_ROW", "MY_GITHUB_OPTIONS_ROW"]

_P = "github.workbench."

GO_MY_GITHUB_ROW = MenuRow(
    f"{_P}go_my_github",
    "&My GitHub",
    "Alt+Shift+Home",
    "Your whole queue in one list: unread notifications, assigned work, review requests "
    "and your pull requests with failing checks.",
)
MY_GITHUB_OPTIONS_ROW = MenuRow(
    f"{_P}my_github_options",
    "My GitHub &View Options...",
    "Ctrl+Alt+M",
    "Choose which kinds My GitHub shows, one repository, how it is ordered and grouped. "
    "Remembered for your account.",
)
