"""Needs My Attention > Updates and Membership Orders, within what REST can tell (WP-A).

**Updates.** WordPress's REST API cannot list or run updates: ``wp/v2/plugins``
installs, activates, deactivates and deletes, ``wp/v2/themes`` only reads, and
neither carries an "update waiting" field; WordPress itself, its translations
and the update check are not on the API at all. So this list says what *is*
known -- each site's WordPress version, every plugin and theme with its
installed version, and Site Health's ``background-updates`` test where the
site runs it -- and says plainly what is not. Every row opens the site's own
Dashboard > Updates screen (``wp-admin/update-core.php``) in the browser,
which is where updates are seen and run. Nothing here updates anything, and
no row claims an update waits unless the site's own payload says so (a field
some plugins add, read when present and never guessed).

**Membership Orders.** Paid Memberships Pro orders that need a person
(pending, in review, waiting on a payment token, or failed), read through
PMPro's read-only ability (:mod:`~quill.core.wordpress.workbench_pmpro`).
These are membership orders, never shop orders: a shop plugin's orders are
outside the Workbench's plugin scope (QUILL Accessible Forms, Gravity Forms
and Paid Memberships Pro), and a site without PMPro's abilities adds no rows.

Wx-free; runs off the UI thread.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from typing import TYPE_CHECKING, Any

from quill.core.wordpress.api import WordPressApiError
from quill.core.wordpress.site import plain_text, rendered
from quill.core.wordpress.workbench_rows import WbRow

if TYPE_CHECKING:
    from quill.core.wordpress.workbench_load import SiteContext

__all__ = [
    "ATTENTION_ORDER_STATUSES",
    "NOT_REPORTED",
    "UPDATES_SCREEN",
    "membership_orders",
    "update_rows",
    "updates_link",
]

UPDATES_SCREEN = "wp-admin/update-core.php"
"""Dashboard > Updates, relative to the site's address."""

NOT_REPORTED = "Not reported over REST"
"""The update cell when the site's payload says nothing about a newer version."""

ATTENTION_ORDER_STATUSES = frozenset({"pending", "review", "token", "error"})
"""PMPro order statuses that wait on a person; success, refunded and cancelled do not."""

_HEALTH_TEST = "background-updates"
_HEALTH_ROUTE = f"/wp-site-health/v1/tests/{_HEALTH_TEST}"
_HEALTH_WORDS = {"good": "Good", "recommended": "Should be improved", "critical": "Critical"}
#: Fields a plugin or host may add to a plugin or theme payload; core adds none.
_UPDATE_FIELDS = ("update_version", "new_version", "update")


def updates_link(ctx: SiteContext) -> str:
    """The site's Dashboard > Updates address ("" when the site's address is unknown)."""
    base = (ctx.url or "").rstrip("/")
    return f"{base}/{UPDATES_SCREEN}" if base else ""


def _reported(raw: Mapping[str, Any]) -> str:
    """What the payload itself says about a newer version, or :data:`NOT_REPORTED`."""
    for name in _UPDATE_FIELDS:
        value = raw.get(name)
        if isinstance(value, Mapping):
            value = value.get("new_version") or value.get("version")
        if isinstance(value, str) and value.strip():
            return f"Version {value.strip()} reported by the site"
    return NOT_REPORTED


def _row(
    ctx: SiteContext,
    key: str,
    what: str,
    installed: str,
    update: str,
    detail: str,
    *,
    status: str = "",
    raw: Mapping[str, Any] | None = None,
) -> WbRow:
    link = updates_link(ctx)
    where = " Enter opens Dashboard > Updates in your browser." if link else ""
    return WbRow(
        "update",
        ctx.name,
        f"update:{key}",
        {"what": what, "site": ctx.name, "installed": installed, "update": update},
        f"{detail}{where}",
        link=link,
        status=status,
        raw=dict(raw or {}),
    )


def _core(ctx: SiteContext) -> WbRow:
    version = ctx.info.wp_version if ctx.info is not None else ""
    said = f"WordPress {version}" if version else "WordPress, version not said"
    return _row(
        ctx,
        "core",
        "WordPress",
        version or "not said",
        NOT_REPORTED,
        f"{said} on {ctx.name}. WordPress's REST API does not say whether a newer "
        "WordPress or new translations wait; Dashboard > Updates does.",
    )


def _automatic(ctx: SiteContext) -> list[WbRow]:
    """Site Health's background-updates test, when the site offers and lets you run it."""
    routes = ctx.info.routes if ctx.info is not None else ()
    if _HEALTH_ROUTE not in routes:
        return []
    try:
        raw = ctx.api.get(_HEALTH_ROUTE.lstrip("/"))
    except WordPressApiError as exc:
        why = (
            "only an administrator can run this Site Health test"
            if exc.status in (401, 403)
            else "the site could not run this Site Health test"
        )
        return [
            _row(
                ctx,
                "automatic",
                "Automatic updates",
                "",
                "Not known",
                f"Automatic updates on {ctx.name}: {why}.",
            )
        ]
    if not isinstance(raw, Mapping):
        return []
    status = str(raw.get("status", "") or "")
    label = plain_text(rendered(raw.get("label"))) or "Automatic updates"
    words = _HEALTH_WORDS.get(status, "Information")
    return [
        _row(
            ctx,
            "automatic",
            "Automatic updates",
            "",
            words,
            f"Automatic updates on {ctx.name}, from Site Health: {label.rstrip('.')}.",
            status=status,
            raw=raw,
        )
    ]


def _listed(ctx: SiteContext, route: str, noun: str) -> list[WbRow]:
    """Each plugin or theme with its installed version, and what the site says of updates."""
    try:
        raw = ctx.api.get(route, context="edit")
    except WordPressApiError as exc:
        why = (
            f"your role on {ctx.name} cannot list its {noun}s"
            if exc.status in (401, 403)
            else f"{ctx.name} did not list its {noun}s"
        )
        return [_row(ctx, f"{noun}s", f"{noun.title()}s", "", "Not known", f"{why.capitalize()}.")]
    rows: list[WbRow] = []
    for item in raw if isinstance(raw, list) else []:
        if not isinstance(item, Mapping):
            continue
        ident = str(item.get("plugin") or item.get("stylesheet") or "")
        name = plain_text(rendered(item.get("name"))) or ident or noun
        version = str(item.get("version", "") or "")
        update = _reported(item)
        known = (
            f" The site reports {update.removesuffix(' reported by the site').lower()}."
            if update != NOT_REPORTED
            else " REST does not say whether an update waits."
        )
        if isinstance(item.get("auto_update"), bool):  # sent by sites that report it
            known += (
                " It updates itself automatically."
                if item["auto_update"]
                else " It does not update itself."
            )
        rows.append(
            _row(
                ctx,
                f"{noun}:{ident or name}",
                name,
                version or "not said",
                update,
                f"{name}, a {noun} on {ctx.name}, version {version or 'not said'}.{known}",
                status=str(item.get("status", "") or ""),
                raw=item,
            )
        )
    return sorted(rows, key=lambda row: row.title.casefold())


def update_rows(ctx: SiteContext) -> list[WbRow]:
    """Everything REST can say about updates on one site, WordPress first."""
    return [
        _core(ctx),
        *_automatic(ctx),
        *_listed(ctx, "wp/v2/plugins", "plugin"),
        *_listed(ctx, "wp/v2/themes", "theme"),
    ]


def membership_orders(ctx: SiteContext) -> list[WbRow]:
    """PMPro orders waiting on a person; none from a site without PMPro's abilities."""
    from quill.core.wordpress.abilities import NAMESPACE
    from quill.core.wordpress.workbench_pmpro import load_pmpro

    if ctx.info is not None and not ctx.info.supports(NAMESPACE):
        return []
    rows: list[WbRow] = []
    for row in load_pmpro(ctx, "orders"):
        if row.subkind != "order" or row.status not in ATTENTION_ORDER_STATUSES:
            continue
        what = f"Membership order {row.title}"
        rows.append(replace(row, cells={**row.cells, "site": row.site, "what": what}))
    return rows
