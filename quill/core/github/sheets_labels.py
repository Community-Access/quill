"""The Label and Milestone sheets (GitHub PRD Appendix C), and New... in their pickers.

A label's colour is typed as a word ("green") or as six hex digits, and read
back with the nearest common colour's name; renaming a label moves its ident,
so the verify-after-save re-read finds it under its new name. A milestone's
due date is a plain year-month-day.

wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from quill.core.github.sheet_engine import Ident, Read, SheetDef, Write
from quill.core.github.sheet_fields import colour_hex, colour_name, ed, page, patch, ro, when
from quill.core.github.sheets_items import _K, _O
from quill.core.workbench.properties import SheetSpec, Value

__all__ = ["CREATE_LABEL", "CREATE_MILESTONE", "LABEL", "MILESTONE"]

# ---------------------------------------------------------------------------

_LABEL_PATH = "/repos/{repo}/labels/{name}"


def _label(data: Mapping[str, Any]) -> dict[str, Value]:
    colour = str(data.get("color") or "")
    return {
        "name": str(data.get("name") or ""),
        "colour": colour,
        "colour_name": colour_name(colour),
        "description": str(data.get("description") or ""),
        "url": str(data.get("url") or ""),
    }


def _label_usage(data: Mapping[str, Any]) -> dict[str, Value]:
    return {"in_use": int(data.get("total_count") or 0)}


def _colour(value: Value, _choices: Mapping[str, object], _ident: Ident) -> dict[str, object]:
    return {"color": colour_hex(str(value or ""))}


LABEL = SheetDef(
    "label",
    SheetSpec(
        "label",
        "Label",
        (
            page(
                "general",
                "General",
                ed("name", "Name", help="Renaming keeps it on every issue that has it."),
                ed("colour", "Colour", help="A name such as green or red, or six hex digits."),
                ro("colour_name", "Nearest colour"),
                ed("description", "Description", help="Up to 100 characters."),
            ),
            page(
                "usage",
                "Usage",
                ro(
                    "in_use",
                    "Issues and pull requests with it",
                    _K.NUMBER,
                    "Find Issues with Label lists them.",
                ),
            ),
        ),
    ),
    (
        Read(_LABEL_PATH, _label),
        Read(
            "/search/issues",
            _label_usage,
            optional=True,
            query=lambda i: {"q": f'repo:{i["repo"]} label:"{i["name"]}"', "per_page": "1"},
        ),
    ),
    {
        "name": patch(_LABEL_PATH, "repo:write", _O, "new_name"),
        "colour": patch(_LABEL_PATH, "repo:write", _O, encode=_colour),
        "description": patch(_LABEL_PATH, "repo:write", _O),
    },
    title=lambda ident: f"Label {ident['name']}",
    url=lambda ident: f"https://github.com/{ident['repo']}/labels",
    renames=("name", "name"),
)

_MILESTONE_PATH = "/repos/{repo}/milestones/{number}"


def _milestone(data: Mapping[str, Any]) -> dict[str, Value]:
    open_count = int(data.get("open_issues") or 0)
    closed_count = int(data.get("closed_issues") or 0)
    total = open_count + closed_count
    percent = round(100 * closed_count / total) if total else 0
    return {
        "title": str(data.get("title") or ""),
        "description": str(data.get("description") or ""),
        "due": str(data.get("due_on") or "")[:10],
        "state": str(data.get("state") or "open"),
        "open_issues": open_count,
        "closed_issues": closed_count,
        "progress": f"{percent} percent: {closed_count} of {total} closed",
        "created": when(data.get("created_at")),
        "updated": str(data.get("updated_at") or ""),
        "url": str(data.get("html_url") or ""),
    }


def _due(value: Value, _choices: Mapping[str, object], _ident: Ident) -> dict[str, object]:
    text = str(value or "").strip()
    return {"due_on": f"{text}T00:00:00Z" if text else None}


MILESTONE = SheetDef(
    "milestone",
    SheetSpec(
        "milestone",
        "Milestone",
        (
            page(
                "general",
                "General",
                ed("title", "Title"),
                ed("description", "Description", _K.MULTILINE),
                ed(
                    "due",
                    "Due date",
                    _K.DATE,
                    "As year-month-day, such as 2027-03-31; empty for none.",
                ),
                ed("state", "State", _K.CHOICE, choices=("open", "closed")),
                ro("url", "Address", _K.LINK),
            ),
            page(
                "progress",
                "Progress",
                ro("progress", "Progress"),
                ro("open_issues", "Open", _K.NUMBER),
                ro("closed_issues", "Closed", _K.NUMBER),
            ),
            page(
                "items",
                "Items",
                ro(
                    "created",
                    "Created",
                    _K.DATE,
                    "Its items are listed by Find Issues in Milestone on the context menu.",
                ),
            ),
        ),
    ),
    (Read(_MILESTONE_PATH, _milestone),),
    {
        "title": patch(_MILESTONE_PATH, "repo:write", _O),
        "description": patch(_MILESTONE_PATH, "repo:write", _O),
        "due": patch(_MILESTONE_PATH, "repo:write", _O, encode=_due),
        "state": patch(_MILESTONE_PATH, "repo:write", _O),
    },
    title=lambda ident: f"Milestone {ident.get('title') or ident['number']}",
    url=lambda ident: f"https://github.com/{ident['repo']}/milestone/{ident['number']}",
)

#: New... in the pickers: what each creates, and the body it sends.
CREATE_LABEL = Write("/repos/{repo}/labels", "repo:write", _O, "POST", "post")
CREATE_MILESTONE = Write("/repos/{repo}/milestones", "repo:write", _O, "POST", "post")
