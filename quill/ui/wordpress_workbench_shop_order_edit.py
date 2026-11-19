"""New Order, Change Items and Change Address in the Workbench (complete.md 2.3, Shop).

The Workbench side of :mod:`quill.core.wordpress.workbench_shop_order_edit`.
Each asks, previews in words, sends one request and becomes a step in Change
History: a new order can be undone by moving it to the Trash, an address by
sending the old one back; changed items cannot be undone here, and the
preview says so.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.wordpress import workbench_shop_order_edit as edit
from quill.core.wordpress.plugin_shop_seo import SHOP_NAMESPACE, ShopValueError
from quill.core.wordpress.site import raw_text
from quill.core.wordpress.workbench_rows import WbRow

__all__ = ["WorkbenchShopOrderEditCommands"]

_GUEST = "A guest, by name and email"
_DONE = "Done choosing"
_ADD = "Add a product..."


def _product_choices(found: Any) -> list[tuple[int, str]]:
    rows = found if isinstance(found, list) else []
    return [
        (int(r["id"]), raw_text(r.get("name")) or f"Product {r['id']}")
        for r in rows
        if isinstance(r, dict) and str(r.get("id", "")).isdigit()
    ]


def _person_words(person: dict[str, Any]) -> str:
    name = f"{raw_text(person.get('first_name'))} {raw_text(person.get('last_name'))}".strip()
    return ", ".join(part for part in (name, str(person.get("email") or "")) if part)


class WorkbenchShopOrderEditCommands:
    """Mixed in beside the other shop commands, whose plumbing it uses."""

    say: Callable[[str], None]
    ctx: Callable[[str], Any]
    background: Callable[..., None]
    refresh: Callable[[], None]
    step: Callable[..., None]
    _shop_site: Callable[[Any, WbRow | None], str]
    _may_change: Callable[[str], bool]
    _pl_ask: Callable[..., str | None]
    _pl_choose: Callable[..., int | None]
    _pl_preview: Callable[[str, str, list[str], str], bool]

    # -- picking products ------------------------------------------------------------

    def _pick_lines(
        self, title: str, products: list[tuple[int, str]]
    ) -> list[tuple[int, str, int]]:
        """Products and quantities, chosen one at a time until Done."""
        chosen: list[tuple[int, str, int]] = []
        while True:
            names = [_DONE] + [name for _id, name in products]
            picked = self._pl_choose(
                title,
                f"&Product ({len(chosen)} chosen so far):",
                names,
                "Choose a product to add, then its quantity. Done choosing ends the list.",
            )
            if picked is None:
                return []
            if picked == 0:
                return chosen
            product_id, name = products[picked - 1]
            quantity = self._ask_quantity(title, name, allow_zero=False)
            if quantity > 0:
                chosen.append((product_id, name, quantity))

    def _ask_quantity(self, title: str, name: str, *, allow_zero: bool, value: str = "1") -> int:
        while True:
            text = self._pl_ask(
                title,
                f"&Quantity of {name}:",
                "A whole number." + (" 0 takes it off the order." if allow_zero else ""),
                value,
            )
            if text is None:
                return -1
            try:
                return edit.parse_quantity(text, allow_zero=allow_zero)
            except ShopValueError as exc:
                self.say(str(exc))

    def _ask_address(
        self, title: str, old: dict[str, Any], *, shipping: bool
    ) -> dict[str, str] | None:
        found: dict[str, str] = {}
        for key, name in edit.ADDRESS_FIELDS:
            if shipping and key in ("email", "phone"):
                continue
            text = self._pl_ask(
                title, f"&{name}:", "Leave it as it is to keep it.", str(old.get(key) or "")
            )
            if text is None:
                return None
            found[key] = text
        return found

    # -- New Order --------------------------------------------------------------------

    def do_new_order(self, ref: Any, row: WbRow | None) -> None:
        site = self._shop_site(ref, row)
        if not site or not self._may_change(site):
            return
        api = self.ctx(site).api

        def read() -> tuple[list[Any], list[tuple[int, str]]]:
            people = api.get(f"{SHOP_NAMESPACE}/customers", per_page=100, role="all")
            goods = api.get(f"{SHOP_NAMESPACE}/products", per_page=100, status="publish")
            return (people if isinstance(people, list) else []), _product_choices(goods)

        self.background(
            f"reading {site}'s customers and products",
            read,
            lambda got: self._new_order(site, *got),
        )

    def _new_order(self, site: str, people: list[Any], products: list[tuple[int, str]]) -> None:
        title = "New Order"
        if not products:
            self.say(f"{site} has no published products to put on an order.")
            return
        named = [p for p in people if isinstance(p, dict) and p.get("id")]
        labels = [_GUEST] + [_person_words(p) for p in named]
        picked = self._pl_choose(title, "&Customer:", labels, "Who the order is for.")
        if picked is None:
            return
        customer_id, customer_name, billing = 0, "", {}
        if picked == 0:
            address = self._ask_address(title, {}, shipping=False)
            if address is None:
                return
            billing = address
            customer_name = (
                f"{address.get('first_name', '')} {address.get('last_name', '')}".strip()
            )
        else:
            person = named[picked - 1]
            customer_id, customer_name = int(person["id"]), labels[picked]
            kept = person.get("billing")
            billing = {k: str(v) for k, v in kept.items() if v} if isinstance(kept, dict) else {}
        lines = self._pick_lines(title, products)
        if not lines:
            self.say("No products were chosen. Nothing was made.")
            return
        statuses = list(edit.NEW_ORDER_STATUSES)
        chosen = self._pl_choose(
            title,
            "&Starts as:",
            [edit.NEW_ORDER_STATUSES[s] for s in statuses],
            "Its first status.",
        )
        if chosen is None:
            return
        order = edit.NewOrder(statuses[chosen], customer_id, customer_name, billing, lines)
        try:
            body = edit.new_order_body(order)
        except ShopValueError as exc:
            self.say(f"{exc} Nothing was made.")
            return
        if not self._pl_preview(
            title,
            f"Make a shop order on {site}.",
            edit.new_order_preview(order, site),
            "Make Order",
        ):
            return
        api = self.ctx(site).api

        def done(made: Any) -> None:
            number = str((made or {}).get("number") or (made or {}).get("id") or "")
            made_id = int((made or {}).get("id") or 0)
            said = f"Made shop order {number} on {site}."

            def undo() -> str:
                api.delete(edit.order_route(made_id))
                return f"Shop order {number} on {site} is in the Trash."

            self.say(said)
            self.step(site, said.rstrip("."), undo if made_id else None)
            self.refresh()

        self.background(
            "making the shop order", lambda: api.post(f"{SHOP_NAMESPACE}/orders", body), done
        )

    # -- Change Items -----------------------------------------------------------------

    def do_change_order_items(self, _ref: Any, row: WbRow | None) -> None:
        if row is None or row.kind != "shop_order" or not self._may_change(row.site):
            return
        api = self.ctx(row.site).api

        def read() -> tuple[Any, list[tuple[int, str]]]:
            order = api.get(edit.order_route(row.object_id))
            goods = api.get(f"{SHOP_NAMESPACE}/products", per_page=100, status="publish")
            return order, _product_choices(goods)

        self.background(
            f"reading shop order {row.raw.get('order', row.key)}",
            read,
            lambda got: self._change_items(row, *got),
        )

    def _change_items(self, row: WbRow, order: Any, products: list[tuple[int, str]]) -> None:
        number = str(row.raw.get("order", row.key))
        title = f"Change Items - Shop Order {number}"
        items = edit.order_items(order if isinstance(order, dict) else {})
        changes: list[edit.ItemChange] = []
        while True:
            labels = [_DONE, _ADD] + [item.words() for item in items]
            picked = self._pl_choose(
                title,
                f"&Item ({len(changes)} changed so far):",
                labels,
                "Choose an item to change its quantity, or add a product.",
            )
            if picked is None:
                return
            if picked == 0:
                break
            if picked == 1:
                for product_id, name, quantity in self._pick_lines(title, products):
                    changes.append(edit.ItemChange(0, product_id, name, quantity))
                continue
            item = items[picked - 2]
            quantity = self._ask_quantity(
                title, item.name, allow_zero=True, value=str(item.quantity)
            )
            if quantity >= 0 and quantity != item.quantity:
                changes = [c for c in changes if c.item_id != item.item_id]
                changes.append(edit.ItemChange(item.item_id, item.product_id, item.name, quantity))
        try:
            body = edit.items_body(changes)
        except ShopValueError as exc:
            self.say(str(exc))
            return
        lines = edit.items_preview(number, items, changes, row.site) + [
            "This cannot be undone here; Change Items again puts it back."
        ]
        if not self._pl_preview(
            title, f"Change the items on shop order {number}.", lines, "Change Items"
        ):
            return
        api = self.ctx(row.site).api
        said = f"Changed the items on shop order {number} on {row.site}."

        def done(_answer: Any) -> None:
            self.say(said)
            self.step(row.site, said.rstrip("."))
            self.refresh()

        self.background(
            f"changing shop order {number}",
            lambda: api.post(edit.order_route(row.object_id), body),
            done,
        )

    # -- Change Address ---------------------------------------------------------------

    def do_change_order_address(self, _ref: Any, row: WbRow | None) -> None:
        if row is None or row.kind != "shop_order" or not self._may_change(row.site):
            return
        api = self.ctx(row.site).api
        self.background(
            f"reading shop order {row.raw.get('order', row.key)}",
            lambda: api.get(edit.order_route(row.object_id)),
            lambda order: self._change_address(row, order if isinstance(order, dict) else {}),
        )

    def _change_address(self, row: WbRow, order: dict[str, Any]) -> None:
        number = str(row.raw.get("order", row.key))
        title = f"Change Address - Shop Order {number}"
        picked = self._pl_choose(
            title, "&Address:", ["Billing", "Shipping"], "Which address to change."
        )
        if picked is None:
            return
        which = ("billing", "shipping")[picked]
        old = order.get(which) if isinstance(order.get(which), dict) else {}
        new = self._ask_address(title, old, shipping=which == "shipping")
        if new is None:
            return
        try:
            body, back = edit.address_body(which, old, new)
        except ShopValueError as exc:
            self.say(str(exc))
            return
        if not self._pl_preview(
            title,
            f"Change the {which} address on shop order {number}.",
            edit.address_preview(number, which, old, body, row.site),
            "Change Address",
        ):
            return
        api = self.ctx(row.site).api
        route = edit.order_route(row.object_id)
        said = f"Changed the {which} address on shop order {number} on {row.site}."

        def undo() -> str:
            api.post(route, back)
            return f"Shop order {number}'s {which} address on {row.site} is as it was."

        def done(_answer: Any) -> None:
            self.say(said)
            self.step(row.site, said.rstrip("."), undo)
            self.refresh()

        self.background(f"changing shop order {number}", lambda: api.post(route, body), done)
