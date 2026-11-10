"""Custom fields: the post meta a site registers for the REST API (wordpress.md 9.15).

A plugin or theme that registers meta with ``show_in_rest`` puts it in the
schema of the post type's route, under ``properties.meta.properties``. That
schema is read with an ``OPTIONS`` request and turned into the same labelled
fields Insert Block's forms use (:class:`~quill.core.wordpress.block_catalog.Field`),
so an SEO title, an event date or a subtitle is one more edit field in
Properties. Lists and groups (``array`` and ``object`` meta: speakers, an
address, a repeater's rows) are :class:`~quill.core.wordpress.custom_field_shapes.StructuredField`
rows, edited whole and sent back whole (WP-R-033); only a schema QUILL cannot
edit safely (a list with no ``items``, a list of lists) is left as the site
has it and counted, never dropped.

Terms, users and comments carry meta the same way (``meta`` in their route's
schema), so :func:`object_route`, :func:`meta_schema_for`,
:func:`site_values_for` and :func:`send_meta` read and write it for any of
them.

Wx-free.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

from quill.core.error_codes import CodedError
from quill.core.wordpress import custom_field_shapes as shapes
from quill.core.wordpress.api import WordPressApi
from quill.core.wordpress.block_catalog import Field, assign_access_keys
from quill.core.wordpress.site import kind_route, taxonomy_route

#: Meta keys the block editor and core use for their own plumbing.
_PLUMBING = frozenset({"footnotes", "_wp_note_status"})

_SHORT = 80


@dataclass
class CustomFields:
    """The form for one item, and what the site had before it was shown."""

    fields: list[Field] = field(default_factory=list)
    #: Key -> value on the site now, for every field shown.
    site_values: dict[str, Any] = field(default_factory=dict)
    #: Key -> JSON type ("string", "integer", "number", "boolean", "array", "object").
    types: dict[str, str] = field(default_factory=dict)
    #: The lists and groups, each edited on its own (WP-R-033).
    structured: list[shapes.StructuredField] = field(default_factory=list)
    #: How many registered fields QUILL cannot edit safely, left as they are.
    left_alone: int = 0


#: The objects that carry registered meta, besides a post's own kind.
OBJECT_TYPES = ("post", "term", "user", "comment")


def object_route(api: WordPressApi | None, object_type: str, subtype: str = "") -> str:
    """The collection route for an object's meta: a post kind, a taxonomy, users or comments.

    *subtype* is the post kind (``post``, ``tribe_events``) or the taxonomy
    (``product_cat``); a taxonomy's route is the site's own ``rest_base``.
    """
    if object_type == "term":
        return taxonomy_route(subtype or "category", api)
    if object_type == "user":
        return "wp/v2/users"
    if object_type == "comment":
        return "wp/v2/comments"
    return kind_route(subtype or "post")


def meta_schema_for(api: WordPressApi, route: str) -> dict[str, Any]:
    """``properties.meta.properties`` of *route*'s schema (an ``OPTIONS`` request), or ``{}``."""
    payload = api.request("OPTIONS", route).payload
    schema = payload.get("schema") if isinstance(payload, dict) else None
    props = schema.get("properties") if isinstance(schema, dict) else None
    meta = props.get("meta") if isinstance(props, dict) else None
    found = meta.get("properties") if isinstance(meta, dict) else None
    return dict(found) if isinstance(found, dict) else {}


def site_values_for(api: WordPressApi, route: str, item_id: int) -> dict[str, Any]:
    """The meta one object has on the site now, by key."""
    if not item_id:
        return {}
    raw = api.get(f"{route}/{item_id}", context="edit", _fields="meta")
    meta = raw.get("meta") if isinstance(raw, dict) else None
    return dict(meta) if isinstance(meta, dict) else {}


def send_meta(api: WordPressApi, route: str, item_id: int, changed: Mapping[str, Any]) -> Any:
    """Write *changed* meta to one term, user or comment now (posts go with the next send)."""
    return api.post(f"{route}/{item_id}", {"meta": dict(changed)}, context="edit")


def meta_schema(api: WordPressApi, kind: str) -> dict[str, Any]:
    """``properties.meta.properties`` of the kind's route schema, or ``{}``."""
    return meta_schema_for(api, kind_route(kind))


def site_values(api: WordPressApi, kind: str, item_id: int) -> dict[str, Any]:
    return site_values_for(api, kind_route(kind), item_id)


def label_for(key: str, schema: Mapping[str, Any]) -> str:
    title = str(schema.get("title", "") or "").strip()
    if title:
        return title
    words = key.lstrip("_").replace("_", " ").replace("-", " ").strip()
    return words[:1].upper() + words[1:] if words else key


def help_for(key: str, schema: Mapping[str, Any]) -> str:
    description = str(schema.get("description", "") or "").strip()
    base = description or "A custom field this site registers"
    return (
        f"{base.rstrip('.')}. Saved as {key} and sent with your next Save Draft to Site or Publish."
    )


def field_for(key: str, spec: Mapping[str, Any], current: Any, *, help_text: str) -> Field:
    """One labelled control for a scalar value: a choice, a check box or a text box."""
    kind = shapes.json_type(spec)
    label = label_for(key, spec)
    enum = spec.get("enum")
    if isinstance(enum, list) and enum:
        f = Field(key, label + ":", "choice", help_text, current)
        f.choices, f.values = [str(v) for v in enum], list(enum)
        return f
    if kind == "boolean":
        return Field(key, label, "check", help_text, bool(current))
    text = "" if current is None else str(current)
    long = kind == "string" and (len(text) > _SHORT or "\n" in text)
    return Field(key, label + ":", "multiline" if long else "text", help_text, text)


def build_form(
    schema: Mapping[str, Any], values: Mapping[str, Any], kept: Mapping[str, Any]
) -> CustomFields:
    """The fields to show: the site's value, or the one kept with the copy if changed."""
    out = CustomFields()
    for key, spec in schema.items():
        if key in _PLUMBING or not isinstance(spec, dict):
            continue
        shape = shapes.shape_of(spec)
        if shape in ("list", "group") and shapes.editable(spec):
            site_value = values.get(key, spec.get("default", shapes.blank(spec)))
            out.site_values[key] = site_value
            out.types[key] = shapes.json_type(spec)
            out.structured.append(
                shapes.StructuredField(
                    key,
                    label_for(key, spec),
                    help_for(key, spec),
                    shape,
                    dict(spec),
                    kept.get(key, site_value),
                )
            )
            continue
        if shape != "scalar":
            out.left_alone += 1
            continue
        current = kept.get(key, values.get(key, spec.get("default")))
        out.site_values[key] = values.get(key, spec.get("default"))
        out.types[key] = shapes.json_type(spec)
        out.fields.append(field_for(key, spec, current, help_text=help_for(key, spec)))
    for f, label in zip(out.fields, assign_access_keys([f.label for f in out.fields]), strict=True):
        f.label = label
    return out


class FieldValueError(CodedError):
    """A number field that does not hold a number (never raised past the command)."""

    code = "QUILL-WP-FIELDS-NOT-A-NUMBER"

    def __init__(self, field_label: str) -> None:
        super().__init__(field_label)
        self.field_label = field_label


def changes(form: CustomFields, answers: Mapping[str, Any]) -> dict[str, Any]:
    """The fields whose answer differs from the site's value, typed for the site.

    Raises :class:`FieldValueError` naming the field when a number field holds
    something that is not a number.
    """
    out: dict[str, Any] = {}
    labels = {f.key: f.label.replace("&", "").rstrip(":") for f in form.fields}
    for key, answer in answers.items():
        kind = form.types.get(key, "string")
        value: Any = answer
        if kind in ("integer", "number") and not isinstance(answer, (int, float)):
            text = str(answer).strip()
            if not text:
                value = None
            else:
                try:
                    value = int(text) if kind == "integer" else float(text)
                except ValueError as exc:
                    raise FieldValueError(labels.get(key, key)) from exc
        before = form.site_values.get(key)
        if value == before or (value in ("", None) and before in ("", None)):
            continue
        out[key] = "" if value is None and kind == "string" else value
    return out


def structured_change(form: CustomFields, key: str, value: Any) -> tuple[bool, Any]:
    """``(changed, value)`` for one list or group: typed for the site, and compared with it.

    Raises :class:`FieldValueError` when a number inside it is not a number.
    """
    found = next((sf for sf in form.structured if sf.key == key), None)
    if found is None:
        return False, value
    typed = shapes.coerce(found.schema, value, found.label.replace("&", "").rstrip(":"))
    return typed != form.site_values.get(key), typed


def merge_kept(
    kept: Mapping[str, Any],
    form: CustomFields,
    changed: Mapping[str, Any],
    *,
    keys: Iterable[str] | None = None,
) -> dict[str, Any]:
    """The meta to keep with the copy after one page of answers.

    *keys* are the fields that page showed (the form's scalar fields when not
    given): each is replaced by its answer, or dropped when it went back to the
    site's value, and every other kept field (a list edited on its own) stays.
    """
    shown = set(keys) if keys is not None else {f.key for f in form.fields}
    out = {k: v for k, v in kept.items() if k not in shown}
    out.update(changed)
    return out
