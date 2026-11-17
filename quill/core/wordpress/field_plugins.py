"""Fields that a field plugin shows in REST: Advanced Custom Fields first (WP-R-034).

Advanced Custom Fields (ACF) does not use registered meta for its fields.
When a field group has "Show in REST API" on, ACF adds one property, ``acf``,
to the route's schema (an object whose properties are the group's fields by
name) and to each item (``"acf": {"venue_name": "The Hall", ...}``). So the
fields are found the same way custom fields are: one ``OPTIONS`` request on
the route, then ``_fields=acf`` on the item.

Read and write, behind detection: a site with no ``acf`` property in the
schema costs one request (the schema, which Properties reads anyway) and
nothing more. A site that has it gets an **Advanced Custom Fields** page on
an item's, term's, user's or comment's Properties (:func:`with_acf_page`),
built by the same schema rules as registered meta, and a save goes back as
``{"acf": {...}}`` on the same route, checked and coerced first and verified
after (:mod:`~quill.core.wordpress.workbench_edit`). Only fields in a group
with "Show in REST API" on reach REST; the rest stay in wp-admin.

Meta Box and Pods (:mod:`~quill.core.wordpress.field_plugins_more`) and CMB2
(:mod:`~quill.core.wordpress.field_plugins_cmb2`) follow the same pattern, each
through its own REST exposure; :func:`plugin_pages` gathers whichever pages a
site has for one object. :data:`FIELD_PLUGIN_SCOPE` says, honestly, what each
plugin gets.

Wx-free.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from quill.core.wordpress import custom_fields as cf
from quill.core.wordpress.api import WordPressApi
from quill.core.workbench.properties import PageSpec, SheetSpec

__all__ = [
    "FIELD_PLUGIN_SCOPE",
    "FieldPluginScope",
    "PluginFields",
    "acf_lookup",
    "acf_schema",
    "acf_values",
    "meta_from_properties",
    "plugin_pages",
    "read_acf",
    "route_properties",
    "with_acf_page",
]

#: The property ACF adds to a route's schema and to each item.
ACF_PROPERTY = "acf"


@dataclass
class PluginFields:
    """One field plugin's fields on one item: which plugin, the form, the raw values."""

    plugin: str
    form: cf.CustomFields
    values: dict[str, Any] = field(default_factory=dict)

    @property
    def count(self) -> int:
        return len(self.form.fields) + len(self.form.structured)


def route_properties(api: WordPressApi, route: str) -> dict[str, Any]:
    """``schema.properties`` of *route*, from an ``OPTIONS`` request, or ``{}``."""
    payload = api.request("OPTIONS", route).payload
    schema = payload.get("schema") if isinstance(payload, dict) else None
    props = schema.get("properties") if isinstance(schema, dict) else None
    return dict(props) if isinstance(props, dict) else {}


def acf_schema(properties: Mapping[str, Any]) -> dict[str, Any] | None:
    """ACF's fields by name when the schema shows them; ``None`` when ACF is not there.

    An ``acf`` property with no fields (a group with nothing in REST) is ``{}``,
    which is ACF being there with nothing to show.
    """
    found = properties.get(ACF_PROPERTY)
    if not isinstance(found, dict):
        return None
    fields = found.get("properties")
    if not isinstance(fields, dict):
        return {}
    return {str(k): v for k, v in fields.items() if isinstance(v, dict)}


def read_acf(
    api: WordPressApi,
    route: str,
    item_id: int,
    *,
    properties: Mapping[str, Any] | None = None,
) -> PluginFields | None:
    """The ACF fields of one item on *route*, or ``None`` when the site does not show any.

    *properties* is the route's schema properties when the caller already has
    them (Custom Fields reads them for ``meta``), saving the ``OPTIONS`` request.
    """
    props = route_properties(api, route) if properties is None else properties
    schema = acf_schema(props)
    if schema is None:
        return None
    values: dict[str, Any] = {}
    if item_id and schema:
        raw = api.get(f"{route}/{item_id}", context="edit", _fields=ACF_PROPERTY)
        found = raw.get(ACF_PROPERTY) if isinstance(raw, dict) else None
        # ACF answers an item with no saved fields as an empty list, not {}.
        values = dict(found) if isinstance(found, dict) else {}
    return PluginFields("Advanced Custom Fields", cf.build_form(schema, values, {}), values)


# -- Properties sheets ------------------------------------------------------------------


def meta_from_properties(properties: Mapping[str, Any]) -> dict[str, Any]:
    """``meta.properties`` from a route's schema properties (one ``OPTIONS`` for meta and ACF)."""
    meta = properties.get("meta")
    found = meta.get("properties") if isinstance(meta, dict) else None
    return dict(found) if isinstance(found, dict) else {}


def with_acf_page(sheet: SheetSpec, schema: Mapping[str, Any] | None) -> SheetSpec:
    """*sheet* with an Advanced Custom Fields page, when the site shows any ACF fields."""
    if not schema:
        return sheet
    from quill.core.wordpress.workbench_sheets import _schema_field

    fields = tuple(
        _schema_field(f"{ACF_PROPERTY}.{name}", cf.label_for(name, spec), spec)
        for name, spec in sorted(schema.items())
        if isinstance(spec, dict)
    )
    if not fields:
        return sheet
    page = PageSpec(ACF_PROPERTY, "Advanced Custom Fields", fields)
    return SheetSpec(sheet.kind, sheet.title, (*sheet.pages, page))


def acf_values(raw: Mapping[str, Any]) -> dict[str, Any]:
    """What each ACF field shows, keyed as the page's fields are (``acf.venue``)."""
    from quill.core.wordpress.workbench_sheets import _scalar

    found = raw.get(ACF_PROPERTY)
    if not isinstance(found, dict):  # ACF sends [] for an item with nothing saved
        return {}
    return {f"{ACF_PROPERTY}.{key}": _scalar(value) for key, value in found.items()}


def acf_lookup(schema: Mapping[str, Any] | None) -> dict[str, Any]:
    """ACF's field schemas under the page's keys, for the save's checks."""
    return {f"{ACF_PROPERTY}.{k}": v for k, v in (schema or {}).items() if isinstance(v, dict)}


def plugin_pages(
    api: WordPressApi,
    *,
    row_kind: str,
    slug: str,
    object_id: int,
    properties: Mapping[str, Any],
    raw: Mapping[str, Any],
    namespaces: Sequence[str] = (),
) -> list[Any]:
    """The Meta Box, Pods and CMB2 pages one object has, each only where the site shows it.

    Meta Box costs nothing more (its ``meta_box`` is in the object or schema
    already read); Pods and CMB2 cost one request each, and only when their
    namespace is in the site's index. A plugin that refuses this account
    (``401``, ``403``) gets no page rather than a wrong one.
    """
    from quill.core.wordpress import field_plugins_cmb2 as cmb2
    from quill.core.wordpress import field_plugins_more as more

    have = {n.strip("/") for n in namespaces}
    pages: list[Any] = []
    found = more.metabox_page(properties, raw)
    if found is not None:
        pages.append(found)
    if more.PODS_NAMESPACE in have:
        pods = more.pods_definitions(api)
        pod = more.pod_for(pods or [], row_kind, slug)
        page = more.pods_page(pod, raw) if pod else None
        if page is not None:
            pages.append(page)
    if cmb2.CMB2_NAMESPACE in have:
        page = cmb2.cmb2_page(api, row_kind, slug, object_id)
        if page is not None:
            pages.append(page)
    return pages


# -- what each field plugin gets ---------------------------------------------------------


@dataclass(frozen=True)
class FieldPluginScope:
    """One field plugin: how its fields reach REST, and what the Workbench does with them."""

    plugin: str
    exposure: str
    status: str  #: "read and write", "as registered meta" or "not integrated"
    workbench: str


FIELD_PLUGIN_SCOPE: tuple[FieldPluginScope, ...] = (
    FieldPluginScope(
        "Advanced Custom Fields",
        "an acf property on the route's schema and on each object, for groups with Show in "
        "REST API on",
        "read and write",
        "Properties has an Advanced Custom Fields page on items, terms, users and comments; a "
        'save goes back as {"acf": {...}}, checked against the schema and verified. Field '
        "groups themselves are defined in wp-admin, and are read only here.",
    ),
    FieldPluginScope(
        "Meta Box",
        "a meta_box property on each object from its MB REST API extension, or fields "
        "registered as post meta with show_in_rest",
        "read and write",
        "Properties has a Meta Box page on items, terms, users and comments; a save goes back "
        'as {"meta_box": {...}} on the same route, checked and verified. A field Meta Box does '
        "not describe takes its kind from the value it holds; one whose value cannot say is read "
        "only. Its field groups are listed in Content Model where its own posts are in REST.",
    ),
    FieldPluginScope(
        "Pods",
        "fields shown as REST fields on each pod's wp/v2 route, described by its pods/v1 routes",
        "read and write",
        "Properties has a Pods page with the pod's fields, read from pods/v1/pods; a save sends "
        "each as its own REST field, only where the pod allows writing in REST, checked and "
        "verified. Relationship and file fields are read only. Content Model lists every pod "
        "and its fields, and can copy one to QUILL Site Types.",
    ),
    FieldPluginScope(
        "CMB2",
        "boxes with show_in_rest, served under cmb2/v1, one route per field",
        "read and write",
        "Properties has a CMB2 page with every box that applies; a save sends each field to its "
        "own cmb2/v1 route and reads it back to check the site kept it. Boxes shown for reading "
        "only, and file and taxonomy fields, are read only. Content Model lists the boxes.",
    ),
    FieldPluginScope(
        "Registered meta (any plugin or theme)",
        "register_meta or register_post_meta with show_in_rest",
        "read and write",
        "Every registered field, scalar or schema-backed list and object, on the Meta or "
        "Custom Fields page of items, terms, users and comments; unsupported schemas stay "
        "read only.",
    ),
)
"""Every field plugin the PRD names (WP-R-034, WP-R-038), with what QUILL really does."""
