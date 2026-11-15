"""WooCommerce in the WordPress Workbench window: catalogue, orders, settings (Packages 8-10).

A mixin on :class:`quill.ui.wordpress_workbench_window.WordPressWorkbenchProvider`;
the words, checks and bodies are wx-free in
:mod:`quill.core.wordpress.workbench_shop_catalog`,
:mod:`~quill.core.wordpress.workbench_shop_orders` and
:mod:`~quill.core.wordpress.workbench_shop_settings`. Every change is
previewed and asked again on every run; every request runs off the UI
thread through the provider's ``background``. A refund is one order at a
time: it refuses a multiple selection, warns about money in its preview, and
is sent only when the person types the amount.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.wordpress import workbench_shop_catalog as cat
from quill.core.wordpress import workbench_shop_orders as orders
from quill.core.wordpress import workbench_shop_settings as settings
from quill.core.wordpress.plugin_shop_seo import SHOP_NAMESPACE, ShopValueError
from quill.core.wordpress.workbench_permissions import tier_allowed
from quill.core.wordpress.workbench_rows import WbRow
from quill.core.workbench.actions import Tier
from quill.ui import wordpress_dialogs as dlg
from quill.ui import wordpress_workbench_dialogs as wdlg

_Ask = Callable[..., Any]


class WorkbenchShopCommands:
    """The do_* handlers for shop rows; the provider supplies ctx, background and say."""

    # -- plumbing -------------------------------------------------------------------------

    def _shop_site(self, ref: Any, row: WbRow | None) -> str:
        return (row.site if row is not None else "") or self.site_of(ref)  # type: ignore[attr-defined]

    def _may_change(self, site: str) -> bool:
        """Workbench access allows a change on *site*; says why not, when it does not."""
        if tier_allowed(Tier.WRITE, self.access_for(site)):  # type: ignore[attr-defined]
            return True
        self.say(self._access_sentence(site))  # type: ignore[attr-defined]
        return False

    def _pl_ask(self, title: str, prompt: str, help_text: str, value: str = "") -> str | None:
        return dlg.ask_text(
            self.parent,  # type: ignore[attr-defined]
            self.show_modal,  # type: ignore[attr-defined]
            title=title,
            prompt=prompt,
            value=value,
            help_text=help_text,
        )

    def _pl_choose(self, title: str, prompt: str, rows: list[str], help_text: str) -> int | None:
        return dlg.ask_choice(
            self.parent,  # type: ignore[attr-defined]
            self.show_modal,  # type: ignore[attr-defined]
            title=title,
            prompt=prompt,
            rows=rows,
            help_text=help_text,
        )

    def _pl_preview(self, title: str, summary: str, lines: list[str], yes: str) -> bool:
        return wdlg.ask_preview(
            self.parent,  # type: ignore[attr-defined]
            self.show_modal,  # type: ignore[attr-defined]
            title=title,
            summary=summary,
            lines=lines,
            yes=yes,
        )

    def _pl_send(self, site: str, name: str, work: Callable[[], Any], said: str) -> None:
        def done(_answer: Any) -> None:
            self.say(said)  # type: ignore[attr-defined]
            self.refresh()  # type: ignore[attr-defined]

        self.background(name, work, done)  # type: ignore[attr-defined]

    def _pl_report(self, title: str, text: str, help_text: str) -> None:
        dlg.show_report(
            self.parent,  # type: ignore[attr-defined]
            self.show_modal,  # type: ignore[attr-defined]
            title=title,
            text=text,
            help_text=help_text,
        )

    # -- products (Package 8) ----------------------------------------------------------

    def do_edit_product(self, _ref: Any, row: WbRow | None) -> None:
        if row is None or row.kind != "shop_product":
            return
        api = self.ctx(row.site).api  # type: ignore[attr-defined]
        title = f"Edit Product - {row.title}"
        answers: dict[str, str] = {}
        for key, prompt, help_text in (
            ("regular_price", "&Regular price:", "Such as 12.50, with no currency sign."),
            ("sale_price", "&Sale price (blank for none):", "Blank ends a sale."),
            ("stock_quantity", "S&tock count (blank to leave):", "A whole number."),
            ("categories", "&Categories (a comma between):", "The shop's own category names."),
        ):
            value = str(row.raw.get(key, "") or "")
            if key == "categories" and value == "none":
                value = ""
            text = self._pl_ask(title, prompt, help_text, value)
            if text is None:
                return
            answers[key] = text
        statuses = list(cat.PRODUCT_STATUSES)
        picked = self._pl_choose(
            title,
            "S&tatus:",
            [cat.PRODUCT_STATUSES[s] for s in statuses],
            "Published products can be bought; a draft cannot be seen.",
        )
        if picked is None:
            return

        def read_categories() -> list[dict[str, Any]]:
            found = api.get(f"{SHOP_NAMESPACE}/products/categories", per_page=100)
            return [c for c in found if isinstance(c, dict)] if isinstance(found, list) else []

        def chosen(known: list[dict[str, Any]]) -> None:
            try:
                ids, names = cat.category_ids(answers["categories"], known)
                edit = cat.ProductEdit(
                    regular_price=answers["regular_price"],
                    sale_price=answers["sale_price"],
                    stock_quantity=answers["stock_quantity"],
                    status=statuses[picked],
                    category_ids=ids,
                    category_names=names,
                )
                body = cat.edit_body(row.raw, edit)
            except ShopValueError as exc:
                self.say(f"{exc} Nothing was changed.")  # type: ignore[attr-defined]
                return
            if not body:
                self.say(f"Nothing about {row.title} would change.")  # type: ignore[attr-defined]
                return
            if not self._pl_preview(
                "Edit Product",
                f"Change {row.title} on {row.site}.",
                cat.edit_preview(row.title, row.site, row.raw, body, edit),
                "Change Product",
            ):
                return
            self._pl_send(
                row.site,
                f"changing {row.title}",
                lambda: api.post(cat.product_route(row.object_id), body),
                f"Changed {row.title} on {row.site}.",
            )

        self.background("reading the shop's categories", read_categories, chosen)  # type: ignore[attr-defined]

    def do_show_variations(self, _ref: Any, row: WbRow | None) -> None:
        if row is None or row.kind != "shop_product":
            return
        api = self.ctx(row.site).api  # type: ignore[attr-defined]

        def read() -> list[str]:
            found = api.iter_collection(
                f"{cat.product_route(row.object_id)}/variations", {}, per_page=100, max_pages=3
            )
            return cat.variation_lines([v for v in found if isinstance(v, dict)])

        def done(lines: list[str]) -> None:
            if not lines:
                self.say(f"{row.title} has no variations; it is not a variable product.")  # type: ignore[attr-defined]
                return
            self._pl_report(
                f"Variations - {row.title}",
                "\n".join(lines),
                "Each variation's options, price and stock, one a line.",
            )

        self.background(f"reading {row.title}'s variations", read, done)  # type: ignore[attr-defined]

    def do_duplicate_product(self, _ref: Any, row: WbRow | None) -> None:
        if row is None or row.kind != "shop_product":
            return
        if not self._pl_preview(
            "Duplicate Product",
            f"Copy {row.title} on {row.site}.",
            cat.duplicate_preview(row.title, row.site),
            "Duplicate",
        ):
            return
        api = self.ctx(row.site).api  # type: ignore[attr-defined]
        self._pl_send(
            row.site,
            f"duplicating {row.title}",
            lambda: api.post(f"{cat.product_route(row.object_id)}/duplicate", {}),
            f"Made a draft copy of {row.title} on {row.site}.",
        )

    def do_new_product(self, ref: Any, row: WbRow | None) -> None:
        site = self._shop_site(ref, row)
        if not site or not self._may_change(site):
            return
        name = self._pl_ask("New Product", "&Name:", "What shoppers see, such as Station Mug.")
        if name is None:
            return
        price = self._pl_ask("New Product", "&Price:", "Such as 12.50, or blank to set it later.")
        if price is None:
            return
        try:
            body = cat.new_product_body(name, price)
        except ShopValueError as exc:
            self.say(f"{exc} Nothing was made.")  # type: ignore[attr-defined]
            return
        if not self._pl_preview(
            "New Product",
            f"Make {body['name']} on {site}.",
            cat.new_product_preview(body, site),
            "Make Product",
        ):
            return
        api = self.ctx(site).api  # type: ignore[attr-defined]
        self._pl_send(
            site,
            f"making {body['name']}",
            lambda: api.post(f"{SHOP_NAMESPACE}/products", body),
            f"Made {body['name']} on {site}, as a draft.",
        )

    def do_trash_product(self, _ref: Any, row: WbRow | None) -> None:
        if row is None or row.kind != "shop_product":
            return
        if not self._pl_preview(
            "Move Product to Trash",
            f"Move {row.title} on {row.site} to the Trash.",
            cat.trash_preview(row.title, row.site),
            "Move to Trash",
        ):
            return
        api = self.ctx(row.site).api  # type: ignore[attr-defined]
        self._pl_send(
            row.site,
            f"trashing {row.title}",
            lambda: api.delete(cat.product_route(row.object_id)),
            f"Moved {row.title} to the Trash on {row.site}.",
        )

    # -- orders (Package 9) ------------------------------------------------------------

    def do_change_order_status(self, _ref: Any, row: WbRow | None) -> None:
        if row is None or row.kind != "shop_order":
            return
        choices = [s for s in orders.ORDER_STATUSES if s != row.status]
        picked = self._pl_choose(
            f"Change Status - {row.title}",
            "&New status:",
            [orders.ORDER_STATUSES[s] for s in choices],
            "The order's new status. The preview says which email WooCommerce sends.",
        )
        if picked is None:
            return
        new = choices[picked]
        number = str(row.raw.get("order", row.key))
        if not self._pl_preview(
            "Change Order Status",
            f"Shop order {number} on {row.site} becomes {orders.ORDER_STATUSES[new]}.",
            orders.status_preview(number, row.status, new, row.site),
            "Change Status",
        ):
            return
        api = self.ctx(row.site).api  # type: ignore[attr-defined]
        self._pl_send(
            row.site,
            f"changing shop order {number}",
            lambda: api.post(f"{SHOP_NAMESPACE}/orders/{row.object_id}", {"status": new}),
            f"Shop order {number} on {row.site} is {orders.ORDER_STATUSES[new]}.",
        )

    def do_order_notes(self, _ref: Any, row: WbRow | None) -> None:
        if row is None or row.kind != "shop_order":
            return
        api = self.ctx(row.site).api  # type: ignore[attr-defined]
        number = str(row.raw.get("order", row.key))
        route = f"{SHOP_NAMESPACE}/orders/{row.object_id}/notes"

        def read() -> list[str]:
            found = api.get(route)
            return orders.note_lines(found if isinstance(found, list) else [])

        def done(lines: list[str]) -> None:
            picked = self._pl_choose(
                f"Notes - Shop order {number}",
                "&Notes, newest first:",
                [*lines, "Add a private note...", "Add a note to the customer..."],
                "Read each note; the last two rows add one.",
            )
            if picked is None or picked < len(lines):
                return
            to_customer = picked == len(lines) + 1
            text = self._pl_ask(f"Add a Note - Shop order {number}", "&Note:", "The note's words.")
            if text is None:
                return
            try:
                lines_said = orders.note_preview(number, text, to_customer, row.site)
            except ShopValueError as exc:
                self.say(f"{exc} Nothing was added.")  # type: ignore[attr-defined]
                return
            if not self._pl_preview(
                "Add a Note", f"A note on shop order {number}.", lines_said, "Add Note"
            ):
                return
            body = {"note": text.strip(), "customer_note": to_customer}
            self._pl_send(
                row.site,
                f"adding a note to shop order {number}",
                lambda: api.post(route, body),
                f"Added the note to shop order {number}"
                + (", and WooCommerce emailed it to the customer." if to_customer else "."),
            )

        self.background(f"reading shop order {number}'s notes", read, done)  # type: ignore[attr-defined]

    def do_refund_order(self, _ref: Any, row: WbRow | None) -> None:
        """Money moves: one order, a money warning, and the amount typed before anything is sent."""
        if row is None or row.kind != "shop_order":
            return
        if len(self.selected_rows()) > 1:  # type: ignore[attr-defined]
            self.say(  # type: ignore[attr-defined]
                "A refund is made one order at a time, never for a selection. Select one order."
            )
            return
        api = self.ctx(row.site).api  # type: ignore[attr-defined]
        number = str(row.raw.get("order", row.key))

        def read() -> dict[str, Any]:
            found = api.get(f"{SHOP_NAMESPACE}/orders/{row.object_id}")
            return found if isinstance(found, dict) else {}

        def chosen(order: dict[str, Any]) -> None:
            title = f"Refund - Shop order {number}"
            amount = self._pl_ask(
                title, "&Amount to refund:", "Such as 12.50, with no currency sign."
            )
            if amount is None:
                return
            reason = self._pl_ask(title, "&Reason (kept with the order):", "Why it is refunded.")
            if reason is None:
                return
            gateway = self._pl_choose(
                title,
                "&How:",
                [
                    "Return the money through the payment gateway",
                    "Record the refund only; I return the money myself",
                ],
                "Whether WooCommerce asks the payment gateway to send the money back.",
            )
            if gateway is None:
                return
            try:
                plan = orders.plan_refund(order, amount, reason, through_gateway=gateway == 0)
            except ShopValueError as exc:
                self.say(f"{exc} Nothing was refunded.")  # type: ignore[attr-defined]
                return
            if not self._pl_preview(
                "Refund",
                f"Money warning: refund {plan.amount} {plan.currency} on shop order {number}.",
                orders.refund_preview(plan, row.site),
                "Go On to Confirm",
            ):
                return
            typed = self._pl_ask(
                title,
                f"&Type the amount, {plan.amount}, to refund it:",
                "The refund is sent only when this is the amount exactly. Cancel sends nothing.",
            )
            if not orders.refund_confirmed(plan, typed):
                self.say("The amount typed did not match, so nothing was refunded.")  # type: ignore[attr-defined]
                return
            how = "through the payment gateway" if plan.through_gateway else "as a record only"
            self._pl_send(
                row.site,
                f"refunding shop order {number}",
                lambda: api.post(orders.refund_route(plan.order_id), orders.refund_body(plan)),
                f"Refunded {plan.amount} {plan.currency} on shop order {number}, {how}.",
            )

        self.background(f"reading shop order {number}", read, chosen)  # type: ignore[attr-defined]

    # -- coupons (Package 9) -------------------------------------------------------------

    def _coupon_spec(self, title: str, old: dict[str, Any]) -> orders.CouponSpec | None:
        kinds = list(orders.COUPON_TYPES)
        code = self._pl_ask(
            title, "&Code:", "What shoppers type, such as SPRING10.", old.get("code", "")
        )
        if code is None:
            return None
        picked = self._pl_choose(
            title,
            "&Discount:",
            [orders.COUPON_TYPES[k] for k in kinds],
            "How the discount is worked out.",
        )
        if picked is None:
            return None
        answers = []
        for key, prompt, help_text in (
            ("amount", "&Amount:", "Such as 10 for ten percent, or 5.00."),
            ("expires", "&Expires (YYYY-MM-DD, blank for never):", "The last day it works."),
            ("usage_limit", "&Uses allowed (blank for no limit):", "A whole number."),
        ):
            text = self._pl_ask(title, prompt, help_text, str(old.get(key, "") or ""))
            if text is None:
                return None
            answers.append(text)
        return orders.CouponSpec(code, kinds[picked], *answers, str(old.get("description", "")))

    def do_new_coupon(self, ref: Any, row: WbRow | None) -> None:
        site = self._shop_site(ref, row)
        if not site or not self._may_change(site):
            return
        spec = self._coupon_spec("New Coupon", {})
        if spec is None:
            return
        try:
            body = orders.coupon_body(spec)
        except ShopValueError as exc:
            self.say(f"{exc} Nothing was made.")  # type: ignore[attr-defined]
            return
        if not self._pl_preview(
            "New Coupon",
            f"Make coupon {spec.code} on {site}.",
            orders.coupon_preview(spec, site, body, new=True),
            "Make Coupon",
        ):
            return
        api = self.ctx(site).api  # type: ignore[attr-defined]
        self._pl_send(
            site,
            f"making coupon {spec.code}",
            lambda: api.post(f"{SHOP_NAMESPACE}/coupons", body),
            f"Made coupon {spec.code} on {site}.",
        )

    def do_edit_coupon(self, _ref: Any, row: WbRow | None) -> None:
        if row is None or row.kind != "shop_coupon":
            return
        spec = self._coupon_spec(f"Edit Coupon - {row.title}", dict(row.raw))
        if spec is None:
            return
        try:
            body = orders.coupon_body(spec, row.raw)
        except ShopValueError as exc:
            self.say(f"{exc} Nothing was changed.")  # type: ignore[attr-defined]
            return
        if not body:
            self.say(f"Nothing about coupon {row.title} would change.")  # type: ignore[attr-defined]
            return
        if not self._pl_preview(
            "Edit Coupon",
            f"Change coupon {row.title} on {row.site}.",
            orders.coupon_preview(spec, row.site, body, new=False),
            "Change Coupon",
        ):
            return
        api = self.ctx(row.site).api  # type: ignore[attr-defined]
        self._pl_send(
            row.site,
            f"changing coupon {row.title}",
            lambda: api.post(f"{SHOP_NAMESPACE}/coupons/{row.object_id}", body),
            f"Changed coupon {spec.code} on {row.site}.",
        )

    def do_trash_coupon(self, _ref: Any, row: WbRow | None) -> None:
        if row is None or row.kind != "shop_coupon":
            return
        if not self._pl_preview(
            "Move Coupon to Trash",
            f"Move coupon {row.title} to the Trash.",
            orders.coupon_trash_preview(row.title, row.site),
            "Move to Trash",
        ):
            return
        api = self.ctx(row.site).api  # type: ignore[attr-defined]
        self._pl_send(
            row.site,
            f"trashing coupon {row.title}",
            lambda: api.delete(f"{SHOP_NAMESPACE}/coupons/{row.object_id}"),
            f"Moved coupon {row.title} to the Trash on {row.site}.",
        )

    # -- store settings (Package 10) ------------------------------------------------------

    def do_change_shop_setting(self, _ref: Any, row: WbRow | None) -> None:
        if row is None or row.kind != "shop_setting" or not row.raw.get("id"):
            return
        title = f"Change Setting - {row.raw.get('label', '')}"
        try:
            choice = settings.choices_for(row.raw)
        except ShopValueError as exc:
            self.say(str(exc))  # type: ignore[attr-defined]
            return
        if choice.values:
            picked = self._pl_choose(
                title,
                "&New value:",
                [words for _v, words in choice.values],
                "The setting's new value.",
            )
            if picked is None:
                return
            new: Any = choice.values[picked][0]
        else:
            text = self._pl_ask(
                title, "&New value:", "The setting's new value.", row.raw.get("said", "")
            )
            if text is None:
                return
            try:
                new = settings.value_to_send(row.raw, text)
            except ShopValueError as exc:
                self.say(f"{exc} Nothing was changed.")  # type: ignore[attr-defined]
                return
        if str(new) == str(row.raw.get("value", "")):
            self.say("That is its value already. Nothing was changed.")  # type: ignore[attr-defined]
            return
        if not self._pl_preview(
            "Change Setting",
            f"Change a WooCommerce setting on {row.site}.",
            settings.setting_preview(row.raw, new, row.site),
            "Change Setting",
        ):
            return
        api = self.ctx(row.site).api  # type: ignore[attr-defined]
        self._pl_send(
            row.site,
            f"changing {row.raw.get('label', 'a setting')}",
            lambda: api.post(settings.setting_route(row.raw), {"value": new}),
            f"Changed {row.raw.get('label', 'the setting')} on {row.site}.",
        )
