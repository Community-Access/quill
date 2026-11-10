"""Projects (version 2), edited richly: the Project sheet and each item's fields (PRD 16.6).

The **Project** sheet: title, short description, README, public or private,
open or closed, and as lists its fields (each with its type), its views (each
with its layout and filter), its items, its workflows (on or off) and its
status updates. Everything is GraphQL, the only API Projects have.

A **project item's** sheet is built from its project: every field the project
has becomes a control of its own type (section 16.6): a single select is a
choice of its options, an iteration a choice of "Iteration 4, 4 to 17
November", a date a date box, a number a number, and text text. Changing a
field is ``updateProjectV2ItemFieldValue``; emptying one is
``clearProjectV2ItemFieldValue``; Archived is archive and unarchive. Moving an
item to another column is changing its single-select field.

wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from quill.core.github.permissions import WriteTier
from quill.core.github.sheet_engine import Ident, Read, SheetDef, Write
from quill.core.github.sheet_fields import dig, ed, page, ro
from quill.core.workbench.properties import FieldKind, FieldSpec, SheetSpec, Value

__all__ = [
    "PROJECT",
    "PROJECT_FIELDS_QUERY",
    "ProjectField",
    "parse_fields",
    "project_item_sheet",
]

_O, _A = WriteTier.ORGANIZING, WriteTier.ACCESS
_K = FieldKind
_NEED = "scope:project+viewer:viewerCanUpdate"

_PROJECT_QUERY = (
    "query($id:ID!){node(id:$id){... on ProjectV2{id title shortDescription readme public "
    "closed template url number viewerCanUpdate viewerCanClose viewerCanReopen "
    "owner{... on Organization{login} ... on User{login}} "
    "fields(first:50){nodes{... on ProjectV2FieldCommon{name dataType}}} "
    "views(first:30){nodes{name layout filter}} "
    "items(first:100){totalCount nodes{content{__typename ... on Issue{number title} "
    "... on PullRequest{number title} ... on DraftIssue{title}}}} "
    "workflows(first:20){nodes{name enabled}} "
    "statusUpdates(first:10){nodes{status body startDate targetDate}} "
    "repositories(first:20){nodes{nameWithOwner}}}}}"
)


def _nodes(data: Mapping[str, Any] | None, *path: str) -> list[Mapping[str, Any]]:
    found = dig(data, *path, "nodes")
    return [node for node in found or () if isinstance(node, Mapping)]


def _content_words(node: Mapping[str, Any]) -> str:
    content = node.get("content") if isinstance(node.get("content"), Mapping) else {}
    kind = str((content or {}).get("__typename") or "")
    number = (content or {}).get("number")
    title = str((content or {}).get("title") or "")
    if kind == "DraftIssue":
        return f"Draft: {title}"
    return f"#{number} {title}" if number else title


def _project(data: Mapping[str, Any]) -> dict[str, Value]:
    found = dig(data, "node") or {}
    return {
        "node_id": str(found.get("id") or ""),
        "title": str(found.get("title") or ""),
        "short_description": str(found.get("shortDescription") or ""),
        "readme": str(found.get("readme") or ""),
        "public": bool(found.get("public")),
        "closed": bool(found.get("closed")),
        "template": bool(found.get("template")),
        "number": int(found.get("number") or 0),
        "owner": str(dig(found, "owner", "login") or ""),
        "url": str(found.get("url") or ""),
        "fields": tuple(
            f"{n.get('name', '')}, {str(n.get('dataType') or '').lower().replace('_', ' ')}"
            for n in _nodes(found, "fields")
        ),
        "views": tuple(
            f"{n.get('name', '')}, {str(n.get('layout') or '').lower().replace('_layout', '')}"
            + (f", filter {n.get('filter')}" if n.get("filter") else "")
            for n in _nodes(found, "views")
        ),
        "items": tuple(_content_words(n) for n in _nodes(found, "items")),
        "item_count": int(dig(found, "items", "totalCount") or 0),
        "workflows": tuple(
            f"{n.get('name', '')}, {'on' if n.get('enabled') else 'off'}"
            for n in _nodes(found, "workflows")
        ),
        "status_updates": tuple(
            f"{str(n.get('status') or '').lower().replace('_', ' ')}: {n.get('body', '')}"
            for n in _nodes(found, "statusUpdates")
        ),
        "repositories": tuple(
            str(n.get("nameWithOwner", "")) for n in _nodes(found, "repositories")
        ),
        **{k: bool(v) for k, v in found.items() if str(k).startswith("viewerCan")},
    }


def _update_project(key: str, api: str, kind: str) -> Write:
    mutation = (
        f"mutation($id:ID!,$value:{kind}!){{updateProjectV2(input:{{projectId:$id,"
        f"{api}:$value}}){{projectV2{{id}}}}}}"
    )
    return Write(
        mutation,
        _NEED,
        _A if key in ("public", "closed") else _O,
        "POST",
        "graphql",
        encode=lambda v, _c, i: {"id": i.get("node_id", ""), "value": v},
    )


PROJECT = SheetDef(
    "project",
    SheetSpec(
        "project",
        "Project",
        (
            page(
                "general",
                "General",
                ed("title", "Title"),
                ed("short_description", "Short description"),
                ed(
                    "public",
                    "Public",
                    _K.CHECK,
                    "A public project is visible to everyone; "
                    "its items still follow their repositories' access.",
                ),
                ed("closed", "Closed", _K.CHECK),
                ro("template", "Template", _K.CHECK),
                ro("owner", "Owner"),
                ro("number", "Number", _K.NUMBER),
                ro("url", "Address", _K.LINK),
            ),
            page("readme", "README", ed("readme", "README", _K.MULTILINE, "Markdown.")),
            page(
                "fields",
                "Fields",
                ro(
                    "fields",
                    "Fields",
                    _K.TABLE,
                    "Each field and its type; an item's sheet edits the values.",
                ),
            ),
            page(
                "views",
                "Views",
                ro("views", "Views", _K.TABLE, "Each saved view: its layout and filter."),
            ),
            page(
                "items",
                "Items",
                ro("item_count", "Items", _K.NUMBER),
                ro("items", "Items", _K.TABLE, "F2 or Change opens the item's own sheet."),
            ),
            page("workflows", "Workflows", ro("workflows", "Built-in workflows", _K.TABLE)),
            page("status", "Status Updates", ro("status_updates", "Status updates", _K.TABLE)),
            page(
                "access",
                "Access",
                ro(
                    "access_note",
                    "Access",
                    help="Who may read, write or "
                    "administer it is set on the project's settings page; "
                    "Open on GitHub goes there.",
                ),
            ),
            page("linked", "Linked Repositories", ro("repositories", "Repositories", _K.TABLE)),
        ),
    ),
    (Read(graphql=_PROJECT_QUERY, variables=lambda i: {"id": i["node_id"]}, extract=_project),),
    {
        "title": _update_project("title", "title", "String"),
        "short_description": _update_project("short_description", "shortDescription", "String"),
        "readme": _update_project("readme", "readme", "String"),
        "public": _update_project("public", "public", "Boolean"),
        "closed": _update_project("closed", "closed", "Boolean"),
    },
    title=lambda ident: f"Project {ident.get('title') or ident['node_id']}",
)


# ---------------------------------------------------------------------------
# Project items: one control per field, by its type
# ---------------------------------------------------------------------------

PROJECT_FIELDS_QUERY = (
    "query($id:ID!){node(id:$id){... on ProjectV2{fields(first:50){nodes{"
    "... on ProjectV2Field{id name dataType} "
    "... on ProjectV2SingleSelectField{id name dataType options{id name}} "
    "... on ProjectV2IterationField{id name dataType configuration{iterations{id title "
    "startDate duration}}}}}}}}"
)


@dataclass(frozen=True)
class ProjectField:
    """One field of a project: its id, name, type and, for choices, option name to id."""

    id: str
    name: str
    kind: str
    options: tuple[tuple[str, str], ...] = ()


def _iteration_words(row: Mapping[str, Any]) -> str:
    start = str(row.get("startDate") or "")
    days = int(row.get("duration") or 0)
    return f"{row.get('title', '')}, from {start} for {days} days"


def parse_fields(data: Mapping[str, Any]) -> list[ProjectField]:
    """The project's fields, from :data:`PROJECT_FIELDS_QUERY`'s answer."""
    found: list[ProjectField] = []
    for node in _nodes(dig(data, "node"), "fields"):
        kind = str(node.get("dataType") or "")
        options: tuple[tuple[str, str], ...] = ()
        if kind == "SINGLE_SELECT":
            options = tuple(
                (str(o.get("name")), str(o.get("id")))
                for o in node.get("options") or ()
                if isinstance(o, Mapping)
            )
        elif kind == "ITERATION":
            options = tuple(
                (_iteration_words(o), str(o.get("id")))
                for o in dig(node, "configuration", "iterations") or ()
                if isinstance(o, Mapping)
            )
        if node.get("id"):
            found.append(ProjectField(str(node["id"]), str(node.get("name") or ""), kind, options))
    return found


_EDITABLE = {
    "TEXT": _K.TEXT,
    "NUMBER": _K.NUMBER,
    "DATE": _K.DATE,
    "SINGLE_SELECT": _K.CHOICE,
    "ITERATION": _K.CHOICE,
}
_VALUE_KEY = {
    "TEXT": "text",
    "NUMBER": "number",
    "DATE": "date",
    "SINGLE_SELECT": "singleSelectOptionId",
    "ITERATION": "iterationId",
}
_SET = (
    "mutation($project:ID!,$item:ID!,$field:ID!,$value:ProjectV2FieldValue!)"
    "{updateProjectV2ItemFieldValue(input:{projectId:$project,itemId:$item,fieldId:$field,"
    "value:$value}){projectV2Item{id}}}"
)
_CLEAR = (
    "mutation($project:ID!,$item:ID!,$field:ID!){clearProjectV2ItemFieldValue(input:"
    "{projectId:$project,itemId:$item,fieldId:$field}){projectV2Item{id}}}"
)
_ITEM_QUERY = (
    "query($id:ID!){node(id:$id){... on ProjectV2Item{id isArchived type "
    "content{... on Issue{number title url} ... on PullRequest{number title url} "
    "... on DraftIssue{title}} fieldValues(first:50){nodes{"
    "... on ProjectV2ItemFieldTextValue{text field{... on ProjectV2FieldCommon{id}}} "
    "... on ProjectV2ItemFieldNumberValue{number field{... on ProjectV2FieldCommon{id}}} "
    "... on ProjectV2ItemFieldDateValue{date field{... on ProjectV2FieldCommon{id}}} "
    "... on ProjectV2ItemFieldSingleSelectValue{optionId field{... on ProjectV2FieldCommon{id}}} "
    "... on ProjectV2ItemFieldIterationValue{iterationId field{... on ProjectV2FieldCommon{id}}}"
    "}}}}}"
)


def _field_key(field: ProjectField) -> str:
    return "f_" + "".join(ch if ch.isalnum() else "_" for ch in field.id)


def _item_extract(fields: Sequence[ProjectField]) -> Any:
    def extract(data: Mapping[str, Any]) -> dict[str, Value]:
        item = dig(data, "node") or {}
        content = item.get("content") if isinstance(item.get("content"), Mapping) else {}
        found: dict[str, Value] = {
            "content": _content_words({"content": content}),
            "kind": str(item.get("type") or "").lower().replace("_", " "),
            "archived": bool(item.get("isArchived")),
        }
        by_id = {f.id: f for f in fields}
        for value in _nodes(item, "fieldValues"):
            field = by_id.get(str(dig(value, "field", "id") or ""))
            if field is None:
                continue
            raw = (
                value.get("text")
                or value.get("number")
                or value.get("date")
                or value.get("optionId")
                or value.get("iterationId")
            )
            names = {option_id: name for name, option_id in field.options}
            found[_field_key(field)] = names.get(str(raw), "" if raw is None else str(raw))
        return found

    return extract


def _field_write(field: ProjectField) -> Write:
    value_key = _VALUE_KEY[field.kind]
    options = dict(field.options)

    def encode(value: Value, _choices: Mapping[str, object], ident: Ident) -> dict[str, object]:
        sent: object = options.get(str(value), value)
        if field.kind == "NUMBER":
            sent = float(str(value or 0))
        variables: dict[str, object] = {
            "project": ident.get("project_id", ""),
            "item": ident.get("item_id", ""),
            "field": field.id,
        }
        if value not in (None, ""):
            variables["value"] = {value_key: sent}
        return variables

    # An empty value clears the field: graphql with value False runs off_path.
    return Write(_SET, _NEED, _O, "POST", "graphql", encode=encode, off_path=_CLEAR)


def project_item_sheet(fields: Sequence[ProjectField]) -> SheetDef:
    """A project item's sheet, built from its project's fields (section 16.6)."""
    editable = [f for f in fields if f.kind in _EDITABLE]
    controls: list[FieldSpec] = [
        ed(
            _field_key(f),
            f.name,
            _EDITABLE[f.kind],
            f"{f.name}: a {f.kind.lower().replace('_', ' ')} field."
            + (" As year-month-day." if f.kind == "DATE" else ""),
            choices=tuple(name for name, _id in f.options),
        )
        for f in editable
    ]
    writes = {_field_key(f): _field_write(f) for f in editable}
    writes["archived"] = Write(
        "mutation($project:ID!,$id:ID!){archiveProjectV2Item(input:{projectId:$project,"
        "itemId:$id}){item{id}}}",
        _NEED,
        _O,
        "POST",
        "graphql",
        encode=lambda _v, _c, i: {"project": i.get("project_id", ""), "id": i.get("item_id", "")},
        off_path="mutation($project:ID!,$id:ID!){unarchiveProjectV2Item(input:"
        "{projectId:$project,itemId:$id}){item{id}}}",
    )
    return SheetDef(
        "project_item",
        SheetSpec(
            "project_item",
            "Project Item",
            (
                page(
                    "general",
                    "General",
                    ro("content", "Item"),
                    ro("kind", "Kind"),
                    ed("archived", "Archived", _K.CHECK),
                ),
                page("fields", "Fields", *controls),
                page(
                    "content",
                    "Content",
                    ro(
                        "content_note",
                        "Content",
                        help="Enter on the item opens the issue or pull request.",
                    ),
                ),
            ),
        ),
        (
            Read(
                graphql=_ITEM_QUERY,
                variables=lambda i: {"id": i["item_id"]},
                extract=_item_extract(fields),
            ),
        ),
        writes,
        title=lambda ident: "Project item",
    )
