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
  field per field, of its own kind (:func:`with_field_page`). A date, a
  number, a single choice and text are edited there and saved by the very
  request Issue Fields... on the row sends (:data:`FIELD_WRITES`), then
  checked by reading the issue again; several issues at once show Mixed
  where they differ (:func:`with_field_page_many`). Several choices, and
  field types QUILL does not know, stay read only.

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
from quill.core.github.issue_admin import field_request
from quill.core.github.permissions import WriteTier
from quill.core.github.sheet_engine import Ident, Write
from quill.core.workbench.properties import (
    FieldChange,
    FieldKind,
    FieldSpec,
    PageSpec,
    SheetSpec,
    Value,
)

__all__ = [
    "FIELD_PAGE",
    "FIELD_WRITES",
    "ISSUE_FIELD_COLUMNS",
    "STATE_KEY",
    "IssueExtras",
    "cell",
    "detail_lines",
    "field_key",
    "field_choices",
    "issue_type_of",
    "read_row_fields",
    "sheet_values",
    "with_field_page",
    "with_field_page_many",
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

#: The field types the sheet edits, each by its own kind of control.
_EDITABLE = ("date", "number", "single_select", "text")
_EDIT_STATES = ("value", "empty", "unset")
_OPTION_SEP = "\x1f"


def _editable(data_type: str, state: str) -> bool:
    return data_type in _EDITABLE and state in _EDIT_STATES


def _sheet_value(value: FieldValue) -> Value:
    """A field's value on the sheet: its text when editable, its state in words when not."""
    if _editable(value.data_type, value.state):
        return value.shown() or None  # empty and not set are told apart in the summary
    if value.state == "value":
        typed = value.typed()
        return typed if isinstance(typed, (tuple, int)) else value.shown()
    if value.state == "unsupported":
        return f"{', '.join(value.values) or 'no value'} (read only)"
    if value.state == "hidden":
        return "hidden from you"
    return f"unreadable: {value.reason or 'unknown error'}"


def _summary(fields: Sequence[FieldValue]) -> str:
    """How many fields, and which are not set or set to nothing (both show an empty box)."""
    said = f"{len(fields)} field{'s' if len(fields) != 1 else ''}."
    for state, words in (("unset", "Not set"), ("empty", "Set to nothing")):
        names = [f.name for f in fields if f.state == state and _editable(f.data_type, state)]
        if names:
            said += f" {words}: {', '.join(names)}."
    return said


def field_key(field_id: str, data_type: str) -> str:
    """A field's key on the sheet, ``issue_field:date:12``: the type says how it is sent."""
    return f"{_PREFIX}{data_type}:{field_id}"


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
        state = _summary(extras.fields) if extras.fields else "the owner defines none"
    values: dict[str, Value] = {STATE_KEY: state}
    values[_INDEX_KEY] = tuple(
        "\t".join((f.field_id, f.name, f.data_type, f.state, _OPTION_SEP.join(f.options)))
        for f in extras.fields
    )
    for field in extras.fields:
        values[field_key(field.field_id, field.data_type)] = _sheet_value(field)
    return values


_HOW = {
    "date": " Type it as year-month-day, such as 2026-12-31.",
    "number": " Type a number, such as 3 or 2.5.",
    "single_select": " Choose one of the owner's choices, or (none).",
    "text": "",
}


def _parts(line: str) -> list[str]:
    """An index line's field id, name, data type, state and choices."""
    return (str(line).split("\t") + [""] * 5)[:5]


def _spec(line: str) -> FieldSpec:
    field_id, name, data_type, state, options = _parts(line)
    key = field_key(field_id, data_type)
    if _editable(data_type, state):
        words = (
            f"{_KIND_WORDS[data_type]}, field {field_id}.{_HOW[data_type]} Saving sets it on "
            "GitHub, and leaving it empty clears it; Issue Fields... on the row does the same."
        )
        choices = ("", *options.split(_OPTION_SEP)) if options else ()
        return FieldSpec(key, name or field_id, _KINDS[data_type], help=words, choices=choices)
    supported = state != "unsupported" and data_type in _KINDS
    kind = _KINDS[data_type] if supported and state == "value" else FieldKind.TEXT
    if supported and data_type == "multi_select":
        words = f"Several choices, field {field_id}. Change them on GitHub's site."
    elif supported:
        words = f"{_KIND_WORDS[data_type]}, field {field_id}. Shown as GitHub sent it."
    else:
        words = f"A field type QUILL does not edit yet ({data_type or 'unknown'}), {field_id}."
        words += " It is shown read only, as GitHub sent it."
    return FieldSpec(key, name or field_id, kind, readonly=True, help=words)


def with_field_page(sheet: SheetSpec, values: Mapping[str, object]) -> SheetSpec:
    """*sheet* with an Issue Fields page for the fields *values* holds; unchanged without."""
    if STATE_KEY not in values:
        return sheet
    state = FieldSpec(
        STATE_KEY,
        "Issue fields",
        readonly=True,
        help="How many fields the issue's owner defines, which are not set or set to "
        "nothing, or why they could not be shown.",
    )
    index = values.get(_INDEX_KEY)
    lines = index if isinstance(index, tuple) else ()
    page = PageSpec(FIELD_PAGE, "Issue Fields", (state, *(_spec(str(line)) for line in lines)))
    pages = [p for p in sheet.pages if p.key != FIELD_PAGE]
    at = next((i + 1 for i, p in enumerate(pages) if p.key == "organize"), len(pages))
    pages.insert(at, page)
    return SheetSpec(sheet.kind, sheet.title, tuple(pages))


def with_field_page_many(sheet: SheetSpec, objects: Sequence[Mapping[str, object]]) -> SheetSpec:
    """The Issue Fields page for several issues: every field any of them has, once.

    A field editable on one of them is editable on the page; the sheet shows
    Mixed where their values differ, and each issue is saved and checked on
    its own (:func:`quill.core.github.batch.run`).
    """
    if not any(STATE_KEY in values for values in objects):
        return sheet
    lines: dict[str, str] = {}
    for values in objects:
        index = values.get(_INDEX_KEY)
        for line in index if isinstance(index, tuple) else ():
            field_id, _name, data_type, state, _options = _parts(line)
            have = _parts(lines[field_id]) if field_id in lines else None
            if have is None or (_editable(data_type, state) and not _editable(have[2], have[3])):
                lines[field_id] = str(line)
    return with_field_page(sheet, {STATE_KEY: "", _INDEX_KEY: tuple(lines.values())})


def _request(
    change: FieldChange, value: Value, ident: Ident
) -> tuple[str, str, dict[str, object] | None]:
    """Issue Fields...'s own request (:func:`issue_admin.field_request`) for one changed field."""
    data_type, _sep, field_id = change.key.removeprefix(_PREFIX).partition(":")
    field = FieldValue(field_id, change.label, data_type, "value")
    answer = "" if value is None else str(value)
    return field_request(ident.get("repo", ""), int(ident.get("number", "0") or 0), field, answer)


#: Every field an issue's owner defines is saved by this one write. Setting one
#: needs triage access, as Issue Fields... does (``POST .../issue-field-values``).
FIELD_WRITES: dict[str, Write] = {
    _PREFIX: Write("", "repo:triage", WriteTier.ORGANIZING, "POST", "request", request=_request)
}
