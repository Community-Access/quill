"""What a site says about itself, as Workbench rows (PRD 12, 12b; W5).

- **More from This Site, by namespace** (:func:`namespace_rows`,
  :func:`route_rows`): each namespace with its routes, each route with its
  methods and where the Workbench reaches it
  (:mod:`~quill.core.wordpress.workbench_coverage`), so a plugin's routes are
  listed the day it is installed, with no QUILL release.
- **The Content Model** (:func:`model_rows`): the site's post types,
  taxonomies and field groups, each with who registered it and the evidence
  (:mod:`~quill.core.wordpress.workbench_model_sources`; "unknown" when the
  site does not say), and a ``definition`` column saying each definition is
  read only and why (:func:`definition_words`); what the QUILL Site Types
  plugin defines (detected by :data:`SITE_TYPES_NAMESPACE`) is editable, and
  the rest can be copied into it (:mod:`~quill.core.wordpress.workbench_model_move`).
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
    "EDITABLE",
    "READ_ONLY",
    "SITE_TYPES_NAMESPACE",
    "ability_input",
    "ability_preview",
    "ability_sheet",
    "ability_values",
    "definition_words",
    "model_rows",
    "namespace_rows",
    "registered_by",
    "route_rows",
]

SITE_TYPES_NAMESPACE = "quill-site-types/v1"
"""The namespace the QUILL Site Types plugin registers (12b, quill-site-types 0.1.0)."""

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


def registered_by(
    slug: str, rest_namespace: str = "wp/v2", *, namespaces: Sequence[str] = ()
) -> str:
    """Who registered *slug*, from evidence only; ``"unknown"`` when the site does not say.

    The evidence and its order are :func:`~quill.core.wordpress.workbench_model_sources.provenance`.
    """
    from quill.core.wordpress.workbench_model_sources import provenance

    return provenance(slug, rest_namespace, namespaces=namespaces, core=CORE_TYPES).owner


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


READ_ONLY = "Read only"
"""The Content Model's ``definition`` cell for a type the Workbench cannot redefine."""


EDITABLE = "Editable through QUILL Site Types"
"""The ``definition`` cell for a type, taxonomy or field group QUILL Site Types defines."""

_SITE_TYPES = "QUILL Site Types"


def definition_words(owner: str, *, site_types: bool, reason: str = "") -> str:
    """Why a definition is read only here, in one sentence (the items stay editable)."""
    where = (
        "part of WordPress"
        if owner == "WordPress"
        else "defined in code this site does not name"
        if owner == "unknown"
        else f"defined in {owner}'s code"
    )
    tail = (
        " QUILL Site Types is on this site: what you define with it (Ctrl+N here) is "
        "editable, and this one was not defined there."
        if site_types
        else ""
    )
    if reason:
        tail += f" {reason}"
    return (
        f"Read only definition, {where}; change it there. Its items are edited "
        f"in their own lists, as your role allows.{tail}"
    )


def _editable_words(noun: str) -> str:
    return (
        f"Defined through QUILL Site Types on this site, so the {noun} itself can change here: "
        "Stop Defining takes the definition away and keeps its content, and Export as Code "
        "writes it as PHP for a theme or plugin."
    )


def model_rows(api: WordPressApi, site: str, *, namespaces: Sequence[str] = ()) -> list[WbRow]:
    """The site's post types, taxonomies and field groups, and who registered each (12b).

    Every row says, in its ``definition`` cell and its detail, whether its
    *definition* can change here, and the evidence for who registered it
    (:func:`~quill.core.wordpress.workbench_model_sources.provenance`). Only what
    QUILL Site Types (detected by its namespace, :data:`SITE_TYPES_NAMESPACE`)
    defines is editable; anything registered elsewhere is read only, with why,
    and carries a ``movable`` record when it can be copied into QUILL Site Types.
    Field groups come from every route's schema (registered meta, ACF, Meta Box)
    and from what the field plugins list (WP-R-036, WP-R-038).
    """
    from quill.core.wordpress import workbench_model_sources as ms
    from quill.core.wordpress.api import WordPressApiError
    from quill.core.wordpress.site_types_plugin import Definitions, read_definitions
    from quill.core.wordpress.workbench_model_move import move_body

    site_types = SITE_TYPES_NAMESPACE in {n.strip("/") for n in namespaces}
    defined = Definitions()
    if site_types:
        try:
            defined = read_definitions(api)
        except WordPressApiError:
            defined = Definitions(reason="QUILL Site Types did not answer.")
    got_types = api.get("wp/v2/types", context="edit")
    got_taxes = api.get("wp/v2/taxonomies", context="edit")
    types = dict(got_types) if isinstance(got_types, dict) else {}
    taxes = dict(got_taxes) if isinstance(got_taxes, dict) else {}
    plugin_defs, cpt_ui = ms.read_plugin_definitions(api, namespaces, types)
    rows: list[WbRow] = []
    for kind, raw_set in (("post type", types), ("taxonomy", taxes)):
        what = "type" if kind == "post type" else "taxonomy"
        theirs = {d.key: d for d in plugin_defs if d.what == what}
        for slug, info in raw_set.items():
            if not isinstance(info, dict):
                continue
            mine = defined.of(what).get(str(slug))
            if mine is not None:
                found = ms.Provenance(_SITE_TYPES, "QUILL Site Types keeps its definition.")
            else:
                found = ms.provenance(
                    str(slug),
                    str(info.get("rest_namespace") or "wp/v2"),
                    namespaces=namespaces,
                    defined=theirs,
                    core=CORE_TYPES,
                    cpt_ui=cpt_ui,
                )
            owner = found.owner
            movable = None
            if mine is None and owner != "WordPress":
                body, skipped = move_body(what, str(slug), info)
                movable = {"what": what, "owner": owner, "body": body, "skipped": skipped}
            name = str(info.get("name") or slug)
            cells = {
                "name": name,
                "kind": kind,
                "registered_by": owner,
                "definition": EDITABLE if mine is not None else READ_ONLY,
                "in_rest": "yes" if info.get("rest_base") else "no",
            }
            said = (
                _editable_words(kind)
                if mine is not None
                else definition_words(owner, site_types=site_types, reason=defined.reason)
            )
            rows.append(
                WbRow(
                    "model",
                    site,
                    str(slug),
                    cells,
                    f"{name}, a {kind} ({slug}), registered by {owner}. {found.evidence} {said}",
                    subkind=what,
                    raw={
                        **info,
                        "editable_definition": mine is not None,
                        "definition": mine,
                        "movable": movable,
                    },
                )
            )
    ours: dict[str, set[str]] = {}
    for key, group in defined.groups.items():
        name = str(group.get("title") or key)
        fields = [f for f in group.get("fields") or [] if isinstance(f, dict)]
        attach = group.get("attach") if isinstance(group.get("attach"), dict) else None
        targets = list((attach or {}).get("post_types") or [])
        targets += [f"taxonomy:{t}" for t in (attach or {}).get("taxonomies") or []]
        for target in targets:
            ours.setdefault(str(target), set()).update(str(f.get("name")) for f in fields)
        kinds = ", ".join(f"{f.get('name')} ({f.get('kind')})" for f in fields)
        rows.append(
            WbRow(
                "model",
                site,
                key,
                {
                    "name": name,
                    "kind": "field group",
                    "registered_by": _SITE_TYPES,
                    "definition": EDITABLE,
                    "in_rest": "yes",
                },
                f"{name}, a field group ({key}), registered by {_SITE_TYPES}, with "
                f"{len(fields)} fields: {kinds or 'none'}. {_editable_words('field group')}",
                subkind="field_group",
                raw={"editable_definition": True, "definition": group},
            )
        )
    rows += ms.field_group_rows(site, ms.route_schemas(api, types, taxes), plugin_defs, ours)
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
