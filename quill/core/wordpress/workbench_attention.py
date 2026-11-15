"""Needs My Attention: one list gathered from every connected site (PRD 5, WP-R-003).

Each node under Needs My Attention asks every site the same question and
puts the answers in one list, newest first, each row naming its site. A site
that cannot be reached does not hide the others: it becomes one row saying
so, which is the honest thing for a list that claims to be everything.

- **Comments Waiting:** ``wp/v2/comments?status=hold``.
- **Pending Review, Scheduled:** posts and pages in ``pending`` and ``future``.
- **Drafts:** your own drafts (``author`` is you, from ``users/me``).
- **Held as Spam (13a.5):** comments in ``spam``, and form entries held as
  spam on sites with QUILL Accessible Forms or Gravity Forms.
- **Form Responses:** entries not yet read, on sites with a forms plugin.
- **Site Health:** the Site Check lines that are critical or should be improved.
- **Updates, Membership Orders:** what REST can say of updates, and PMPro
  orders waiting on a person (:mod:`~quill.core.wordpress.workbench_updates`).
- **Inbox:** all of the above, newest first.

Wx-free; runs off the UI thread.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

from quill.core.wordpress.api import WordPressApiError
from quill.core.wordpress.link_targets import (
    MAX_LINKS,
    URL_DETAILS,
    dead_links,
    links_in,
    web_links,
)
from quill.core.wordpress.site import raw_text, rendered
from quill.core.wordpress.workbench_forms import form_plugins, load_forms
from quill.core.wordpress.workbench_load import (
    SiteContext,
    load_comments,
    load_health,
    load_items,
    load_media,
)
from quill.core.wordpress.workbench_rows import WbRow, fact_rows
from quill.core.wordpress.workbench_updates import membership_orders, update_rows

__all__ = ["ATTENTION", "gather", "unreachable_row"]


def unreachable_row(site: str, error: BaseException) -> WbRow:
    """One row standing for a site that could not answer."""
    said = error.plain if isinstance(error, WordPressApiError) else str(error)
    return WbRow(
        kind="fact",
        site=site,
        key=f"unreachable:{site}",
        cells={"what": f"Could not ask {site}", "site": site, "title": f"Could not ask {site}"},
        detail=f"{site} did not answer: {said}",
    )


def _items(ctx: SiteContext, status: str, *, mine: bool = False) -> list[WbRow]:
    query: dict[str, object] = {"status": status}
    if mine and ctx.account is not None:
        query["author"] = ctx.account.id
    rows: list[WbRow] = []
    for kind in ("post", "page"):
        rows += load_items(ctx, kind, {"status": status}, query)
    return rows


def _waiting(ctx: SiteContext) -> list[WbRow]:
    return load_comments(ctx, "hold", {})


def _spam(ctx: SiteContext) -> list[WbRow]:
    rows = load_comments(ctx, "spam", {})
    if form_plugins(ctx):
        rows += load_forms(ctx, "spam")
    return rows


def _responses(ctx: SiteContext) -> list[WbRow]:
    if not form_plugins(ctx):
        return []
    return [row for row in load_forms(ctx, "entries") if not row.raw.get("is_read")]


def _health(ctx: SiteContext) -> list[WbRow]:
    return [row for row in load_health(ctx) if row.status in ("critical", "recommended")]


def _accessibility(ctx: SiteContext) -> list[WbRow]:
    """Pictures missing alternative text, from the same site-wide media list."""
    return load_media(ctx, "no_alt", {})


def _broken_links(ctx: SiteContext) -> list[WbRow]:
    """Check a bounded sample of published post and page links using the site's route."""
    index = ctx.api.get("")
    routes = index.get("routes") if isinstance(index, dict) else None
    if not isinstance(routes, dict) or f"/{URL_DETAILS}" not in routes:
        return [
            WbRow(
                "fact",
                ctx.name,
                "broken-links-unavailable",
                {"fact": "Link checking", "value": "Not offered by this site's REST API"},
                f"{ctx.name} does not expose the WordPress link-check route. "
                "Check This Page still works.",
            )
        ]

    limit = MAX_LINKS
    source_by_url: dict[str, tuple[str, str, int, str]] = {}
    item_totals: list[tuple[str, int | None, int]] = []
    for route, kind in (("wp/v2/posts", "post"), ("wp/v2/pages", "page")):
        response = ctx.api.request(
            "GET",
            route,
            params={
                "context": "edit",
                "status": "publish",
                "per_page": 100,
                "page": 1,
                "orderby": "modified",
                "order": "desc",
                "_fields": "id,title,content,link",
            },
        )
        items = response.payload if isinstance(response.payload, list) else []
        item_totals.append((kind, response.total, len(items)))
        for item in items:
            if not isinstance(item, dict):
                continue
            content = item.get("content")
            text = raw_text(content) or rendered(content)
            for url in web_links(links_in(text, "html")):
                source_by_url.setdefault(
                    url,
                    (
                        raw_text(item.get("title")) or rendered(item.get("title")) or "(untitled)",
                        str(item.get("link", "") or ""),
                        int(item.get("id", 0) or 0),
                        kind,
                    ),
                )

    urls = list(source_by_url)[:limit]
    if not urls:
        return [
            fact_rows(
                ctx.name,
                [
                    (
                        "Broken Links",
                        "No web links were found in the first published posts and pages.",
                    )
                ],
            )[0]
        ]

    dead = dead_links(ctx.api, urls)
    rows: list[WbRow] = []
    for target in dead:
        title, source_url, item_id, kind = source_by_url[target.url]
        rows.append(
            WbRow(
                "problem",
                ctx.name,
                f"broken:{item_id}:{target.url}",
                {
                    "problem": "Broken link",
                    "test": title,
                    "site": ctx.name,
                    "status": "Could not reach",
                    "says": target.why,
                    "what": f"{title}: {target.url}",
                    "target": target.url,
                    "kind": kind,
                },
                f"{title} links to {target.url}; the site could not reach it: {target.why}",
                link=source_url,
                raw={
                    "source_id": item_id,
                    "source_type": kind,
                    "source_url": source_url,
                    "target_url": target.url,
                },
            )
        )
    if not dead:
        rows.extend(
            fact_rows(
                ctx.name, [("Broken Links", f"All {len(urls)} checked links reached their pages.")]
            )
        )

    notes: list[str] = []
    if len(source_by_url) > limit:
        notes.append(f"Only the first {limit} unique links were checked")
    if any(total is not None and total > found for _kind, total, found in item_totals):
        notes.append("the site has more published posts or pages than this check loaded")
    if notes:
        rows.extend(fact_rows(ctx.name, [("Scope", "; ".join(notes) + ".")]))
    return rows


def _with_what(rows: list[WbRow], what: str) -> list[WbRow]:
    out = []
    for row in rows:
        if row.cells.get("what"):
            out.append(row)
            continue
        cells = {**row.cells, "what": f"{what}: {row.title}", "site": row.site}
        out.append(
            WbRow(
                row.kind,
                row.site,
                row.key,
                cells,
                row.detail,
                row.route,
                row.link,
                row.status,
                row.subkind,
                row.modified_gmt,
                row.raw,
            )
        )
    return out


def _queued(rows: list[WbRow]) -> list[WbRow]:
    """Each waiting item with where it stands: "2 of 5 waiting on Radio" (15.4)."""
    from dataclasses import replace

    from quill.core.wordpress.workbench_editorial import queue_positions

    places = queue_positions(rows)
    return [
        replace(row, cells={**row.cells, "queue": places[(row.site, row.key)]})
        if (row.site, row.key) in places
        else row
        for row in rows
    ]


def _inbox(ctx: SiteContext) -> list[WbRow]:
    rows = _with_what(_waiting(ctx), "Comment")
    rows += _with_what(_items(ctx, "pending"), "Pending review")
    rows += _with_what(_spam(ctx), "Held as spam")
    rows += _with_what(_responses(ctx), "Form response")
    return rows


ATTENTION: dict[str, Callable[[SiteContext], list[WbRow]]] = {
    "inbox": _inbox,
    "waiting": _waiting,
    "pending": lambda ctx: _queued(_items(ctx, "pending")),
    "scheduled": lambda ctx: _items(ctx, "future"),
    "drafts": lambda ctx: _items(ctx, "draft", mine=True),
    "spam": _spam,
    "responses": _responses,
    "health": _health,
    "accessibility": _accessibility,
    "broken_links": _broken_links,
    "updates": update_rows,
    "orders": membership_orders,
}
"""Each Needs My Attention node's question, asked of one site."""


def _when(row: WbRow) -> str:
    return row.modified_gmt or str(row.raw.get("date_gmt", "") or row.raw.get("date", "") or "")


def gather(what: str, sites: Sequence[SiteContext]) -> list[WbRow]:
    """Ask every site *what*; newest first, with a row for each site that failed."""
    ask = ATTENTION[what]
    rows: list[WbRow] = []
    failed: list[WbRow] = []
    for ctx in sites:
        try:
            rows += ask(ctx)
        except WordPressApiError as exc:
            failed.append(unreachable_row(ctx.name, exc))
    rows.sort(key=_when, reverse=True)
    return failed + rows
