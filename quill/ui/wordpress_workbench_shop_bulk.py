"""Change Many Products... in the Workbench (complete.md 2.3, Shop: ``products/batch``).

The Workbench side of :mod:`quill.core.wordpress.workbench_shop_bulk`: the
selected products (or every product shown, when one row is chosen and the
list is asked for), one change, one preview naming each product's old and new
value and every product left alone, then WooCommerce's batch route. One step
in Change History; Ctrl+Z sends the old values back the same way.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.wordpress import workbench_shop_bulk as bulk
from quill.core.wordpress.plugin_shop_seo import SHOP_NAMESPACE, ShopValueError
from quill.core.wordpress.site import raw_text
from quill.core.wordpress.workbench_rows import WbRow
from quill.core.wordpress.workbench_shop_catalog import PRODUCT_STATUSES

__all__ = ["WorkbenchShopBulkCommands"]


class WorkbenchShopBulkCommands:
    """Mixed into the shop commands, whose ask, choose and preview helpers it uses."""

    say: Callable[[str], None]
    ctx: Callable[[str], Any]
    background: Callable[..., None]
    refresh: Callable[[], None]
    step: Callable[..., None]
    selected_rows: Callable[[], list[WbRow]]
    _may_change: Callable[[str], bool]
    _pl_ask: Callable[..., str | None]
    _pl_choose: Callable[..., int | None]
    _pl_preview: Callable[[str, str, list[str], str], bool]
    _pl_report: Callable[[str, str, str], None]

    def do_bulk_edit_products(self, _ref: Any, row: WbRow | None) -> None:
        chosen = self.selected_rows() or ([row] if row is not None else [])
        rows = [r for r in chosen if r.kind == "shop_product"]
        if not rows:
            self.say("Select the products to change first; Ctrl+A selects every one shown.")
            return
        site = rows[0].site
        if any(r.site != site for r in rows):
            self.say("Change products on one site at a time.")
            return
        if not self._may_change(site):
            return
        changes = list(bulk.BULK_CHANGES)
        title = f"Change {len(rows)} Products"
        picked = self._pl_choose(
            title,
            "&Change:",
            [bulk.BULK_CHANGES[c] for c in changes],
            "One change for every selected product, previewed product by product first.",
        )
        if picked is None:
            return
        change = changes[picked]
        if change in ("add_category", "remove_category"):
            api = self.ctx(site).api
            self.background(
                f"reading {site}'s product categories",
                lambda: api.get(f"{SHOP_NAMESPACE}/products/categories", per_page=100),
                lambda found: self._bulk_category(site, rows, change, title, found),
            )
            return
        options: dict[str, Any] = {}
        try:
            if change in ("sale", "price"):
                prompt = (
                    "&Percent off the regular price:"
                    if change == "sale"
                    else "&Percent to change the price by (such as 5, or -10 to lower it):"
                )
                text = self._pl_ask(title, prompt, "A number; 12.5 is fine.", "")
                if text is None:
                    return
                options["percent"] = bulk.parse_percent(text, allow_negative=change == "price")
            elif change in ("stock", "status"):
                table = bulk.STOCK_STATUSES if change == "stock" else PRODUCT_STATUSES
                keys = list(table)
                which = self._pl_choose(title, "&To:", [table[k] for k in keys], "The new value.")
                if which is None:
                    return
                options["choice"] = keys[which]
        except ShopValueError as exc:
            self.say(f"{exc} Nothing was changed.")
            return
        self._bulk_send(site, rows, change, title, options)

    def _bulk_category(
        self, site: str, rows: list[WbRow], change: str, title: str, found: Any
    ) -> None:
        known = [
            (int(c["id"]), raw_text(c.get("name")) or f"Category {c['id']}")
            for c in (found if isinstance(found, list) else [])
            if isinstance(c, dict) and str(c.get("id", "")).isdigit()
        ]
        if not known:
            self.say(f"{site} has no product categories to choose from.")
            return
        which = self._pl_choose(title, "&Category:", [name for _id, name in known], "Which one.")
        if which is not None:
            self._bulk_send(site, rows, change, title, {"category": known[which]})

    def _bulk_send(
        self, site: str, rows: list[WbRow], change: str, title: str, options: dict[str, Any]
    ) -> None:
        try:
            plan = bulk.plan_bulk(rows, change, **options)
        except ShopValueError as exc:
            self.say(f"{exc} Nothing was changed.")
            return
        count = len(plan.updates)
        lines = list(plan.lines)
        if plan.skipped:
            lines += ["Left alone:", *plan.skipped]
        summary = f"Change {count} product{'s' if count != 1 else ''} on {site}."
        if not self._pl_preview(title, summary, lines, "Change Products"):
            return
        api = self.ctx(site).api

        def send(updates: list[dict[str, Any]]) -> list[str]:
            failed: list[str] = []
            for body in bulk.batch_bodies(updates):
                failed += bulk.batch_failures(api.post(bulk.BATCH_ROUTE, body))
            return failed

        def undo() -> str:
            failed = send(plan.undo)
            back = count - len(failed)
            return f"{back} of {count} products on {site} are as they were."

        def done(failed: list[str]) -> None:
            changed = count - len(failed)
            said = f"Changed {changed} of {count} products on {site}." + (
                f" {len(failed)} {'was' if len(failed) == 1 else 'were'} refused." if failed else ""
            )
            self.say(said)
            self.step(site, said.rstrip("."), undo if changed else None)
            if failed:
                self._pl_report(title, "\n".join(failed), "Each product WooCommerce refused.")
            self.refresh()

        self.background(f"changing {count} products", lambda: send(plan.updates), done)
