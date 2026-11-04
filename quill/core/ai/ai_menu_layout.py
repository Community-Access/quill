"""One AI menu shape for the whole QuillVille family (2026-11-03).

Every AI menu reads in the same order, so a listener learns it once and finds
it again in every app:

1. **Ask**: the ways to ask a question.
2. **What this app's AI does**: its tasks and features, in the app's own order.
3. **Which AI Am I Using** and **Choose Your AI**.
4. **Accounts and Usage**, a submenu: Use My Own AI Key, Use My ChatGPT
   Subscription, Connect or Sign Out, Usage, Web Searches Left and the Privacy
   Agreement. These are windows a person opens a few times a year, and every one
   keeps its shortcut key, so moving them a level down costs nothing to the
   person who uses the key and takes six rows out of everybody's way.

Before this, the editors' AI menu was sixteen rows with one separator, with Ask
About an Image and Tidy Dictated Text sitting among the account rows, and each
app arranged its own differently. A row's place now comes from what it is, not
from when it was added.

The apps' rows are ``(command_id, label, handler_name)``, a separator being
``("", "", "")``. :func:`arrange` sorts them into the shape above and
:func:`fill` appends them to a menu. Both are wx-free: ``fill`` takes the menu,
a function that appends one row to a menu, and a function that makes a new
(sub)menu, so the same code serves wx menus and the tests' stand-ins.

wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

__all__ = [
    "ACCOUNTS_TITLE",
    "ACCOUNT_HANDLERS",
    "CHOOSE_HANDLERS",
    "Row",
    "arrange",
    "fill",
]

Row = tuple[str, str, str]

#: The submenu's title. U: the account rows that used it moved inside.
ACCOUNTS_TITLE = "Accounts and &Usage"

#: The account rows, in the order the submenu lists them, by handler.
ACCOUNT_HANDLERS: tuple[str, ...] = (
    "cmd_ai_own_key",
    "cmd_ai_chatgpt",
    "cmd_ai_sign_in",
    "cmd_ai_usage",
    "cmd_ai_web_searches",
    "cmd_ai_privacy",
)

#: Which AI Am I Using and Choose Your AI, in that order, after the features.
CHOOSE_HANDLERS: tuple[str, ...] = ("cmd_ai_which", "cmd_ai_choose")

_SEPARATOR: Row = ("", "", "")


def _tidy(rows: list[Row]) -> list[Row]:
    """No separator first, last, or twice in a row."""
    out: list[Row] = []
    for row in rows:
        if not row[0] and (not out or not out[-1][0]):
            continue
        out.append(row)
    while out and not out[-1][0]:
        out.pop()
    return out


def arrange(rows: Sequence[Row]) -> tuple[list[Row], list[Row], list[Row]]:
    """``(features, choose, accounts)``: the rows sorted into the family shape.

    *features* keeps the app's own order (Ask first, as every app lists it) and
    its own separators; *choose* and *accounts* follow the order above.
    """
    features: list[Row] = []
    choose: dict[str, Row] = {}
    accounts: dict[str, Row] = {}
    for row in rows:
        handler = row[2]
        if handler in CHOOSE_HANDLERS:
            choose[handler] = row
        elif handler in ACCOUNT_HANDLERS:
            accounts[handler] = row
        else:
            features.append(row)
    return (
        _tidy(features),
        [choose[h] for h in CHOOSE_HANDLERS if h in choose],
        [accounts[h] for h in ACCOUNT_HANDLERS if h in accounts],
    )


def fill(
    menu: Any,
    rows: Sequence[Row],
    append_row: Callable[[Any, Row], None],
    new_menu: Callable[[], Any],
    *,
    extra: Callable[[Any], None] | None = None,
) -> Any:
    """Append *rows* to *menu* in the family shape; return the accounts submenu.

    *extra*, when given, appends the app's own feature rows after the shared
    ones (QUILL Cast's listening commands), still above Which AI and the
    accounts. Returns None when there are no account rows.
    """
    features, choose, accounts = arrange(rows)
    for row in features:
        if row[0]:
            append_row(menu, row)
        else:
            menu.AppendSeparator()
    if extra is not None:
        extra(menu)
    if choose:
        if menu.GetMenuItemCount():
            menu.AppendSeparator()
        for row in choose:
            append_row(menu, row)
    if not accounts:
        return None
    sub = new_menu()
    for row in accounts:
        append_row(sub, row)
    if menu.GetMenuItemCount():
        menu.AppendSeparator()
    menu.AppendSubMenu(sub, ACCOUNTS_TITLE)
    return sub
