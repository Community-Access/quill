"""The Practice Site's own commands, for its context menus and Tools > Practice Site.

Jeff, 2026-11-23: starting the Practice Site and then not finding it in New
Page was the whole lesson's first five minutes. Start now connects it, and
Start, Stop, Connect, Reset and Make It My Default Site are on the context
menu of everything that is the Practice Site:

- its rows in the Practice Site list (:data:`PRACTICE_ROW_KIND`);
- its row in the Sites list (:data:`PRACTICE_SITE_KIND`);
- the Practice Site node in the tree, and its own node under Sites
  (:data:`PRACTICE_NODE_KIND`, :data:`PRACTICE_SITE_NODE_KIND`).

Each is also in Tools > Practice Site (:data:`PRACTICE_SUB`), so every one has
a keyboard route outside a context menu too. None has a chord of its own:
:data:`KEYLESS` says why (family rule 8). Every one changes only this
computer, so each is READ for the access check, like Tools > Practice Site
itself; Reset asks first all the same. Wx-free.
"""

from __future__ import annotations

from collections.abc import Sequence

from quill.core.workbench.actions import ActionRow, Tier
from quill.core.workbench.menus import MenuRow, MenuSub

__all__ = [
    "KEYLESS",
    "PRACTICE_NODE_KIND",
    "PRACTICE_ROWS",
    "PRACTICE_ROW_KIND",
    "PRACTICE_SITE_KIND",
    "PRACTICE_SITE_NODE_KIND",
    "PRACTICE_SUB",
    "PRACTICE_VERBS",
    "practice_menus",
]

PRACTICE_ROW_KIND = "practice_fact"
PRACTICE_SITE_KIND = "practice_site"
PRACTICE_NODE_KIND = "practice_node"
PRACTICE_SITE_NODE_KIND = "practice_site_node"


def command(verb: str) -> str:
    """The Workbench command id (here, not imported: the menu bar imports this module)."""
    return f"wordpress.workbench.{verb}"


#: verb, label, help: in menu order, the order a lesson meets them.
_ROWS: tuple[tuple[str, str, str], ...] = (
    (
        "practice_start",
        "Start the Practice Site",
        "Starts the WordPress site on this computer and connects it, so it is under Sites.",
    ),
    (
        "practice_stop",
        "Stop the Practice Site",
        "Stops it. What is on it stays for the next start.",
    ),
    (
        "practice_connect",
        "Connect It as Practice Site",
        "Connects it under Sites, for when starting it could not.",
    ),
    (
        "practice_default",
        "Make It My Default Site",
        "New Page and New Post start on the Practice Site until you choose another default.",
    ),
    (
        "practice_reset",
        "Reset the Practice Site...",
        "Deletes everything on it, after you confirm. Your real sites are not touched.",
    ),
)

PRACTICE_VERBS: tuple[str, ...] = tuple(verb for verb, _label, _help in _ROWS)

PRACTICE_ROWS: tuple[ActionRow, ...] = tuple(
    ActionRow(command(verb), label, Tier.READ, "", help_text) for verb, label, help_text in _ROWS
)


def practice_menus(
    read: ActionRow,
    sheet: ActionRow,
    node_rows: Sequence[ActionRow],
    site_rows: Sequence[ActionRow],
) -> dict[str, tuple[ActionRow, ...]]:
    """The four Practice Site menus, given Read in Full, Properties, a node's and a site's rows.

    Its own commands come straight after the default, so they are on top even
    where the rest of a node's or a site's menu moves under More.
    """
    return {
        PRACTICE_ROW_KIND: (read, *PRACTICE_ROWS, sheet),
        PRACTICE_SITE_KIND: (site_rows[0], *PRACTICE_ROWS, *site_rows[1:]),
        PRACTICE_NODE_KIND: (node_rows[0], *PRACTICE_ROWS, sheet),
        PRACTICE_SITE_NODE_KIND: (node_rows[0], *PRACTICE_ROWS, *node_rows[1:]),
    }


#: Tools > Practice Site: the chooser keeps Ctrl+Alt+P; the rest have letters.
PRACTICE_SUB = MenuSub(
    "&Practice Site",
    (
        MenuRow(
            command("practice"),
            "&All Practice Site Choices...",
            "Ctrl+Alt+P",
            "Start, stop, connect or reset it, and its lesson material.",
        ),
        None,
        MenuRow(command("practice_start"), "&Start the Practice Site", "", _ROWS[0][2]),
        MenuRow(command("practice_stop"), "S&top the Practice Site", "", _ROWS[1][2]),
        MenuRow(command("practice_connect"), "&Connect It as Practice Site", "", _ROWS[2][2]),
        MenuRow(command("practice_default"), "Make It My &Default Site", "", _ROWS[3][2]),
        MenuRow(command("practice_reset"), "&Reset the Practice Site...", "", _ROWS[4][2]),
    ),
    help="The WordPress site on this computer, for learning with nothing at stake.",
)

KEYLESS: dict[str, str] = {
    command("practice_start"): "Ctrl+Alt+P, then Enter, already starts it (rule 9).",
    command("practice_stop"): "Closing the Workbench stops it too; Ctrl+Alt+P has it (rule 9).",
    command("practice_connect"): "Start connects it; this is only for when that failed (rule 9).",
    command("practice_default"): "Chosen once, while learning (rule 9).",
    command("practice_reset"): "Deletes the whole site: never a bare key (rules 4 and 9).",
}
