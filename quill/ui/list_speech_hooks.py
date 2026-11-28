"""How the two Workbenches ask "is a speech template speaking this list?".

The Workbench windows already shape their rows (GitHub's short rows for braille
is one example). These helpers add the List Speech Template step with one
small call each, so the windows change by a few lines and nothing here needs
wx. With no template assigned, every function returns the existing behaviour:

- :func:`speaking_columns` is the one ``row`` column a list shows while a
  template speaks it, or None to keep the list's own columns;
- :func:`spoken_cells` is that column's text for one row, falling back to the
  list's own cells joined, so a row no template covers still reads as before;
- :func:`row_label` is the same for a list box that shows one string a row.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

from quill.core.list_speech.catalog import get_list_type
from quill.core.list_speech.library import resolve
from quill.core.list_speech.speak import SPEECH_COLUMN, speak_row
from quill.core.list_speech.store import load_cached

__all__ = [
    "SPEECH_COLUMN",
    "github_items_columns",
    "row_label",
    "speaking_columns",
    "spoken_cells",
    "wordpress_cells",
    "wordpress_columns",
]

#: The columns that mark GitHub's issues and pull requests list.
_ITEM_MARKERS = frozenset({"number", "title", "state"})


def _any_assigned(list_types: Sequence[str]) -> bool:
    try:
        library = load_cached()
        return any(
            get_list_type(t) is not None and resolve(library, t).template is not None
            for t in list_types
        )
    except Exception:  # noqa: BLE001 - an unreadable file never stops a list opening
        return False


def speaking_columns(list_types: Sequence[str]) -> tuple[str, ...] | None:
    """``("row",)`` when any of *list_types* has a template assigned, else None."""
    return (SPEECH_COLUMN,) if _any_assigned(list_types) else None


def github_items_columns(visible: Sequence[str]) -> tuple[str, ...] | None:
    """The speaking column for GitHub's issues and pull requests list, if one is assigned."""
    if _ITEM_MARKERS <= set(visible):
        return speaking_columns(("github_issues", "github_pulls"))
    return None


def spoken_cells(
    row: Any, source: Sequence[str], cells_for: Callable[[Any, tuple[str, ...]], list[str]]
) -> list[str]:
    """One cell: the row spoken by its template, or the list's own cells joined."""
    try:
        text = speak_row(row)
    except Exception:  # noqa: BLE001 - a bad template never blanks a row
        text = None
    if text:
        return [text]
    return [", ".join(c for c in cells_for(row, tuple(source)) if c)]


def row_label(row: Any, default: str) -> str:
    """The text a one-string-per-row list box shows for *row*."""
    try:
        return speak_row(row) or default
    except Exception:  # noqa: BLE001
        return default


#: The list types a WordPress Workbench node's row type can be spoken under.
_WORDPRESS_LISTS: dict[str, tuple[str, ...]] = {
    "item": ("wordpress_posts",),
    "comment": ("wordpress_comments",),
    "media": ("wordpress_media",),
    "user": ("wordpress_users",),
}


def wordpress_columns(window: Any, row_type: str, chosen: tuple[str, ...]) -> tuple[str, ...]:
    """The node's columns, or the one speaking column when a template is assigned."""
    spoken = speaking_columns(_WORDPRESS_LISTS.get(row_type, ()))
    window._speech_source = chosen if spoken else ()
    return spoken or chosen


def wordpress_cells(window: Any, row: Any, columns: tuple[str, ...]) -> list[str]:
    """The speaking column's cell for *row*, or an empty list to use the usual cells."""
    source = getattr(window, "_speech_source", ())
    if columns != (SPEECH_COLUMN,) or not source:
        return []
    return spoken_cells(row, source, lambda r, c: [window.cell_for(r, k) for k in c])
