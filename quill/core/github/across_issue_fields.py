"""Issue type and organization-defined issue fields on Across Repositories' issue rows (GX16).

PRD 22.11 asks that a category issue row carry its **issue type** and every
**organization-defined issue field** the signed-in account can see, with the
field's identifier and declared type kept beside its value, and that five
states never be confused:

- ``value`` -- the field has a value;
- ``empty`` -- the field is set to nothing (an empty text, no choices);
- ``unset`` -- the organization defines the field and this issue has none;
- ``hidden`` -- GitHub says this account may not see issue fields here;
- ``unsupported`` -- a field type GitHub added after this was written; its
  value is shown as GitHub sent it, never guessed at;
- ``unavailable`` -- the read failed, so nothing is known: a missing
  permission never looks like an unset field.

Type and field filters (``type:Bug``, ``field:"Priority=High"``) use these
same values, and an issue whose fields could not be read is reported apart
from one that does not match (:func:`match`).

The reads are the REST rows ``GET /repos/{owner}/{repo}/issues`` (its
``type``), ``GET /orgs/{org}/issue-fields`` (the definitions) and
``GET /repos/{owner}/{repo}/issues/{n}/issue-field-values``, bounded by
:data:`MAX_FIELD_READS` per repository, through the Workbench's one
:class:`~quill.core.github.workbench_api.GitHubApi`. GitHub documents these
payloads loosely, so the parsers read every spelling they have been seen in
and keep anything else as ``unsupported`` rather than dropping it.

wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import date
from typing import Any
from urllib.parse import quote

__all__ = [
    "FIELD_STATES",
    "KNOWN_TYPES",
    "MAX_FIELD_READS",
    "FieldDefinition",
    "FieldValue",
    "IssueExtras",
    "TypedValue",
    "combine",
    "match",
    "parse_definitions",
    "parse_values",
    "read_definitions",
    "read_issue_extras",
]

FIELD_STATES = ("value", "empty", "unset", "hidden", "unsupported", "unavailable")
KNOWN_TYPES = ("text", "number", "date", "single_select", "multi_select")
#: Field values are one request per issue, so each repository reads at most this many.
MAX_FIELD_READS = 30

#: What :meth:`FieldValue.typed` gives: a date, a number, choices, text, or None.
TypedValue = date | int | float | str | tuple[str, ...] | None

_TYPE_WORDS = {
    "text": "text",
    "number": "number",
    "date": "date",
    "single_select": "single choice",
    "multi_select": "multiple choice",
}


@dataclass(frozen=True, slots=True)
class FieldDefinition:
    field_id: str
    name: str
    data_type: str
    options: tuple[str, ...] = ()
    """A single or multiple select's choices, by name, in the owner's order."""


@dataclass(frozen=True, slots=True)
class FieldValue:
    """One field on one issue, in one of :data:`FIELD_STATES`."""

    field_id: str
    name: str
    data_type: str
    state: str
    values: tuple[str, ...] = ()
    reason: str = ""
    options: tuple[str, ...] = field(default=(), compare=False)
    """The choices a select offers (from the definitions), for a picker; not part of equality."""

    def typed(self) -> TypedValue:
        """The value as its type: a date, a number, a choice's name, choices, or text.

        None unless the state is ``value``: an empty, unset, hidden, unsupported
        or unreadable field has no typed value, and :meth:`words` says why. A
        value that does not read as its declared type stays the text GitHub sent.
        """
        if self.state != "value" or not self.values:
            return None
        first = self.values[0]
        if self.data_type == "multi_select":
            return self.values
        if self.data_type == "date":
            try:
                return date.fromisoformat(first[:10])
            except ValueError:
                return first
        if self.data_type == "number":
            try:
                number = float(first)
            except ValueError:
                return first
            return int(number) if number.is_integer() else number
        return first

    def shown(self) -> str:
        """The typed value as text: 2026-12-31, 3, 2.5, High, or "Red, Blue"."""
        typed = self.typed()
        if isinstance(typed, tuple):
            return ", ".join(typed)
        if isinstance(typed, date):
            return typed.isoformat()
        return "" if typed is None else str(typed)

    def short(self) -> str:
        """The field in a list cell, "Priority: High"; every state has its own word."""
        if self.state == "value":
            return f"{self.name}: {self.shown()}"
        if self.state == "unsupported":
            return f"{self.name}: {', '.join(self.values) or 'no value'} (read only)"
        said = {"empty": "empty", "unset": "not set", "hidden": "hidden"}
        return f"{self.name}: {said.get(self.state, 'unreadable')}"

    def words(self) -> str:
        kind = _TYPE_WORDS.get(self.data_type, self.data_type or "unknown type")
        head = f"{self.name} ({kind}, field {self.field_id})"
        if self.state == "value":
            return f"{head}: {self.shown()}"
        if self.state == "unsupported":
            shown = ", ".join(self.values) or "no value"
            return f"{head}: {shown}, a field type QUILL does not edit yet, so read only"
        said = {
            "empty": "set to nothing",
            "unset": "not set",
            "hidden": "hidden from you",
            "unavailable": f"could not be read{': ' + self.reason if self.reason else ''}",
        }[self.state]
        return f"{head}: {said}"


@dataclass(frozen=True, slots=True)
class IssueExtras:
    """An issue's type and fields, and how sure we are of each."""

    issue_type: str = ""
    #: ``set``, ``none`` or ``unavailable``.
    type_state: str = "none"
    fields: tuple[FieldValue, ...] = ()
    #: ``read``, ``hidden``, ``unavailable``, ``not_read`` (past the bound) or ``none``.
    fields_state: str = "none"
    reason: str = ""

    def detail_lines(self) -> list[str]:
        if self.type_state == "set":
            lines = [f"Issue type: {self.issue_type}"]
        elif self.type_state == "unavailable":
            lines = [f"Issue type: could not be read{': ' + self.reason if self.reason else ''}"]
        else:
            lines = ["Issue type: none"]
        if self.fields_state == "hidden":
            lines.append("Issue fields: hidden from you in this repository")
        elif self.fields_state == "unavailable":
            lines.append(f"Issue fields: could not be read: {self.reason or 'unknown error'}")
        elif self.fields_state == "not_read":
            lines.append("Issue fields: not read, past the first 30 in this repository")
        elif self.fields_state == "read" and not self.fields:
            lines.append("Issue fields: the organization defines none")
        lines.extend(f"Field {value.words()}" for value in self.fields)
        return lines


def _text(value: object) -> str:
    return "" if value is None else str(value)


def _field_id(entry: Mapping[str, Any]) -> str:
    for key in ("issue_field_id", "field_id", "id", "node_id"):
        if entry.get(key) not in (None, ""):
            return _text(entry.get(key))
    nested = entry.get("issue_field") or entry.get("field")
    if isinstance(nested, Mapping):
        return _field_id(nested)
    return ""


def _data_type(entry: Mapping[str, Any]) -> str:
    for key in ("data_type", "type", "field_type"):
        value = entry.get(key)
        if isinstance(value, str) and value:
            return value.lower()
    nested = entry.get("issue_field") or entry.get("field")
    if isinstance(nested, Mapping):
        return _data_type(nested)
    return ""


def _name(entry: Mapping[str, Any]) -> str:
    value = entry.get("name")
    if isinstance(value, str) and value:
        return value
    nested = entry.get("issue_field") or entry.get("field")
    return _name(nested) if isinstance(nested, Mapping) else ""


def _options(entry: Mapping[str, Any]) -> tuple[str, ...]:
    raw = entry.get("options")
    names = (o.get("name") for o in raw if isinstance(o, Mapping)) if isinstance(raw, list) else ()
    return tuple(str(name) for name in names if name)


def parse_definitions(data: object) -> list[FieldDefinition]:
    """The organization's field definitions from ``GET /orgs/{org}/issue-fields``."""
    rows = data.get("issue_fields") if isinstance(data, Mapping) else data
    found: list[FieldDefinition] = []
    for entry in rows if isinstance(rows, list) else []:
        if isinstance(entry, Mapping) and _field_id(entry):
            found.append(
                FieldDefinition(_field_id(entry), _name(entry), _data_type(entry), _options(entry))
            )
    return found


def _values_of(entry: Mapping[str, Any]) -> tuple[str, ...] | None:
    """The value(s) an entry carries; None when it carries no value key at all."""
    for key in ("value", "values", "single_select_option", "options", "text", "number", "date"):
        if key not in entry:
            continue
        raw = entry[key]
        items = raw if isinstance(raw, list) else [raw]
        out: list[str] = []
        for item in items:
            if isinstance(item, Mapping):
                out.append(_text(item.get("name") or item.get("value") or item.get("id")))
            elif item is not None:
                out.append(_text(item))
        return tuple(v for v in out if v != "")
    return None


def parse_values(data: object) -> dict[str, tuple[str, str, tuple[str, ...] | None]]:
    """``{field_id: (name, data_type, values)}`` from one issue's field values."""
    rows = data.get("issue_field_values") if isinstance(data, Mapping) else data
    found: dict[str, tuple[str, str, tuple[str, ...] | None]] = {}
    for entry in rows if isinstance(rows, list) else []:
        if isinstance(entry, Mapping) and _field_id(entry):
            found[_field_id(entry)] = (_name(entry), _data_type(entry), _values_of(entry))
    return found


def combine(
    definitions: Sequence[FieldDefinition],
    values: Mapping[str, tuple[str, str, tuple[str, ...] | None]],
) -> tuple[FieldValue, ...]:
    """Every defined field, then any value for a field the definitions did not list."""
    out: list[FieldValue] = []
    seen: set[str] = set()
    for definition in definitions:
        seen.add(definition.field_id)
        name, data_type, got = values.get(definition.field_id, ("", "", None))
        kind = definition.data_type or data_type
        found = _value(definition.field_id, definition.name or name, kind, got)
        out.append(replace(found, options=definition.options))
    for field_id, (name, data_type, got) in values.items():
        if field_id not in seen:
            out.append(_value(field_id, name, data_type, got))
    return tuple(out)


def _value(field_id: str, name: str, data_type: str, got: tuple[str, ...] | None) -> FieldValue:
    if got is None:
        return FieldValue(field_id, name, data_type, "unset")
    if data_type not in KNOWN_TYPES:
        return FieldValue(field_id, name, data_type, "unsupported", got)
    return FieldValue(field_id, name, data_type, "value" if got else "empty", got)


def _reason(error: BaseException) -> str:
    from quill.core.github.across import why_failed

    return why_failed(error)


def _status(error: BaseException) -> int | None:
    status = getattr(error, "status", None)
    if isinstance(status, int):
        return status
    return 404 if "404" in str(error) else None


def _forbidden(error: BaseException) -> bool:
    """GitHub refused this account (401 or 403): the fields are hidden, not unreadable."""
    return getattr(error, "status", None) in (401, 403) or _reason(error) == "no access"


def read_definitions(api: Any, owner: str) -> object:
    """The fields *owner* defines: an organization's, else your own (``/user``).

    A 404 on the organization read means *owner* is a person, so the fields
    are the signed-in account's own; any other failure is raised.
    """
    try:
        return api.rest("GET", f"/orgs/{quote(owner)}/issue-fields").data
    except Exception as exc:
        if _status(exc) != 404:
            raise
    return api.rest("GET", "/user/issue-fields").data


def _read_types(api: Any, repository: str) -> tuple[dict[int, str], str]:
    """Each issue's type from the repository's issue list, or why it could not be read."""
    types: dict[int, str] = {}
    try:
        answer = api.rest(
            "GET",
            f"/repos/{repository}/issues",
            query={"state": "all", "per_page": "100"},
        )
    except Exception as exc:  # noqa: BLE001 - one unreadable list is "unavailable", not "none"
        return types, _reason(exc)
    for entry in answer.data if isinstance(answer.data, list) else []:
        if isinstance(entry, Mapping) and isinstance(entry.get("number"), int):
            kind = entry.get("type")
            name = kind.get("name") if isinstance(kind, Mapping) else kind
            types[int(entry["number"])] = _text(name)
    return types, ""


def read_issue_extras(
    api: Any,
    repository: str,
    numbers: Iterable[int],
    *,
    organization: str = "",
    can_see_fields: bool | None = None,
    types: Mapping[int, str] | None = None,
) -> dict[int, IssueExtras]:
    """Type and fields for *numbers* in *repository*. Runs off the UI thread.

    *can_see_fields* is the repository's ``viewerCanSeeIssueFields`` when it
    is known; False makes every issue's fields ``hidden`` without a request.
    *types* is each issue's type when the caller already has it (the
    Workbench's issue rows carry it), which saves reading the issue list.
    """
    wanted = list(dict.fromkeys(numbers))
    type_error = ""
    if types is None:
        types, type_error = _read_types(api, repository)
    definitions: list[FieldDefinition] = []
    fields_error = ""
    if can_see_fields is not False and organization:
        try:
            definitions = parse_definitions(read_definitions(api, organization))
        except Exception as exc:  # noqa: BLE001
            fields_error = _reason(exc)
            if _forbidden(exc):
                can_see_fields = False
    found: dict[int, IssueExtras] = {}
    for index, number in enumerate(wanted):
        type_name = types.get(number, "")
        type_state = "unavailable" if type_error else ("set" if type_name else "none")
        base = IssueExtras(type_name, type_state, reason=type_error)
        if can_see_fields is False:
            found[number] = _with(base, (), "hidden", "")
            continue
        if fields_error:
            found[number] = _with(base, (), "unavailable", fields_error)
            continue
        if index >= MAX_FIELD_READS:
            found[number] = _with(base, (), "not_read", "")
            continue
        try:
            answer = api.rest("GET", f"/repos/{repository}/issues/{number}/issue-field-values")
        except Exception as exc:  # noqa: BLE001
            state = "hidden" if _forbidden(exc) else "unavailable"
            found[number] = _with(base, (), state, _reason(exc))
            continue
        found[number] = _with(base, combine(definitions, parse_values(answer.data)), "read", "")
    return found


def _with(
    base: IssueExtras, fields: tuple[FieldValue, ...], state: str, reason: str
) -> IssueExtras:
    return IssueExtras(
        base.issue_type,
        base.type_state,
        fields,
        state,
        reason or base.reason,
    )


def match(extras: IssueExtras | None, conditions: Sequence[tuple[str, str, bool]]) -> bool | None:
    """Whether an issue meets ``type:`` and ``field:`` conditions; None when it cannot be known.

    Each condition is ``(attribute, value, negated)``; ``field:`` values are
    ``Name=Value`` (``Name=`` asks for unset or empty). An issue whose type or
    fields were not read answers None, which the list reports as unknown,
    never as "does not match".
    """
    for attribute, wanted, negated in conditions:
        if attribute == "type":
            if extras is None or extras.type_state == "unavailable":
                return None
            hit = extras.issue_type.casefold() == wanted.casefold()
        elif attribute == "field":
            if extras is None or extras.fields_state != "read":
                return None
            name, _sep, value = wanted.partition("=")
            chosen = [f for f in extras.fields if f.name.casefold() == name.strip().casefold()]
            if not chosen:
                hit = False
            elif not value.strip():
                hit = any(f.state in ("unset", "empty") for f in chosen)
            else:
                hit = any(
                    value.strip().casefold() in (v.casefold() for v in f.values)
                    for f in chosen
                    if f.state in ("value", "unsupported")
                )
        else:
            continue
        if hit == negated:
            return False
    return True
