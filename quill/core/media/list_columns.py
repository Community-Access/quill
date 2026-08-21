"""List columns: what a row says, in the order it says it.

A report-view list is read out column by column. Whoever chose the columns
therefore chose the sentence every row speaks -- and until now that choice was
made once, in code, for everybody. Somebody who never wants to hear a country
heard one on every station; somebody who navigates by network heard it last, or
not at all.

This module is the app-independent half, deliberately the same shape as
:mod:`quill.core.quick_actions`: an app supplies a **catalogue** (surface id ->
the columns that surface can offer, in shipped order) and a store filename, and
gets ordering, hiding, repair and persistence for nothing. Nothing here knows
what a station or an episode is.

Three rules are requirements rather than implementation details:

- **One column is pinned.** Every surface names one column that cannot be
  hidden -- the station's name, the episode's title -- because a row with
  nothing to identify it is a row nobody can use, and a preference that can
  produce one is a preference that can break the app.
- **Hidden is not reordered-to-the-end.** A hidden column is not read at all,
  which is the whole point: on a report list a screen reader speaks every
  column it is given, so the only way to stop hearing something is for the
  column not to exist. Order and visibility are therefore two separate answers,
  not one list with the unwanted part pushed down.
- **Repair on read, always.** A layout saved by a later build can name columns
  this one has never heard of, and one saved by an earlier build is missing
  everything added since. Unknown ids are dropped and missing ones appended, so
  an upgrade, a downgrade, or a settings file carried from another machine can
  never leave somebody in front of a list that reads nothing.

wx-free, strict-typed.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

__all__ = [
    "ColumnDef",
    "ColumnLayouts",
    "SurfaceDef",
    "default_order",
    "load_column_layouts",
    "preview_row",
    "repair_order",
    "save_column_layouts",
]


@dataclass(frozen=True, slots=True)
class ColumnDef:
    """One column: a stable id, the words at the top of it, and what it holds."""

    id: str
    #: The column header. Also what a screen reader set to announce headers
    #: says before the value, so it is written to be heard, not just seen.
    label: str
    #: Shown in the configuration dialog, so the list explains itself without a
    #: manual.
    description: str = ""
    #: The shipped pixel width. A listener's own width changes are the list
    #: control's business, not this record's.
    width: int = 120
    #: True for the column that names the row. It can be reordered but never
    #: hidden -- see the module docstring.
    pinned: bool = False
    #: False for a column the surface can offer but does not show until asked.
    #: Everything a row *could* say is in the catalogue; only some of it is on
    #: by default, because a default list that says everything says nothing.
    default_visible: bool = True


@dataclass(frozen=True, slots=True)
class SurfaceDef:
    """One list a person arrows through, and every column it can offer."""

    id: str
    #: How the surface is named in the configuration dialog's chooser.
    label: str
    columns: tuple[ColumnDef, ...]
    #: One example row, keyed by column id, so the dialog can show the sentence
    #: a row will actually read rather than describing it. A sample is part of
    #: the surface definition because only the surface knows what its rows look
    #: like.
    sample: Mapping[str, str] = field(default_factory=dict)

    def column(self, column_id: str) -> ColumnDef | None:
        for column in self.columns:
            if column.id == column_id:
                return column
        return None

    @property
    def pinned_id(self) -> str:
        """The id of the column that cannot be hidden (the first, by default).

        Falling back to the first column rather than raising means a surface
        whose author forgot to pin one still cannot produce an empty row.
        """
        for column in self.columns:
            if column.pinned:
                return column.id
        return self.columns[0].id if self.columns else ""


#: An app's column catalogue: surface id -> what that surface can show.
Catalogue = Mapping[str, SurfaceDef]


def default_order(catalogue: Catalogue, surface: str) -> list[str]:
    """The shipped column order for one surface (also the Reset target)."""
    definition = catalogue.get(surface)
    return [column.id for column in definition.columns] if definition else []


def default_hidden(catalogue: Catalogue, surface: str) -> list[str]:
    """The columns a surface ships switched off."""
    definition = catalogue.get(surface)
    if definition is None:
        return []
    return [column.id for column in definition.columns if not column.default_visible]


def repair_order(catalogue: Catalogue, surface: str, ids: Sequence[str]) -> list[str]:
    """A saved order made safe for this build.

    Unknown ids are dropped, duplicates collapse to their first appearance, and
    every column missing from the list is appended in its shipped position -- so
    a column added in a later release turns up at the end of an existing
    listener's rows rather than not at all.
    """
    definition = catalogue.get(surface)
    if definition is None:
        return []
    known = {column.id for column in definition.columns}
    seen: set[str] = set()
    ordered: list[str] = []
    for column_id in ids:
        if column_id in known and column_id not in seen:
            seen.add(column_id)
            ordered.append(column_id)
    ordered.extend(
        column_id for column_id in default_order(catalogue, surface) if column_id not in seen
    )
    return ordered


def repair_hidden(catalogue: Catalogue, surface: str, ids: Sequence[str]) -> list[str]:
    """A saved hidden-set made safe for this build.

    Unknown ids are dropped, the pinned column is never hidden however the file
    arrived, and a set that would hide *everything* is refused wholesale: a list
    whose rows read nothing at all is not a preference anybody expressed.
    """
    definition = catalogue.get(surface)
    if definition is None:
        return []
    known = {column.id for column in definition.columns}
    pinned = definition.pinned_id
    hidden = [
        column_id for column_id in dict.fromkeys(ids) if column_id in known and column_id != pinned
    ]
    if len(hidden) >= len(known):  # pragma: no cover - pinned makes this unreachable
        return default_hidden(catalogue, surface)
    return hidden


def preview_row(columns: Sequence[ColumnDef], sample: Mapping[str, str]) -> str:
    """The sentence a row of *columns* reads out, given one sample row.

    Comma-separated because that is how a screen reader runs a report row's
    cells together, so the preview is the announcement rather than a diagram of
    it. Columns the sample has nothing for are skipped rather than shown empty:
    an empty cell is silence, and a preview that shows a gap the listener will
    never hear is a preview that lies.
    """
    parts = [sample.get(column.id, "").strip() for column in columns]
    return ", ".join(part for part in parts if part)


@dataclass(slots=True)
class ColumnLayouts:
    """One order and one hidden-set per surface, plus the catalogue they mean.

    The catalogue travels with the layouts rather than being looked up globally,
    so two apps' layouts can exist in one process without either being able to
    repair itself against the other's columns.
    """

    catalogue: Catalogue
    orders: dict[str, list[str]]
    hidden: dict[str, list[str]]

    @classmethod
    def defaults(cls, catalogue: Catalogue) -> ColumnLayouts:
        """Every surface as shipped."""
        return cls(
            catalogue=catalogue,
            orders={surface: default_order(catalogue, surface) for surface in catalogue},
            hidden={surface: default_hidden(catalogue, surface) for surface in catalogue},
        )

    def order(self, surface: str) -> list[str]:
        """The repaired column order for *surface*, hidden columns included."""
        return repair_order(self.catalogue, surface, self.orders.get(surface, []))

    def hidden_ids(self, surface: str) -> list[str]:
        """The repaired set of columns *surface* does not show."""
        return repair_hidden(self.catalogue, surface, self.hidden.get(surface, []))

    def columns(self, surface: str) -> list[ColumnDef]:
        """The columns to build, in order: what a row of *surface* will say."""
        definition = self.catalogue.get(surface)
        if definition is None:
            return []
        hidden = set(self.hidden_ids(surface))
        by_id = {column.id: column for column in definition.columns}
        return [
            by_id[column_id]
            for column_id in self.order(surface)
            if column_id not in hidden and column_id in by_id
        ]

    def all_columns(self, surface: str) -> list[tuple[ColumnDef, bool]]:
        """Every column of *surface* in order, each with whether it is shown.

        For the configuration dialog, which has to offer the hidden ones too.
        """
        definition = self.catalogue.get(surface)
        if definition is None:
            return []
        hidden = set(self.hidden_ids(surface))
        by_id = {column.id: column for column in definition.columns}
        return [
            (by_id[column_id], column_id not in hidden)
            for column_id in self.order(surface)
            if column_id in by_id
        ]

    def is_visible(self, surface: str, column_id: str) -> bool:
        return column_id not in set(self.hidden_ids(surface))

    def set_order(self, surface: str, ids: Sequence[str]) -> None:
        if surface in self.catalogue:
            self.orders[surface] = repair_order(self.catalogue, surface, ids)

    def set_visible(self, surface: str, column_id: str, visible: bool) -> None:
        """Show or hide one column. Hiding the pinned column does nothing."""
        if surface not in self.catalogue:
            return
        hidden = self.hidden_ids(surface)
        if visible:
            hidden = [entry for entry in hidden if entry != column_id]
        elif column_id not in hidden:
            hidden = [*hidden, column_id]
        self.hidden[surface] = repair_hidden(self.catalogue, surface, hidden)

    def preview(self, surface: str) -> str:
        """What one row of *surface* will read out under the current layout."""
        definition = self.catalogue.get(surface)
        if definition is None:
            return ""
        return preview_row(self.columns(surface), definition.sample)

    def reset(self, surface: str) -> None:
        if surface in self.catalogue:
            self.orders[surface] = default_order(self.catalogue, surface)
            self.hidden[surface] = default_hidden(self.catalogue, surface)

    def copy(self) -> ColumnLayouts:
        """An independent copy, for a dialog that has to be cancellable."""
        return ColumnLayouts(
            catalogue=self.catalogue,
            orders={surface: list(ids) for surface, ids in self.orders.items()},
            hidden={surface: list(ids) for surface, ids in self.hidden.items()},
        )

    def to_dict(self) -> dict[str, dict[str, list[str]]]:
        return {
            surface: {"order": self.order(surface), "hidden": self.hidden_ids(surface)}
            for surface in self.catalogue
        }

    @classmethod
    def from_dict(cls, catalogue: Catalogue, data: object) -> ColumnLayouts:
        layouts = cls.defaults(catalogue)
        if not isinstance(data, dict):
            return layouts
        for surface in catalogue:
            raw = data.get(surface)
            if not isinstance(raw, dict):
                continue
            order = raw.get("order")
            if isinstance(order, list):
                layouts.set_order(surface, [str(entry) for entry in order])
            hidden = raw.get("hidden")
            if isinstance(hidden, list):
                layouts.hidden[surface] = repair_hidden(
                    catalogue, surface, [str(entry) for entry in hidden]
                )
        return layouts


def load_column_layouts(data_dir: Path, *, file_name: str, catalogue: Catalogue) -> ColumnLayouts:
    """Read the saved layouts. An absent or broken file reads as the default.

    A store of its own rather than fields on an app's settings record, for the
    reason ``load_quick_actions`` gives: no per-item override ever wants its own
    column layout, and putting several lists in the settings would push them
    through every clone of it.
    """
    try:
        raw = json.loads((data_dir / file_name).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ColumnLayouts.defaults(catalogue)
    return ColumnLayouts.from_dict(catalogue, raw)


def save_column_layouts(data_dir: Path, layouts: ColumnLayouts, *, file_name: str) -> None:
    """Persist the layouts atomically."""
    from quill.core.storage import write_json_atomic

    write_json_atomic(data_dir / file_name, layouts.to_dict())
