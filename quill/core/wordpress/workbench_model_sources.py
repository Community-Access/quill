"""Who defines what on a site, from evidence, and the field groups (WP-R-036, WP-R-038).

The Content Model (:func:`quill.core.wordpress.workbench_discovered.model_rows`)
names who registered each post type, taxonomy and field group. WordPress's REST
API never says which plugin or theme registered a type, so the name comes only
from evidence the site gives, strongest first (:func:`provenance`):

1. a definition QUILL Site Types keeps;
2. one of WordPress's own types (a plugin that extends Posts does not own it);
3. a definition a field plugin lists through its own REST routes
   (:func:`read_plugin_definitions`);
4. the type's ``rest_namespace``, when it is not ``wp/v2`` (a known plugin's
   namespace names the plugin; any other is "the plugin behind" it);
5. a slug a known plugin registers, *and* that plugin's namespace in the index.

Anything else is **unknown**, said as such, never guessed from the slug.

**Definitions from the field plugins**, each as far as its REST reaches:

- **Pods**: ``GET pods/v1/pods?return_type=full`` lists every pod, its type
  (``post_type``, ``taxonomy``, ``user``, ``comment``), label, storage and fields.
- **Advanced Custom Fields** keeps its post types, taxonomies and field groups
  as posts of ``acf-post-type``, ``acf-taxonomy`` and ``acf-field-group``; those
  are not in REST unless the site shows them, and when it does the type's key is
  the post's excerpt. The fields themselves show on each route's schema as the
  ``acf`` property, which is read for every site.
- **Meta Box** keeps definitions as ``mb-post-type``, ``mb-taxonomy`` and
  ``meta-box`` posts (MB Builder, MB Custom Post Types), with the settings as JSON
  in the post content; read only where the site shows those types in REST. Its
  fields show as the ``meta_box`` property on schemas that describe it.
- **CMB2**: ``GET cmb2/v1/boxes`` lists the boxes in REST.
- **Custom Post Type UI** has no REST API: its definitions stay in wp-admin, so
  its types are "unknown" here, and when the plugin list shows it active the
  detail says it may be the one (:data:`DEFINITION_SOURCES`).

**Field groups** (:func:`field_group_rows`) come from every object route's
schema: its registered ``meta`` (one group per post type, taxonomy, users and
comments), the ``acf`` and ``meta_box`` properties, and the plugins' own lists.

**Moving to QUILL Site Types** is :mod:`~quill.core.wordpress.workbench_model_move`.

Wx-free; requests go through the site's own client.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from quill.core.wordpress.api import WordPressApi, WordPressApiError
from quill.core.wordpress.workbench_rows import WbRow

__all__ = [
    "CORE_META",
    "DEFINITION_SOURCES",
    "KNOWN_NAMESPACES",
    "DefinitionSource",
    "PluginDefinition",
    "Provenance",
    "field_group_rows",
    "plugin_for_namespace",
    "provenance",
    "read_plugin_definitions",
    "route_schemas",
]

#: Registered meta keys WordPress itself registers.
CORE_META = frozenset({"footnotes", "_wp_note_status"})

#: REST namespaces whose plugin is known, by their first part (or first two, which win).
KNOWN_NAMESPACES: tuple[tuple[str, str], ...] = (
    ("wp", "WordPress"),
    ("oembed", "WordPress"),
    ("wp-site-health", "WordPress"),
    ("wp-block-editor", "WordPress"),
    ("wp-abilities", "WordPress"),
    ("wc", "WooCommerce"),
    ("wc-analytics", "WooCommerce"),
    ("woocommerce", "WooCommerce"),
    ("tribe/tickets", "Event Tickets"),
    ("tribe", "The Events Calendar"),
    ("pmpro", "Paid Memberships Pro"),
    ("gf", "Gravity Forms"),
    ("qaf", "QUILL Accessible Forms"),
    ("quill-site-types", "QUILL Site Types"),
    ("acf", "Advanced Custom Fields"),
    ("pods", "Pods"),
    ("cmb2", "CMB2"),
    ("meta-box", "Meta Box"),
    ("mb", "Meta Box"),
    ("elementor", "Elementor"),
    ("jetpack", "Jetpack"),
    ("yoast", "Yoast SEO"),
    ("rankmath", "Rank Math"),
    ("ldlms", "LearnDash"),
    ("contact-form-7", "Contact Form 7"),
)

#: Slugs a plugin registers, believed only when that plugin's namespace is in the index.
_PLUGIN_SLUGS: tuple[tuple[str, str, frozenset[str]], ...] = (
    ("WooCommerce", "wc", frozenset({
        "product", "product_variation", "shop_order", "shop_order_refund", "shop_coupon",
        "product_cat", "product_tag", "product_shipping_class", "product_type",
        "product_visibility",
    })),
    ("The Events Calendar", "tribe", frozenset({
        "tribe_events", "tribe_venue", "tribe_organizer", "tribe_events_cat",
    })),
    ("Jetpack", "jetpack", frozenset({"feedback", "jetpack-portfolio", "jetpack-testimonial"})),
    ("Elementor", "elementor", frozenset({"elementor_library", "elementor_library_type"})),
    ("Contact Form 7", "contact-form-7", frozenset({"wpcf7_contact_form"})),
    ("LearnDash", "ldlms", frozenset({
        "sfwd-courses", "sfwd-lessons", "sfwd-topic", "sfwd-quiz", "sfwd-certificates",
    })),
    ("Advanced Custom Fields", "acf", frozenset({
        "acf-field-group", "acf-field", "acf-post-type", "acf-taxonomy", "acf-ui-options-page",
    })),
)  # fmt: skip

#: Where a field plugin keeps its definitions as posts (shown in REST only if the site does).
_DEFINITION_POSTS: tuple[tuple[str, str, str], ...] = (
    ("acf-post-type", "Advanced Custom Fields", "type"),
    ("acf-taxonomy", "Advanced Custom Fields", "taxonomy"),
    ("acf-field-group", "Advanced Custom Fields", "field_group"),
    ("mb-post-type", "Meta Box", "type"),
    ("mb-taxonomy", "Meta Box", "taxonomy"),
    ("meta-box", "Meta Box", "field_group"),
)

_CPT_UI = "custom-post-type-ui/custom-post-type-ui"


@dataclass(frozen=True)
class DefinitionSource:
    """One plugin that defines types or fields: what of its definitions REST shows."""

    plugin: str
    reads: str
    moves: str


DEFINITION_SOURCES: tuple[DefinitionSource, ...] = (
    DefinitionSource(
        "Advanced Custom Fields",
        "its fields on every route's schema (the acf property); its own post types, "
        "taxonomies and field groups only where the site shows those posts in REST",
        "a field group seen on a route's schema, and a post type or taxonomy, copied to QUILL "
        "Site Types after a preview; ACF keeps its own",
    ),
    DefinitionSource(
        "Pods",
        "every pod and its fields, through pods/v1/pods (needs Pods' admin capability)",
        "a pod's type, taxonomy or fields stored as meta, copied after a preview; Pods keeps it",
    ),
    DefinitionSource(
        "Meta Box",
        "fields on schemas that describe meta_box; its mb-post-type, mb-taxonomy and meta-box "
        "posts only where the site shows them in REST",
        "a field group seen on a route's schema, and a post type or taxonomy, copied after a "
        "preview",
    ),
    DefinitionSource(
        "CMB2",
        "every box in REST, through cmb2/v1/boxes",
        "a box's fields, copied as a field group after a preview",
    ),
    DefinitionSource(
        "Custom Post Type UI",
        "nothing: it has no REST API, so its types show as unknown, with a note when the "
        "plugin list shows it active",
        "its post types and taxonomies, copied from what WordPress says about them",
    ),
)
"""What each definition plugin the PRD names (WP-R-038) shows the Workbench."""


@dataclass(frozen=True)
class Provenance:
    """Who registered something, and the evidence for it, as a sentence."""

    owner: str
    evidence: str

    @property
    def known(self) -> bool:
        return self.owner != "unknown"


@dataclass(frozen=True)
class PluginDefinition:
    """A type, taxonomy or field group a plugin lists through its own REST routes."""

    plugin: str
    what: str  #: "type", "taxonomy" or "field_group"
    key: str
    name: str
    source: str  #: where it was read, in words
    fields: tuple[dict[str, Any], ...] = ()
    attach: tuple[str, ...] = ()
    #: Why it cannot be copied to QUILL Site Types ("" when it can).
    unmovable: str = ""


@dataclass
class _Found:
    definitions: list[PluginDefinition] = field(default_factory=list)
    cpt_ui: bool = False


def plugin_for_namespace(namespace: str) -> str:
    """The plugin behind a REST namespace (``tribe/events/v1``), or ``""`` when not known."""
    parts = namespace.strip("/").lower().split("/")
    for wanted in ("/".join(parts[:2]), parts[0]):
        found = next((name for prefix, name in KNOWN_NAMESPACES if wanted == prefix), "")
        if found:
            return found
    return ""


def _firsts(namespaces: Sequence[str]) -> set[str]:
    return {n.strip("/").split("/", 1)[0].lower() for n in namespaces}


def provenance(
    slug: str,
    rest_namespace: str = "wp/v2",
    *,
    namespaces: Sequence[str] = (),
    defined: Mapping[str, PluginDefinition] | None = None,
    core: frozenset[str] = frozenset(),
    cpt_ui: bool = False,
) -> Provenance:
    """Who registered *slug*, from the strongest evidence the site gives (see the module)."""
    if slug in core:  # first: Pods can extend Posts, and that does not make Posts its own
        return Provenance("WordPress", "It is one of WordPress's own.")
    found = (defined or {}).get(slug)
    if found is not None:
        return Provenance(found.plugin, f"{found.plugin} lists it in {found.source}.")
    namespace = (rest_namespace or "wp/v2").strip("/")
    if namespace != "wp/v2":
        owner = plugin_for_namespace(namespace)
        said = f"Its REST namespace is {namespace}."
        return Provenance(owner or f"the plugin behind {namespace}", said)
    firsts = _firsts(namespaces)
    for plugin, prefix, slugs in _PLUGIN_SLUGS:
        if slug in slugs and prefix in firsts:
            return Provenance(
                plugin,
                f"{plugin} registers a type of this name, and its REST namespace is on the site.",
            )
    said = (
        "The site does not say who registered it: WordPress's REST API does not name the "
        "plugin or theme behind a type."
    )
    if cpt_ui:
        said += (
            " Custom Post Type UI is active here and keeps its definitions in wp-admin only, "
            "so it may be the one."
        )
    return Provenance("unknown", said)


# -- reading definitions ----------------------------------------------------------------


def _quiet(api: WordPressApi, route: str, **params: Any) -> Any:
    """GET *route*, or ``None`` when this account may not read it or it is not there."""
    try:
        return api.get(route, **params)
    except WordPressApiError as exc:
        if exc.status in (400, 401, 403, 404):
            return None
        raise


def _pods(api: WordPressApi) -> list[PluginDefinition]:
    from quill.core.wordpress.field_plugins_more import (
        _option,
        pod_fields,
        pods_definitions,
        pods_schema,
    )

    found: list[PluginDefinition] = []
    for pod in pods_definitions(api) or []:
        kind = str(pod.get("type", ""))
        name = str(pod.get("name", ""))
        label = str(pod.get("label") or name)
        source = "its pods/v1 routes"
        if kind in ("post_type", "taxonomy") and name:
            found.append(
                PluginDefinition(
                    "Pods", "type" if kind == "post_type" else "taxonomy", name, label, source
                )  # fmt: skip
            )
        fields = []
        for one in pod_fields(pod):
            spec = pods_schema(one)
            fields.append({"name": str(one["name"]), "label": str(one.get("label") or ""),
                           "schema": spec, "plugin_type": str(one.get("type", ""))})  # fmt: skip
        if fields:
            storage = str(_option(pod, "storage") or "meta")
            found.append(
                PluginDefinition(
                    "Pods", "field_group", f"pods:{name}", f"Pods fields on {label}", source,
                    tuple(fields), (_attach_key(kind, name),),
                    "" if storage == "meta" else
                    f"the pod keeps its values in a table of its own ({storage}), not as meta.",
                )
            )  # fmt: skip
    return found


def _attach_key(kind: str, slug: str) -> str:
    """How a field group's attachment is named: a post type's slug, ``taxonomy:<slug>``,
    ``user`` or ``comment`` (anything else, such as a settings pod, by its kind)."""
    if kind in ("post_type", "type"):
        return slug
    if kind == "taxonomy":
        return f"taxonomy:{slug}"
    return kind


def _cmb2(api: WordPressApi) -> list[PluginDefinition]:
    from quill.core.wordpress.field_plugins_cmb2 import _keyed, cmb2_boxes, cmb2_schema

    found: list[PluginDefinition] = []
    for box_id, box in cmb2_boxes(api).items():
        types = box.get("object_types")
        attach = tuple(str(t) for t in types) if isinstance(types, list) else ()
        fields = tuple(
            {"name": fid, "label": str(one.get("name") or ""), "schema": cmb2_schema(one),
             "plugin_type": str(one.get("type", ""))}
            for fid, one in _keyed(box.get("fields")).items()
        )  # fmt: skip
        found.append(
            PluginDefinition(
                "CMB2",
                "field_group",
                f"cmb2:{box_id}",
                str(box.get("title") or box_id),
                "its cmb2/v1 boxes",
                fields,
                attach,
            )  # fmt: skip
        )
    return found


def _post_key(post: Mapping[str, Any], what: str) -> str:
    """The key a definition post stands for: its excerpt (ACF), JSON content (Meta Box), slug."""
    excerpt = post.get("excerpt")
    raw = excerpt.get("raw") if isinstance(excerpt, dict) else None
    if isinstance(raw, str) and re.fullmatch(r"[a-z0-9_-]{1,32}", raw.strip()):
        return raw.strip()
    content = post.get("content")
    text = content.get("raw") if isinstance(content, dict) else None
    try:
        settings = json.loads(text) if isinstance(text, str) and text.strip() else None
    except ValueError:
        settings = None
    if isinstance(settings, dict):
        for name in ("slug", "post_type", "taxonomy", "id"):
            if isinstance(settings.get(name), str) and settings[name]:
                return str(settings[name])
    return str(post.get("slug") or "")


def _definition_posts(api: WordPressApi, types: Mapping[str, Any]) -> list[PluginDefinition]:
    found: list[PluginDefinition] = []
    for slug, plugin, what in _DEFINITION_POSTS:
        info = types.get(slug)
        if not isinstance(info, dict) or not info.get("rest_base"):
            continue
        base = info["rest_base"]
        namespace = str(info.get("rest_namespace") or "wp/v2")
        posts = _quiet(api, f"{namespace}/{base}", context="edit", per_page=100)
        for post in posts if isinstance(posts, list) else []:
            if not isinstance(post, dict):
                continue
            key = _post_key(post, what)
            title = post.get("title")
            name = str((title.get("raw") or title.get("rendered")) if isinstance(title, dict)
                       else title or key)  # fmt: skip
            if key:
                found.append(
                    PluginDefinition(plugin, what, key if what != "field_group" else
                                     f"{slug}:{key}", name or key,
                                     f"its {slug} posts, which this site shows in REST")
                )  # fmt: skip
    return found


def read_plugin_definitions(
    api: WordPressApi, namespaces: Sequence[str], types: Mapping[str, Any]
) -> tuple[list[PluginDefinition], bool]:
    """Every definition the field plugins show through REST, and whether CPT UI is active."""
    firsts = _firsts(namespaces)
    found = _Found()
    if "pods" in firsts:
        found.definitions += _pods(api)
    if "cmb2" in firsts:
        found.definitions += _cmb2(api)
    found.definitions += _definition_posts(api, types)
    plugins = _quiet(api, "wp/v2/plugins", _fields="plugin,status")
    for plugin in plugins if isinstance(plugins, list) else []:
        if isinstance(plugin, dict) and plugin.get("plugin") == _CPT_UI:
            found.cpt_ui = plugin.get("status") == "active"
    return found.definitions, found.cpt_ui


# -- field groups from the route schemas ---------------------------------------------------


def route_schemas(
    api: WordPressApi, types: Mapping[str, Any], taxes: Mapping[str, Any]
) -> list[tuple[str, str, str, dict[str, Any]]]:
    """(attach key, what it attaches to in words, route, schema properties) per object route."""
    from quill.core.wordpress.field_plugins import route_properties

    routes: list[tuple[str, str, str]] = []
    for kind, raw_set in (("type", types), ("taxonomy", taxes)):
        for slug, info in raw_set.items():
            if isinstance(info, dict) and info.get("rest_base"):
                namespace = str(info.get("rest_namespace") or "wp/v2").strip("/")
                name = str(info.get("name") or slug)
                route = f"{namespace}/{info['rest_base']}"
                routes.append((_attach_key(kind, str(slug)), name, route))
    routes += [("user", "Users", "wp/v2/users"), ("comment", "Comments", "wp/v2/comments")]
    found: list[tuple[str, str, str, dict[str, Any]]] = []
    for key, name, route in routes:
        try:
            props = route_properties(api, route)
        except WordPressApiError:
            continue
        found.append((key, name, route, props))
    return found


def _group_row(
    site: str,
    key: str,
    name: str,
    owner: str,
    evidence: str,
    fields: Sequence[Mapping[str, Any]],
    attach: Sequence[str],
    *,
    unmovable: str = "",
) -> WbRow:
    from quill.core.wordpress.workbench_discovered import READ_ONLY, definition_words

    listed = ", ".join(str(f.get("name")) for f in fields) or "none shown in REST"
    from quill.core.wordpress.workbench_model_move import move_body

    movable = None
    if owner not in ("WordPress", "QUILL Site Types") and fields and not unmovable:
        record = {"key": key, "name": name, "fields": fields, "attach": attach}
        body, skipped = move_body("field_group", key, record)
        movable = {"what": "field_group", "owner": owner, "body": body, "skipped": skipped}
    said = definition_words(owner, site_types=False)
    if unmovable:
        said += f" It cannot be copied to QUILL Site Types: {unmovable}"
    return WbRow(
        "model",
        site,
        key,
        {"name": name, "kind": "field group", "registered_by": owner,
         "definition": READ_ONLY, "in_rest": "yes"},
        f"{name}, a field group, registered by {owner}. {evidence} Fields: {listed}. {said}",
        subkind="field_group",
        raw={"editable_definition": False, "definition": None, "movable": movable,
             "fields": [dict(f) for f in fields], "attach": list(attach)},
    )  # fmt: skip


def field_group_rows(
    site: str,
    schemas: Sequence[tuple[str, str, str, Mapping[str, Any]]],
    definitions: Sequence[PluginDefinition],
    site_type_fields: Mapping[str, set[str]] | None = None,
) -> list[WbRow]:
    """The field groups the route schemas and the plugins show, each with who registered it.

    *site_type_fields* is each object's field names that a QUILL Site Types
    group defines, so those registered meta keys are named as its own.
    """
    from quill.core.wordpress.field_plugins import ACF_PROPERTY, acf_schema, meta_from_properties
    from quill.core.wordpress.field_plugins_more import METABOX_PROPERTY

    ours = site_type_fields or {}
    rows: list[WbRow] = []
    for attach, name, route, props in schemas:
        meta = {k: v for k, v in meta_from_properties(props).items() if isinstance(v, dict)}
        mine = {k for k in meta if k not in CORE_META and k not in ours.get(attach, set())}
        if mine:  # registered meta nobody here owns: who called register_meta is not said
            fields = [{"name": k, "label": str(meta[k].get("title") or ""), "schema": meta[k]}
                      for k in sorted(mine)]  # fmt: skip
            rows.append(_group_row(
                site, f"meta:{attach}", f"Registered fields on {name}", "unknown",
                f"Registered meta on {route}; register_meta does not record who called it.",
                fields, [attach], unmovable="registered meta is already in REST as it is.",
            ))  # fmt: skip
        core = sorted(k for k in meta if k in CORE_META)
        if core:
            rows.append(_group_row(
                site, f"core-meta:{attach}", f"WordPress fields on {name}", "WordPress",
                "Meta WordPress itself registers.", [{"name": k} for k in core], [attach],
            ))  # fmt: skip
        acf = acf_schema(props)
        if acf:
            fields = [{"name": k, "label": str(v.get("title") or ""), "schema": v}
                      for k, v in sorted(acf.items())]  # fmt: skip
            rows.append(_group_row(
                site, f"acf:{attach}", f"Advanced Custom Fields on {name}",
                "Advanced Custom Fields",
                f"The acf property ACF adds to the schema of {route}, for groups shown in REST.",
                fields, [attach],
            ))  # fmt: skip
        box = props.get(METABOX_PROPERTY)
        described = box.get("properties") if isinstance(box, dict) else None
        if isinstance(described, dict) and described:
            fields = [{"name": k, "schema": v} for k, v in sorted(described.items())
                      if isinstance(v, dict)]  # fmt: skip
            rows.append(_group_row(
                site, f"meta_box:{attach}", f"Meta Box fields on {name}", "Meta Box",
                f"The meta_box property Meta Box adds to the schema of {route}.", fields,
                [attach],
            ))  # fmt: skip
        elif ACF_PROPERTY not in props and METABOX_PROPERTY in props:
            rows.append(_group_row(
                site, f"meta_box:{attach}", f"Meta Box fields on {name}", "Meta Box",
                f"Meta Box adds meta_box to {route} without describing its fields; Properties "
                "shows them item by item.", [], [attach],
            ))  # fmt: skip
    for found in definitions:
        if found.what != "field_group":
            continue
        rows.append(_group_row(
            site, found.key, found.name, found.plugin, f"{found.plugin} lists it in "
            f"{found.source}.", found.fields, found.attach, unmovable=found.unmovable,
        ))  # fmt: skip
    return rows
