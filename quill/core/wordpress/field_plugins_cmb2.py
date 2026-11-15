"""CMB2 fields on Properties, read and written one field at a time (WP-R-034).

CMB2 does not add its fields to the ``wp/v2`` objects. A box registered with
``show_in_rest`` is served under ``cmb2/v1`` instead, and each field is read
and written on its own route with the object named in the query::

    GET  cmb2/v1/boxes
         -> {"book_box": {"id": "book_box", "title": "Book details",
                          "object_types": ["book"], "show_in_rest": "GET, POST", ...}}
    GET  cmb2/v1/boxes/book_box/fields?object_id=7&object_type=post
         -> {"isbn": {"id": "isbn", "name": "ISBN", "type": "text",
                      "description": "...", "value": "978..."}, ...}
    POST cmb2/v1/boxes/book_box/fields/isbn
         {"object_id": 7, "object_type": "post", "value": "978..."}
    GET  cmb2/v1/boxes/book_box/fields/isbn?object_id=7&object_type=post
         -> {"id": "isbn", "value": "978..."}             (the check after a save)

``object_types`` names post types for a post box and ``term``, ``user`` or
``comment`` for the others; ``object_type`` in the query is ``post`` for every
post type. A box whose ``show_in_rest`` says only reading (``GET`` or
``READABLE``) is read only here; one that says nothing is offered, and the
site's refusal, if it refuses, is said as the failure. Some CMB2 versions send
the boxes and fields as lists rather than keyed objects; both are read.

The page's keys are ``cmb2.<box>.<field>``; a save sends the main object as
usual and then each CMB2 field to its own route, and reads each back to say
whether the site kept it (:func:`save_with_cmb2`). Wx-free.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from quill.core.wordpress.api import WordPressApi, WordPressApiError
from quill.core.wordpress.field_plugins_more import PluginPage, plugin_field
from quill.core.wordpress.workbench_rows import WbRow
from quill.core.workbench.properties import FieldSpec, Value

__all__ = [
    "CMB2_BODY",
    "CMB2_NAMESPACE",
    "boxes_for",
    "cmb2_boxes",
    "cmb2_page",
    "cmb2_schema",
    "object_type_of",
    "save_with_cmb2",
]

CMB2_NAMESPACE = "cmb2/v1"
CMB2_BODY = "cmb2"
"""The body key :func:`~quill.core.wordpress.workbench_edit.body_for` gathers CMB2 changes under."""

_OBJECT = {"item": "post", "term": "term", "user": "user", "comment": "comment"}

#: CMB2 field types with a plain stored form.
_STRINGS = frozenset({
    "text", "text_small", "text_medium", "text_email", "text_url", "text_money", "textarea",
    "textarea_small", "textarea_code", "text_date", "text_time", "select_timezone",
    "colorpicker", "oembed", "wysiwyg", "text_datetime_timestamp_timezone",
})  # fmt: skip
_CHOICES = frozenset({"select", "radio", "radio_inline"})


def object_type_of(row_kind: str) -> str:
    """CMB2's ``object_type`` for a Workbench row kind; ``""`` for kinds CMB2 has no boxes for."""
    return _OBJECT.get(row_kind, "")


def _keyed(raw: Any, key: str = "id") -> dict[str, dict[str, Any]]:
    if isinstance(raw, dict):
        return {str(k): dict(v) for k, v in raw.items() if isinstance(v, dict)}
    found: dict[str, dict[str, Any]] = {}
    for one in raw if isinstance(raw, list) else []:
        if isinstance(one, dict) and one.get(key):
            found[str(one[key])] = dict(one)
    return found


def cmb2_boxes(api: WordPressApi) -> dict[str, dict[str, Any]]:
    """Every box CMB2 shows in REST, by id; ``{}`` when it shows none or will not say."""
    try:
        return _keyed(api.get(f"{CMB2_NAMESPACE}/boxes"))
    except WordPressApiError as exc:
        if exc.status in (401, 403, 404):
            return {}
        raise


def boxes_for(boxes: Mapping[str, Mapping[str, Any]], row_kind: str, slug: str = "") -> list[str]:
    """The boxes that apply to one object: by post type for items, by kind for the rest."""
    wanted = slug if row_kind == "item" else object_type_of(row_kind)
    found: list[str] = []
    for box_id, box in boxes.items():
        types = box.get("object_types")
        names = [str(t) for t in types] if isinstance(types, list) else [str(types or "")]
        if wanted and wanted in names:
            found.append(box_id)
    return found


def _writable(box: Mapping[str, Any]) -> bool:
    said = str(box.get("show_in_rest", "") or "").upper()
    return not said or any(word in said for word in ("POST", "EDITABLE", "ALLMETHODS", "PUT"))


def cmb2_schema(one: Mapping[str, Any]) -> dict[str, Any]:
    """A CMB2 field's JSON schema from its type; ``{}`` for a type with no plain form."""
    kind = str(one.get("type", ""))
    options = one.get("options")
    choices = [str(k) for k in options] if isinstance(options, (dict, list)) else []
    if kind in _STRINGS:
        spec: dict[str, Any] = {"type": "string"}
    elif kind in _CHOICES and choices:
        spec = {"type": "string", "enum": choices}
    elif kind == "checkbox":
        spec = {"type": "string", "enum": ["on", ""]}  # CMB2 stores "on", or nothing
    elif kind == "multicheck" and choices:
        spec = {"type": "array", "items": {"type": "string", "enum": choices}}
    elif kind in ("text_date_timestamp", "text_datetime_timestamp"):
        spec = {"type": "integer"}
    elif kind == "group":
        inner = _keyed(one.get("fields"))
        props = {k: cmb2_schema(v) for k, v in inner.items()}
        if not props or not all(props.values()):
            return {}
        spec = {"type": "array", "items": {"type": "object", "properties": props}}
    else:
        return {}
    if one.get("repeatable") and kind != "group":
        spec = {"type": "array", "items": spec}
    spec["title"] = str(one.get("name") or one.get("id") or "")
    if one.get("description"):
        spec["description"] = str(one["description"])
    return spec


def cmb2_page(api: WordPressApi, row_kind: str, slug: str, object_id: int) -> PluginPage | None:
    """The CMB2 page for one object, every box that applies to it; ``None`` when none does."""
    from quill.core.wordpress.workbench_sheets import _scalar

    object_type = object_type_of(row_kind)
    if not object_type or not object_id:
        return None
    boxes = cmb2_boxes(api)
    fields: list[FieldSpec] = []
    shown: dict[str, Value] = {}
    lookup: dict[str, dict[str, Any]] = {}
    before: dict[str, Any] = {}
    for box_id in boxes_for(boxes, row_kind, slug):
        box = boxes[box_id]
        raw = api.get(
            f"{CMB2_NAMESPACE}/boxes/{box_id}/fields",
            object_id=object_id,
            object_type=object_type,
        )
        why_box = "" if _writable(box) else "this box is shown in REST for reading only."
        for field_id, one in _keyed(raw).items():
            key = f"{CMB2_BODY}.{box_id}.{field_id}"
            spec = cmb2_schema(one)
            why = why_box
            if not spec:
                why = why or f"its kind ({one.get('type') or 'not said'}) has no plain form."
                spec = {"title": str(one.get("name") or field_id)}
            title = str(box.get("title") or box_id)
            built, writable = plugin_field(
                key, field_id, spec, plugin="CMB2", why_not=why, note=f"In the box {title}."
            )
            fields.append(built)
            shown[key] = _scalar(one.get("value"))
            before[f"{box_id}.{field_id}"] = one.get("value")
            if writable:
                lookup[key] = spec
    if not fields:
        return None
    return PluginPage("CMB2", CMB2_BODY, "CMB2", tuple(fields), shown, lookup, before)


def _same(a: Any, b: Any) -> bool:
    from quill.core.wordpress.workbench_edit import _comparable

    return bool(_comparable(a) == _comparable(b))


def save_with_cmb2(
    api: WordPressApi,
    row: WbRow,
    body: Mapping[str, Any],
    *,
    loaded_modified: str = "",
    before: Mapping[str, Any] | None = None,
) -> Any:
    """:func:`~quill.core.wordpress.workbench_edit.save`, then each CMB2 field on its own route.

    The result's sentence counts both, names any field the site did not keep,
    and its undo body carries the CMB2 values as they were, so Ctrl+Z goes back
    through here.
    """
    from quill.core.wordpress.workbench_edit import _FIELD_GROUPS, SaveResult, save

    main = {k: v for k, v in body.items() if k != CMB2_BODY}
    writes = body.get(CMB2_BODY)
    writes = dict(writes) if isinstance(writes, Mapping) else {}
    if not writes:
        return save(api, row, main, loaded_modified=loaded_modified, before=before)
    result = save(api, row, main, loaded_modified=loaded_modified, before=before) if main else None
    object_type = object_type_of(row.kind)
    missed: list[str] = []
    for where, value in writes.items():
        box_id, _dot, field_id = where.partition(".")
        route = f"{CMB2_NAMESPACE}/boxes/{box_id}/fields/{field_id}"
        api.post(route, {"object_id": row.object_id, "object_type": object_type, "value": value})
        kept = api.get(route, object_id=row.object_id, object_type=object_type)
        if not _same(kept.get("value") if isinstance(kept, dict) else None, value):
            missed.append(f"{CMB2_BODY}.{where}")
    old = (before or {}).get(CMB2_BODY)
    old = old if isinstance(old, Mapping) else {}
    undo = {**dict(result.undo if result else {}), CMB2_BODY: {k: old.get(k) for k in writes}}
    count = len(writes) + sum(
        len(v) if k in _FIELD_GROUPS and isinstance(v, Mapping) else 1 for k, v in main.items()
    )
    noun = "change" if count == 1 else "changes"
    sentence = f"Saved {count} {noun} to {row.title} on {row.site}."
    not_kept = (*(result.not_kept if result else ()), *missed)
    if not_kept:
        sentence += f" The site did not keep: {', '.join(not_kept)}."
    return SaveResult(result.raw if result else {}, sentence, tuple(not_kept), undo)
