"""The GitHub Workbench window's own menu bar, as a table (GitHub PRD section 4).

The Phase 1 spike's bar: the rows the window can already do. Each later phase
adds its rows here, and :func:`quill.core.workbench.menus.problems` keeps the
whole bar inside the accelerator and access-key rules as it grows (a test
fails on any breach). Keys follow Part C: F-keys keep their Windows meanings,
Ctrl+number goes to a place, Alt+number says something, and Alt+Enter is
Properties. No row uses a plain letter, Enter, Backspace or Ctrl+C, which
belong to the focused control.
"""

from __future__ import annotations

from quill.core.github.item_actions import PROPERTIES_COMMAND
from quill.core.workbench.menus import MenuRow, MenuSpec

__all__ = ["GO_NODES", "WINDOW_MENU"]


def _row(verb: str, label: str, key: str, help: str) -> MenuRow:  # noqa: A002 - field name
    return MenuRow(f"github.workbench.{verb}", label, key, help)


WINDOW_MENU: tuple[MenuSpec, ...] = (
    MenuSpec(
        "&File",
        (
            _row(
                "open_address",
                "&Open GitHub Address...",
                "Ctrl+L",
                "Type or paste owner/name or a GitHub link to go to that repository.",
            ),
            _row(
                "open_on_github",
                "Open on &GitHub",
                "Shift+Enter",
                "Open the selected row, or the node, in your browser.",
            ),
            None,
            _row("close", "&Close Workbench", "Alt+F4", "Close this window. The editor stays."),
        ),
    ),
    MenuSpec(
        "&Edit",
        (
            _row("copy_link", "Copy &Link", "Ctrl+Shift+C", "Copy the selected row's address."),
            _row("filter", "&Filter...", "Ctrl+E", "Move to the filter box above the list."),
        ),
    ),
    MenuSpec(
        "&View",
        (
            _row("refresh", "&Refresh", "F5", "Load this view again from GitHub."),
            None,
            _row("back", "&Back", "Alt+Left", "The view you were on before. Backspace too."),
            _row("forward", "&Forward", "Alt+Right", "The view you went back from."),
            None,
            _row("next_pane", "&Next Pane", "F6", "Tree, filter, list, details, status bar."),
            _row("previous_pane", "&Previous Pane", "Shift+F6", "The same panes, backwards."),
            None,
            _row("where_am_i", "&Where Am I", "Alt+1", "Say the node and the filter in effect."),
            _row("say_selection", "Say &Selection", "Alt+2", "Say how many rows are selected."),
        ),
    ),
    MenuSpec(
        "&Go",
        (
            _row("go_start", "&Start Here", "Ctrl+9", "What this window is and how it works."),
            _row("go_inbox", "I&nbox", "Ctrl+1", "What needs you, across GitHub."),
            _row(
                "go_repository",
                "Current &Repository",
                "Ctrl+2",
                "The repository this window opened on.",
            ),
            _row("go_issues", "&Issues", "Ctrl+Shift+1", "This repository's issues."),
            _row("go_pulls", "&Pull Requests", "Ctrl+Shift+2", "This repository's pull requests."),
            _row("go_runs", "&Actions Runs", "Ctrl+Shift+4", "This repository's workflow runs."),
            _row("go_releases", "R&eleases", "Ctrl+Shift+6", "This repository's releases."),
            None,
            _row("go_parent", "Paren&t Node", "Alt+Up", "The node above this one in the tree."),
        ),
    ),
    MenuSpec(
        "&Item",
        (
            MenuRow(
                PROPERTIES_COMMAND,
                "&Properties...",
                "Alt+Enter",
                "Everything about the selected row on one sheet.",
            ),
        ),
    ),
    MenuSpec(
        "&Window",
        (
            _row(
                "switch_to_editor",
                "Switch to &Editor",
                "Ctrl+Shift+E",
                "Bring forward the editor that opened this window.",
            ),
        ),
    ),
    MenuSpec(
        "&Help",
        (_row("help_view", "&Help for This View", "F1", "What this view and control do."),),
    ),
)
"""The bar, in order: File, Edit, View, Go, Item, Window, Help."""

GO_NODES: dict[str, tuple[str, str]] = {
    "github.workbench.go_start": ("", "start"),
    "github.workbench.go_inbox": ("", "inbox"),
    "github.workbench.go_repository": ("repository", "repository"),
    "github.workbench.go_issues": ("repository", "issues"),
    "github.workbench.go_pulls": ("repository", "pulls"),
    "github.workbench.go_runs": ("repository", "runs"),
    "github.workbench.go_releases": ("repository", "releases"),
}
"""Where each Go row lands: (template, node key); a template node is the current repository's."""
