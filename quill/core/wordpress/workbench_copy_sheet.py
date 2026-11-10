"""File > WordPress > Properties, built from the Workbench's item sheet (PRD 8).

The editor's Properties for the open post or page and the Workbench's sheet
for the same post are one sheet: :func:`copy_sheet` takes the Workbench's
item sheet (:func:`quill.core.wordpress.workbench_sheets.sheet_for`) and
keeps the fields a working copy carries to the site on its next send, so a
field added to the item sheet once appears in both. An About page at the end
holds the facts the editor already showed (the site, the address, the
reading level), read only.

:func:`copy_values` fills the sheet from the working copy's properties, and
:func:`copy_answer` turns the fields the person changed back into what the
working copy keeps: categories and tags by id (typed as "News (12)", "12" or
"News"), the rest under the same WordPress names the copy sends. Wx-free and
network-free.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from quill.core.wordpress.workbench_rows import WbRow
from quill.core.wordpress.workbench_sheets import labelled, sheet_for, term_ids
from quill.core.workbench.properties import FieldKind, FieldSpec, PageSpec, SheetSpec, Value

__all__ = ["COPY_FIELDS", "CopyAnswer", "copy_answer", "copy_sheet", "copy_values"]

COPY_FIELDS = frozenset({
    "title",
    "slug",
    "status",
    "password",
    "excerpt",
    "categories",
    "tags",
    "featured_media",
    "comment_status",
    "sticky",
    "format",
    "parent",
    "template",
})
"""The item sheet's fields a working copy keeps and sends (``item_from_copy``)."""

_NUMBERS = ("featured_media", "parent")


@dataclass
class CopyAnswer:
    """What the person changed, as the working copy keeps it."""

    title: str | None = None
    status: str | None = None
    properties: dict[str, Any] = field(default_factory=dict)
    unknown_terms: list[str] = field(default_factory=list)
    password: str = field(default="", repr=False)


def copy_sheet(kind: str) -> SheetSpec:
    """The item sheet for a working copy of *kind* (``post`` or ``page``), with an About page."""
    raw: dict[str, Any] = {"type": kind}
    if kind == "page":
        raw["parent"] = 0
    taxonomies = {"categories": "Categories", "tags": "Tags"} if kind == "post" else {}
    row = WbRow("item", "", "0", {}, "", subkind=kind, raw=raw)
    item = sheet_for(row, taxonomies=taxonomies)
    pages: list[PageSpec] = []
    for page in item.pages:
        kept = tuple(spec for spec in page.fields if spec.key in COPY_FIELDS)
        if kept:
            pages.append(PageSpec(page.key, page.title, kept))
    about = PageSpec(
        "about",
        "About",
        (
            FieldSpec(
                "about",
                "About",
                FieldKind.MULTILINE,
                readonly=True,
                help="Which site this belongs to, its address and when it last changed.",
            ),
        ),
    )
    return SheetSpec("copy", "WordPress Properties", (*pages, about))


def copy_values(
    *,
    title: str,
    status: str,
    properties: Mapping[str, Any],
    facts: str,
    categories: Sequence[tuple[int, str]] = (),
    tags: Sequence[tuple[int, str]] = (),
) -> dict[str, Value]:
    """What each field shows, from the working copy."""
    names = {ident: name for ident, name in (*categories, *tags)}

    def terms(key: str) -> tuple[str, ...]:
        return tuple(labelled(names.get(int(i), ""), int(i)) for i in properties.get(key) or [])

    values: dict[str, Value] = {
        "about": facts,
        "title": title,
        "status": status,
        "password": "",
        "slug": str(properties.get("slug", "") or ""),
        "excerpt": str(properties.get("excerpt", "") or ""),
        "categories": terms("categories"),
        "tags": terms("tags"),
        "comment_status": str(properties.get("comment_status", "") or "open"),
        "sticky": bool(properties.get("sticky", False)),
        "format": str(properties.get("format", "") or "standard"),
        "template": str(properties.get("template", "") or ""),
    }
    for key in _NUMBERS:
        values[key] = int(properties.get(key, 0) or 0)
    return values


def copy_answer(
    pending: Mapping[str, Any],
    *,
    categories: Sequence[tuple[int, str]] = (),
    tags: Sequence[tuple[int, str]] = (),
) -> CopyAnswer:
    """The working copy's new values for the fields in *pending* (only what changed)."""
    answer = CopyAnswer()
    for key, value in pending.items():
        if key not in COPY_FIELDS:
            continue
        if key == "title":
            answer.title = str(value or "").strip()
        elif key == "status":
            answer.status = str(value or "draft")
        elif key == "password":
            answer.password = str(value or "")
        elif key in ("categories", "tags"):
            pool = categories if key == "categories" else tags
            listed = (value,) if isinstance(value, str) else tuple(value or ())
            ids, unknown = term_ids([str(v) for v in listed], {n: i for i, n in pool})
            answer.properties[key] = ids
            answer.unknown_terms.extend(unknown)
        elif key in _NUMBERS:
            try:
                answer.properties[key] = int(str(value or 0).strip() or 0)
            except ValueError:
                answer.unknown_terms.append(f"{key}: {value}")
        elif key == "sticky":
            answer.properties[key] = bool(value)
        else:
            answer.properties[key] = str(value or "").strip()
    return answer
