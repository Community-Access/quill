"""The shop, certificate, plugin, statement and weekly Watches (PRD 15.7, D5; WP-R-020, WP-R-050).

Called from :func:`quill.core.wordpress.workbench_watches.check` for each
site that answered, after the Watches kept there. Each one follows the same
rules: off until the person checks it in Workbench Options, its first look at
a site silent, and a change said once.

- ``order``: WooCommerce orders newer than the newest seen (``wc/v3/orders``).
- ``low_stock``: products whose stock has fallen to the shop's low-stock
  amount or below (the product's own amount, else the shop's
  ``woocommerce_notify_low_stock_amount``, else WooCommerce's default of 2).
- ``certificate``: once a day, the date the site's own security certificate
  runs out (:mod:`quill.core.wordpress.site_certificate`); said once when it
  is 30 days away or less, or no longer trusted, and once again when it is
  renewed.
- ``abandoned``: once a week, each installed plugin's WordPress.org entry
  (:func:`quill.core.wordpress.dotorg.plugin_details`, one short name a
  request, nothing about the site); a plugin closed there, or not updated for
  over two years, is said once.
- ``statement``: the facts an accessibility statement is drafted from (the
  newest Check the Whole Site, :class:`~quill.core.wordpress.site_report.CheckHistory`);
  when they change and the site's published ``accessibility`` page was last
  saved before that check, the statement is out of date, and Write an
  Accessibility Statement drafts it again.
- ``weekly``: once a week, one sentence for the whole site: comments waiting,
  plugin updates, Site Health tests that are critical, plugins that may be
  abandoned, low stock, the certificate, and a statement out of date -- the
  same checks, said together.

What each Watch remembers lives in :attr:`WatchState.extra`, by kind and then
by site. Wx-free.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from quill.core.wordpress.api import WordPressApiError

__all__ = ["MORE_KINDS", "WatchContext", "more_round"]

MORE_KINDS: Mapping[str, str] = {
    "order": "New shop orders (WooCommerce)",
    "low_stock": "Products running low on stock (WooCommerce)",
    "certificate": "A security certificate running out within 30 days (checked once a day)",
    "abandoned": "Plugins that may be abandoned (asks WordPress.org once a week)",
    "statement": "An accessibility statement whose facts have changed",
    "weekly": "A weekly sentence about each whole site",
}
_SHOP = "wc/v3"
_LOW_DEFAULT = 2
_SOON_DAYS = 30
_DAY = 86400.0
_UNTRUSTED = -1.0


def _read_certificate(host: str, port: int) -> float:
    from quill.core.wordpress.site_certificate import certificate_expiry

    return certificate_expiry(host, port)


@dataclass
class WatchContext:
    """What a round needs besides the site: the local check history, and the outside readers.

    *history* maps a site's name to its newest Check the Whole Site entry (or
    None); *cert_reader* and *dotorg_opener* are replaced in tests.
    """

    history: Mapping[str, Any] = field(default_factory=dict)
    cert_reader: Callable[[str, int], float] = _read_certificate
    dotorg_opener: Callable[..., Any] | None = None
    now: float = 0.0

    @property
    def today(self) -> date:
        return datetime.fromtimestamp(self.now or time.time()).date()

    @property
    def week(self) -> str:
        year, week, _day = self.today.isocalendar()
        return f"{year}-W{week:02d}"


def _slot(state: Any, name: str) -> dict[str, Any]:
    found = state.extra.get(name)
    if isinstance(found, dict):
        return found
    made: dict[str, Any] = {}
    state.extra[name] = made
    return made


def _once(state: Any, site: str, kind: str, period: str) -> bool:
    """True the first time in *period* (a day or a week) this Watch looks at *site*."""
    slot = _slot(state, "period")
    key = f"{site}:{kind}"
    if slot.get(key) == period:
        return False
    slot[key] = period
    return True


def more_round(
    site: str,
    api: Any,
    namespaces: Sequence[str],
    state: Any,
    wanted: set[str],
    ctx: WatchContext,
) -> list[str]:
    """The sentences these Watches have for *site* this round."""
    clean = {n.strip("/") for n in namespaces}
    said: list[str] = []
    if "order" in wanted and _SHOP in clean:
        said += _orders(site, api, state)
    if "low_stock" in wanted and _SHOP in clean:
        said += _low_stock(site, api, state)
    if "certificate" in wanted:
        said += _certificate(site, api, state, ctx)
    if "abandoned" in wanted and _once(state, site, "abandoned", ctx.week):
        said += _abandoned(site, api, state, ctx)
    if "statement" in wanted:
        said += _statement(site, api, state, ctx)
    if "weekly" in wanted:
        said += _weekly(site, api, clean, state, ctx)
    return said


def _first(state: Any, site: str, kind: str) -> bool:
    from quill.core.wordpress.workbench_watches import first_sample

    return first_sample(state, site, kind)


# -- the shop ----------------------------------------------------------------------------


def _orders(site: str, api: Any, state: Any) -> list[str]:
    found = api.get(f"{_SHOP}/orders", per_page=20, orderby="id", order="desc", _fields="id,number")
    rows = [r for r in found if isinstance(r, Mapping)] if isinstance(found, list) else []
    newest = max((int(r.get("id", 0) or 0) for r in rows), default=0)
    slot = _slot(state, "orders")
    before = int(slot.get(site, 0) or 0)
    first = _first(state, site, "order")
    slot[site] = max(before, newest)
    if first or newest <= before:
        return []
    new = sorted((r for r in rows if int(r.get("id", 0) or 0) > before), key=lambda r: r["id"])
    numbers = ", ".join(str(r.get("number") or r.get("id")) for r in new)
    count = f"{len(new)} or more new orders" if len(new) >= 20 else _plural(len(new), "order")
    return [f"{count} on {site}: number {numbers}."]


def _plural(count: int, noun: str) -> str:
    return f"{count} new {noun}" + ("" if count == 1 else "s")


def _low_amount(api: Any) -> int:
    try:
        raw = api.get(f"{_SHOP}/settings/products/woocommerce_notify_low_stock_amount")
        return int(str(raw.get("value"))) if isinstance(raw, Mapping) else _LOW_DEFAULT
    except (WordPressApiError, TypeError, ValueError):
        return _LOW_DEFAULT


def low_products(api: Any) -> dict[str, tuple[str, int]]:
    """Product id -> (name, how many are left), for every product at or under its low amount."""
    amount = _low_amount(api)
    low: dict[str, tuple[str, int]] = {}
    params = {"_fields": "id,name,manage_stock,stock_quantity,low_stock_amount"}
    for raw in api.iter_collection(f"{_SHOP}/products", params, per_page=100, max_pages=3):
        quantity = raw.get("stock_quantity")
        if raw.get("manage_stock") is not True or not isinstance(quantity, (int, float)):
            continue
        own = raw.get("low_stock_amount")
        limit = int(own) if isinstance(own, (int, float)) else amount
        if quantity <= limit:
            low[str(raw.get("id", ""))] = (str(raw.get("name", "") or "A product"), int(quantity))
    return low


def _low_stock(site: str, api: Any, state: Any) -> list[str]:
    low = low_products(api)
    slot = _slot(state, "low_stock")
    before = set(slot.get(site, []))
    first = _first(state, site, "low_stock")
    slot[site] = sorted(low)
    new = [key for key in sorted(low) if key not in before]
    if first or not new:
        return []
    parts = [f"{low[key][0]}, {'none' if low[key][1] <= 0 else low[key][1]} left" for key in new]
    return [f"Low stock on {site}: {'; '.join(parts)}."]


# -- the certificate ---------------------------------------------------------------------


def _day_words(stamp: float) -> str:
    return datetime.fromtimestamp(stamp).strftime("%d %B %Y").lstrip("0")


def _certificate(site: str, api: Any, state: Any, ctx: WatchContext) -> list[str]:
    from quill.core.wordpress.site_certificate import CertificateError, certificate_host
    from quill.core.wordpress.workbench_practice import is_practice_address

    address = getattr(api, "address", None)
    url = str(getattr(address, "site_url", "") or "")
    target = certificate_host(url)
    if getattr(address, "is_wpcom", False) or target is None or is_practice_address(url):
        return []
    if not _once(state, site, "certificate", ctx.today.isoformat()):
        return []
    warned = _slot(state, "certificate_warned")
    first = _first(state, site, "certificate")
    try:
        expiry = ctx.cert_reader(*target)
    except CertificateError as exc:
        if not exc.untrusted or first or warned.get(site) == _UNTRUSTED:
            return []
        warned[site] = _UNTRUSTED
        return [
            f"The security certificate for {site} is not trusted now, so browsers warn "
            f"visitors away. {exc.plain}"
        ]
    _slot(state, "certificate")[site] = expiry
    said: list[str] = []
    before = warned.get(site)
    if before is not None and (before == _UNTRUSTED or expiry > float(before) + _DAY):
        warned.pop(site)
        said.append(
            f"The security certificate for {site} was renewed: good until {_day_words(expiry)}."
        )
    days = int((expiry - (ctx.now or time.time())) // _DAY)
    if days <= _SOON_DAYS and not first and warned.get(site) != expiry:
        warned[site] = expiry
        when = "today" if days <= 0 else f"in {days} day" + ("" if days == 1 else "s")
        said.append(
            f"The security certificate for {site} runs out on {_day_words(expiry)}, {when}. "
            "Most hosts renew it by themselves; if yours does not, ask them before then."
        )
    return said


# -- plugins that may be abandoned -------------------------------------------------------


def _abandoned(site: str, api: Any, state: Any, ctx: WatchContext) -> list[str]:
    from quill.core.wordpress.dotorg import DotorgError, plugin_details, plugin_slug

    try:
        plugins = list(
            api.iter_collection(
                "wp/v2/plugins", {"_fields": "plugin,name"}, per_page=100, max_pages=1
            )
        )
    except WordPressApiError:
        return []  # only an administrator can list plugins: nothing to watch
    slugs = [plugin_slug(str(raw.get("plugin", ""))) for raw in plugins]
    try:
        found = plugin_details([s for s in slugs if s], opener=ctx.dotorg_opener)
    except DotorgError:
        _slot(state, "period").pop(f"{site}:abandoned", None)  # try again next round
        return []
    warnings = {slug: p.warning(ctx.today) for slug, p in found.items() if p is not None}
    flagged = sorted(slug for slug, words in warnings.items() if words)
    slot = _slot(state, "abandoned")
    before = set(slot.get(site, []))
    first = _first(state, site, "abandoned")
    slot[site] = flagged
    new = [slug for slug in flagged if slug not in before]
    if first or not new:
        return []
    return [f"On {site}: {' '.join(warnings[slug] for slug in new)}"]


# -- the accessibility statement ---------------------------------------------------------


def _facts(entry: Any) -> str:
    if entry is None:
        return "none"
    themes = ",".join(getattr(entry, "theme_problems", []) or [])
    return f"{str(entry.date)[:10]}|{entry.problems}|{entry.pages}|{themes}"


def statement_page(api: Any) -> Mapping[str, Any] | None:
    """The site's published accessibility statement, the page with the slug accessibility."""
    found = api.get(
        "wp/v2/pages", slug="accessibility", status="publish", _fields="id,modified_gmt"
    )
    rows = [r for r in found if isinstance(r, Mapping)] if isinstance(found, list) else []
    return rows[0] if rows else None


def _statement(site: str, api: Any, state: Any, ctx: WatchContext) -> list[str]:
    entry = ctx.history.get(site)
    facts = _facts(entry)
    slot = _slot(state, "statement")
    before = slot.get(site)
    first = _first(state, site, "statement")
    slot[site] = facts
    if first or before == facts or entry is None:
        return []
    page = statement_page(api)
    if page is None:
        return []  # no statement published: nothing to keep current
    if str(page.get("modified_gmt", ""))[:19] >= str(entry.date)[:19]:
        return []  # saved since that check
    found = (
        f"found {entry.problems} things to fix across {entry.pages} pages"
        if entry.problems
        else f"found no problems on {entry.pages} pages"
    )
    return [
        f"The accessibility statement on {site} is out of date: Check the Whole Site, in "
        f"{entry.month}, {found}, and the statement was last saved before that. Write an "
        "Accessibility Statement drafts it again."
    ]


# -- the weekly sentence -----------------------------------------------------------------


def _count(count: int, one: str, many: str) -> str:
    return f"{count} {one if count == 1 else many}"


def _weekly(site: str, api: Any, namespaces: set[str], state: Any, ctx: WatchContext) -> list[str]:
    from quill.core.wordpress.workbench_watches import plugin_updates, waiting_comments

    slot = _slot(state, "weekly")
    before = slot.get(site)
    first = _first(state, site, "weekly")
    slot[site] = ctx.week
    if first or before == ctx.week:
        return []
    parts: list[str] = []
    for read, one, many in (
        (lambda: len(waiting_comments(api)), "comment waiting", "comments waiting"),
        (lambda: len(plugin_updates(api)), "plugin update available", "plugin updates available"),
        (lambda: len(low_products(api)) if _SHOP in namespaces else 0, "product low on stock",
         "products low on stock"),
    ):  # fmt: skip
        try:
            count = read()
        except WordPressApiError:
            continue
        if count:
            parts.append(_count(count, one, many))
    critical = sum(1 for s in state.health.get(site, {}).values() if s == "critical")
    if critical:
        parts.append(_count(critical, "Site Health test critical", "Site Health tests critical"))
    abandoned = len(_slot(state, "abandoned").get(site, []))
    if abandoned:
        parts.append(
            _count(abandoned, "plugin that may be abandoned", "plugins that may be abandoned")
        )
    expiry = _slot(state, "certificate").get(site)
    if isinstance(expiry, (int, float)) and expiry > 0:
        parts.append(f"the security certificate good until {_day_words(float(expiry))}")
    if not parts:
        return [f"This week on {site}: nothing waiting for you."]
    return [f"This week on {site}: {'; '.join(parts)}."]
