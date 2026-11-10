"""Properties sheets as data: pages, fields, mixed values, and what a save changes.

Alt+Enter on anything opens its sheet (GitHub PRD section 15). A provider
describes each object's sheet once, as a :class:`SheetSpec`; the window
builds a notebook from it, one page per :class:`PageSpec`, every fact a
focusable, labelled control. This module also does the arithmetic a sheet
needs and no window should: the value a field shows across several selected
objects ("Mixed" when they differ), the list of fields a save would send (only
the ones changed), the fields somebody else changed meanwhile, and the sheet
as plain text for Copy as Text.

A check list over several objects is three-state (section 15.2): each choice
is on all of them, none, or "on 3 of 5". What the person does to it is a
:class:`ListDelta` (added and removed), never a replacement, so a label that
was on only some of the items stays on exactly those unless it was touched
(:func:`list_states`, :func:`apply_delta`).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Final

from quill.core.workbench import WorkbenchSpecError

__all__ = [
    "MIXED",
    "FieldChange",
    "FieldKind",
    "FieldSpec",
    "ListDelta",
    "PageSpec",
    "SheetSpec",
    "SheetState",
    "Value",
    "apply_delta",
    "as_text",
    "changes",
    "conflicts",
    "list_states",
    "merge_values",
]


@dataclass(frozen=True)
class ListDelta:
    """What a three-state check list did across several objects: added and removed."""

    added: tuple[str, ...] = ()
    removed: tuple[str, ...] = ()

    def __bool__(self) -> bool:
        return bool(self.added or self.removed)


Value = str | int | bool | tuple[str, ...] | ListDelta | None


class _Mixed:
    """The value of a field that differs across the selected objects."""

    _instance: _Mixed | None = None

    def __new__(cls) -> _Mixed:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self) -> str:
        return "MIXED"

    def __str__(self) -> str:
        return "Mixed"


MIXED: Final = _Mixed()


class FieldKind(StrEnum):
    TEXT = "text"
    MULTILINE = "multiline"
    NUMBER = "number"
    CHECK = "check"
    CHOICE = "choice"
    LIST = "list"
    DATE = "date"
    LINK = "link"
    CHECKLIST = "checklist"
    TABLE = "table"


@dataclass(frozen=True)
class FieldSpec:
    """One fact on a sheet.

    A *readonly* field is shown as a read-only text box, never bare static
    text, so Tab reaches it. *requirement* names what changing it needs
    (``"triage"``); the window makes the field read-only, with *help*
    saying why, when the person lacks it.
    """

    key: str
    label: str
    kind: FieldKind = FieldKind.TEXT
    readonly: bool = False
    requirement: str = ""
    help: str = ""
    choices: tuple[str, ...] = ()
    create: str = ""
    """A picker's New... button ("New Label..."): creates the thing and uses it at once."""


@dataclass(frozen=True)
class PageSpec:
    key: str
    title: str
    fields: tuple[FieldSpec, ...]


@dataclass(frozen=True)
class SheetSpec:
    """An object kind's sheet. The first page is always General."""

    kind: str
    title: str
    pages: tuple[PageSpec, ...]

    def __post_init__(self) -> None:
        if not self.pages or self.pages[0].key != "general":
            raise WorkbenchSpecError(f"The {self.kind} sheet must open on its General page.")
        keys = [spec.key for page in self.pages for spec in page.fields]
        if len(keys) != len(set(keys)):
            raise WorkbenchSpecError(f"The {self.kind} sheet names a field twice.")

    def fields(self) -> tuple[FieldSpec, ...]:
        return tuple(spec for page in self.pages for spec in page.fields)

    def field(self, key: str) -> FieldSpec:
        for spec in self.fields():
            if spec.key == key:
                return spec
        raise KeyError(key)

    def heading(self, name: str, where: str = "") -> str:
        """The sheet's window title: "Issue #42 Properties - owner/name"."""
        title = f"{name} Properties"
        return f"{title} - {where}" if where else title


@dataclass(frozen=True)
class FieldChange:
    key: str
    label: str
    before: object
    after: Value


def merge_values(objects: Sequence[Mapping[str, Value]]) -> dict[str, Value | _Mixed]:
    """What each field shows for several objects at once: the value, or :data:`MIXED`."""
    if not objects:
        return {}
    merged: dict[str, Value | _Mixed] = {}
    keys = {key for values in objects for key in values}
    for key in keys:
        seen = {values.get(key) for values in objects}
        merged[key] = seen.pop() if len(seen) == 1 else MIXED
    return merged


def list_states(objects: Sequence[Mapping[str, Value]], key: str) -> dict[str, int]:
    """For a list field over several objects: how many of them have each value."""
    counts: dict[str, int] = {}
    for values in objects:
        found = values.get(key)
        for item in found if isinstance(found, tuple) else ():
            counts[item] = counts.get(item, 0) + 1
    return counts


def apply_delta(current: Sequence[str], delta: ListDelta) -> tuple[str, ...]:
    """*current* with *delta* applied: removals first, then additions, order kept."""
    removed = set(delta.removed)
    kept = [item for item in current if item not in removed]
    kept.extend(item for item in delta.added if item not in kept)
    return tuple(kept)


def changes(
    sheet: SheetSpec,
    loaded: Mapping[str, Value | _Mixed],
    edited: Mapping[str, Value | _Mixed],
) -> tuple[FieldChange, ...]:
    """The fields a save would send: editable, and different from what was loaded.

    A field left on :data:`MIXED` is untouched, so it is never sent.
    """
    found: list[FieldChange] = []
    for spec in sheet.fields():
        if spec.readonly or spec.key not in edited:
            continue
        after = edited[spec.key]
        if isinstance(after, _Mixed) or after == loaded.get(spec.key):
            continue
        if isinstance(after, ListDelta) and not after:
            continue
        found.append(FieldChange(spec.key, spec.label, loaded.get(spec.key), after))
    return tuple(found)


def conflicts(
    pending: Sequence[FieldChange],
    loaded: Mapping[str, Value | _Mixed],
    current: Mapping[str, Value],
) -> tuple[FieldChange, ...]:
    """The pending changes to fields somebody else changed since the sheet loaded.

    Each result's *before* is the value now on the service, so the window can
    say "Changed since you opened this: milestone is now 2027.2" and offer
    Keep Theirs or Use Mine. Fields nobody else touched are not listed.
    """
    return tuple(
        FieldChange(change.key, change.label, current.get(change.key), change.after)
        for change in pending
        if current.get(change.key) != loaded.get(change.key)
    )


def _say(value: object) -> str:
    if isinstance(value, ListDelta):
        parts = [f"add {', '.join(value.added)}"] if value.added else []
        parts += [f"remove {', '.join(value.removed)}"] if value.removed else []
        return "; ".join(parts) or "no change"
    if isinstance(value, tuple):
        return ", ".join(value) if value else "none"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if value is None or value == "":
        return "none"
    return str(value)


def as_text(sheet: SheetSpec, values: Mapping[str, object], *, title: str = "") -> str:
    """Every page of the sheet as plain text, for Copy as Text."""
    lines = [title or sheet.title]
    for page in sheet.pages:
        lines.append("")
        lines.append(page.title)
        for spec in page.fields:
            lines.append(f"{spec.label}: {_say(values.get(spec.key))}")
    return "\n".join(lines)


@dataclass
class SheetState:
    """A sheet's values while it is open: what loaded, and what the person typed."""

    sheet: SheetSpec
    loaded: dict[str, Value | _Mixed] = field(default_factory=dict)
    edited: dict[str, Value | _Mixed] = field(default_factory=dict)

    def set(self, key: str, value: Value) -> None:
        if self.sheet.field(key).readonly:
            raise WorkbenchSpecError(f"{key} is read-only on the {self.sheet.kind} sheet.")
        self.edited[key] = value

    def pending(self) -> tuple[FieldChange, ...]:
        return changes(self.sheet, self.loaded, {**self.loaded, **self.edited})
