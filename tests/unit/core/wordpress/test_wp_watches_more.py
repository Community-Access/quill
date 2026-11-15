"""The later Watches (WP-R-020, WP-R-050): shop, certificate, abandoned plugins, statement, weekly.

A fake site answers as WordPress and WooCommerce do; the certificate and
WordPress.org readers are fakes, so nothing here touches the network. Every
Watch's first look is silent, and a change is said once.
"""

from __future__ import annotations

import io
import json
from datetime import datetime
from typing import Any

from quill.core.wordpress import workbench_watches as watches
from quill.core.wordpress.site_certificate import CertificateError, certificate_host
from quill.core.wordpress.site_report import HistoryEntry
from quill.core.wordpress.workbench_watches import WatchState, check
from quill.core.wordpress.workbench_watches_more import WatchContext

DAY = 86400.0
NOW = datetime(2026, 11, 10, 9, 0).timestamp()  # a Tuesday, ISO week 46


class _Address:
    wpcom_site = ""
    is_wpcom = False

    def __init__(self, url: str) -> None:
        self.site_url = url


class Shop:
    def __init__(self, url: str = "https://shop.example") -> None:
        self.address = _Address(url)
        self.orders: list[dict[str, Any]] = [{"id": 10, "number": "1010"}]
        self.products: list[dict[str, Any]] = [
            {"id": 1, "name": "Blue Mug", "manage_stock": True, "stock_quantity": 9,
             "low_stock_amount": None},
            {"id": 2, "name": "Tote", "manage_stock": True, "stock_quantity": 5,
             "low_stock_amount": 6},
            {"id": 3, "name": "Poster", "manage_stock": False, "stock_quantity": None},
        ]  # fmt: skip
        self.plugins = [{"plugin": "old-gallery/old-gallery", "name": "Old Gallery"}]
        self.comments: list[int] = []
        self.statement: list[dict[str, Any]] = []
        self.reads: list[str] = []

    def get(self, route: str, **params: Any) -> Any:
        self.reads.append(route)
        if route == "wc/v3/orders":
            return sorted(self.orders, key=lambda o: -o["id"])[: params.get("per_page", 10)]
        if route == "wc/v3/settings/products/woocommerce_notify_low_stock_amount":
            return {"id": "woocommerce_notify_low_stock_amount", "value": "3"}
        if route == "wp/v2/pages" and params.get("slug") == "accessibility":
            return list(self.statement)
        return []

    def iter_collection(self, route: str, params: Any = None, **_kw: Any):
        self.reads.append(route)
        if route == "wc/v3/products":
            yield from self.products
        if route == "wp/v2/plugins":
            yield from self.plugins
        if route == "wp/v2/comments":
            for ident in self.comments:
                yield {"id": ident}


SPACES = ["wp/v2", "wc/v3"]


def _round(site: Shop, state: WatchState, kinds: list[str], ctx: WatchContext, now=NOW):
    return check([("Shop", site, SPACES)], state, kinds, now=lambda: now, context=ctx)


def test_new_orders_are_said_once_after_a_silent_first_look() -> None:
    site, state, ctx = Shop(), WatchState(), WatchContext()
    assert _round(site, state, ["order"], ctx) == []
    site.orders += [{"id": 11, "number": "1011"}, {"id": 12, "number": "1012"}]
    assert _round(site, state, ["order"], ctx) == ["2 new orders on Shop: number 1011, 1012."]
    assert _round(site, state, ["order"], ctx) == []


def test_a_site_without_woocommerce_is_never_asked_about_orders_or_stock() -> None:
    site, state = Shop(), WatchState()
    check([("Plain", site, ["wp/v2"])], state, ["order", "low_stock"], context=WatchContext())
    assert not [r for r in site.reads if r.startswith("wc/v3")]


def test_low_stock_uses_each_products_amount_else_the_shops() -> None:
    site, state, ctx = Shop(), WatchState(), WatchContext()
    assert _round(site, state, ["low_stock"], ctx) == []  # Tote (5 of 6) is learned, not said
    site.products[0]["stock_quantity"] = 0  # the shop's amount is 3
    assert _round(site, state, ["low_stock"], ctx) == ["Low stock on Shop: Blue Mug, none left."]
    assert _round(site, state, ["low_stock"], ctx) == []


def test_the_certificate_watch_reads_once_a_day_and_says_it_once() -> None:
    asked: list[tuple[str, int]] = []
    expiry = {"at": NOW + 90 * DAY}

    def reader(host: str, port: int) -> float:
        asked.append((host, port))
        return expiry["at"]

    site, state, ctx = (
        Shop("https://shop.example:8443/"),
        WatchState(),
        WatchContext(cert_reader=reader),
    )
    assert _round(site, state, ["certificate"], ctx) == []
    assert _round(site, state, ["certificate"], ctx, now=NOW + 60) == []
    assert asked == [("shop.example", 8443)], "once a day"
    expiry["at"] = NOW + 20 * DAY
    said = _round(site, state, ["certificate"], ctx, now=NOW + DAY)
    assert len(said) == 1 and "runs out on 30 November 2026, in 19 days" in said[0]
    assert _round(site, state, ["certificate"], ctx, now=NOW + 2 * DAY) == []
    expiry["at"] = NOW + 400 * DAY
    said = _round(site, state, ["certificate"], ctx, now=NOW + 3 * DAY)
    assert said and said[0].startswith("The security certificate for Shop was renewed")


def test_an_untrusted_certificate_is_said_once_and_plain_http_is_never_read() -> None:
    def reader(_host: str, _port: int) -> float:
        raise CertificateError(
            "The certificate is not trusted: certificate has expired.", untrusted=True
        )

    site, state, ctx = Shop(), WatchState(), WatchContext(cert_reader=reader)
    assert _round(site, state, ["certificate"], ctx) == []
    said = _round(site, state, ["certificate"], ctx, now=NOW + DAY)
    assert said == [
        "The security certificate for Shop is not trusted now, so browsers warn visitors "
        "away. The certificate is not trusted: certificate has expired."
    ]
    assert _round(site, state, ["certificate"], ctx, now=NOW + 2 * DAY) == []
    assert certificate_host("http://plain.example") is None
    assert certificate_host("https://a.example") == ("a.example", 443)


def _dotorg(updated: str):
    asked: list[str] = []

    class _Answer(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *_a: Any) -> None:
            return None

    def opener(request: Any, timeout: float | None = None) -> Any:
        asked.append(request.full_url)
        body = {"slug": "old-gallery", "name": "Old Gallery", "version": "1.0",
                "last_updated": updated}  # fmt: skip
        return _Answer(json.dumps(body).encode())

    return opener, asked


def test_abandoned_plugins_ask_wordpress_org_once_a_week_with_the_short_name_only() -> None:
    opener, asked = _dotorg("2025-06-01")
    site, state = Shop(), WatchState()
    ctx = WatchContext(dotorg_opener=opener)
    assert _round(site, state, ["abandoned"], ctx) == []
    assert len(asked) == 1 and "old-gallery" in asked[0] and "shop.example" not in asked[0]
    assert _round(site, state, ["abandoned"], ctx, now=NOW + DAY) == []
    assert len(asked) == 1, "once a week"
    opener2, asked2 = _dotorg("2024-01-02")  # a week on, WordPress.org says two years and more
    ctx.dotorg_opener = opener2
    said = _round(site, state, ["abandoned"], ctx, now=NOW + 7 * DAY)
    assert said == [
        "On Shop: Old Gallery has not been updated on WordPress.org since 2024-01-02, over "
        "two years: it may be abandoned."
    ]
    assert len(asked2) == 1


def _entry(day: str, problems: int) -> HistoryEntry:
    return HistoryEntry(date=f"{day}T10:00:00+00:00", pages=40, problems=problems)


def test_the_statement_watch_notices_when_its_facts_change() -> None:
    site, state = Shop(), WatchState()
    site.statement = [{"id": 7, "modified_gmt": "2026-10-05T09:00:00"}]
    ctx = WatchContext(history={"Shop": _entry("2026-10-01", 41)})
    assert _round(site, state, ["statement"], ctx) == []
    assert _round(site, state, ["statement"], ctx) == [], "the same facts say nothing"
    ctx.history = {"Shop": _entry("2026-11-08", 6)}
    said = _round(site, state, ["statement"], ctx)
    assert said == [
        "The accessibility statement on Shop is out of date: Check the Whole Site, in November "
        "2026, found 6 things to fix across 40 pages, and the statement was last saved before "
        "that. Write an Accessibility Statement drafts it again."
    ]
    site.statement = [{"id": 7, "modified_gmt": "2026-11-09T09:00:00"}]
    ctx.history = {"Shop": _entry("2026-11-09", 0)}
    site.statement = [{"id": 7, "modified_gmt": "2026-11-09T12:00:00"}]
    assert _round(site, state, ["statement"], ctx) == [], "saved since the check"


def test_the_weekly_sentence_sums_up_the_site_once_a_week(tmp_path) -> None:
    site, state = Shop(), WatchState()
    site.comments = [1, 2]
    state.health["Shop"] = {"https": "critical", "php": "good"}
    ctx = WatchContext()
    assert _round(site, state, ["weekly"], ctx) == []
    assert _round(site, state, ["weekly"], ctx, now=NOW + DAY) == [], "the same week"
    said = _round(site, state, ["weekly"], ctx, now=NOW + 7 * DAY)
    assert said == [
        "This week on Shop: 2 comments waiting; 1 product low on stock; 1 Site Health test "
        "critical."
    ]
    watches.save_state(state, tmp_path)
    again = watches.load_state(tmp_path)
    assert again.extra["weekly"] == {"Shop": "2026-W47"}
    assert "Shop:weekly" in again.seen


def test_the_editor_s_round_hands_the_statement_watch_its_local_check_history(tmp_path) -> None:
    from quill.core.wordpress.sites import SiteProfile, SiteStore
    from quill.core.wordpress.workbench_options import WorkbenchOptions, save_options
    from quill.ui.wordpress_watch_commands import watch_round

    said: list[str] = []
    site = Shop()
    site.statement = [{"id": 7, "modified_gmt": "2026-01-01T09:00:00"}]
    latest = {"entry": _entry("2026-10-01", 41)}

    class _Host:
        def announce(self, text: str) -> None:
            said.append(text)

        def run_task(self, _name: str, work: Any, done: Any, _failed: Any) -> None:
            done(work())

    class _History:
        def latest(self, site_id: str) -> Any:
            assert site_id == "s1"
            return latest["entry"]

    class _Commands:
        _data_dir = tmp_path
        host = _Host()

        def sites(self) -> SiteStore:
            return SiteStore([SiteProfile("s1", "Shop", "https://shop.example", "jeff")], "s1")

        def api(self, _profile: Any) -> Any:
            return site

        def _check_history(self) -> _History:
            return _History()

    save_options(WorkbenchOptions(watches=("statement",)), tmp_path)
    watch_round(_Commands())
    assert said == []
    latest["entry"] = _entry("2026-11-08", 6)
    state = watches.load_state(tmp_path)
    state.last_round = 0.0  # due again
    watches.save_state(state, tmp_path)
    watch_round(_Commands())
    assert len(said) == 1 and said[0].startswith(
        "The accessibility statement on Shop is out of date"
    )


def test_every_new_watch_is_offered_in_workbench_options() -> None:
    for kind in ("order", "low_stock", "certificate", "abandoned", "statement", "weekly"):
        assert kind in watches.KINDS
