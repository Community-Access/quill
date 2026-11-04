"""Shop Orders, read aloud and never edited (wordpress.md 9.15).

A mixin of :class:`~quill.ui.wordpress_commands.WordPressCommands`, offered
only when the site has WooCommerce (``wc/v3``). Orders hold customers' names
and addresses, so this window only reads: nothing here changes an order, and
an order leaves QUILL (to the clipboard) only after a question that says what
goes with it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from quill.core.wordpress import plugin_shop_seo as shop
from quill.core.wordpress import site as wp
from quill.core.wordpress import site_features as sf
from quill.ui import wordpress_dialogs as dlg
from quill.ui.wordpress_api_site_base import WordPressApiSiteBase, role_cannot

if TYPE_CHECKING:
    from quill.core.wordpress import sites as st


class WordPressShopCommands(WordPressApiSiteBase):
    def cmd_shop_orders(self) -> None:
        profile = self.chosen_site("Shop Orders")
        if profile is None:
            return

        def why_not(index: sf.SiteIndex, account: wp.Account) -> str:
            if not index.supports(shop.SHOP_NAMESPACE):
                return f"{profile.name} does not have WooCommerce, so it has no shop orders."
            return role_cannot(
                profile.name, account, "manage_woocommerce", "read the shop's orders"
            )

        self.when_offered(
            profile,
            f"reading {profile.name}'s orders",
            why_not,
            lambda api, _index, _account: shop.recent_orders(api),
            lambda orders: self._show_orders(profile, orders),
        )

    def _show_orders(self, profile: st.SiteProfile, orders: list[shop.Order]) -> None:
        if not orders:
            self.host.announce(f"{profile.name} has no orders yet.")
            return

        def copy_one(index: int | None) -> object:
            if index is None or index >= len(orders):
                return None
            order = orders[index]
            if not dlg.confirm(
                self.host.parent,
                self.host.show_modal,
                title="Copy Order",
                message=(
                    f"Copy order {order.number} to the clipboard? It includes the customer's "
                    "name and shipping address, which then go wherever you paste them."
                ),
                yes_label="Copy Order",
            ):
                return None
            self.host.set_clipboard_text(f"{order.spoken()}\n{order.details()}")
            self.host.announce(f"Order {order.number} copied.")
            return None

        window = dlg.show_list_window(
            self.host.parent,
            self.host.show_modal,
            title=f"Shop Orders, {profile.name}",
            purpose=(
                f"The newest orders on {profile.name}, read only. QUILL never changes an order; "
                "use the shop's own screens for that."
            ),
            list_label="&Orders:",
            list_help="Each order's number, status, items, total, customer and date.",
            rows=[o.spoken() for o in orders],
            details=lambda index: orders[index].details(),
            actions=[
                dlg.Action(
                    "&Copy Order...",
                    "Copy the selected order to the clipboard, after asking.",
                    copy_one,
                )
            ],
        )
        window.Destroy()
