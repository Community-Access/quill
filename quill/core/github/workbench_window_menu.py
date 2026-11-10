"""The GitHub Workbench window's own menu bar, as a table (GitHub PRD section 4, Part C).

The whole bar: File, Edit, View, Go, Item, Repository, Account, Tools,
Window and Help. :func:`quill.core.workbench.menus.problems` keeps it inside
the accelerator and access-key rules (a test fails on any breach), and
:data:`WORKBENCH_KEYS` is the window's ``keymap.APP_KEYMAPS`` entry
(decision 7), so the keyboard reference and the Key Describer are generated
from the same rows.

How the keys were chosen (Part C, C1):

- **Ctrl+number goes** to a top-level place, **Ctrl+Shift+number** to a part of
  the current repository, and **Alt+number says** something without moving.
- **F-keys keep their Windows meanings:** F1 help, F5 refresh, F6 pane.
- **Plain letters are always type-ahead** in the tree and the lists, so no
  row is ever a bare letter, and there is no option to make one (decision 11).
- **No key sets a single property:** Alt+Enter opens Properties and the sheet
  does the rest (decisions 10 and 11).
- **Nothing a screen reader or the family owns system-wide**: no Insert or
  Caps Lock, no Ctrl+Alt+arrows, nothing with the Windows key, and no
  Ctrl+Alt+letter on anything pressed while a text box has focus, except the
  Filter Builder, which a text box never needs (C1.7). The family's free-chord
  gate (``tests/unit/ui/test_global_hotkeys.py``) holds the table against
  every system-wide key, because this entry is part of ``APP_KEYMAPS``.

The Item menu holds the actions that have a key; every other action of the
selected row is on its context menu and in What Can I Do Here? (Shift+F1),
which lists all of them from the same action table, so none is reachable only
by right-clicking. Keys that belong to the focused control (Enter, Delete,
Backspace, Escape) are not menu rows; the window handles them itself and
lists them in :data:`CONTROL_KEYS`.
"""

from __future__ import annotations

from quill.core.github.item_actions import PROPERTIES_COMMAND
from quill.core.workbench.menus import MenuRow, MenuSpec, rows

__all__ = [
    "ALIAS_KEYS",
    "CONTROL_KEYS",
    "GO_NODES",
    "PLACEHOLDER_COMMANDS",
    "WINDOW_MENU",
    "WORKBENCH_KEYMAP_ID",
    "WORKBENCH_KEYS",
]

#: The window's section of ``keymap.APP_KEYMAPS``.
WORKBENCH_KEYMAP_ID = "github_workbench"

_P = "github.workbench."


def _row(verb: str, label: str, key: str, help: str) -> MenuRow:  # noqa: A002 - field name
    return MenuRow(f"{_P}{verb}", label, key, help)


_FILE = MenuSpec(
    "&File",
    (
        _row(
            "new_here",
            "&New Here...",
            "Ctrl+N",
            "Something new where you are: an issue in Issues, a saved search in Saved Searches.",
        ),
        _row("new_any", "Ne&w...", "Ctrl+Shift+N", "Choose what to create, wherever you are."),
        None,
        _row(
            "open_address",
            "&Open GitHub Address...",
            "Ctrl+L",
            "Type or paste owner/name, #42, owner/name#42 or any GitHub link to go there.",
        ),
        _row(
            "go_to_number",
            "&Go to Number...",
            "Ctrl+G",
            "Go to an issue or pull request in this repository by its number.",
        ),
        None,
        _row(
            "open_on_github",
            "Open on Git&Hub",
            "Shift+Enter",
            "Open the selected row, or the node, in your browser.",
        ),
        _row(
            "open_in_editor",
            "Open in &Editor",
            "Ctrl+Enter",
            "Open the selected file in the editor that opened this window.",
        ),
        None,
        _row("close", "&Close Workbench", "Alt+F4", "Close this window. The editor stays."),
    ),
)

_EDIT = MenuSpec(
    "&Edit",
    (
        _row(
            "copy",
            "&Copy",
            "Ctrl+C",
            "Copy the selected rows as text; in a text box, its own selection.",
        ),
        _row("copy_link", "Copy &Link", "Ctrl+Shift+C", "Copy the selected row's address."),
        None,
        _row("filter", "&Filter...", "Ctrl+E", "Move to the filter box. Ctrl+Shift+F too."),
        _row(
            "filter_builder",
            "Filter &Builder...",
            "Ctrl+Alt+F",
            "Build a filter one condition at a time. Coming in a later release.",
        ),
        None,
        _row(
            "select_all",
            "Select &All",
            "Ctrl+A",
            "Select every row in the list; in a text box, all its text.",
        ),
    ),
)

_VIEW = MenuSpec(
    "&View",
    (
        _row("refresh", "R&efresh", "F5", "Load this view again from GitHub."),
        _row(
            "refresh_uncached",
            "Refresh &Ignoring Cache",
            "Ctrl+F5",
            "Load this view again, asking GitHub for everything afresh.",
        ),
        _row(
            "load_more",
            "Load &More",
            "Alt+PageDown",
            "Load the next page of rows, if GitHub has more.",
        ),
        None,
        _row("back", "&Back", "Alt+Left", "The view you were on before. Backspace too."),
        _row("forward", "&Forward", "Alt+Right", "The view you went back from."),
        None,
        _row("next_pane", "&Next Pane", "F6", "Tree, filter, list, details, status bar."),
        _row("previous_pane", "&Previous Pane", "Shift+F6", "The same panes, backwards."),
        None,
        _row("where_am_i", "&Where Am I", "Alt+1", "Say the node and the filter in effect."),
        _row("say_selection", "Say &Selection", "Alt+2", "Say how many rows are selected."),
        _row("say_item", "Say I&tem State", "Alt+3", "Say the selected item's state in one line."),
        _row("say_counts", "Say &Counts", "Alt+4", "Say how many rows this view holds."),
        _row("say_access", "Say Your &Access", "Alt+5", "Say what you can do here."),
        _row("say_rate", "Say Rate &Limit", "Alt+6", "Say how much of the GitHub API is left."),
        _row("say_filter", "Say Filte&r", "Alt+7", "Say the filter in effect, in words."),
        _row("say_loading", "Say L&oading", "Alt+8", "Say what is loading, or when it loaded."),
        _row(
            "say_account",
            "Say Acco&unt",
            "Alt+9",
            "Say the account, and whether you are signed in.",
        ),
    ),
)

_GO = MenuSpec(
    "&Go",
    (
        _row("go_inbox", "I&nbox", "Ctrl+1", "What needs you, across GitHub. Alt+Home too."),
        _row(
            "go_repository",
            "Current &Repository",
            "Ctrl+2",
            "The repository this window opened on.",
        ),
        _row("go_search", "Searc&h", "Ctrl+3", "Search GitHub."),
        _row("go_people", "Peop&le", "Ctrl+4", "People you follow and who follow you."),
        _row("go_gists", "Gis&ts", "Ctrl+5", "Your gists."),
        _row("go_projects", "Pro&jects", "Ctrl+6", "Projects."),
        _row("go_watches", "&Watches", "Ctrl+7", "Watches: tell me when it happens. Coming later."),
        _row("go_saved_searches", "Sa&ved Searches", "Ctrl+8", "Searches you saved."),
        _row("go_start", "Start Her&e", "Ctrl+9", "What this window is and how it works."),
        _row(
            "go_across",
            "Across Repositories",
            "Ctrl+0",
            "Every kind of thing, by name, everywhere. Coming later.",
        ),
        None,
        _row("go_issues", "Iss&ues", "Ctrl+Shift+1", "This repository's issues."),
        _row("go_pulls", "&Pull Requests", "Ctrl+Shift+2", "This repository's pull requests."),
        _row("go_discussions", "&Discussions", "Ctrl+Shift+3", "This repository's discussions."),
        _row("go_runs", "&Actions Runs", "Ctrl+Shift+4", "This repository's workflow runs."),
        _row("go_files", "&Files", "Ctrl+Shift+5", "This repository's files."),
        _row("go_releases", "Relea&ses", "Ctrl+Shift+6", "This repository's releases."),
        _row("go_repo_projects", "Repositor&y Projects", "Ctrl+Shift+7", "Its Projects."),
        _row("go_security", "Se&curity", "Ctrl+Shift+8", "Its security alerts."),
        _row("go_settings", "Settin&gs", "Ctrl+Shift+9", "Its settings."),
        _row("go_insights", "Ins&ights", "Ctrl+Shift+0", "Its traffic and community profile."),
        None,
        _row("go_parent", "Parent N&ode", "Alt+Up", "The node above this one in the tree."),
    ),
)

_ITEM = MenuSpec(
    "&Item",
    (
        MenuRow(
            PROPERTIES_COMMAND,
            "&Properties...",
            "Alt+Enter",
            "Everything about the selected row on one sheet.",
        ),
        None,
        _row("comment", "&Comment...", "Ctrl+Shift+M", "Write a comment on the selected item."),
        _row(
            "diff",
            "File &Differences...",
            "Ctrl+Shift+D",
            "The selected pull request's changed files.",
        ),
        _row("merge", "&Merge...", "Ctrl+Shift+Enter", "Merge the selected pull request."),
        _row(
            "assign_copilot",
            "Assign to C&opilot...",
            "Ctrl+Shift+A",
            "Ask Copilot to work on the selected issue.",
        ),
        _row(
            "start_worktree",
            "Start in Local &Worktree...",
            "Ctrl+Shift+T",
            "A branch and a folder on this computer for the selected item.",
        ),
        None,
        _row(
            "what_failed",
            "What &Failed...",
            "Ctrl+Shift+W",
            "The failing steps of the selected run, and their log lines.",
        ),
        _row(
            "rerun_failed",
            "&Re-run Failed Jobs",
            "Ctrl+Shift+F5",
            "Run only what failed in the selected run again.",
        ),
        None,
        _row("mark_read", "Mark Re&ad", "Ctrl+Q", "Mark the selected notification read."),
        _row(
            "mark_all_read",
            "Mark All Read in &View",
            "Ctrl+Shift+Q",
            "Mark every notification in this view read. Asks first when there are many.",
        ),
        None,
        _row(
            "favorite",
            "Add to or Remove from Favor&ites",
            "Ctrl+D",
            "Keep the selected row under Repositories, Favorites.",
        ),
    ),
)

_REPOSITORY = MenuSpec(
    "&Repository",
    (
        _row(
            "compare",
            "&Compare Branches...",
            "Ctrl+Shift+B",
            "Commits ahead and behind between two branches, and the changed files.",
        ),
        _row(
            "run_workflow",
            "&Run Workflow on Branch...",
            "Ctrl+Shift+R",
            "Start a workflow that can be started by hand, on a branch.",
        ),
        _row(
            "repository_actions",
            "Repository &Actions...",
            "Ctrl+Shift+G",
            "Everything else for this repository: star, watch, fork, clone, Codespaces, "
            "settings and administration, as a list you can run from.",
        ),
    ),
)

_ACCOUNT = MenuSpec(
    "&Account",
    (
        _row(
            "manage_accounts",
            "&Manage GitHub Accounts...",
            "Ctrl+Shift+K",
            "Add, switch, sign in again or remove GitHub accounts.",
        ),
        _row(
            "rate_limit",
            "GitHub API &Rate Limit",
            "Ctrl+Shift+L",
            "How much of the GitHub API is left, and when it resets.",
        ),
    ),
)

_TOOLS = MenuSpec(
    "&Tools",
    (
        _row(
            "options",
            "Workbench &Options...",
            "Ctrl+Shift+O",
            "Where the Workbench opens, how notifications check, lists and privacy.",
        ),
    ),
)

_WINDOW = MenuSpec(
    "&Window",
    (
        _row(
            "switch_to_editor",
            "Switch to &Editor",
            "Ctrl+Shift+E",
            "Bring forward the editor that opened this window.",
        ),
    ),
)

_HELP = MenuSpec(
    "&Help",
    (
        _row("help_view", "&Help for This View", "F1", "What this view and control do."),
        _row(
            "what_can_i_do",
            "&What Can I Do Here?...",
            "Shift+F1",
            "Every action for the selection, its key, and why any is greyed.",
        ),
        _row("glossary", "What &Is This?", "Alt+F1", "The GitHub word for this row, explained."),
        _row(
            "guide_chapter",
            "GitHub Workbench &Guide",
            "Ctrl+F1",
            "The guide, opened at the chapter for where you are.",
        ),
        _row(
            "search_help",
            "&Search Help...",
            "Ctrl+Shift+F1",
            "Type a few words to find a help topic, a command or a GitHub word.",
        ),
        _row(
            "keys",
            "Workbench &Keys",
            "Alt+Shift+F1",
            "Every key in this window, by family.",
        ),
        None,
        _row("repeat_result", "Say &Last Result Again", "F9", "Say the last result again."),
        _row(
            "explain_result",
            "E&xplain That",
            "Shift+F9",
            "What the last result means and what you might do next.",
        ),
    ),
)

WINDOW_MENU: tuple[MenuSpec, ...] = (
    _FILE,
    _EDIT,
    _VIEW,
    _GO,
    _ITEM,
    _REPOSITORY,
    _ACCOUNT,
    _TOOLS,
    _WINDOW,
    _HELP,
)
"""The bar, in order (GitHub PRD section 4)."""

GO_NODES: dict[str, tuple[str, str]] = {
    f"{_P}go_start": ("", "start"),
    f"{_P}go_inbox": ("", "inbox"),
    f"{_P}go_repository": ("repository", "repository"),
    f"{_P}go_search": ("", "search"),
    f"{_P}go_people": ("", "people"),
    f"{_P}go_gists": ("", "gists"),
    f"{_P}go_projects": ("", "projects"),
    f"{_P}go_watches": ("", "watches"),
    f"{_P}go_saved_searches": ("", "saved_searches"),
    f"{_P}go_across": ("", "across"),
    f"{_P}go_issues": ("repository", "issues"),
    f"{_P}go_pulls": ("repository", "pulls"),
    f"{_P}go_discussions": ("repository", "discussions"),
    f"{_P}go_runs": ("repository", "runs"),
    f"{_P}go_files": ("repository", "files"),
    f"{_P}go_releases": ("repository", "releases"),
    f"{_P}go_repo_projects": ("repository", "repo_projects"),
    f"{_P}go_security": ("repository", "security"),
    f"{_P}go_settings": ("repository", "settings"),
    f"{_P}go_insights": ("repository", "insights"),
}
"""Where each Go row lands: (template, node key); a template node is the current repository's."""

#: Second keys for a menu row's command, handled by the window itself: a menu
#: label can show one key, so the other is here (and in the keyboard reference).
ALIAS_KEYS: dict[str, str] = {
    f"{_P}filter_alias": "Ctrl+Shift+F",
    f"{_P}inbox_home": "Alt+Home",
    f"{_P}refresh_alias": "Ctrl+R",
}

#: Keys the focused control owns, which the window answers only in the tree or
#: the list (C2, C3): Delete removes safely and Ctrl+Break cancels a run,
#: asking first. Enter, Backspace and Escape are listed in the reference.
CONTROL_KEYS: dict[str, str] = {
    f"{_P}remove": "Delete",
    f"{_P}cancel_run": "Ctrl+Cancel",
}

#: Rows that name a place or tool still to come: they explain and do nothing else.
PLACEHOLDER_COMMANDS = frozenset({f"{_P}filter_builder", f"{_P}go_watches", f"{_P}go_across"})

WORKBENCH_KEYS: dict[str, str] = {
    **{row.command_id: row.key for _menu, row in rows(WINDOW_MENU)},
    **ALIAS_KEYS,
    **CONTROL_KEYS,
}
"""Every default key in the Workbench window: its ``APP_KEYMAPS`` entry."""
