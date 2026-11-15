"""wp-admin's Dashboard, for one site, in sentences (wordpress.md 9.18, package 6).

Sites > site > Overview has three children that are wp-admin's Home screen
and the rest of its map:

- **At a Glance** (:func:`glance_rows`): posts and pages by status, comments
  waiting, approved and held as spam, the people on the site, the WordPress
  version and the active theme, each one sentence. Every count is one
  ``per_page=1`` request read from ``X-WP-Total``; a count the site refuses
  this account is left out of its sentence, never said as none. Then a
  sentence for each plugin whose namespace the site offers: WooCommerce's
  orders waiting and products, The Events Calendar's upcoming events, Yoast
  SEO's scores, and Paid Memberships Pro's levels and renewals due.
- **Activity** (:func:`activity_rows`): Publishing Soon, Recently Published
  and Recent Comments, five of each, as rows whose ``group`` cell says which;
  a post opens in the editor with Enter and a comment is moderated as in
  Comments. An empty group is still said ("nothing scheduled").
- **wp-admin Screens** is :mod:`quill.core.wordpress.workbench_admin_map`.

Wx-free; runs off the UI thread.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Callable, Mapping
from typing import Any

from quill.core.wordpress import site_types as stypes
from quill.core.wordpress.api import WordPressApiError
from quill.core.wordpress.site import friendly_date, rendered
from quill.core.wordpress.workbench_parity import count
from quill.core.wordpress.workbench_rows import WbRow, comment_row, fact_rows, item_row

__all__ = [
    "ACTIVITY_GROUPS",
    "activity_rows",
    "glance_facts",
    "glance_rows",
    "load_dashboard",
    "places",
    "plugin_summaries",
    "said_counts",
]

ACTIVITY_SIZE = 5
ACTIVITY_GROUPS = ("Publishing soon", "Recently published", "Recent comments")

_ITEM_WORDS = (
    ("publish", "published", "published"),
    ("draft", "draft", "drafts"),
    ("pending", "waiting for review", "waiting for review"),
    ("future", "scheduled", "scheduled"),
    ("private", "private", "private"),
)
_COMMENT_WORDS = (
    ("hold", "waiting", "waiting"),
    ("approve", "approved", "approved"),
    ("spam", "held as spam", "held as spam"),
)


def said_counts(counts: Mapping[str, int | None], words: tuple[tuple[str, str, str], ...]) -> str:
    """ "12 published, 3 drafts"; "none" when all are zero; "" when every count was refused."""
    known = {k: n for k, n in counts.items() if n is not None}
    if not known:
        return ""
    parts = [
        f"{known[key]} {one if known[key] == 1 else many}"
        for key, one, many in words
        if known.get(key)
    ]
    return ", ".join(parts) or "none"


def _plain(error: WordPressApiError) -> str:
    if error.status in (401, 403):
        return "this account may not read it"
    return error.plain or "the site did not say"


def _active_theme(ctx: Any) -> str:
    themes = ctx.api.get("wp/v2/themes", status="active")
    for theme in themes if isinstance(themes, list) else []:
        if isinstance(theme, dict):
            name = rendered(theme.get("name")) or str(theme.get("stylesheet", ""))
            version = str(theme.get("version", "") or "")
            return f"{name}, version {version}" if version else name
    return ""


def glance_facts(ctx: Any) -> list[tuple[str, str]]:
    """At a Glance as (fact, sentence) pairs, without the plugins."""
    api = ctx.api
    facts: list[tuple[str, str]] = []
    for kind, label in (("post", "Posts"), ("page", "Pages")):
        counts = stypes.count_by_status(api, kind, [key for key, _o, _m in _ITEM_WORDS])
        facts.append((label, said_counts(counts, _ITEM_WORDS) or "this account may not count them"))
    comments = {
        key: count(api, "wp/v2/comments", {"status": key}) for key, _o, _m in _COMMENT_WORDS
    }
    facts.append((
        "Comments",
        said_counts(comments, _COMMENT_WORDS) or "this account may not count them",
    ))
    people = count(api, "wp/v2/users", {})
    if people is not None:
        facts.append(("People", f"{people} on the site"))
    info = ctx.info
    facts.append(("WordPress", (info.wp_version if info is not None else "") or "version not said"))
    try:
        theme = _active_theme(ctx)
    except WordPressApiError as exc:
        theme = _plain(exc)
    facts.append(("Theme", theme or "not said"))
    return facts


def _shop(ctx: Any) -> str:
    api = ctx.api
    processing = count(api, "wc/v3/orders", {"status": "processing"})
    on_hold = count(api, "wc/v3/orders", {"status": "on-hold"})
    products = count(api, "wc/v3/products", {"status": "publish"})
    if processing is None and on_hold is None and products is None:
        return "this account may not read the shop"
    parts = []
    if processing is not None:
        parts.append(f"{processing} order{'' if processing == 1 else 's'} to fulfil")
    if on_hold is not None:
        parts.append(f"{on_hold} on hold")
    if products is not None:
        parts.append(f"{products} product{'' if products == 1 else 's'} published")
    return ", ".join(parts)


def _events(ctx: Any) -> str:
    answer = ctx.api.get("tribe/events/v1/events", start_date="now", per_page=1)
    total = answer.get("total") if isinstance(answer, dict) else None
    if total is None:
        return "the calendar did not say how many are coming"
    total = int(total)
    return f"{total} upcoming event{'' if total == 1 else 's'}"


def _scores(answer: Any) -> str:
    scores = answer.get("scores") if isinstance(answer, dict) else None
    parts = [
        f"{int(s.get('amount', 0) or 0)} {str(s.get('name', '')).replace('_', ' ')}"
        for s in (scores if isinstance(scores, list) else [])
        if isinstance(s, dict) and s.get("name")
    ]
    return ", ".join(parts)


def _seo(ctx: Any) -> str:
    seo = _scores(ctx.api.get("yoast/v1/seo_scores", contentType="post"))
    readability = _scores(ctx.api.get("yoast/v1/readability_scores", contentType="post"))
    said = []
    if seo:
        said.append(f"SEO scores on posts: {seo}")
    if readability:
        said.append(f"readability: {readability}")
    return "; ".join(said) or "its scores are in Yoast SEO's own dashboard"


def _memberships(ctx: Any) -> str:
    from quill.core.wordpress.workbench_pmpro import load_pmpro

    levels = [r for r in load_pmpro(ctx, "levels") if r.kind == "pmpro"]
    if not levels:
        return "its abilities are not exposed, so Memberships cannot read it"
    renewals = [r for r in load_pmpro(ctx, "renewals") if r.kind == "pmpro"]
    return (
        f"{len(levels)} level{'' if len(levels) == 1 else 's'}, "
        f"{len(renewals)} renewal{'' if len(renewals) == 1 else 's'} due within thirty days"
    )


_PLUGINS: tuple[tuple[str, str, Callable[[Any], str]], ...] = (
    ("wc/v3", "WooCommerce", _shop),
    ("tribe/events/v1", "The Events Calendar", _events),
    ("yoast/v1", "Yoast SEO", _seo),
    ("pmpro/v1", "Paid Memberships Pro", _memberships),
)


def plugin_summaries(ctx: Any) -> list[tuple[str, str]]:
    """One sentence a plugin whose namespace the site offers; a refusal is said, not hidden."""
    offered = {n.strip("/") for n in (ctx.info.namespaces if ctx.info is not None else ())}
    said: list[tuple[str, str]] = []
    for namespace, name, read in _PLUGINS:
        if namespace not in offered:
            continue
        try:
            said.append((name, read(ctx)))
        except WordPressApiError as exc:
            said.append((name, _plain(exc)))
    return said


def glance_rows(ctx: Any) -> list[WbRow]:
    return fact_rows(ctx.name, [*glance_facts(ctx), *plugin_summaries(ctx)])


def _grouped(row: WbRow, group: str, when: str) -> WbRow:
    cells = {**row.cells, "group": group, "when": when, "title": row.title}
    return dataclasses.replace(row, cells=cells, detail=f"{group}: {row.detail}")


def _nothing(site: str, group: str, words: str) -> WbRow:
    return WbRow(
        "fact", site, f"none:{group}", {"group": group, "title": words}, f"{group}: {words}."
    )


def _posts(ctx: Any, status: str, order: str) -> list[dict[str, Any]]:
    got = ctx.api.get(
        "wp/v2/posts",
        status=status,
        orderby="date",
        order=order,
        per_page=ACTIVITY_SIZE,
        context="edit",
    )
    return [r for r in got if isinstance(r, dict)] if isinstance(got, list) else []


def _comments(ctx: Any) -> list[dict[str, Any]]:
    params: dict[str, object] = {"per_page": ACTIVITY_SIZE, "orderby": "date_gmt", "order": "desc"}
    try:
        got = ctx.api.get("wp/v2/comments", status="all", context="edit", **params)
    except WordPressApiError as exc:
        if exc.status not in (400, 401, 403):
            raise
        got = ctx.api.get("wp/v2/comments", **params)  # an author sees approved ones only
    return [r for r in got if isinstance(r, dict)] if isinstance(got, list) else []


def activity_rows(ctx: Any) -> list[WbRow]:
    """Publishing soon, recently published and recent comments, each group said even empty."""
    rows: list[WbRow] = []
    soon, recent, said = ACTIVITY_GROUPS
    future = [item_row(r, "post", ctx.name) for r in _posts(ctx, "future", "asc")]
    rows += [_grouped(r, soon, r.cell("date")) for r in future] or [
        _nothing(ctx.name, soon, "nothing scheduled")
    ]
    published = [item_row(r, "post", ctx.name) for r in _posts(ctx, "publish", "desc")]
    rows += [_grouped(r, recent, r.cell("date")) for r in published] or [
        _nothing(ctx.name, recent, "nothing published yet")
    ]
    comments = [comment_row(r, ctx.name) for r in _comments(ctx)]
    rows += [
        _grouped(r, said, friendly_date(str(r.raw.get("date_gmt", "") or ""))) for r in comments
    ] or [_nothing(ctx.name, said, "no comments yet")]
    return rows


def places() -> dict[str, str]:
    """Each site node's key, named as the tree says it ("Appearance > Themes")."""
    from quill.core.wordpress.workbench_tree import WORDPRESS_TREE

    nodes = {node.key: node for node in WORDPRESS_TREE.template("site")}
    named: dict[str, str] = {}
    for key, node in nodes.items():
        labels: list[str] = []
        current: Any = node
        while current is not None and current.key != "site":
            labels.append(current.label)
            current = nodes.get(current.parent or "")
        named[key] = " > ".join(reversed(labels))
    return named


def load_dashboard(ctx: Any, what: str) -> list[WbRow]:
    """The rows of one Overview child: ``glance``, ``activity`` or ``screens``."""
    if what == "glance":
        return glance_rows(ctx)
    if what == "activity":
        return activity_rows(ctx)
    if what == "screens":
        from quill.core.wordpress.workbench_admin_map import map_rows

        namespaces = ctx.info.namespaces if ctx.info is not None else ()
        return map_rows(ctx.name, ctx.url, namespaces, places())
    raise WordPressApiError(f"The Workbench does not know the dashboard view {what}.")
