"""Sort By Column and Group By Column for every Workbench list (GitHub PRD 17.4).

The Issues lists have their own View > Sort By and Group By rows, which ask
GitHub for an order and group on an issue's labels, milestone or author.
Every other list (branches, tags, releases, workflows, runs, discussions,
notifications, alerts, people, teams, repositories, projects) is ordered and
grouped here, over its loaded rows, by one of its own fields:

- a list with several columns sorts and groups by any of them, by the text
  the column shows;
- a one-column list (an Explore list of results) by its name, repository,
  kind or last update, which every such row carries.

The choice is remembered per account per list, in the same store as the
list's columns (:class:`quill.core.github.saved_items.GitHubSavedItems`).

wx-free and strict-typed.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from quill.core.github.filter_menu import group_rows

__all__ = [
    "ONE_COLUMN_FIELDS",
    "ColumnOrder",
    "field_label",
    "fields_for",
    "group_by_field",
    "order_rows",
    "sort_store_key",
    "group_store_key",
    "text_of",
]

#: What a one-column (Explore) row can be sorted and grouped by.
ONE_COLUMN_FIELDS: tuple[str, ...] = ("name", "repository", "kind", "updated")

_NUMBER = re.compile(r"^-?\d+(\.\d+)?$")


@dataclass(frozen=True)
class ColumnOrder:
    """A list's chosen order: a field, and whether it runs from the end."""

    field: str = ""
    descending: bool = False

    @property
    def chosen(self) -> bool:
        return bool(self.field)

    def stored(self) -> list[str]:
        return [self.field, "descending" if self.descending else "ascending"] if self.field else []

    @classmethod
    def from_stored(cls, saved: Sequence[str]) -> ColumnOrder:
        if not saved or not saved[0]:
            return cls()
        return cls(saved[0], len(saved) > 1 and saved[1] == "descending")

    def words(self) -> str:
        if not self.field:
            return "as GitHub sends it"
        end = "last to first" if self.descending else "first to last"
        return f"by {field_label(self.field).lower()}, {end}"


def sort_store_key(loader: str) -> str:
    """Where a list's Sort By Column choice is kept, beside its columns."""
    return f"workbench-sort:{loader}"


def group_store_key(loader: str) -> str:
    """Where a list's Group By Column choice is kept, beside its columns."""
    return f"workbench-group:{loader}"


def field_label(name: str) -> str:
    """A field's name as the Columns chooser writes it: "run_number" is "Run number"."""
    return name.replace("_", " ").capitalize()


def fields_for(columns: Sequence[str]) -> tuple[str, ...]:
    """The fields a list sorts and groups by: its columns, or the one-column fields."""
    named = tuple(c for c in columns if c and c != "result")
    return named if len(named) > 1 else ONE_COLUMN_FIELDS


def text_of(row: object, field: str, cell: Callable[[object, str], str]) -> str:
    """*row*'s text for *field*: its cell, or for a one-column row its own attribute."""
    if field in ONE_COLUMN_FIELDS and hasattr(row, "label") and hasattr(row, "kind"):
        value = {
            "name": getattr(row, "title", "") or getattr(row, "label", ""),
            "repository": getattr(row, "repo", ""),
            "kind": getattr(row, "kind", ""),
            "updated": getattr(row, "updated_at", ""),
        }[field]
        return str(value or "")
    return cell(row, field)


def _key(text: str) -> tuple[int, float, str]:
    """Numbers as numbers, words without case, and an empty value last."""
    value = text.strip()
    if not value:
        return (2, 0.0, "")
    if _NUMBER.match(value):
        return (0, float(value), "")
    return (1, 0.0, value.casefold())


def order_rows[T](rows: Sequence[T], order: ColumnOrder, value: Callable[[T], str]) -> list[T]:
    """*rows* in *order* (stable), an empty value last either way; unchanged when unchosen."""
    if not order.chosen:
        return list(rows)
    filled = [row for row in rows if value(row).strip()]
    empty = [row for row in rows if not value(row).strip()]
    filled.sort(key=lambda row: _key(value(row)), reverse=order.descending)
    return filled + empty


def group_by_field[T](rows: Sequence[T], value: Callable[[T], str]) -> list[tuple[str, list[T]]]:
    """Groups for the tree, "None" last; a date groups by its day."""

    def values(row: T) -> list[str]:
        text = value(row).strip()
        if re.match(r"^\d{4}-\d{2}-\d{2}T", text):
            text = text[:10]
        return [text] if text else []

    return group_rows(rows, "", values)
