"""Issue types and issue fields on the Workbench's own issue rows (complete.md 1.3).

Across Repositories already read an issue's type and its owner's fields
(:mod:`quill.core.github.across_issue_fields`). This module puts the same
typed values on every Issues list, its details, its filters and an issue's
Properties sheet, through those same readers:

- **Rows:** the issue type comes with the list row (REST ``type``), at no
  cost. The fields are one request an issue, so they are read only when the
  **Issue fields** column is chosen (View > Columns..., Ctrl+Shift+U), at
  most :data:`~quill.core.github.across_issue_fields.MAX_FIELD_READS` a list.
- **Typed:** a date is a date, a number a number, a single select a choice
  by name, a multiple select its choices, and text is text
  (:meth:`~quill.core.github.across_issue_fields.FieldValue.typed`).
- **States kept apart:** a value, empty (set to nothing), not set, hidden
  from you, a field type QUILL does not edit yet (read only), and unreadable
  (the read failed) each have their own words in a cell, in details and on
  the sheet, so a missing permission never looks like an unset field.
- **Filters:** GitHub's issue search answers ``type:Bug`` and
  ``field.priority:high`` itself, so Show Only on a type or field cell writes
  those qualifiers into the one filter box (:func:`field_choices`).
- **Properties:** an issue's sheet gains an Issue Fields page with one
  read-only field per field, of its own kind (:func:`with_field_page`);
  Issue Fields... on the row sets or clears one.

wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import replace
from typing import Any

from quill.core.github.across_issue_fields import (
    MAX_FIELD_READS,
    FieldValue,
    IssueExtras,
    read_issue_extras,
)
from quill.core.workbench.properties import FieldKind, FieldSpec, PageSpec, SheetSpec, Value

__all__ = [
    "FIELD_PAGE",
    "ISSUE_FIELD_COLUMNS",
    "STATE_KEY",
    "IssueExtras",
    "cell",
    "detail_lines",
    "field_choices",
    "issue_type_of",
    "read_row_fields",
    "sheet_values",
    "with_field_page",
]

#: Columns an Issues list offers but does not show until chosen: the fields
#: cost a request an issue, and the type column is new beside Kind.
ISSUE_FIELD_COLUMNS = ("issue_type", "issue_fields")
FIELD_PAGE = "fields"
STATE_KEY = "issue_fields_state"
_INDEX_KEY = "issue_fields_index"
_PREFIX = "issue_field:"

_KINDS = {
    "date": FieldKind.DATE,
    "number": FieldKind.NUMBER,
    "single_select": FieldKind.CHOICE,
    "multi_select": FieldKind.LIST,
    "text": FieldKind.TEXT,
}
_KIND_WORDS = {
    "date": "A date",
    "number": "A number",
    "single_select": "One choice",
    "multi_select": "Several choices",
    "text": "Text",
}


def issue_type_of(row: Any) -> str:
    """An issue's type name from a PyGithub row, without a request.

    ``raw_data`` is the JSON GitHub sent with the list, so reading ``type``
    from it never makes PyGithub fetch the issue again; "" is no type.
    """
    raw = getattr(row, "raw_data", None)
    kind = raw.get("type") if isinstance(raw, Mapping) else getattr(row, "type", None)
    if isinstance(kind, Mapping):
        kind = kind.get("name")
    name = getattr(kind, "name", kind)
    return name if isinstance(name, str) else ""


def _is_issue(item: object) -> bool:
    return hasattr(item, "issue_fields") and not getattr(item, "is_pr", True)


def _fields_words(extras: IssueExtras | None) -> str:
    """The Issue fields cell: each field's short form, or why there are none."""
    if extras is None:
        return "not read"
    state = extras.fields_state
    if state == "hidden":
        return "hidden from you"
    if state == "unavailable":
        return f"unreadable: {extras.reason or 'unknown error'}"
    if state == "not_read":
        return f"not read, past the first {MAX_FIELD_READS}"
    if not extras.fields:
        return "none defined"
    return "; ".join(value.short() for value in extras.fields)


def cell(item: object, column: str) -> str | None:
    """The Issue type or Issue fields cell; None for any other column."""
    if column not in ISSUE_FIELD_COLUMNS:
        return None
    if not _is_issue(item):
        return ""
    if column == "issue_type":
        return str(getattr(item, "issue_type", "")) or "no type"
    return _fields_words(getattr(item, "issue_fields", None))


def detail_lines(item: object) -> list[str]:
    """An issue's type and fields for the details pane; nothing for a pull request."""
    if not _is_issue(item):
        return []
    extras = getattr(item, "issue_fields", None)
    if isinstance(extras, IssueExtras):
        return extras.detail_lines()
    return [f"Issue type: {str(getattr(item, 'issue_type', '')) or 'none'}"]


def field_choices(item: object) -> list[tuple[str, str]]:
    """Show Only and Hide for each field value: ``field.priority:High``, as GitHub searches.

    A field whose name holds a space is left out: GitHub's search wants it
    quoted in a way the one filter box cannot yet carry.
    """
    extras = getattr(item, "issue_fields", None)
    if not _is_issue(item) or not isinstance(extras, IssueExtras):
        return []
    found: list[tuple[str, str]] = []
    for value in extras.fields:
        if value.state != "value" or " " in value.name:
            continue
        typed = value.typed()
        for one in typed if isinstance(typed, tuple) else (value.shown(),):
            text = f'"{one}"' if " " in one else one
            found.append((f"field.{value.name.lower()}:{text}", f"{value.name} {one}"))
    return found


def read_row_fields(api: Any, repository: str, rows: Sequence[object]) -> list[object]:
    """*rows* with each issue's fields read (off the UI thread); pull requests as they were."""
    issues = [row for row in rows if _is_issue(row)]
    if not issues:
        return list(rows)
    types = {int(getattr(row, "number", 0)): str(getattr(row, "issue_type", "")) for row in issues}
    found = read_issue_extras(
        api, repository, list(types), organization=repository.split("/")[0], types=types
    )
    out: list[object] = []
    for row in rows:
        extras = found.get(int(getattr(row, "number", 0))) if _is_issue(row) else None
        out.append(replace(row, issue_fields=extras) if extras is not None else row)  # type: ignore[type-var]
    return out


# -- Properties -------------------------------------------------------------------------


def _sheet_value(value: FieldValue) -> Value:
    """A field's value on the sheet: typed when it has one, its state in words when not."""
    if value.state == "value":
        typed = value.typed()
        if isinstance(typed, tuple):
            return typed
        if isinstance(typed, int):
            return typed
        return value.shown()
    if value.state == "unsupported":
        return f"{', '.join(value.values) or 'no value'} (read only)"
    return {
        "empty": "set to nothing",
        "unset": "not set",
        "hidden": "hidden from you",
    }.get(value.state, f"unreadable: {value.reason or 'unknown error'}")


def sheet_values(api: Any, ident: Mapping[str, str]) -> dict[str, Value]:
    """An issue's fields as sheet values; every failure becomes a state, never an error."""
    repo, number = ident.get("repo", ""), int(ident.get("number", "0") or 0)
    try:
        extras = read_issue_extras(
            api, repo, [number], organization=repo.split("/")[0], types={number: ""}
        )[number]
    except Exception as exc:  # noqa: BLE001 - the sheet says it could not be read
        return {STATE_KEY: f"could not be read: {exc}"}
    state = {
        "hidden": "hidden from you in this repository",
        "unavailable": f"could not be read: {extras.reason or 'unknown error'}",
    }.get(extras.fields_state, "")
    if not state:
        state = f"{len(extras.fields)} fields" if extras.fields else "the owner defines none"
    values: dict[str, Value] = {STATE_KEY: state}
    values[_INDEX_KEY] = tuple(
        "\t".join((f.field_id, f.name, f.data_type, f.state)) for f in extras.fields
    )
    for field in extras.fields:
        values[_PREFIX + field.field_id] = _sheet_value(field)
    return values


def _spec(line: str) -> FieldSpec:
    field_id, name, data_type, state = (line.split("\t") + ["", "", "", ""])[:4]
    supported = state != "unsupported" and data_type in _KINDS
    kind = _KINDS[data_type] if supported and state == "value" else FieldKind.TEXT
    if supported:
        words = f"{_KIND_WORDS[data_type]}, field {field_id}."
        how = " Issue Fields... on the issue's row sets or clears it."
    else:
        words = f"A field type QUILL does not edit yet ({data_type or 'unknown'}), {field_id}."
        how = " It is shown read only, as GitHub sent it."
    return FieldSpec(_PREFIX + field_id, name or field_id, kind, readonly=True, help=words + how)


def with_field_page(sheet: SheetSpec, values: Mapping[str, object]) -> SheetSpec:
    """*sheet* with an Issue Fields page for the fields *values* holds; unchanged without."""
    if STATE_KEY not in values:
        return sheet
    state = FieldSpec(
        STATE_KEY,
        "Issue fields",
        readonly=True,
        help="How many fields the issue's owner defines, or why they could not be shown.",
    )
    index = values.get(_INDEX_KEY)
    lines = index if isinstance(index, tuple) else ()
    page = PageSpec(FIELD_PAGE, "Issue Fields", (state, *(_spec(str(line)) for line in lines)))
    pages = [p for p in sheet.pages if p.key != FIELD_PAGE]
    at = next((i + 1 for i, p in enumerate(pages) if p.key == "organize"), len(pages))
    pages.insert(at, page)
    return SheetSpec(sheet.kind, sheet.title, tuple(pages))
