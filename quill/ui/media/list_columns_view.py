"""Putting a chosen column layout onto a real ``wx.ListCtrl``.

Three small jobs the five configurable lists would otherwise each do their own
way: read the saved layout, build the report columns from it, and fill a row by
column *id* rather than by position. Filling by id is the part that matters --
once columns can be reordered and hidden, ``SetItem(row, 2, ...)`` is a promise
about a position nobody can keep, and the first hidden column silently puts
every value in the wrong cell.

**The layout is cached per app and per data directory.** It is read when a list
is built rather than per row, and a dialog that saves a new layout invalidates
the entry, so the next list built reads the new one. Keying on the data
directory as well as the app means a test that points ``QUILL_DATA_DIR``
somewhere else cannot be handed the previous test's answer.

A layout that will not load is not fatal: every accessor falls back to the
shipped defaults, because a list with its default columns is a working list and
a list with no columns is not.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from quill.core.media.list_columns import Catalogue, ColumnDef, ColumnLayouts

__all__ = [
    "build_columns",
    "columns_for",
    "fill_row",
    "invalidate",
    "layouts_for",
    "reset_cache",
    "set_row",
]

#: (app, data directory) -> the layouts read for it. See the module docstring.
_CACHE: dict[tuple[str, str], ColumnLayouts] = {}


def _catalogue_and_file(app: str) -> tuple[Catalogue, str]:
    """The catalogue and store file name for *app*."""
    if app == "radio":
        from quill.core.radio.list_columns import FILE_NAME, SURFACES

        return SURFACES, FILE_NAME
    from quill.core.podcasts.list_columns import FILE_NAME, SURFACES

    return SURFACES, FILE_NAME


def layouts_for(app: str) -> ColumnLayouts:
    """The saved layouts for *app* (``"radio"`` or ``"cast"``), cached."""
    catalogue, file_name = _catalogue_and_file(app)
    try:
        from quill.core.paths import app_data_dir

        data_dir = app_data_dir()
    except Exception:  # noqa: BLE001 - no data directory is not a reason to have no list
        return ColumnLayouts.defaults(catalogue)
    key = (app, str(data_dir))
    cached = _CACHE.get(key)
    if cached is not None:
        return cached
    try:
        from quill.core.media.list_columns import load_column_layouts

        layouts = load_column_layouts(data_dir, file_name=file_name, catalogue=catalogue)
    except Exception:  # noqa: BLE001 - a preference that will not load is not fatal
        layouts = ColumnLayouts.defaults(catalogue)
    _CACHE[key] = layouts
    return layouts


def invalidate(app: str) -> None:
    """Forget the cached layouts for *app*, after they have been re-saved."""
    for key in [entry for entry in _CACHE if entry[0] == app]:
        del _CACHE[key]


def reset_cache() -> None:
    """Forget every cached layout. For tests that move the data directory."""
    _CACHE.clear()


def columns_for(app: str, surface: str) -> list[ColumnDef]:
    """The columns to build for one list, in the order they will be read."""
    columns = layouts_for(app).columns(surface)
    if columns:
        return columns
    # An empty answer means an unknown surface id -- a coding mistake rather
    # than a preference. Fall back to the shipped catalogue so the list still
    # works while the mistake is found.
    catalogue, _file_name = _catalogue_and_file(app)
    definition = catalogue.get(surface)
    return [column for column in definition.columns if column.default_visible] if definition else []


def build_columns(list_ctrl: Any, columns: Sequence[ColumnDef]) -> None:
    """Replace *list_ctrl*'s report columns with *columns*.

    ``DeleteAllColumns`` first, so this is safe to call again when the layout
    changes while a window is open -- otherwise a re-application would append a
    second set of columns to the first.
    """
    list_ctrl.DeleteAllItems()
    list_ctrl.DeleteAllColumns()
    for index, column in enumerate(columns):
        list_ctrl.InsertColumn(index, column.label, width=column.width)


def fill_row(
    list_ctrl: Any, row: int, columns: Sequence[ColumnDef], values: Mapping[str, str]
) -> None:
    """Insert row *row*, taking each cell from *values* by column id."""
    if not columns:
        return
    list_ctrl.InsertItem(row, values.get(columns[0].id, ""))
    for index, column in enumerate(columns[1:], start=1):
        list_ctrl.SetItem(row, index, values.get(column.id, ""))


def set_row(
    list_ctrl: Any, row: int, columns: Sequence[ColumnDef], values: Mapping[str, str]
) -> None:
    """Update an existing row in place, by column id.

    The in-place counterpart of :func:`fill_row`, for the lists that refresh on
    a tick and must not rebuild (a rebuild moves the cursor out from under
    somebody reading a row).
    """
    for index, column in enumerate(columns):
        list_ctrl.SetItem(row, index, values.get(column.id, ""))
