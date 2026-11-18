"""Every command as one list, in the order the reader chooses.

EdSharp lists all its commands three ways -- the order the menus show them,
by name, and by key -- because each answers a different question: "what is
in the Edit menu", "is there a command called that", and "what does
Ctrl+Shift+K do". QUILL's Key Cheatsheet had only the name order; this is the
other two, as plain text a screen reader reads line by line (complete.md
Part 4, from EdSharp's history, 2026-11).

No ``wx``; strict-typed.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass

__all__ = ["LABELS", "ORDERS", "CommandRow", "command_list_text", "menu_of"]

ORDERS: tuple[str, ...] = ("menu", "name", "key")
LABELS: dict[str, str] = {
    "menu": "Menu order",
    "name": "Name order",
    "key": "Key order",
}

#: The editor's top-level menus, in the order its menu bar shows them; a
#: command's id names the menu it lives in ("edit.find" is in Edit).
_MENUS: tuple[tuple[str, str], ...] = (
    ("file", "File"),
    ("edit", "Edit"),
    ("view", "View"),
    ("insert", "Insert"),
    ("format", "Format"),
    ("navigate", "Navigate"),
    ("tools", "Tools"),
    ("help", "Help"),
)
_MENU_NAMES = dict(_MENUS)
_MENU_RANK = {key: rank for rank, (key, _name) in enumerate(_MENUS)}


@dataclass(frozen=True, slots=True)
class CommandRow:
    command_id: str
    title: str
    key: str


def menu_of(command_id: str) -> str:
    """The menu a command is listed under: its id's first part, named."""
    prefix = command_id.split(".", 1)[0]
    return _MENU_NAMES.get(prefix, prefix.replace("_", " ").title() or "Other")


def _menu_sort(row: CommandRow) -> tuple[int, str, str]:
    prefix = row.command_id.split(".", 1)[0]
    return (_MENU_RANK.get(prefix, len(_MENU_RANK)), menu_of(row.command_id), row.title.lower())


def _key_sort(row: CommandRow) -> tuple[int, str, str]:
    return (0 if row.key else 1, row.key.lower(), row.title.lower())


def command_list_text(
    commands: Iterable[tuple[str, str]],
    key_for: Callable[[str], str],
    *,
    order: str = "name",
    query: str = "",
) -> str:
    """The list as text, one command a line ("Find: Ctrl+F").

    *commands* are ``(id, title)`` pairs; *key_for* gives a command's key or
    "". *query* keeps only commands whose name or key contains it. In menu
    order each menu starts with its own name on a line ("Edit menu:"), so a
    reader can jump between menus by searching for "menu:".
    """
    wanted = query.strip().lower()
    rows = [CommandRow(cid, title, key_for(cid) or "") for cid, title in commands]
    if wanted:
        rows = [row for row in rows if wanted in row.title.lower() or wanted in row.key.lower()]
    if not rows:
        return "No matching commands."
    order = order if order in ORDERS else "name"
    if order == "key":
        rows.sort(key=_key_sort)
    elif order == "menu":
        rows.sort(key=_menu_sort)
    else:
        rows.sort(key=lambda row: row.title.lower())
    lines: list[str] = []
    heading = ""
    for row in rows:
        if order == "menu" and menu_of(row.command_id) != heading:
            heading = menu_of(row.command_id)
            if lines:
                lines.append("")
            lines.append(f"{heading} menu:")
        if order == "key":
            lines.append(f"{row.key or '(no key)'}: {row.title}")
        else:
            lines.append(f"{row.title}: {row.key or '(no key)'}")
    return "\n".join(lines)
