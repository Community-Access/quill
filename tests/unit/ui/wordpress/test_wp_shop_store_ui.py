"""The Workbench's Payment Gateways, Run Tool and Resend Order Details (complete.md 2.3)."""

from __future__ import annotations

import pytest

pytest.importorskip("wx")

from quill.core.wordpress import workbench_shop_store as store  # noqa: E402
from quill.core.wordpress.workbench_rows import WbRow  # noqa: E402
from tests.unit.ui.wordpress.test_wp_workbench_plugins_ui import (  # noqa: E402
    SITE,
    _ref,
)
from tests.unit.ui.wordpress.test_wp_workbench_plugins_ui import bench as _bench  # noqa: E402

bench = _bench


def _gateway(on: bool) -> WbRow:
    raw = {"id": "cod", "method_title": "Cash on delivery", "title": "Pay later", "enabled": on}
    return store.gateway_row(raw, SITE)


def test_turning_a_gateway_off_previews_records_and_undoes(bench) -> None:
    bench.provider.do_toggle_gateway(_ref("shop_gateways"), _gateway(True))
    assert bench.answers.previews[-1]["yes"] == "Turn Off"
    assert bench.api.sent[-1] == ("POST", "wc/v3/payment_gateways/cod", {"enabled": False})
    assert bench.said[-1] == f"Cash on delivery on {SITE} is off."
    step = bench.provider.history.entries[-1]
    assert step.undo is not None


def test_running_a_tool_says_it_cannot_be_undone_first(bench) -> None:
    tool = store.tool_row({"id": "clear_transients", "name": "Transients"}, SITE)
    bench.provider.do_run_shop_tool(_ref("shop_status"), tool)
    assert "cannot be undone" in bench.answers.previews[-1]["summary"]
    assert bench.api.sent[-1] == (
        "POST",
        "wc/v3/system_status/tools/clear_transients",
        {"confirm": True},
    )


def test_resend_order_details_on_an_order(bench) -> None:
    order = WbRow("shop_order", SITE, "77", {"customer": "Ann"}, "", raw={"order": "1077"})
    bench.provider.do_resend_order_details(_ref("shop_orders"), order)
    assert bench.answers.previews[-1]["summary"] == "Send shop order 1077's details to Ann again?"
    assert bench.api.sent[-1] == ("POST", "wc/v3/orders/77/actions/send_order_details", {})
    assert bench.provider.history.entries[-1].summary.startswith("Resent shop order 1077")
