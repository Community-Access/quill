"""The Workbench's loaders for a site's structure: styles, types, design and routes.

Split from :mod:`quill.core.wordpress.workbench_load` (which dispatches to these
from :func:`~quill.core.wordpress.workbench_load.load`): global styles, the
site's own types and taxonomies, templates, synced patterns, fonts, widget
areas, menus, abilities, and the REST namespaces, routes and data model.
Wx-free; runs off the UI thread.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from quill.core.wordpress import site_taxonomies as tx
from quill.core.wordpress import site_types as stypes
from quill.core.wordpress.api import WordPressApiError
from quill.core.wordpress.site import friendly_date, kind_route, rendered
from quill.core.wordpress.workbench_load import SiteContext, _collect, _simple, page_params
from quill.core.wordpress.workbench_rows import WbRow, fact_rows

__all__ = [
    "index_routes",
    "load_abilities",
    "load_fonts",
    "load_global_styles",
    "load_menus",
    "load_model",
    "load_namespaces",
    "load_patterns",
    "load_routes",
    "load_sidebars",
    "load_taxonomies",
    "load_templates",
    "load_types",
]


def load_global_styles(ctx: SiteContext) -> list[WbRow]:
    """The active block theme's colours and font sizes, with their contrast."""
    from quill.core.wordpress import site_styles as styles

    theme = styles.active_theme(ctx.api)
    if not theme.block_theme or not theme.stylesheet:
        return fact_rows(
            ctx.name,
            [("Global Styles", "The active theme does not expose WordPress global styles.")],
        )
    base = styles.theme_styles(ctx.api, theme.stylesheet)
    user: dict[str, Any] = {}
    user_styles_hidden = False
    if theme.styles_id:
        try:
            user = styles.load_user_styles(ctx.api, theme.styles_id)
        except WordPressApiError as exc:
            if exc.status not in (401, 403):
                raise
            user_styles_hidden = True
    background, foreground = styles.page_colours(base, user)
    entries = styles.entries(base, user)
    if not entries:
        return fact_rows(
            ctx.name,
            [
                (
                    "Global Styles",
                    f"{theme.name or 'The active theme'} exposes no palette or font sizes.",
                )
            ],
        )
    rows: list[WbRow] = []
    for entry in entries:
        colour = entry.kind == "colour"
        contrast = (
            styles.contrast_sentence(entry.name, entry.value, background, foreground)
            if colour
            else ""
        )
        detail = contrast or f"{entry.name}, font size {entry.value}."
        kind = "Colour" if colour else "Font size"
        rows.append(
            WbRow(
                "global_style",
                ctx.name,
                f"{entry.kind}:{entry.slug}",
                {
                    "setting": entry.name,
                    "kind": kind,
                    "value": entry.value,
                    "contrast": contrast,
                },
                detail,
                subkind=entry.kind,
                raw={
                    "slug": entry.slug,
                    "kind": entry.kind,
                    "name": entry.name,
                    "value": entry.value,
                    "contrast": contrast,
                    "stylesheet": theme.stylesheet,
                    "styles_id": theme.styles_id,
                    "_background": background,
                    "_foreground": foreground,
                },
            )
        )
    if user_styles_hidden:
        rows.extend(
            fact_rows(
                ctx.name,
                [
                    (
                        "User styles",
                        "This account cannot read the site's own style overrides; these rows show "
                        "the active theme's defaults.",
                    )
                ],
            )
        )
    return rows


def load_types(ctx: SiteContext) -> list[WbRow]:
    return [
        _simple(
            ctx,
            "writing_type",
            t.kind,
            {"type": t.name, "route": kind_route(t.kind), "taxonomies": ", ".join(t.taxonomies)},
            f"{t.name}: the site's own content type, at {kind_route(t.kind)}.",
            subkind=t.slug,
        )
        for t in stypes.discover_writing_types(ctx.api)
    ]


def load_taxonomies(ctx: SiteContext) -> list[WbRow]:
    return [
        _simple(
            ctx,
            "taxonomy",
            t.slug,
            {"taxonomy": t.name, "route": t.route, "types": ", ".join(t.types)},
            f"{t.name}, for {', '.join(t.types) or 'no type'}, at {t.route}.",
            subkind=t.slug,
        )
        for t in tx.discover_taxonomies(ctx.api).values()
        if t.slug not in ("category", "post_tag", "nav_menu", "wp_pattern_category")
    ]


def _titled(raw: Mapping[str, Any]) -> str:
    return rendered(raw.get("title")) or str(raw.get("slug", "") or raw.get("id", ""))


def load_templates(ctx: SiteContext, which: str) -> list[WbRow]:
    route = "wp/v2/templates" if which == "wp_template" else "wp/v2/template-parts"
    rows = []
    for r in _collect(ctx.api, route, page_params()):
        title = _titled(r)
        source = "customized" if r.get("source") == "custom" else "from the theme"
        rows.append(
            _simple(
                ctx,
                "template",
                str(r.get("id", "")),
                {"title": title, "source": source, "slug": str(r.get("slug", ""))},
                f"{title}, {source}.",
                route=f"{route}/{r.get('id', '')}",
                subkind=which,
                raw=r,
            )
        )
    return rows


def load_patterns(ctx: SiteContext, query: Mapping[str, object]) -> list[WbRow]:
    rows = []
    for r in _collect(ctx.api, "wp/v2/blocks", page_params(query)):
        title = _titled(r)
        status = str(r.get("status", ""))
        rows.append(
            _simple(
                ctx,
                "pattern",
                str(r.get("id", "")),
                {
                    "title": title,
                    "status": status,
                    "modified": friendly_date(str(r.get("modified_gmt", "") or "")),
                },
                f"{title}, a synced pattern, {status}.",
                route=f"wp/v2/blocks/{r.get('id', '')}",
                status=status,
                raw=r,
            )
        )
    return rows


def load_fonts(ctx: SiteContext) -> list[WbRow]:
    rows = []
    for r in _collect(ctx.api, "wp/v2/font-families", page_params()):
        settings = r.get("font_family_settings") if isinstance(r, dict) else {}
        settings = settings if isinstance(settings, dict) else {}
        name = str(settings.get("name", "") or r.get("id", ""))
        rows.append(
            _simple(
                ctx,
                "font",
                str(r.get("id", "")),
                {"family": name, "slug": str(settings.get("slug", ""))},
                f"{name}, a font family installed on the site.",
                route=f"wp/v2/font-families/{r.get('id', '')}",
                raw=r,
            )
        )
    return rows


def load_sidebars(ctx: SiteContext) -> list[WbRow]:
    raw = ctx.api.get("wp/v2/sidebars", context="edit")
    rows = []
    for r in raw if isinstance(raw, list) else []:
        if not isinstance(r, dict):
            continue
        name = str(r.get("name", "") or r.get("id", ""))
        count = len(r.get("widgets", []) or [])
        rows.append(
            _simple(
                ctx,
                "sidebar",
                str(r.get("id", "")),
                {"sidebar": name, "widgets": str(count), "status": str(r.get("status", ""))},
                f"{name}, {count} widgets.",
                route=f"wp/v2/sidebars/{r.get('id', '')}",
                raw=r,
            )
        )
    return rows


def load_menus(ctx: SiteContext) -> list[WbRow]:
    rows = []
    for r in _collect(ctx.api, "wp/v2/menus", page_params()):
        name = rendered(r.get("name")) or str(r.get("name", ""))
        places = ", ".join(str(p) for p in r.get("locations", []) or []) or "none"
        rows.append(
            _simple(
                ctx,
                "menu",
                str(r.get("id", "")),
                {"menu": name, "locations": places, "items": ""},
                f"{name}, shown in: {places}.",
                route=f"wp/v2/menus/{r.get('id', '')}",
                raw=r,
            )
        )
    return rows


def load_abilities(ctx: SiteContext) -> list[WbRow]:
    from quill.core.wordpress.abilities import category_labels, list_abilities
    from quill.core.wordpress.workbench_model_sources import plugin_for_namespace

    rows: list[WbRow] = []
    abilities = list_abilities(ctx.api)
    labels = category_labels(ctx.api) if abilities else {}  # wp-abilities/v1/categories
    for ability in abilities:
        plugin = plugin_for_namespace(ability.name.split("/", 1)[0])  # "" when not known
        detail = f"{plugin}: " if plugin else ""
        rows.append(
            _simple(
                ctx,
                "ability",
                ability.name,
                {
                    "ability": ability.label,
                    "plugin": plugin,
                    "category": labels.get(ability.category, ability.category),
                    "says": ability.description,
                },
                f"{detail}{ability.label}: {ability.description}",
                raw={
                    "name": ability.name,
                    "plugin": plugin,
                    "readonly": ability.readonly,
                    "destructive": ability.destructive,
                },
            )
        )
    return rows


def load_namespaces(ctx: SiteContext) -> list[WbRow]:
    from quill.core.wordpress.workbench_discovered import namespace_rows

    info = ctx.info
    if info is None:
        return []
    return namespace_rows(ctx.name, info.namespaces, info.routes)


def index_routes(ctx: SiteContext) -> dict[str, list[str]]:
    """Every route of the site's index with its methods (one request for the index)."""
    raw = ctx.api.get("")
    routes = raw.get("routes") if isinstance(raw, dict) else None
    found: dict[str, list[str]] = {}
    for route, info in (routes or {}).items() if isinstance(routes, dict) else ():
        methods: list[str] = []
        if isinstance(info, dict):
            if isinstance(info.get("methods"), list):
                methods = [str(m) for m in info["methods"]]
            for endpoint in info.get("endpoints") or []:
                if isinstance(endpoint, dict):
                    methods += [str(m) for m in endpoint.get("methods") or [] if m not in methods]
        found[str(route)] = sorted(set(methods), key=methods.index)
    return found


def load_routes(ctx: SiteContext, namespace: str) -> list[WbRow]:
    from quill.core.wordpress.workbench_discovered import route_rows

    namespaces = ctx.info.namespaces if ctx.info is not None else (namespace,)
    return route_rows(ctx.name, namespace, namespaces, index_routes(ctx))


def load_model(ctx: SiteContext) -> list[WbRow]:
    from quill.core.wordpress.workbench_discovered import model_rows

    namespaces = ctx.info.namespaces if ctx.info is not None else ()
    return model_rows(ctx.api, ctx.name, namespaces=namespaces)
