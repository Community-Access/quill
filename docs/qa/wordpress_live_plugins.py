"""Tests 127 onward of the live WordPress run: the plugin features of complete.md 2.4.

Loaded by ``docs/qa/wordpress-live-run.py`` (``_load_workbench_checks``), which
passes itself to :func:`register`. Each test goes through the core functions
the Workbench's commands call, in the order the commands call them:

- 127 to 131, WooCommerce: New Order, Change Items (a quantity of 0 removes a
  line), Change Address, shipping classes, Generate Variations and Shop
  Analytics (``workbench_shop_order_edit``, ``workbench_shop_classes``,
  ``workbench_shop_variations``, ``workbench_shop_analytics``);
- 132, Yoast SEO's canonical address, primary category and schema types
  (``workbench_seo_fields``);
- 133 to 135, Paid Memberships Pro: Members of This Level, an editor refused,
  New and Edit Membership Level (``workbench_pmpro_members``,
  ``workbench_pmpro_levels``);
- 136 and 137, Redirection: its options, Redirect Groups and Import Redirects
  (``workbench_redirect_options``, ``workbench_redirect_files``);
- 138 to 140, Gravity Forms: notifications and confirmations saved on a form,
  feeds, and a real test submission to a form the run made (``gravity_messages``,
  ``workbench_gravity``, ``workbench_gravity_submit``);
- 141 and 142, Advanced Custom Fields read and write, and the QUILL Site Types
  plugin (``field_plugins``, ``site_types_plugin``).

The test site is a sandbox: no payment is ever taken, an order is made
"pending payment" and never marked paid, and every order, class, level,
group, form and definition made here is titled "QUILL live test" and deleted
afterwards. A Gravity Forms form made here has no notifications left on it
when it is submitted, so nobody is emailed.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping
from typing import Any

#: The harness module, set by :func:`register`.
H: Any = None

AREA = "Workbench, plugins and WordPress.org (10B.3)"
WC = "wc/v3"


def register(harness: Any) -> None:
    """Put tests 127 onward on the harness's list."""
    global H
    H = harness
    for ref, name, fn, who, writes in _TESTS:
        harness.check(AREA, ref, name, who=getattr(harness, who), writes=writes)(fn)


def _need(ctx: Any, namespace: str, plugin: str) -> None:
    if ctx.index is None or namespace not in set(ctx.index.namespaces):
        raise H.NotRun(f"skipped: {plugin} not installed")


def _site_ctx(ctx: Any, login: str) -> Any:
    from quill.core.wordpress.site import load_account, load_site_info
    from quill.core.wordpress.workbench_load import SiteContext

    api = ctx.api(login)
    key = f"wb_info_{login}"
    if key not in ctx.state:
        ctx.state[key] = load_site_info(api)
    if login not in ctx.accounts:
        ctx.accounts[login] = load_account(api)
    return SiteContext(
        H.SITE_NAME, api, url=H.SITE_URL, account=ctx.accounts[login], info=ctx.state[key]
    )


def _simple_products(api: Any) -> list[dict[str, Any]]:
    """Published simple products with a price, as New Order offers them."""
    found = api.get(f"{WC}/products", per_page=100, status="publish")
    return [p for p in found if p.get("type") == "simple" and str(p.get("price") or "")]


# =========================================================================== #
# WooCommerce


def _new_order(ctx: Any) -> str:
    from quill.core.wordpress import workbench_shop_order_edit as edit

    _need(ctx, WC, "WooCommerce")
    api = ctx.api(H.ADMIN)
    goods = _simple_products(api)
    if len(goods) < 2:
        raise H.NotRun("the shop needs two published simple products with a price")
    first, second = goods[0], goods[1]
    order = edit.NewOrder(
        "pending",
        billing={
            "first_name": "QUILL",
            "last_name": "live test",
            "email": "quill-live-test@example.com",
            "address_1": "1 Test Street",
            "city": "Phoenix",
            "postcode": "85001",
            "country": "US",
        },
        lines=(
            (int(first["id"]), str(first["name"]), 1),
            (int(second["id"]), str(second["name"]), 2),
        ),
    )
    made = api.post(f"{WC}/orders", edit.new_order_body(order))
    number = int(made["id"])
    ctx.later(
        f"delete shop order {number}", lambda: api.delete(edit.order_route(number), force=True)
    )
    ctx.state["order"] = number
    H.expect(made.get("status") == "pending", f"status {made.get('status')}")
    H.expect(not made.get("date_paid"), "the order was marked paid")
    items = edit.order_items(made)
    H.expect([i.quantity for i in items] == [1, 2], f"items {[i.words() for i in items]}")
    want = float(first["price"]) + 2 * float(second["price"])
    H.expect(abs(float(made["total"]) - want) < 0.005, f"total {made['total']}, expected {want}")
    shipping = made.get("shipping") or {}
    H.expect(shipping.get("city") == "Phoenix", f"shipping address {shipping}")
    return (
        f"order {number}: {', '.join(i.words() for i in items)}, total {made['total']}, "
        "pending payment, not paid; shipping address copied from billing"
    )


def _change_items(ctx: Any) -> str:
    from quill.core.wordpress import workbench_shop_order_edit as edit

    number = ctx.state.get("order")
    if not number:
        raise H.NotRun("no order from test 127")
    api = ctx.api(H.ADMIN)
    route = edit.order_route(number)
    items = edit.order_items(api.get(route))
    one, two = items[0], items[1]
    # One line's quantity up, the other line off (0 removes it), a product added.
    goods = _simple_products(api)
    extra = next((p for p in goods if int(p["id"]) not in {one.product_id, two.product_id}), None)
    changes = [
        edit.ItemChange(one.item_id, one.product_id, one.name, 3),
        edit.ItemChange(two.item_id, two.product_id, two.name, 0),
    ]
    if extra is not None:
        changes.append(edit.ItemChange(0, int(extra["id"]), str(extra["name"]), 1))
    preview = edit.items_preview(str(number), items, changes, H.SITE_NAME)
    after = api.post(route, edit.items_body(changes, items))
    now = {i.product_id: i for i in edit.order_items(after)}
    H.expect(two.product_id not in now, f"quantity 0 left {two.name} on the order")
    kept = now.get(one.product_id)
    H.expect(kept is not None and kept.quantity == 3, f"{one.name} is {kept}")
    price = float(one.subtotal) / one.quantity
    H.expect(
        kept is not None and abs(float(kept.total) - 3 * price) < 0.005,
        f"{one.name} line total {kept.total if kept else '?'}, expected {3 * price:.2f}",
    )
    if extra is not None:
        H.expect(int(extra["id"]) in now, f"{extra['name']} was not added")
    lines = sum(float(i.total) for i in now.values())
    H.expect(abs(float(after["total"]) - lines) < 0.005, f"order total {after['total']} != {lines}")
    return (
        f"{H.cell(' '.join(preview[:2]), 90)} Now: "
        f"{', '.join(i.words() for i in now.values())}; total {after['total']}"
    )


def _change_address(ctx: Any) -> str:
    from quill.core.wordpress import workbench_shop_order_edit as edit

    number = ctx.state.get("order")
    if not number:
        raise H.NotRun("no order from test 127")
    api = ctx.api(H.ADMIN)
    route = edit.order_route(number)
    order = api.get(route)
    said = []
    for which, city in (("billing", "Tucson"), ("shipping", "Flagstaff")):
        old = order.get(which) or {}
        body, back = edit.address_body(which, old, {"city": city, "address_2": "Suite 2"})
        H.expect(set(body[which]) == {"city", "address_2"}, f"{which} sends {body}")
        api.post(route, body)
        read = api.get(route).get(which) or {}
        H.expect(read.get("city") == city, f"{which} city is {read.get('city')}")
        api.post(route, back)
        undone = api.get(route).get(which) or {}
        H.expect(undone.get("city") == old.get("city"), f"undo left {undone.get('city')}")
        said.append(f"{which} {old.get('city')} to {city} and back")
    other = api.get(route)
    H.expect(other["billing"]["city"] == "Phoenix", "billing changed with shipping")
    return "; ".join(said) + "; only the changed fields were sent"


def _shipping_classes(ctx: Any) -> str:
    from quill.core.wordpress import plugin_shop_seo as shop
    from quill.core.wordpress import workbench_shop_classes as sc

    _need(ctx, WC, "WooCommerce")
    api = ctx.api(H.ADMIN)
    body = sc.class_body({}, {"name": ctx.title("heavy"), "description": "Live test"})
    made = api.post(sc.ROUTE, body)
    ident = int(made["id"])
    ctx.later(
        f"delete shipping class {ident}", lambda: api.delete(f"{sc.ROUTE}/{ident}", force=True)
    )
    change = sc.class_body(made, {"name": ctx.title("heavy, renamed"), "description": "Live test"})
    H.expect(set(change) == {"name"}, f"a rename sends {change}")
    api.post(f"{sc.ROUTE}/{ident}", change)
    rows = [r for r in sc.load_classes(api, H.SITE_NAME) if r.object_id == ident]
    H.expect(rows and "renamed" in rows[0].title, "the renamed class is not listed")
    product = _simple_products(api)[0]
    pid, was = int(product["id"]), str(product.get("shipping_class") or "")
    ctx.later(
        "put back the product's shipping class",
        lambda: api.post(f"{WC}/products/{pid}", {"shipping_class": was}),
    )
    api.post(f"{WC}/products/{pid}", {"shipping_class": made["slug"]})
    now = shop.load_product(api, pid)
    read = api.get(f"{WC}/products/{pid}")
    H.expect(read.get("shipping_class") == made["slug"], f"class {read.get('shipping_class')}")
    zones = api.get(f"{WC}/shipping/zones")
    methods = sum(len(api.get(f"{WC}/shipping/zones/{z['id']}/methods")) for z in zones)
    return (
        f"class {ident} made, renamed, {now.name} put in it and back; "
        f"{len(zones)} shipping zones with {methods} methods on the site"
    )


def _variations(ctx: Any) -> str:
    from quill.core.wordpress import workbench_shop_variations as sv

    _need(ctx, WC, "WooCommerce")
    api = ctx.api(H.ADMIN)
    variable = [p for p in api.get(f"{WC}/products", per_page=100, type="variable", status="any")]
    H.expect(variable, "the shop has no variable product")
    refused = [p for p in variable if sv.refusal(str(p["name"]), H.SITE_NAME, p)]
    ready = [p for p in variable if not sv.refusal(str(p["name"]), H.SITE_NAME, p)]
    said = [f"{len(variable)} variable products, {len(refused)} refused before sending"]
    if refused:
        said.append(H.cell(sv.refusal(str(refused[0]["name"]), H.SITE_NAME, refused[0]), 90))
    for product in ready:
        before = sv.variation_ids(product)
        count, made = sv.generate(api, int(product["id"]), before)
        for ident in made:
            route = f"{WC}/products/{product['id']}/variations/{ident}"
            ctx.later(f"delete variation {ident}", lambda r=route: api.delete(r, force=True))
        H.expect(count == len(made), f"WooCommerce said {count}, {len(made)} new ids read")
        said.append(sv.made_sentence(str(product["name"]), H.SITE_NAME, count))
    if not ready:
        raise H.NotRun("; ".join(said))
    return "; ".join(said)


def _analytics(ctx: Any) -> str:
    from quill.core.wordpress import workbench_shop_analytics as sa
    from quill.core.wordpress.workbench_shop_analytics_places import REPORTS

    site = _site_ctx(ctx, H.ADMIN)
    if not sa.has_analytics(site):
        raise H.NotRun(sa.no_analytics_words(H.SITE_NAME))
    said = []
    for report in REPORTS:
        rows = sa.load_analytics(site, f"analytics_{report.key}", {"range": "this_year"})
        said.append(f"{report.label} {len(rows)}")
    totals = site.api.get(sa.IMPORT_TOTALS, skip_existing="true")
    revenue = sa.load_analytics(site, "analytics_revenue", {"range": "this_year"})
    first = revenue[0].raw.get("summary", "") if revenue else ""
    unimported = int(totals.get("orders") or 0)
    if unimported:
        H.expect(sa.unimported_words(unimported) in first, "the total row does not say so")
    return (
        f"{', '.join(said)} rows; {unimported} not imported yet, said on the total row; "
        f"{H.cell(first, 100)}"
    )


# =========================================================================== #
# Yoast SEO


def _yoast(ctx: Any) -> str:
    from quill.core.wordpress import field_plugins as fp
    from quill.core.wordpress import workbench_seo_fields as sf

    _need(ctx, "yoast/v1", "Yoast SEO")
    api = ctx.api(H.ADMIN)
    posts = api.get("wp/v2/posts", context="edit", per_page=20, status="publish")
    post = next((p for p in posts if len(p.get("categories") or []) > 1), posts[0])
    names = {c["name"]: c["id"] for c in api.get("wp/v2/categories", per_page=100)}
    mine = {n: i for n, i in names.items() if i in (post.get("categories") or [])}
    meta = fp.meta_from_properties(fp.route_properties(api, "wp/v2/posts"))
    page, shown = sf.seo_page(post, meta, mine)
    H.expect(page is not None, "no SEO page")
    fields = {f.key: f for f in page.fields}
    registered = [k for k in (sf.CANONICAL, sf.PRIMARY_CATEGORY, sf.SCHEMA_PAGE) if k in meta]
    ro = [k for k, f in fields.items() if f.readonly]
    head = post.get("yoast_head_json") or {}
    page_type, article_type = sf.schema_types(head)
    H.expect(page_type, f"no page schema type in yoast_head_json: {list(head)[:8]}")
    canonical = sf.canonical_shown(head)
    H.expect(canonical and canonical != "none given", f"canonical: {canonical}")
    return (
        f"post {post['id']} ({len(mine)} categories): {len(registered)} of 3 Yoast fields "
        f"registered for REST, {len(ro)} read only; schema {page_type}/{article_type or '-'}; "
        f"canonical: {H.cell(canonical, 90)}"
    )


# =========================================================================== #
# Paid Memberships Pro


def _pmpro_members(ctx: Any) -> str:
    from quill.core.wordpress import workbench_pmpro_members as pm
    from quill.core.wordpress import workbench_pmpro_rest as pr

    _need(ctx, pr.PMPRO_NAMESPACE, "Paid Memberships Pro")
    api = ctx.api(H.ADMIN)
    levels = api.get("pmpro/v1/membership_levels")
    levels = list(levels.values()) if isinstance(levels, dict) else list(levels or [])
    H.expect(levels, "no membership levels")
    people = pm.count_people(api)
    said = []
    for level in levels[:2]:
        found = pm.find_members(
            api, int(level["id"]), str(level["name"]), H.SITE_NAME, people=people
        )
        H.expect(found.checked == people, f"asked about {found.checked} of {people}")
        said.append(found.sentence())
        if found.members:
            said.append(H.cell(found.members[0].line(), 60))
    return f"{people} people; " + " ".join(said)


def _pmpro_members_editor(ctx: Any) -> str:
    from quill.core.wordpress import workbench_pmpro_members as pm
    from quill.core.wordpress import workbench_pmpro_rest as pr

    _need(ctx, pr.PMPRO_NAMESPACE, "Paid Memberships Pro")
    error = H.refused(lambda: pm.find_members(ctx.api(H.EDITOR), 1, "QUILL Free", H.SITE_NAME))
    H.expect("list_users" in error.plain, error.plain)
    return f"{error.status}: {H.cell(error.plain, 120)}"


def _pmpro_level(ctx: Any) -> str:
    """New and Edit Membership Level on one standing test level, then the deletion refused.

    PMPro turns DELETE off in its REST API by default, so a level made here could
    never be cleaned up: the run makes "QUILL live test: level" once, keeps it with
    signups off, and changes it and puts it back on every later run.
    """
    from dataclasses import replace

    from quill.core.wordpress import workbench_pmpro_levels as lv
    from quill.core.wordpress import workbench_pmpro_rest as pr

    _need(ctx, pr.PMPRO_NAMESPACE, "Paid Memberships Pro")
    api = ctx.api(H.ADMIN)
    name = f"{H.TAG}: level"
    levels = api.get("pmpro/v1/membership_levels")
    levels = list(levels.values()) if isinstance(levels, dict) else list(levels or [])
    found = next((lvl for lvl in levels if lvl.get("name") == name), None)
    said = []
    if found is None:
        spec = lv.LevelSpec(name=name, description="Kept by the live run", allow_signups=False)
        body = lv.level_body(spec)
        answer = lv.save_level(api, body)
        made = int(answer.get("id") or 0) if isinstance(answer, dict) else 0
        H.expect(made, f"no level id in {H.cell(answer, 80)}")
        said.append(f"New Membership Level made level {made}")
    else:
        made = int(found["id"])
        said.append(f"level {made} kept from an earlier run")
    count = len(levels) + (found is None)
    old = lv.level_from(api.get(lv.LEVEL_ROUTE, id=made))
    new = replace(old, initial_payment="5.00", billing_amount="7.50", cycle_number=1,
                  cycle_period="Month", expiration_number=1, expiration_period="Year",
                  allow_signups=False)  # fmt: skip
    body = lv.level_body(new, made)
    ctx.later(
        f"put back membership level {made}", lambda: lv.save_level(api, lv.level_body(old, made))
    )
    lv.save_level(api, body)
    stored = api.get(lv.LEVEL_ROUTE, id=made)
    after = api.get("pmpro/v1/membership_levels")
    H.expect(len(after) == count, f"an edit made a level: {len(after)} levels, not {count}")
    read = lv.level_from(stored)
    H.expect(read.billing_amount == "7.50", f"billing {read.billing_amount}")
    H.expect(not read.allow_signups, "signups turned on")
    missed = lv.not_saved(body, stored)
    said.append(f"Edit changed it by id ({len(after)} levels, none added)")
    if missed:
        said.append(f"PMPro did not keep: {', '.join(missed)} (its route, not QUILL)")
    error = H.refused(lambda: api.delete(lv.LEVEL_ROUTE, id=made))
    H.expect(error.status == 403, f"delete answered {error.status}")
    said.append(f"delete refused {error.status}, as PMPro's default allows")
    return "; ".join(said)


# =========================================================================== #
# Redirection


def _redirect_options(ctx: Any) -> str:
    from quill.core.wordpress import workbench_redirect_options as ro
    from quill.core.wordpress import workbench_redirects as rd
    from quill.core.workbench.properties import FieldChange

    _need(ctx, rd.NAMESPACE, "Redirection")
    api = ctx.api(H.ADMIN)
    settings = ro.read_options(api)
    H.expect(settings, "no options read")
    rows = ro.option_rows(H.SITE_NAME, H.SITE_URL, settings)
    key = "expire_404"
    H.expect(key in settings, f"no {key} in {sorted(settings)[:10]}")
    was = settings[key]
    now = 7 if str(was) != "7" else 30
    pending = [FieldChange(key, "Keep the 404 log", was, now)]
    body = ro.body_for(pending)
    ctx.later(
        "put back Redirection's 404 log", lambda: api.post(ro.OPTIONS_ROUTE, ro.undo_body(pending))
    )
    answer = api.post(ro.OPTIONS_ROUTE, body)
    said = ro.verified(H.SITE_NAME, body, answer)
    H.expect(str(ro.read_options(api).get(key)) == str(now), f"{key} did not change")
    error = H.refused(lambda: ctx.api(H.EDITOR).get(ro.OPTIONS_ROUTE))
    return f"{len(rows)} option rows; {H.cell(said, 90)}; an editor: {error.status}"


def _redirect_groups(ctx: Any) -> str:
    from quill.core.wordpress import workbench_redirect_files as rf
    from quill.core.wordpress import workbench_redirects as rd

    _need(ctx, rd.NAMESPACE, "Redirection")
    api = ctx.api(H.ADMIN)
    name = ctx.title("group")
    api.post(rf.group_route(), rf.group_body(name))
    found = [g for g in rd.read_groups(api) if g.get("name") == name]
    H.expect(found, "the new group is not listed")
    gid = int(found[0]["id"])
    ctx.later(
        f"delete redirect group {gid}",
        lambda: api.post(rf.group_route(action="delete"), {"items": [gid]}),
    )
    # The slug-change offer: a 301 from the old address, in this group, as Properties makes it.
    from quill.core.wordpress import workbench_sweep as sw

    old = f"{H.SITE_URL}/quill-live-test-old-{ctx.stamp[-5:].replace(':', '')}/"
    api.post(f"{rd.NAMESPACE}/redirect", sw.redirect_body(old, H.SITE_URL + "/about/", gid))
    moved = [r for r in rd.read_pages(api, "redirect") if int(r.get("group_id") or 0) == gid]
    H.expect(len(moved) == 1, f"{len(moved)} slug-change redirects in the group")
    said_old = rd.trace_address(old, moved, H.SITE_URL)
    H.expect("leads to" in said_old, said_old)
    slug_id = int(moved[0]["id"])
    ctx.later(
        f"delete redirect {slug_id}",
        lambda: api.post(f"{rd.NAMESPACE}/bulk/redirect/delete", {"items": [slug_id]}),
    )
    api.post(rf.group_route(gid), rf.group_body(name + " renamed"))
    api.post(rf.group_route(action="disable"), {"items": [gid]})
    group = next(g for g in rd.read_groups(api) if int(g["id"]) == gid)
    row = rf.group_row(H.SITE_NAME, group)
    H.expect(group.get("name") == name + " renamed", f"name {group.get('name')}")
    H.expect(group.get("enabled") is False, f"enabled {group.get('enabled')}")
    stamp = H.cell(ctx.stamp.replace(" ", "-").replace(":", ""), 20)
    text = (
        "source,target,code\n"
        f"/quill-live-test-import-{stamp}/,{H.SITE_URL}/about/,301\n"
        "not a redirect\n"
    )
    plan = rf.parse_import(
        text, "redirects.csv", [str(r.get("url")) for r in rd.read_pages(api, "redirect")]
    )
    H.expect(len(plan.adds) == 1 and len(plan.problems) == 1, f"plan {plan.lines()}")
    for source, target, code, regex in plan.adds:
        body = rd.edit_body(source, target, code, group_id=gid, regex=regex)
        api.post("redirection/v1/redirect", body)
    made = [
        r
        for r in rd.read_pages(api, "redirect")
        if int(r.get("group_id") or 0) == gid and int(r["id"]) != slug_id
    ]
    H.expect(len(made) == 1, f"{len(made)} imported")
    ident = int(made[0]["id"])
    ctx.later(
        f"delete redirect {ident}",
        lambda: api.post("redirection/v1/bulk/redirect/delete", {"items": [ident]}),
    )
    return (
        f"slug change: {H.cell(said_old, 70)}; {row.detail} Import: 1 made, "
        f"{len(plan.problems)} skipped"
    )


# =========================================================================== #
# Gravity Forms


def _gravity_form(ctx: Any) -> dict[str, Any]:
    """A form the run made, with a name, an email and a paragraph field and no notifications."""
    from quill.core.wordpress import gravity_build as gb
    from quill.core.wordpress import gravity_build_save as gs

    if "gf_form" in ctx.state:
        return ctx.state["gf_form"]
    api = ctx.api(H.ADMIN)
    form = gb.new_form(ctx.title("gravity messages"))
    form["notifications"] = {}  # no Admin Notification: test 141 submits, and nobody is emailed
    gb.add_field(form, "text", {"label": "Your name", "isRequired": True})
    gb.add_field(form, "email", {"label": "Email"})
    gb.add_field(form, "textarea", {"label": "Message"})
    saved = gs.create(api, form)
    route = saved.route
    ctx.later(f"delete Gravity Forms form {saved.form_id}", lambda: api.delete(route, force=1))
    ctx.state["gf_form"] = {"id": saved.form_id, "route": route, "stored": saved.stored}
    return ctx.state["gf_form"]


def _gravity_messages(ctx: Any) -> str:
    from quill.core.wordpress import gravity_build_save as gs
    from quill.core.wordpress import gravity_messages as gm

    _need(ctx, "gf/v2", "Gravity Forms")
    api = ctx.api(H.ADMIN)
    made = _gravity_form(ctx)
    opened = api.get(made["route"])
    edited = copy.deepcopy(opened)
    note = gm.add_notification(
        edited, "QUILL live test", "{admin_email}", "Live test", "{all_fields}"
    )
    gm.toggle(note)  # off: saved and read back, never sent
    gm.add_confirmation(edited, "QUILL live test thanks", "Thank you, from the live test.")
    after = gs.update(api, made["route"], opened, edited)
    H.expect(not after.problems, "; ".join(after.problems))
    stored = api.get(made["route"])
    notes = list((stored.get("notifications") or {}).values())
    confirms = list((stored.get("confirmations") or {}).values())
    H.expect(any(n.get("name") == "QUILL live test" for n in notes), "notification not saved")
    H.expect(not any(n.get("isActive", True) for n in notes), "a notification is on")
    H.expect(any(c.get("name") == "QUILL live test thanks" for c in confirms), "confirmation lost")
    words = [gm.spoken(m) for m in gm.others(stored)]
    return (
        f"form {made['id']}: {len(notes)} notifications (off), {len(confirms)} confirmations; "
        f"{H.cell('; '.join(words), 120)}"
    )


def _gravity_feeds(ctx: Any) -> str:
    from quill.core.wordpress import workbench_gravity as gf

    _need(ctx, "gf/v2", "Gravity Forms")
    _gravity_form(ctx)
    site = _site_ctx(ctx, H.ADMIN)
    raw = site.api.get(f"{gf.NS}/feeds")
    feeds = gf.load_feeds(site)
    if isinstance(raw, Mapping) and raw.get("errors"):
        raise H.NotRun(
            f"no add-on with feeds on the site ({H.cell(raw['errors'], 80)}); QUILL lists "
            f"{len(feeds)} feeds"
        )
    return f"{len(feeds)} feeds"


def _gravity_submit(ctx: Any) -> str:
    from quill.core.wordpress import workbench_gravity as gf
    from quill.core.wordpress import workbench_gravity_submit as gs

    _need(ctx, "gf/v2", "Gravity Forms")
    api = ctx.api(H.ADMIN)
    made = _gravity_form(ctx)
    form = api.get(made["route"])
    H.expect(
        not any(n.get("isActive", True) for n in (form.get("notifications") or {}).values()),
        "a notification is on: test 138 first",
    )
    inputs, skipped = gs.sample_inputs(form)
    values = {i.name: i.value for i in inputs}
    check = gs.submit(api, made["id"], values, validate_only=True)
    H.expect(check.valid, f"validation: {check.lines({})}")
    sent = gs.submit(api, made["id"], values, validate_only=False)
    H.expect(sent.valid, f"submission: {sent.lines({})}")
    entries = api.get(f"{gf.NS}/forms/{made['id']}/entries")
    rows = entries.get("entries", []) if isinstance(entries, Mapping) else entries
    H.expect(rows, "no entry made")
    entry = rows[0]
    ctx.later(
        f"delete entry {entry['id']}", lambda: api.delete(f"{gf.NS}/entries/{entry['id']}", force=1)
    )
    results = gf.load_results(_site_ctx(ctx, H.ADMIN))
    sends = gf.entry_notifications(form, entry)
    on = [n for n in sends if n.active]
    H.expect(not on, f"{len(on)} notifications are on")
    H.expect(sent.entry_id == str(entry["id"]), f"the answer named entry {sent.entry_id!r}")
    return (
        f"form {made['id']}: {len(inputs)} filled, {len(skipped)} skipped, valid; entry "
        f"{entry['id']} made and named for Ctrl+Z; {len(results)} result rows (no quiz, poll or "
        f"survey add-on); {len(sends)} notification previewed, turned off, so nobody was emailed"
    )


# =========================================================================== #
# Advanced Custom Fields and QUILL Site Types


def _acf(ctx: Any) -> str:
    from quill.core.wordpress import field_plugins as fp

    api = ctx.api(H.ADMIN)
    props = fp.route_properties(api, "wp/v2/posts")
    schema = fp.acf_schema(props)
    if schema is None:
        raise H.NotRun("skipped: Advanced Custom Fields shows nothing in REST")
    if not schema:
        raise H.NotRun("ACF is there, but no field group has Show in REST API on")
    made = api.post("wp/v2/posts", {"title": ctx.title("acf"), "status": "draft"})
    pid = int(made["id"])
    ctx.later(f"delete post {pid}", lambda: api.delete(f"wp/v2/posts/{pid}", force=True))
    name, spec = next((n, s) for n, s in schema.items() if "string" in str(s.get("type")))
    api.post(f"wp/v2/posts/{pid}", {"acf": {name: "Written by QUILL"}})
    read = fp.read_acf(api, "wp/v2/posts", pid, properties=props)
    H.expect(read is not None and read.values.get(name) == "Written by QUILL", f"read {read}")
    return f"{len(schema)} ACF fields in REST; {name} written and read back on draft {pid}"


def _site_types(ctx: Any) -> str:
    from quill.core.wordpress import site_types_plugin as stp

    api = ctx.api(H.ADMIN)
    _need(ctx, stp.NAMESPACE, "QUILL Site Types")
    slug = "qlt" + ctx.stamp[-5:].replace(":", "")
    stp.define(api, "type", stp.define_body("type", slug, "QUILL live test books"))
    ctx.later(f"stop defining {slug}", lambda: stp.stop_defining(api, "type", slug))
    kinds = stp.read_kinds(api)
    fields = stp.parse_fields("isbn: text", kinds)
    group = slug + "_f"
    stp.define(
        api,
        "field_group",
        stp.define_body("field_group", group, "Live test", attach=slug, fields=fields),
    )
    ctx.later(f"stop defining {group}", lambda: stp.stop_defining(api, "field_group", group))
    types = api.get("wp/v2/types")
    H.expect(slug in types, f"{slug} is not a post type in REST")
    base = types[slug].get("rest_base") or slug
    item = api.post(
        f"wp/v2/{base}", {"title": ctx.title("book"), "status": "draft", "meta": {"isbn": "978-0"}}
    )
    iid = int(item["id"])
    ctx.later(f"delete {slug} {iid}", lambda: api.delete(f"wp/v2/{base}/{iid}", force=True))
    read = api.get(f"wp/v2/{base}/{iid}", context="edit")
    H.expect((read.get("meta") or {}).get("isbn") == "978-0", f"meta {read.get('meta')}")
    previous = stp.stop_defining(api, "field_group", group)
    said = stp.put_back(api, "field_group", previous)
    return f"type {slug}, field group {group}; item {iid} keeps isbn in REST; stopped and {said}"


_TESTS: tuple[tuple[str, str, Any, str, bool], ...] = (
    ("127", "WooCommerce: New Order, pending, for a guest", _new_order, "ADMIN", True),
    ("128", "WooCommerce: Change Items, quantity 0 removes a line", _change_items, "ADMIN", True),
    (
        "129",
        "WooCommerce: Change Address, billing and shipping, undone",
        _change_address,
        "ADMIN",
        True,
    ),
    (
        "130",
        "WooCommerce: shipping classes, a product put in one",
        _shipping_classes,
        "ADMIN",
        True,
    ),
    ("131", "WooCommerce: Generate Variations, undone", _variations, "ADMIN", True),
    ("132", "WooCommerce: Shop Analytics, every report", _analytics, "ADMIN", False),
    ("133", "Yoast SEO: canonical, primary category, schema", _yoast, "ADMIN", False),
    ("134", "Paid Memberships Pro: Members of This Level", _pmpro_members, "ADMIN", False),
    (
        "135",
        "Paid Memberships Pro: an editor cannot list members",
        _pmpro_members_editor,
        "EDITOR",
        False,
    ),
    ("136", "Paid Memberships Pro: New and Edit Membership Level", _pmpro_level, "ADMIN", True),
    ("137", "Redirection: options changed and put back", _redirect_options, "ADMIN", True),
    (
        "138",
        "Redirection: Redirect Groups and Import Redirects",
        _redirect_groups,
        "ADMIN",
        True,
    ),
    (
        "139",
        "Gravity Forms: notifications and confirmations saved",
        _gravity_messages,
        "ADMIN",
        True,
    ),
    ("140", "Gravity Forms: feeds", _gravity_feeds, "ADMIN", True),
    ("141", "Gravity Forms: a test submission and its results", _gravity_submit, "ADMIN", True),
    ("142", "Advanced Custom Fields: write and read back", _acf, "ADMIN", True),
    ("143", "QUILL Site Types: a type and its fields in REST", _site_types, "ADMIN", True),
)
