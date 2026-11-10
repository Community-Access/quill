"""What fills each node of the WordPress Workbench: one site, one loader name.

The tree (:mod:`quill.core.wordpress.workbench_tree`) names a loader per
node; :func:`load` turns the name into requests through the site's own
client (:class:`~quill.core.wordpress.api.WordPressApi`), so the Workbench
adds no new host and no new way in. Each list is read with ``context=edit``
where the route has it, a page at a time, at most :data:`MAX_PAGES` pages, so
a big site's list is honest about stopping (the window says "first 300").

Discovery (a site's own post types and taxonomies) is cached per client by
:mod:`~quill.core.wordpress.site_taxonomies`; nothing here caches rows.
Wx-free; runs off the UI thread.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from quill.core.wordpress import site_admin as admin
from quill.core.wordpress import site_taxonomies as tx
from quill.core.wordpress import site_types as stypes
from quill.core.wordpress.api import WordPressApi, WordPressApiError
from quill.core.wordpress.comments import post_titles
from quill.core.wordpress.site import Account, SiteInfo, friendly_date, kind_route, rendered
from quill.core.wordpress.workbench_rows import (
    WbRow,
    comment_row,
    fact_rows,
    item_row,
    media_row,
    term_row,
    tree_order,
    user_row,
)

__all__ = ["MAX_PAGES", "PER_PAGE", "SiteContext", "load", "page_params"]

PER_PAGE = 100
MAX_PAGES = 3

_MEDIA_TYPES = {"pictures": "image", "audio": "audio", "video": "video", "documents": "application"}


@dataclass
class SiteContext:
    """One connected site as the Workbench holds it: its name, client and who you are."""

    name: str
    api: WordPressApi
    url: str = ""
    account: Account | None = None
    info: SiteInfo | None = None


def page_params(params: Mapping[str, object] | None = None) -> dict[str, object]:
    return {"context": "edit", **(params or {})}


def _collect(
    api: WordPressApi, route: str, params: Mapping[str, object], *, max_pages: int = MAX_PAGES
) -> list[dict[str, Any]]:
    return list(api.iter_collection(route, params, per_page=PER_PAGE, max_pages=max_pages))


def _authors(api: WordPressApi, ids: Sequence[int]) -> dict[int, str]:
    wanted = sorted({i for i in ids if i})
    if not wanted:
        return {}
    try:
        found = _collect(api, "wp/v2/users", {"include": wanted, "_fields": "id,name"})
    except WordPressApiError:
        return {}
    return {int(r.get("id", 0)): str(r.get("name", "")) for r in found}


def load_items(
    ctx: SiteContext, kind: str, preset: Mapping[str, str], query: Mapping[str, object]
) -> list[WbRow]:
    """A post type's items, newest change first, narrowed by status and the filter."""
    params: dict[str, object] = page_params({"orderby": "modified", "order": "desc", **query})
    status = preset.get("status", "any")
    params.setdefault("status", status)
    raw = _collect(ctx.api, kind_route(kind), params)
    authors = _authors(ctx.api, [int(r.get("author", 0) or 0) for r in raw])
    rows = [item_row(r, kind, ctx.name, authors=authors) for r in raw]
    return tree_order(rows) if preset.get("tree") == "parent" else rows


def load_media(ctx: SiteContext, which: str, query: Mapping[str, object]) -> list[WbRow]:
    params: dict[str, object] = page_params({"orderby": "date", "order": "desc", **query})
    if which in _MEDIA_TYPES:
        params["media_type"] = _MEDIA_TYPES[which]
    if which == "unattached":
        params["parent"] = 0
    if which == "no_alt":
        params["media_type"] = "image"
    rows = [media_row(r, ctx.name) for r in _collect(ctx.api, "wp/v2/media", params)]
    if which == "no_alt":
        rows = [row for row in rows if not row.raw.get("alt_text")]
    return rows


def load_comments(ctx: SiteContext, status: str, query: Mapping[str, object]) -> list[WbRow]:
    params: dict[str, object] = page_params({**query, "status": status})
    raw = _collect(ctx.api, "wp/v2/comments", params)
    titles = post_titles(ctx.api, {int(r.get("post", 0) or 0) for r in raw if r.get("post")})
    return [
        comment_row(r, ctx.name, post_title=titles.get(int(r.get("post", 0) or 0), "")) for r in raw
    ]


def load_terms(ctx: SiteContext, taxonomy: str, query: Mapping[str, object]) -> list[WbRow]:
    found = tx.lookup(ctx.api, taxonomy)
    if found is None:
        try:
            found = tx.discover_taxonomies(ctx.api).get(taxonomy)
        except WordPressApiError:
            found = None
    route = found.route if found else f"wp/v2/{tx.CORE_TAXONOMY_BASES.get(taxonomy, taxonomy)}"
    params = page_params({"orderby": "name", "hide_empty": False, **query})
    rows = [term_row(r, ctx.name, taxonomy, route) for r in _collect(ctx.api, route, params)]
    return tree_order(rows) if found is None or found.hierarchical else rows


def load_users(ctx: SiteContext, query: Mapping[str, object]) -> list[WbRow]:
    params = page_params({"orderby": "name", **query})
    words = dict(admin.ROLES)
    return [user_row(r, ctx.name, words) for r in _collect(ctx.api, "wp/v2/users", params)]


def _simple(
    ctx: SiteContext,
    kind: str,
    key: str,
    cells: dict[str, str],
    detail: str,
    *,
    route: str = "",
    status: str = "",
    subkind: str = "",
    raw: Mapping[str, Any] | None = None,
    link: str = "",
) -> WbRow:
    return WbRow(
        kind=kind,
        site=ctx.name,
        key=key,
        cells=cells,
        detail=detail,
        route=route,
        link=link,
        status=status,
        subkind=subkind,
        raw=dict(raw or {}),
    )


def load_plugins(ctx: SiteContext) -> list[WbRow]:
    raw = ctx.api.get("wp/v2/plugins", context="edit")
    rows: list[WbRow] = []
    for r in raw if isinstance(raw, list) else []:
        if not isinstance(r, dict):
            continue
        plugin = admin.plugin_from_payload(r)
        state = str(r.get("status", "") or "inactive")
        rows.append(
            _simple(
                ctx,
                "plugin",
                plugin.plugin,
                {
                    "plugin": plugin.name,
                    "version": plugin.version,
                    "status": state.replace("-", " "),
                    "author": plugin.author,
                },
                plugin.spoken() + ".",
                route=f"wp/v2/plugins/{plugin.plugin}",
                status=state,
                raw=r,
            )
        )
    return sorted(rows, key=lambda row: row.title.casefold())


def load_themes(ctx: SiteContext) -> list[WbRow]:
    raw = ctx.api.get("wp/v2/themes")
    rows: list[WbRow] = []
    for r in raw if isinstance(raw, list) else []:
        if not isinstance(r, dict):
            continue
        name = rendered(r.get("name")) or str(r.get("stylesheet", ""))
        state = str(r.get("status", "") or "inactive")
        version = str(r.get("version", "") or "")
        rows.append(
            _simple(
                ctx,
                "theme",
                str(r.get("stylesheet", "")),
                {"theme": name, "version": version, "status": state},
                f"{name}, version {version}, {state}.",
                route=f"wp/v2/themes/{r.get('stylesheet', '')}",
                status=state,
                raw=r,
            )
        )
    return rows


def load_app_passwords(ctx: SiteContext) -> list[WbRow]:
    current = admin.current_password_uuid(ctx.api)
    rows: list[WbRow] = []
    for pw in admin.list_app_passwords(ctx.api):
        mine = " QUILL on this computer signs in with it." if pw.uuid == current else ""
        rows.append(
            _simple(
                ctx,
                "app_password",
                pw.uuid,
                {
                    "name": pw.name,
                    "created": friendly_date(pw.created) if pw.created else "",
                    "last_used": friendly_date(pw.last_used) if pw.last_used else "never",
                },
                pw.spoken(current) + "." + mine,
                route=f"wp/v2/users/me/application-passwords/{pw.uuid}",
                status="current" if pw.uuid == current else "",
                raw={
                    "uuid": pw.uuid,
                    "name": pw.name,
                    "created": pw.created,
                    "last_used": pw.last_used,
                },
            )
        )
    return rows


def load_settings(ctx: SiteContext) -> list[WbRow]:
    settings = admin.load_settings(ctx.api)
    rows = []
    for index, (key, label, text) in enumerate(admin.settings_rows(settings, {})):
        rows.append(
            _simple(
                ctx,
                "setting",
                key,
                {"setting": label, "value": text},
                f"{label}: {text}.",
                route="wp/v2/settings",
                subkind=str(index),
                raw={"key": key, "value": settings.get(key)},
            )
        )
    return rows


def load_health(ctx: SiteContext) -> list[WbRow]:
    lines = admin.site_check(
        ctx.api, site_url=ctx.url, wp_version=ctx.info.wp_version if ctx.info else ""
    )
    words = {"critical": "Critical", "recommended": "Should be improved", "good": "Good"}
    return [
        _simple(
            ctx,
            "problem",
            str(index),
            {
                "test": line.text.split(".")[0],
                "problem": line.text.split(".")[0],
                "status": words.get(line.status, "Information"),
                "says": line.text,
                "site": ctx.name,
            },
            line.text,
            status=line.status,
        )
        for index, line in enumerate(lines)
    ]


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
    from quill.core.wordpress.abilities import list_abilities

    return [
        _simple(
            ctx,
            "ability",
            a.name,
            {"ability": a.label, "category": a.category, "says": a.description},
            f"{a.label}: {a.description}",
            raw={"name": a.name, "readonly": a.readonly, "destructive": a.destructive},
        )
        for a in list_abilities(ctx.api)
    ]


def load_namespaces(ctx: SiteContext) -> list[WbRow]:
    info = ctx.info
    if info is None:
        return []
    rows = []
    for namespace in info.namespaces:
        count = sum(1 for r in info.routes if r.strip("/").startswith(namespace))
        rows.append(
            _simple(
                ctx,
                "namespace",
                namespace,
                {"namespace": namespace, "routes": str(count)},
                f"{namespace}: {count} routes on this site.",
            )
        )
    return rows


def overview(ctx: SiteContext) -> list[WbRow]:
    info, account = ctx.info, ctx.account
    facts: list[tuple[str, str]] = [("Name", ctx.name), ("Address", ctx.url)]
    if info is not None:
        facts += [
            ("Tagline", info.description or "none"),
            ("WordPress version", info.wp_version or "not said"),
            ("REST namespaces", str(len(info.namespaces))),
        ]
    if account is not None:
        facts.append(("Your role", account.role_name))
    for kind, label in (("post", "Posts"), ("page", "Pages")):
        counts = stypes.count_by_status(ctx.api, kind, ("publish", "draft", "pending", "future"))
        said = ", ".join(f"{n} {s}" for s, n in counts.items() if n)
        facts.append((label, said or "none"))
    return fact_rows(ctx.name, facts)


def load(
    ctx: SiteContext,
    loader: str,
    preset: Mapping[str, str],
    query: Mapping[str, object],
    *,
    dynamic: str = "",
) -> list[WbRow]:
    """The rows for one site node. *dynamic* is a dynamic node's kind or taxonomy."""
    family, _sep, what = loader.partition(":")
    if family == "items":
        return load_items(ctx, dynamic if what == "custom" else what, preset, query)
    if family == "terms":
        return load_terms(ctx, dynamic if what == "custom" else what, query)
    if family == "media":
        return load_media(ctx, what, query)
    if family == "comments":
        return load_comments(ctx, what, query)
    simple: dict[str, Any] = {
        "users": lambda: load_users(ctx, query),
        "plugins": lambda: load_plugins(ctx),
        "themes": lambda: load_themes(ctx),
        "app_passwords": lambda: load_app_passwords(ctx),
        "settings": lambda: load_settings(ctx),
        "health": lambda: load_health(ctx),
        "types": lambda: load_types(ctx),
        "taxonomies": lambda: load_taxonomies(ctx),
        "templates": lambda: load_templates(ctx, what),
        "patterns": lambda: load_patterns(ctx, query),
        "fonts": lambda: load_fonts(ctx),
        "widgets": lambda: load_sidebars(ctx),
        "menus": lambda: load_menus(ctx),
        "abilities": lambda: load_abilities(ctx),
        "routes": lambda: load_namespaces(ctx),
        "site": lambda: overview(ctx),
    }
    if family == "forms":
        from quill.core.wordpress.workbench_forms import load_forms

        return load_forms(ctx, what)
    found = simple.get(family)
    if found is None:
        raise WordPressApiError(f"The Workbench does not know how to load {loader}.")
    rows: list[WbRow] = found()
    return rows
