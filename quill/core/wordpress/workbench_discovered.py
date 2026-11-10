"""What a site says about itself, as Workbench rows (PRD 12, 12b; W5).

- **More from This Site, by namespace** (:func:`namespace_rows`,
  :func:`route_rows`): each namespace with its routes, each route with its
  methods and where the Workbench reaches it
  (:mod:`~quill.core.wordpress.workbench_coverage`), so a plugin's routes are
  listed the day it is installed, with no QUILL release.
- **The Content Model** (:func:`model_rows`): the site's post types and
  taxonomies, each with who registered it (WordPress, a plugin it can name,
  or "a plugin or the theme"), read only; the PRD's QUILL Site Types plugin
  is what would make them editable, and it is detected by namespace
  (:data:`SITE_TYPES_NAMESPACE`) so the row can say so.
- **Abilities as commands** (:func:`ability_sheet`, :func:`ability_preview`):
  an ability's input schema becomes its sheet, by the same rules as any
  discovered route (12a), and the preview says what it will do before it runs.

Wx-free; the loaders make their requests through the site's own client.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any

from quill.core.wordpress.abilities import Ability
from quill.core.wordpress.api import WordPressApi
from quill.core.wordpress.workbench_coverage import classify, namespace_of, status_words
from quill.core.wordpress.workbench_rows import WbRow
from quill.core.wordpress.workbench_sheets import schema_sheet
from quill.core.workbench.properties import FieldKind, FieldSpec, PageSpec, SheetSpec

__all__ = [
    "CORE_TYPES",
    "SITE_TYPES_NAMESPACE",
    "ability_input",
    "ability_preview",
    "ability_sheet",
    "ability_values",
    "model_rows",
    "namespace_rows",
    "registered_by",
    "route_rows",
]

SITE_TYPES_NAMESPACE = "quill-site-types/v1"
"""The namespace the PRD's QUILL Site Types plugin would register (12b)."""

CORE_TYPES = frozenset({
    "post",
    "page",
    "attachment",
    "nav_menu_item",
    "wp_block",
    "wp_template",
    "wp_template_part",
    "wp_navigation",
    "wp_global_styles",
    "wp_font_family",
    "wp_font_face",
    "category",
    "post_tag",
    "nav_menu",
    "link_category",
    "post_format",
    "wp_pattern_category",
    "wp_theme",
    "wp_template_part_area",
})

_OWNERS: tuple[tuple[str, str], ...] = (
    ("tribe_", "The Events Calendar"),
    ("tec_", "The Events Calendar"),
    ("product", "WooCommerce"),
    ("shop_", "WooCommerce"),
    ("pa_", "WooCommerce"),
    ("elementor", "Elementor"),
    ("acf", "Advanced Custom Fields"),
    ("wpcf7", "Contact Form 7"),
    ("qaf", "QUILL Accessible Forms"),
    ("baf", "QUILL Accessible Forms"),
    ("jetpack", "Jetpack"),
    ("feedback", "Jetpack"),
    ("wpseo", "Yoast SEO"),
    ("yoast", "Yoast SEO"),
    ("sfwd", "LearnDash"),
    ("course", "a learning plugin"),
)


def registered_by(slug: str, rest_namespace: str = "wp/v2") -> str:
    """Who registered *slug*: WordPress, a plugin by name, or a plugin or the theme."""
    if slug in CORE_TYPES:
        return "WordPress"
    lowered = slug.lower()
    for prefix, owner in _OWNERS:
        if lowered.startswith(prefix):
            return owner
    namespace = (rest_namespace or "wp/v2").strip("/")
    if namespace != "wp/v2":
        return f"the plugin behind {namespace}"
    return "a plugin or the theme"


def namespace_rows(site: str, namespaces: Sequence[str], routes: Sequence[str]) -> list[WbRow]:
    """One row per namespace, with how many routes it has and how many the Workbench reaches."""
    rows: list[WbRow] = []
    for namespace in namespaces:
        mine = [r for r in routes if namespace_of(r, namespaces) == namespace.strip("/")]
        reached = sum(1 for r in mine if classify(r).status in ("covered", "schema_built"))
        rows.append(
            WbRow(
                "namespace",
                site,
                namespace,
                {"namespace": namespace, "routes": str(len(mine)), "reached": str(reached)},
                f"{namespace}: {len(mine)} routes on {site}; the Workbench reaches {reached}. "
                "Enter lists them.",
            )
        )
    return rows


def route_rows(
    site: str,
    namespace: str,
    namespaces: Sequence[str],
    routes: Mapping[str, Sequence[str]],
) -> list[WbRow]:
    """The routes of *namespace*, each with its methods and where the Workbench reaches it."""
    rows: list[WbRow] = []
    for route, methods in sorted(routes.items()):
        if namespace_of(route, namespaces) != namespace.strip("/"):
            continue
        found = classify(route, methods)
        said = ", ".join(methods) or "methods not said"
        rows.append(
            WbRow(
                "route",
                site,
                route,
                {
                    "route": route,
                    "methods": said,
                    "coverage": status_words(found.status),
                },
                f"{route}, {said}. {status_words(found.status).capitalize()}: {found.home}.",
                route=route.strip("/"),
                status=found.status,
                raw={"methods": list(methods), "home": found.home},
            )
        )
    return rows


def model_rows(api: WordPressApi, site: str, *, namespaces: Sequence[str] = ()) -> list[WbRow]:
    """The site's post types and taxonomies, who registered each, read only (12b)."""
    editable = SITE_TYPES_NAMESPACE in {n.strip("/") for n in namespaces}
    rows: list[WbRow] = []
    types = api.get("wp/v2/types", context="edit")
    taxes = api.get("wp/v2/taxonomies", context="edit")
    for kind, raw_set in (("post type", types), ("taxonomy", taxes)):
        for slug, info in (raw_set or {}).items() if isinstance(raw_set, dict) else ():
            if not isinstance(info, dict):
                continue
            owner = registered_by(str(slug), str(info.get("rest_namespace") or "wp/v2"))
            name = str(info.get("name") or slug)
            in_rest = "yes" if info.get("rest_base") else "no"
            lock = (
                "QUILL Site Types is on this site; defining types from here comes with its routes."
                if editable
                else f"Read only: {owner} registered it."
            )
            rows.append(
                WbRow(
                    "model",
                    site,
                    str(slug),
                    {"name": name, "kind": kind, "registered_by": owner, "in_rest": in_rest},
                    f"{name}, a {kind} ({slug}), registered by {owner}. {lock}",
                    subkind="type" if kind == "post type" else "taxonomy",
                    raw=dict(info),
                )
            )
    return rows


# -- abilities -----------------------------------------------------------------


def ability_sheet(ability: Ability) -> SheetSpec:
    """The ability's input as a sheet, built from its input schema (12a)."""
    properties = (ability.input_schema or {}).get("properties")
    if isinstance(properties, dict) and properties:
        built = schema_sheet("ability", ability.label, properties)
        return SheetSpec("ability", ability.label, built.pages)
    return SheetSpec(
        "ability",
        ability.label,
        (
            PageSpec(
                "general",
                "General",
                (
                    FieldSpec(
                        "about",
                        "About",
                        FieldKind.MULTILINE,
                        readonly=True,
                        help="What the ability does. It takes no input.",
                    ),
                ),
            ),
        ),
    )


def ability_values(ability: Ability) -> dict[str, Any]:
    """Each input's default from the schema, and the About text for one with none."""
    values: dict[str, Any] = {"about": ability.details()}
    properties = (ability.input_schema or {}).get("properties")
    for name, spec in (properties or {}).items() if isinstance(properties, dict) else ():
        if isinstance(spec, dict) and "default" in spec:
            values[name] = spec["default"]
    return values


def _typed(value: Any, spec: Mapping[str, Any]) -> Any:
    kind = spec.get("type")
    kinds = kind if isinstance(kind, list) else [kind]
    if isinstance(value, str):
        text = value.strip()
        if "integer" in kinds and text.lstrip("-").isdigit():
            return int(text)
        if "number" in kinds:
            try:
                return float(text)
            except ValueError:
                return text
        if "boolean" in kinds:
            return text.lower() in ("1", "true", "yes", "on")
    if isinstance(value, tuple):
        return list(value)
    return value


def ability_input(ability: Ability, pending: Mapping[str, Any]) -> dict[str, Any]:
    """The input to send: what the person filled in, typed as the schema says."""
    properties = (ability.input_schema or {}).get("properties")
    specs = properties if isinstance(properties, dict) else {}
    given: dict[str, Any] = {}
    for key, value in pending.items():
        if key == "about" or value in (None, ""):
            continue
        spec = specs.get(key)
        given[key] = _typed(value, spec if isinstance(spec, dict) else {})
    return given


def ability_preview(site: str, ability: Ability, given: Mapping[str, Any]) -> tuple[str, list[str]]:
    """(the summary, one line per input) shown before an ability runs."""
    if ability.destructive:
        weight = "It can delete or overwrite things on the site."
    elif ability.readonly:
        weight = "It only reads; nothing on the site changes."
    else:
        weight = "It can change the site."
    summary = f"Run {ability.label} on {site}. {weight}"
    lines = [f"{key}: {json.dumps(value, ensure_ascii=False)}" for key, value in given.items()]
    return summary, lines or ["It takes no input."]
