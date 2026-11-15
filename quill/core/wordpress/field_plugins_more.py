"""Meta Box and Pods fields on Properties, beside Advanced Custom Fields (WP-R-034).

Each adapter follows the ACF pattern in :mod:`~quill.core.wordpress.field_plugins`:
detection costs at most the request Properties makes anyway, the plugin gets a
page of its own on an item's, term's, user's or comment's sheet, and a save is
checked against the field's schema before it is sent and verified after
(:func:`quill.core.wordpress.workbench_edit.save`). The REST shapes below are
each plugin's documented exposure; no live site was used to build them.

**Meta Box**, through its MB REST API extension. Every object a field group
applies to carries one extra field::

    GET  wp/v2/posts/12?context=edit  ->  {..., "meta_box": {"venue": "The Hall",
                                                             "seats": 120}}
    POST wp/v2/posts/12  {"meta_box": {"seats": 140}}   (the same route)

MB REST API registers ``meta_box`` with ``register_rest_field`` and usually no
schema, so a field's type is taken from the value it holds now (a number stays
a number, a list of words stays one); a field whose value says nothing about its
type (empty, or a list of lists) is read only, and its help says so. When a
site's schema does describe ``meta_box`` (``properties`` under it), that wins.

**Pods**, through the REST fields it adds per pod. A pod with REST enabled
adds each field it shows as its own top-level field on the pod's ``wp/v2``
route, writable where the pod or the field allows writing::

    GET pods/v1/pods?return_type=full -> {"pods": [{"name": "book",
        "type": "post_type", "label": "Books", "rest_enable": "1",
        "read_all": "0", "write_all": "0",
        "fields": {"isbn": {"name": "isbn", "label": "ISBN", "type": "text",
                            "rest_read": "1", "rest_write": "1"}}}]}
    GET  wp/v2/book/7  ->  {..., "isbn": "978..."}
    POST wp/v2/book/7  {"isbn": "978..."}

``pods/v1`` needs Pods' admin capability; without it there is no way to tell
which top-level fields are Pods', so no Pods page is shown rather than a guess.
Relationship (``pick``), file and other fields whose REST form depends on the
pod's settings are read only here.

Wx-free.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from quill.core.wordpress import custom_field_shapes as shapes
from quill.core.wordpress import custom_fields as cf
from quill.core.wordpress.api import WordPressApi, WordPressApiError
from quill.core.workbench.properties import FieldKind, FieldSpec, PageSpec, SheetSpec, Value

__all__ = [
    "METABOX_PROPERTY",
    "PODS_NAMESPACE",
    "PODS_PREFIX",
    "PluginPage",
    "box_text",
    "box_value",
    "infer_schema",
    "metabox_page",
    "plugin_field",
    "pod_for",
    "pod_fields",
    "pods_definitions",
    "pods_page",
    "pods_schema",
    "structured_fields",
    "with_pages",
]

METABOX_PROPERTY = "meta_box"
PODS_NAMESPACE = "pods/v1"
PODS_PREFIX = "pods."
"""Sheet keys of Pods fields; :func:`~quill.core.wordpress.workbench_edit.body_for`
sends them as the top-level fields they are."""

#: The object kinds a Workbench row can be, as Pods names its pod types.
_POD_TYPES = {"item": "post_type", "term": "taxonomy", "user": "user", "comment": "comment"}

#: Pods field types with a plain REST form, as JSON schema; the rest are read only.
_PODS_TYPES: dict[str, dict[str, Any]] = {
    "text": {"type": "string"},
    "paragraph": {"type": "string"},
    "wysiwyg": {"type": "string"},
    "code": {"type": "string"},
    "email": {"type": "string", "format": "email"},
    "phone": {"type": "string"},
    "website": {"type": "string", "format": "uri"},
    "password": {"type": "string"},
    "color": {"type": "string"},
    "slug": {"type": "string"},
    "oembed": {"type": "string"},
    "date": {"type": "string"},
    "time": {"type": "string"},
    "datetime": {"type": "string"},
    "number": {"type": "number"},
    "currency": {"type": "number"},
    "boolean": {"type": "boolean"},
}


_T = FieldKind.TEXT


@dataclass(frozen=True)
class PluginPage:
    """One field plugin's page on a sheet, the values it shows, and the checks for a save."""

    plugin: str
    key: str
    title: str
    fields: tuple[FieldSpec, ...]
    values: dict[str, Value] = field(default_factory=dict)
    #: Sheet key -> the schema a save is checked against (writable fields only).
    lookup: dict[str, dict[str, Any]] = field(default_factory=dict)
    #: What the page adds to the object as loaded, for Ctrl+Z (CMB2's values).
    before: dict[str, Any] = field(default_factory=dict)


def with_pages(
    sheet: SheetSpec, pages: Sequence[PluginPage]
) -> tuple[SheetSpec, dict[str, Value], dict[str, dict[str, Any]]]:
    """*sheet* with each plugin's page added, the values they show, and their checks."""
    values: dict[str, Value] = {}
    lookup: dict[str, dict[str, Any]] = {}
    added: list[PageSpec] = []
    taken = {spec.key for spec in sheet.fields()}
    for page in pages:
        fields = tuple(f for f in page.fields if f.key not in taken)
        if not fields:
            continue
        added.append(PageSpec(page.key, page.title, fields))
        values.update(page.values)
        lookup.update(page.lookup)
    if not added:
        return sheet, values, lookup
    return SheetSpec(sheet.kind, sheet.title, (*sheet.pages, *added)), values, lookup


def plugin_field(
    key: str, name: str, spec: Mapping[str, Any], *, plugin: str, why_not: str = "", note: str = ""
) -> tuple[FieldSpec, bool]:
    """One field from a plugin, and whether it can be written: by schema, or read only.

    *why_not* makes it read only with that reason; a schema QUILL cannot check
    every value of is read only too, so nothing is sent unchecked.
    """
    from quill.core.wordpress.workbench_sheets import _schema_field

    label = cf.label_for(name, spec)
    if not why_not and not (shapes.json_type(spec) and shapes.json_editable(spec)):
        why_not = f"{plugin} does not say what kind of value it holds, so QUILL leaves it as it is."
    if why_not:
        kind = FieldKind.MULTILINE if shapes.json_type(spec) in ("array", "object") else _T
        text = f"{name}, a {plugin} field. Read only here: {why_not} Change it in wp-admin."
        return FieldSpec(key, label, kind, True, help=text), False
    built = _schema_field(key, name, spec)
    help_text = f"{built.help} A {plugin} field.{(' ' + note) if note else ''}"
    return FieldSpec(
        key, label, built.kind, built.readonly, help=help_text, choices=built.choices
    ), not built.readonly


# -- Meta Box ---------------------------------------------------------------------------


def infer_schema(value: Any) -> dict[str, Any]:
    """A schema for *value* from what it holds: ``{}`` when the value cannot say."""
    if isinstance(value, bool):
        return {"type": "boolean"}
    if isinstance(value, int):
        return {"type": "integer"}
    if isinstance(value, float):
        return {"type": "number"}
    if isinstance(value, str):
        return {"type": "string"}
    if isinstance(value, list) and value:
        kinds = [infer_schema(v) for v in value]
        if all(k and k == kinds[0] for k in kinds) and kinds[0].get("type") != "array":
            if kinds[0].get("type") == "object":  # a list of groups: every key any row has
                props: dict[str, Any] = {}
                for k in kinds:
                    props.update(k["properties"])
                return {"type": "array", "items": {"type": "object", "properties": props}}
            return {"type": "array", "items": kinds[0]}
        return {}
    if isinstance(value, dict) and value:
        props = {str(k): infer_schema(v) for k, v in value.items()}
        if all(p and p.get("type") in shapes.SCALARS for p in props.values()):
            return {"type": "object", "properties": props}
    return {}


def metabox_page(properties: Mapping[str, Any], raw: Mapping[str, Any]) -> PluginPage | None:
    """The Meta Box page, when the schema or the object carries ``meta_box``; else ``None``."""
    declared = properties.get(METABOX_PROPERTY)
    values = raw.get(METABOX_PROPERTY)
    if not isinstance(declared, dict) and not isinstance(values, dict):
        return None
    described = declared.get("properties") if isinstance(declared, dict) else None
    schemas = {str(k): v for k, v in (described or {}).items() if isinstance(v, dict)}
    held = dict(values) if isinstance(values, dict) else {}
    from quill.core.wordpress.workbench_sheets import _scalar

    fields: list[FieldSpec] = []
    shown: dict[str, Value] = {}
    lookup: dict[str, dict[str, Any]] = {}
    for name in sorted(set(schemas) | set(held)):
        key = f"{METABOX_PROPERTY}.{name}"
        spec = schemas.get(name)
        note = ""
        if spec is None:
            spec = infer_schema(held.get(name))
            note = "Its kind is taken from the value it holds now; Meta Box does not describe it."
        built, writable = plugin_field(key, name, spec, plugin="Meta Box", note=note)
        fields.append(built)
        shown[key] = _scalar(held.get(name))
        if writable:
            lookup[key] = dict(spec)
    if not fields:
        return None
    return PluginPage("Meta Box", METABOX_PROPERTY, "Meta Box", tuple(fields), shown, lookup)


# -- Pods -------------------------------------------------------------------------------


def _on(value: Any) -> bool:
    return str(value).strip().lower() in ("1", "true", "yes", "on")


def pods_definitions(api: WordPressApi) -> list[dict[str, Any]] | None:
    """Every pod and its fields (``pods/v1/pods``); ``pods/v1/pods`` ``None`` if unreadable."""
    try:
        raw = api.get(f"{PODS_NAMESPACE}/pods", return_type="full")
    except WordPressApiError as exc:
        if exc.status in (401, 403, 404):
            return None
        raise
    found = raw.get("pods") if isinstance(raw, dict) else raw
    if isinstance(found, dict):  # some versions key the pods by name
        found = list(found.values())
    return [dict(p) for p in found or [] if isinstance(p, dict)] if isinstance(found, list) else []


def _option(thing: Mapping[str, Any], name: str) -> Any:
    """A pod's or field's option, at the top or under ``options`` (Pods has used both)."""
    if name in thing:
        return thing[name]
    options = thing.get("options")
    return options.get(name) if isinstance(options, dict) else None


def pod_for(
    pods: Sequence[Mapping[str, Any]], row_kind: str, slug: str = ""
) -> dict[str, Any] | None:
    """The pod behind one Workbench row kind (and post type or taxonomy *slug*)."""
    wanted = _POD_TYPES.get(row_kind)
    for pod in pods:
        if str(pod.get("type", "")) != wanted:
            continue
        if wanted in ("post_type", "taxonomy") and str(pod.get("name", "")) != slug:
            continue
        return dict(pod)
    return None


def pod_fields(pod: Mapping[str, Any]) -> list[dict[str, Any]]:
    """A pod's fields as a list, whether Pods sent them keyed by name or as a list."""
    raw = pod.get("fields")
    items = raw.values() if isinstance(raw, dict) else raw if isinstance(raw, list) else []
    return [dict(f) for f in items if isinstance(f, dict) and f.get("name")]


def pods_schema(one: Mapping[str, Any]) -> dict[str, Any]:
    """A Pods field's JSON schema from its type, with its label and help; ``{}`` when not plain."""
    base = _PODS_TYPES.get(str(one.get("type", "")))
    if base is None:
        return {}
    spec = dict(base)
    spec["title"] = str(one.get("label") or one.get("name"))
    if one.get("description"):
        spec["description"] = str(one["description"])
    return spec


def pods_page(pod: Mapping[str, Any], raw: Mapping[str, Any]) -> PluginPage | None:
    """The Pods page for one object: the pod's fields the object carries in REST."""
    from quill.core.wordpress.workbench_sheets import _scalar

    write_all = _on(_option(pod, "write_all"))
    fields: list[FieldSpec] = []
    shown: dict[str, Value] = {}
    lookup: dict[str, dict[str, Any]] = {}
    for one in pod_fields(pod):
        name = str(one["name"])
        if name not in raw:  # Pods shows only the fields set to show in REST
            continue
        key = f"{PODS_PREFIX}{name}"
        spec = pods_schema(one)
        why_not = ""
        if not spec:
            why_not = (
                f"its kind ({one.get('type') or 'not said'}) has a REST form that depends "
                "on the pod's settings."
            )
            spec = {"title": str(one.get("label") or name)}
        elif not (write_all or _on(_option(one, "rest_write"))):
            why_not = "the pod does not let it be written over REST (Allow write in REST is off)."
        built, writable = plugin_field(key, name, spec, plugin="Pods", why_not=why_not)
        fields.append(built)
        shown[key] = _scalar(raw.get(name))
        if writable:
            lookup[key] = spec
    if not fields:
        return None
    title = f"Pods ({pod.get('label') or pod.get('name')})"
    return PluginPage("Pods", "pods", title, tuple(fields), shown, lookup)


# -- lists and groups in a Properties text box (WP-R-033) --------------------------------


def structured_fields(sheet: SheetSpec, lookup: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    """Fields of *sheet* the list and group windows can edit, each with its schema.

    *lookup* is the save's checks: registered meta by its key (``venue`` for the
    field ``meta.venue``), a plugin's by its sheet key. Only a list or group
    whose every value has a control qualifies (:func:`custom_field_shapes.editable`);
    anything deeper keeps its JSON box, and a schema QUILL cannot check stays
    read only, as before.
    """
    found: dict[str, dict[str, Any]] = {}
    for spec in sheet.fields():
        if spec.readonly or spec.kind is not FieldKind.MULTILINE:
            continue
        schema = lookup.get(spec.key)
        if schema is None and spec.key.startswith("meta."):
            schema = lookup.get(spec.key.removeprefix("meta."))
        if not isinstance(schema, dict):
            continue
        if shapes.shape_of(schema) in ("list", "group") and shapes.editable(schema):
            found[spec.key] = dict(schema)
    return found


def box_value(text: str, schema: Mapping[str, Any]) -> Any:
    """What a list or group's text box holds, as a value; ``None`` when it is not valid JSON.

    An empty box is an empty list or group.
    """
    shape = shapes.shape_of(schema)
    if not text.strip():
        return [] if shape == "list" else {}
    try:
        value = json.loads(text)
    except ValueError:
        return None
    return value if isinstance(value, list if shape == "list" else dict) else None


def box_text(value: Any) -> str:
    """A list or group as its text box shows it (the same JSON Properties loads)."""
    return json.dumps(value, ensure_ascii=False, indent=1)
