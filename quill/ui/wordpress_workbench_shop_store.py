"""Payment Gateways, System Status's tools, and Resend Order Details in the Workbench.

The Workbench side of :mod:`quill.core.wordpress.workbench_shop_store` (complete.md
2.3, Shop). Each is a preview, then one request, then a step in Change History;
turning a gateway on or off can be undone, running a tool or sending an email
cannot, and says so.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.wordpress import workbench_shop_store as store
from quill.core.wordpress.workbench_rows import WbRow
from quill.ui.wordpress_workbench_shop_order_edit import WorkbenchShopOrderEditCommands

__all__ = ["WorkbenchShopStoreCommands"]


class WorkbenchShopStoreCommands(WorkbenchShopOrderEditCommands):
    """Mixed into the provider beside the other shop commands, whose helpers it uses.

    New Order, Change Items and Change Address come from its base.
    """

    say: Callable[[str], None]
    ctx: Callable[[str], Any]
    background: Callable[..., None]
    refresh: Callable[[], None]
    step: Callable[..., None]
    _pl_preview: Callable[[str, str, list[str], str], bool]

    def do_toggle_gateway(self, _ref: Any, row: WbRow | None) -> None:
        if row is None or row.kind != "shop_gateway":
            return
        on = row.status != "active"
        verb = "Turn On" if on else "Turn Off"
        name = row.cell("name") or row.title
        summary = (
            f"{name} on {row.site} is offered at checkout from now on."
            if on
            else f"{name} on {row.site} is no longer offered at checkout."
        )
        if not self._pl_preview(f"{verb} {name}", summary, [summary], verb):
            return
        api = self.ctx(row.site).api

        def undo() -> str:
            store.set_gateway(api, row.key, not on)
            return f"{name} on {row.site} is {'off' if on else 'on'} again."

        def done(kept: bool) -> None:
            if not kept:
                self.say(f"WooCommerce did not keep the change to {name}. Nothing changed.")
                return
            said = f"{name} on {row.site} is {'on' if on else 'off'}."
            self.say(said)
            self.step(row.site, said, undo)
            self.refresh()

        self.background(
            f"turning {name} {'on' if on else 'off'}",
            lambda: store.set_gateway(api, row.key, on),
            done,
        )

    def do_run_shop_tool(self, _ref: Any, row: WbRow | None) -> None:
        if row is None or row.kind != "shop_tool":
            return
        name = row.cell("name") or row.title
        what = row.cell("value")
        if not self._pl_preview(
            f"Run {name}",
            f"Run {name} on {row.site}? It cannot be undone.",
            [line for line in (what, f"On {row.site}.") if line],
            "Run Tool",
        ):
            return
        api = self.ctx(row.site).api

        def done(said: str) -> None:
            self.say(f"{name} on {row.site}: {said}")
            self.step(row.site, f"Ran {name} on {row.site}")

        self.background(f"running {name}", lambda: store.run_tool(api, row.key), done)

    def do_resend_order_details(self, _ref: Any, row: WbRow | None) -> None:
        if row is None or row.kind != "shop_order":
            return
        number = str(row.raw.get("order", row.key))
        who = row.cell("customer") or "the customer"
        if not self._pl_preview(
            "Resend Order Details",
            f"Send shop order {number}'s details to {who} again?",
            [f"WooCommerce emails {who} the order details, as when the order was placed."],
            "Send",
        ):
            return
        api = self.ctx(row.site).api

        def done(said: str) -> None:
            self.say(f"Shop order {number}: {said}")
            self.step(row.site, f"Resent shop order {number}'s details on {row.site}")

        self.background(
            f"resending shop order {number}",
            lambda: store.resend_order_details(api, row.object_id),
            done,
        )
