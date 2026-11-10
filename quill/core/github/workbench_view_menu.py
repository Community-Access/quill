"""The Workbench bar's submenus and later rows: View, Go, Filter and Account (GitHub PRD 4, 17, 18).

Split out of :mod:`quill.core.github.workbench_window_menu` (GATE-11), which
puts these into the bar. Every row here follows the accelerator rule through
:func:`quill.core.workbench.menus.problems`: a submenu row has an access
letter (decision 11: no chord per toggle), a top-level row a key.

- **View:** Show (issues, pull requests or both), Open or Closed, Sort By,
  Quick Filters (the Filter menu of section 17.1), Group By (17.4), Columns...
  and Load All (17.3).
- **Go:** Next and Previous Unread (Ctrl+Period, Ctrl+Shift+Period), and the
  person's own Pinned, Favorites and saved searches as dynamic submenus.
- **Account:** GitHub Permissions (18.1), Change History (18.5), and the
  roles and access tools of 18.3 and 22.10.

wx-free and strict-typed.
"""

from __future__ import annotations

from quill.core.github.filter_menu import GROUP_FIELDS, TOGGLES
from quill.core.github.workbench_prefs import CHOICES
from quill.core.workbench.menus import MenuRow, MenuSub

__all__ = [
    "ACCOUNT_ROWS",
    "COLUMNS_ROW",
    "FILTER_SUB",
    "GO_ROWS",
    "GROUP_SUB",
    "LOAD_ALL_ROW",
    "ROLES_SUB",
    "SHOW_CHOICES",
    "SHOW_SUB",
    "SORT_SUB",
    "STATE_SUB",
]

_P = "github.workbench."

#: View > Show: what an Issues list holds.
SHOW_CHOICES: tuple[tuple[str, str], ...] = (
    ("issues", "&Issues"),
    ("prs", "&Pull Requests"),
    ("both", "&Both"),
)
SHOW_SUB = MenuSub(
    "S&how",
    tuple(
        MenuRow(
            f"{_P}show_{key}",
            label,
            help=f"Show {label.replace('&', '').lower()} here.",
            radio="show",
        )
        for key, label in SHOW_CHOICES
    ),
    help="Issues, pull requests or both, in the Issues lists.",
)
STATE_SUB = MenuSub(
    "Open or Close&d",
    tuple(
        MenuRow(f"{_P}state_{key}", label, help=f"Show {key} items.", radio="state")
        for key, label in (("open", "&Open"), ("closed", "&Closed"), ("all", "&All"))
    ),
    help="Open items, closed ones, or both.",
)
_SORT_LABELS = {
    "number_desc": "&Newest First",
    "number_asc": "&Oldest First",
    "title_asc": "&Title, A to Z",
    "title_desc": "Title, &Z to A",
    "updated_desc": "&Recently Updated",
    "updated_asc": "&Least Recently Updated",
    "comments_desc": "&Most Comments",
}
SORT_SUB = MenuSub(
    "Sort B&y",
    tuple(
        MenuRow(f"{_P}sort_{key}", _SORT_LABELS[key], help="Order the list this way.", radio="sort")
        for key in CHOICES["default_sort"]
    ),
    help="How the list is ordered.",
)
FILTER_SUB = MenuSub(
    "&Quick Filters",
    (
        *(
            MenuRow(
                f"{_P}filter_{item.key}",
                item.label,
                help=(
                    f"Show only items {item.words.replace('{value}', 'someone you name')}. "
                    "Checked when it is on; it combines with the others and with what you "
                    "type in the filter box."
                    + (" Filtered over the loaded rows: Load All to be sure." if item.local else "")
                ),
                check=True,
            )
            for item in TOGGLES
        ),
        None,
        MenuRow(f"{_P}filter_clear", "Cl&ear These Filters", help="Turn every quick filter off."),
    ),
    help="The everyday filters, each a checked row (section 17.1).",
)
_GROUP_LABELS = {
    "label": "&Label",
    "milestone": "&Milestone",
    "assignee": "&Assignee",
    "author": "A&uthor",
    "type": "&Type",
    "state": "&State",
    "repository": "&Repository",
    "review": "Re&view State",
}
GROUP_SUB = MenuSub(
    "&Group By",
    (
        MenuRow(f"{_P}group_none", "&No Grouping", help="A flat list again.", radio="group"),
        *(
            MenuRow(
                f"{_P}group_{key}",
                _GROUP_LABELS[key],
                help=f"Put the list's groups in the tree, one node per {label.lower()}.",
                radio="group",
            )
            for key, label in GROUP_FIELDS
        ),
    ),
    help="Groups as tree nodes, which a screen reader reads better than rows (17.4).",
)
COLUMNS_ROW = MenuRow(
    f"{_P}columns",
    "Columns...",
    "Ctrl+Shift+U",
    "Choose which columns this list shows, and their order.",
)
LOAD_ALL_ROW = MenuRow(
    f"{_P}load_all",
    "Load All",
    "Ctrl+Shift+PageDown",
    "Load every page, so a filter over the loaded rows is sure to see everything.",
)

GO_ROWS: tuple[MenuRow | MenuSub | None, ...] = (
    MenuRow(
        f"{_P}next_unread",
        "Ne&xt Unread",
        "Ctrl+.",
        "Move to the next unread row in this list.",
    ),
    MenuRow(
        f"{_P}previous_unread",
        "Previous Unread",
        "Ctrl+Shift+.",
        "Move to the previous unread row in this list.",
    ),
    None,
    MenuSub("&Pinned", dynamic="pinned", help="Your pinned repositories; Enter goes there."),
    MenuSub("Fa&vorites", dynamic="favorites", help="Your favorite items; Enter opens one."),
    MenuSub(
        "Run a Saved Searc&h",
        dynamic="saved_searches",
        help="Your saved searches; Enter runs one under Search.",
    ),
)

ROLES_SUB = MenuSub(
    "Roles and &Access",
    (
        MenuRow(
            f"{_P}my_access",
            "&My Access Here...",
            help="Your effective role here, and where each part comes from.",
        ),
        MenuRow(
            f"{_P}view_as_role",
            "&View As Role...",
            help="What a role could do here, read-only: nothing you do is sent.",
        ),
        MenuRow(
            f"{_P}compare_roles",
            "&Compare Roles...",
            help="Two roles side by side: what one may do that the other may not.",
        ),
        MenuRow(
            f"{_P}why_cant_they",
            "&Why Can't They?...",
            help="Name a person and an action; hear what stops them and who can fix it.",
        ),
        None,
        MenuRow(
            f"{_P}access_matrix",
            "Access &Review...",
            help="Every person and repository pair in an organization, with role and "
            "source: filterable, exportable as CSV.",
        ),
        MenuRow(
            f"{_P}bulk_access",
            "&Bulk Access Changes...",
            help="One team or person, many repositories: previewed, then a result per change.",
        ),
        None,
        MenuRow(
            f"{_P}account_level",
            "Workbench &Level for This Account...",
            help="Read Only, Organize or Full: what the Workbench may change with this "
            "account, whatever GitHub would allow.",
        ),
    ),
    help="Who may do what, and changing it (sections 18.2 to 18.3.2).",
)

ACCOUNT_ROWS: tuple[MenuRow | MenuSub | None, ...] = (
    None,
    MenuRow(
        f"{_P}permissions",
        "GitHub &Permissions...",
        "Ctrl+Shift+P",
        "Every permission the Workbench can use, what it unlocks, whether you have it, and "
        "one step to add the missing ones.",
    ),
    MenuRow(
        f"{_P}change_history",
        "Change &History...",
        "Ctrl+Shift+H",
        "Every change the Workbench made on GitHub: before and after, and Undo where GitHub "
        "allows it.",
    ),
    ROLES_SUB,
)
