"""Fields that a field plugin shows in REST: Advanced Custom Fields first (WP-R-034).

Advanced Custom Fields (ACF) does not use registered meta for its fields.
When a field group has "Show in REST API" on, ACF adds one property, ``acf``,
to the route's schema (an object whose properties are the group's fields by
name) and to each item (``"acf": {"venue_name": "The Hall", ...}``). So the
fields are found the same way custom fields are: one ``OPTIONS`` request on
the route, then ``_fields=acf`` on the item.

This is read support, behind detection: a site with no ``acf`` property in
the schema costs one request (the schema, which Custom Fields reads anyway)
and nothing more, and a site that has it gets the same
:class:`~quill.core.wordpress.custom_fields.CustomFields` form as its meta,
lists and groups included. Writing goes back as ``{"acf": {...}}``, which
ACF accepts on the same route; QUILL does not send it yet.

Meta Box, Pods and CMB2 expose fields their own ways and are not read here.

Wx-free.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from quill.core.wordpress import custom_fields as cf
from quill.core.wordpress.api import WordPressApi

__all__ = [
    "PluginFields",
    "acf_schema",
    "read_acf",
    "route_properties",
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
