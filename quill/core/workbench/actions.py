"""What can be done to each row type: the context menus and the Item menu, as data.

One :class:`ActionRow` per command a row type offers, in menu order. The
context menu of a row is its rows in order, the first being the default (what
Enter does), the last being Properties; when there are more than about eight,
the rest go under a More submenu (GitHub PRD section 5). The same rows, in the
same order, are the Item menu, so More never hides anything that only a
right-click could reach.

Provider-neutral: GitHub fills an :class:`ActionTable` in
``quill/core/github/item_actions.py``; WordPress will fill its own.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from enum import IntEnum, StrEnum

from quill.core.workbench import WorkbenchSpecError

__all__ = [
    "MENU_TOP_LIMIT",
    "PROPERTIES_COMMAND",
    "ActionRow",
    "ActionScope",
    "ActionTable",
    "Tier",
    "split_for_menu",
]

MENU_TOP_LIMIT = 8
"""Rows a context menu shows before the rest go under More (More counts as one)."""

PROPERTIES_COMMAND = "workbench.properties"
"""The engine's own Properties command; a provider may alias it with its own id."""


class Tier(IntEnum):
    """How much a command changes, which decides how it is confirmed.

    0 reads, 1 organizes (local or easily undone), 2 writes to the service,
    3 deletes or cannot be undone (always asks first, never a bare key).
    """

    READ = 0
    ORGANIZE = 1
    WRITE = 2
    DESTRUCTIVE = 3


class ActionScope(StrEnum):
    """What a command acts on. A row's context menu holds only ``ITEM`` rows."""

    ITEM = "item"
    VIEW = "view"
    REPOSITORY = "repository"
    ACCOUNT = "account"
    APP = "app"


@dataclass(frozen=True)
class ActionRow:
    """One command on one row type's menu.

    *requirement* names what the command needs ("" for nothing,
    ``"sign_in"``, ``"push"`` and so on); the window greys a row whose need
    is not met and its help says why.
    """

    command_id: str
    label: str
    tier: Tier = Tier.READ
    requirement: str = ""
    help: str = ""
    default: bool = False
    scope: ActionScope = ActionScope.ITEM


def split_for_menu[T](rows: Sequence[T], limit: int = MENU_TOP_LIMIT) -> tuple[list[T], list[T]]:
    """Split *rows* into what the menu shows and what goes under More.

    At most *limit* entries show, More among them, so a menu longer than
    *limit* keeps ``limit - 1`` rows on top. A menu that would put a single
    row under More keeps it on top instead: a submenu of one is a detour.
    """
    if limit < 2:
        raise WorkbenchSpecError(f"A menu needs room for at least two rows, not {limit}.")
    if len(rows) <= limit:
        return list(rows), []
    return list(rows[: limit - 1]), list(rows[limit - 1 :])


class ActionTable:
    """Every row type's ordered rows, checked against the context-menu rules.

    Construction enforces what holds for every provider: each row type has
    rows, exactly one default and it comes first, every row is item-scoped,
    no command appears twice for one row type, and the last row is
    Properties. Provider rules (GitHub's Codespaces placement, say) are
    tested next to the provider's table.
    """

    def __init__(
        self,
        rows: Mapping[str, Sequence[ActionRow]],
        *,
        properties_command: str = PROPERTIES_COMMAND,
    ) -> None:
        self._rows = {kind: tuple(entries) for kind, entries in rows.items()}
        self.properties_command = properties_command
        for kind, entries in self._rows.items():
            self._check(kind, entries)

    def _check(self, kind: str, entries: tuple[ActionRow, ...]) -> None:
        if not entries:
            raise WorkbenchSpecError(f"Row type {kind!r} has no actions.")
        defaults = [row for row in entries if row.default]
        if len(defaults) != 1 or not entries[0].default:
            raise WorkbenchSpecError(f"Row type {kind!r} must start with its one default action.")
        if entries[-1].command_id != self.properties_command:
            raise WorkbenchSpecError(f"Row type {kind!r} must end with Properties.")
        seen: set[str] = set()
        for row in entries:
            if row.scope is not ActionScope.ITEM:
                raise WorkbenchSpecError(
                    f"{row.command_id} is {row.scope} scoped and cannot sit on a {kind!r} row."
                )
            if row.command_id in seen:
                raise WorkbenchSpecError(f"{row.command_id} appears twice on {kind!r}.")
            seen.add(row.command_id)

    @property
    def row_types(self) -> tuple[str, ...]:
        return tuple(self._rows)

    def rows_for(self, kind: str) -> tuple[ActionRow, ...]:
        """The rows for *kind*, in menu order (``KeyError`` for an unknown type)."""
        return self._rows[kind]

    def default_for(self, kind: str) -> ActionRow:
        """What Enter does on a *kind* row."""
        return self._rows[kind][0]

    def menu_for(
        self, kind: str, limit: int = MENU_TOP_LIMIT
    ) -> tuple[list[ActionRow], list[ActionRow]]:
        """The context menu for *kind*: (rows shown, rows under More).

        Properties stays the last row shown even when More is needed, so it
        is always one arrow press up from the bottom of the menu.
        """
        entries = list(self._rows[kind])
        properties = entries.pop()
        top, more = split_for_menu(entries, limit - 1)
        return [*top, properties], more

    def commands(self) -> frozenset[str]:
        """Every command id any row type offers."""
        return frozenset(row.command_id for rows in self._rows.values() for row in rows)

    def row_types_offering(self, command_id: str) -> tuple[str, ...]:
        """The row types whose menus offer *command_id*."""
        return tuple(
            kind
            for kind, rows in self._rows.items()
            if any(row.command_id == command_id for row in rows)
        )

    def labels(self, kind: str) -> Iterable[str]:
        return (row.label for row in self._rows[kind])
