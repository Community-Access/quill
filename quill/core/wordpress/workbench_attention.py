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
- **Inbox:** all of the above, newest first.

Wx-free; runs off the UI thread.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

from quill.core.wordpress.api import WordPressApiError
from quill.core.wordpress.workbench_forms import form_plugins, load_forms
from quill.core.wordpress.workbench_load import (
    SiteContext,
    load_comments,
    load_health,
    load_items,
)
from quill.core.wordpress.workbench_rows import WbRow

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


def _inbox(ctx: SiteContext) -> list[WbRow]:
    rows = _with_what(_waiting(ctx), "Comment")
    rows += _with_what(_items(ctx, "pending"), "Pending review")
    rows += _with_what(_spam(ctx), "Held as spam")
    rows += _with_what(_responses(ctx), "Form response")
    return rows


ATTENTION: dict[str, Callable[[SiteContext], list[WbRow]]] = {
    "inbox": _inbox,
    "waiting": _waiting,
    "pending": lambda ctx: _items(ctx, "pending"),
    "scheduled": lambda ctx: _items(ctx, "future"),
    "drafts": lambda ctx: _items(ctx, "draft", mine=True),
    "spam": _spam,
    "responses": _responses,
    "health": _health,
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
