"""Tests 70 onward of the live WordPress run: the WordPress Workbench.

Loaded by ``docs/qa/wordpress-live-run.py`` (``_load_workbench_checks``), which
passes itself to :func:`register`; every check here is registered on the
harness's own ``CHECKS`` list and runs under its rules: through the core
functions the Workbench calls (``quill/core/wordpress/workbench_*.py``), read
only where it can be, anything it makes titled "QUILL live test" and trashed or
deleted afterwards, ``--dry-run`` and ``--public`` honoured by each check's
``who`` and ``writes``. A plugin the site lacks is "skipped: <plugin> not
installed", read from the site's REST index, never a failure.

The test site is one site, so the Across Sites tests read it twice -- as
quilladmin and as quill-editor -- as two "sites". That is meaningful where the
two views differ (what an editor may read) and is said to be single-site
limited where the feature needs two real sites; those parts are "needs Jeff".
"""

from __future__ import annotations

import re
from typing import Any

#: The harness module, set by :func:`register`.
H: Any = None

AREA_SITE = "Workbench, one site (15)"
AREA_ACROSS = "Workbench, across sites (15.2, 15.12)"
AREA_PLUGINS = "Workbench, plugins and WordPress.org (10B.3)"
AREAS = (AREA_SITE, AREA_ACROSS, AREA_PLUGINS)

ADMIN_VIEW = "Test site as quilladmin"
EDITOR_VIEW = "Test site as quill-editor"

#: The Workbench parts only a person (or a second real site) can do.
HUMAN: tuple[tuple[str, str, str, str], ...] = (
    (
        AREA_ACROSS,
        "75",
        "Make Them the Same between two real sites",
        "a second site; the run makes one site's tag match a made-up winner",
    ),
    (AREA_ACROSS, "76", "Promote to Network", "a multisite network; the test site is single"),
    (
        AREA_ACROSS,
        "77",
        "Install on Sites Missing It, for real",
        "a second site that lacks a plugin; the run checks only the editor's refusal",
    ),
    (
        AREA_ACROSS,
        "78",
        "Revoke a password everywhere",
        "revoking would end the harness's own sign-in; revoke a throwaway password by hand",
    ),
    (AREA_ACROSS, "81", "Copy pictures and menus to another site", "a second site"),
    (
        AREA_PLUGINS,
        "102",
        "New Discount Code",
        "pmpro/v1 has no route to delete a code, so the run only previews one",
    ),
    (AREA_PLUGINS, "105", "Resend Notifications", "it sends email to real people"),
)


def register(harness: Any) -> None:
    """Put tests 70 onward on the harness's list, in order."""
    global H
    H = harness
    for area, ref, name, fn, who, writes in _TESTS:
        harness.check(area, ref, name, who=who, writes=writes)(fn)
    harness.HUMAN = tuple(harness.HUMAN) + HUMAN


# =========================================================================== #
# Shared parts


def _need(ctx: Any, namespace: str, plugin: str) -> None:
    """NotRun "skipped: <plugin> not installed" when the index lacks *namespace*."""
    if ctx.index is None or namespace not in set(ctx.index.namespaces):
        raise H.NotRun(f"skipped: {plugin} not installed")


def _site_ctx(ctx: Any, login: str, name: str = "") -> Any:
    """The Workbench's SiteContext for *login*: the client, the account and the index."""
    from quill.core.wordpress.site import load_account, load_site_info
    from quill.core.wordpress.workbench_load import SiteContext

    api = ctx.api(login)
    key = f"wb_info_{login}"
    if key not in ctx.state:
        ctx.state[key] = load_site_info(api)
    if login not in ctx.accounts:
        ctx.accounts[login] = load_account(api)
    return SiteContext(
        name or f"Test site as {login}",
        api,
        url=H.SITE_URL,
        account=ctx.accounts[login],
        info=ctx.state[key],
    )


def _two_views(ctx: Any) -> list[tuple[str, Any]]:
    """The one test site, as quilladmin and as quill-editor: Across Sites' two "sites"."""
    if H.EDITOR not in ctx.apis:
        raise H.NotRun("needs quill-editor too, as the second view of the site")
    return [(ADMIN_VIEW, ctx.api(H.ADMIN)), (EDITOR_VIEW, ctx.api(H.EDITOR))]


def _stamp_slug(ctx: Any, words: str) -> str:
    return "quill-live-test-" + words + "-" + re.sub(r"\D", "", ctx.stamp)


def _first(rows: Any) -> Any:
    return next(iter(rows), None)


def _new_tag(ctx: Any, login: str, words: str, *, slug: str = "") -> dict[str, Any]:
    """A tag titled "QUILL live test: ...", deleted (not trashed: terms have none) afterwards."""
    api = ctx.api(login)
    body = {"name": ctx.title(words)}
    if slug:
        body["slug"] = slug
    made = api.post("wp/v2/tags", body)
    ident = int(made["id"])

    def undo() -> None:
        try:
            api.delete(f"wp/v2/tags/{ident}", force=True)
        except Exception:  # noqa: BLE001 - the admin can when the maker cannot
            ctx.api(H.ADMIN).delete(f"wp/v2/tags/{ident}", force=True)

    ctx.later(f"delete tag {ident}", undo)
    return made


def _page_id(ctx: Any, api: Any, slug: str) -> int:
    found = api.get("wp/v2/pages", slug=slug, _fields="id,slug")
    match = next((p for p in found or [] if p.get("slug") == slug), None)
    if match is None:
        raise H.NotRun(f"no page /{slug}/ on the site; run reset.sh first")
    return int(match["id"])


# =========================================================================== #
# One site: By Name (15.12)


def _by_name_read(ctx: Any) -> str:
    from quill.core.wordpress import workbench_across as wa
    from quill.core.wordpress import workbench_by_name as bn

    api = ctx.api(H.EDITOR)
    scan = wa.scan_site(api, H.SITE_NAME, pages=3)
    if not any(i.get("type") == "page" for i in scan.items):
        # scan_site drops a list the site will not give; say why pages are missing.
        try:
            api.get("wp/v2/pages", context="edit", status="any", per_page=100)
            why = "the site lists them now; the scan read none"
        except Exception as exc:  # noqa: BLE001 - the reason is the result
            why = getattr(exc, "plain", "") or str(exc)
        raise H.CheckFailed(f"the scan read no pages (Every Block holds [gallery]): {why}")
    terms = wa.kind_rows(scan, "terms")
    news = next((r for r in terms if r.cell("value") == "News (category)"), None)
    H.expect(news is not None, "no News category in Every Term")
    H.expect("Welcome to the test site" in news.detail, f"News reads: {news.detail}")
    uses = bn.term_uses(scan, news.key)
    edits = bn.plan_term_rename(scan, news.key, "News, renamed", "")
    H.expect(len(edits) == 1 and edits[0].before == {"name": "News"}, f"plan: {edits}")
    blocks = wa.kind_rows(scan, "blocks")
    gallery = next((r for r in blocks if r.key == "[gallery] shortcode"), None)
    H.expect(gallery is not None, "Blocks and Shortcodes has no [gallery] shortcode")
    replace, why = bn.plan_replace(scan, "blocks", "[gallery] shortcode", "[quillgallery]")
    H.expect(replace, f"no replace planned: {why}")
    refusal = bn.plan_replace(scan, "blocks", "core/paragraph block", "core/heading")[1]
    H.expect("does not rewrite blocks" in refusal, f"a block replace said: {refusal}")
    authors = wa.kind_rows(scan, "authors")
    parts = wa.kind_rows(scan, "template_parts")
    return (
        f"{len(scan.items)} items read; News in {len(uses)} items, rename planned and not sent; "
        f"[gallery] in {len(replace)} items; {len(authors)} authors; "
        f"{len(parts)} template parts" + ("" if parts else " (the theme has none)")
    )


def _by_name_rename(ctx: Any) -> str:
    from quill.core.wordpress import workbench_across as wa
    from quill.core.wordpress import workbench_by_name as bn

    api = ctx.api(H.EDITOR)
    tag = _new_tag(ctx, H.EDITOR, "by name")
    post = H._new_post(ctx, H.EDITOR, "by name")
    api.post(f"wp/v2/posts/{post.id}", {"tags": [int(tag["id"])]})
    ctx.state["wb_tag"] = tag
    ctx.state["wb_tag_post"] = post.id
    scan = wa.scan_site(api, H.SITE_NAME, pages=3)
    key = f"post_tag:{tag['id']}"
    H.expect([int(r["id"]) for r in bn.term_uses(scan, key)] == [post.id], "the tag's use")
    renamed = ctx.title("by name, renamed")
    outcomes, sent = bn.apply_edits(api, bn.plan_term_rename(scan, key, renamed, ""))
    said, _report = bn.outcome_report(outcomes)
    H.expect(sent and all(o.ok for o in outcomes), said)
    now = api.get(f"wp/v2/tags/{tag['id']}", context="edit")
    H.expect(now["name"] == renamed, f"after rename it is {now['name']!r}")
    # The conflict stamp of a term rename is its name, so a stale send is a
    # conflict only while the name differs from the scan: try it before undo
    # (after undo the name is as scanned again, and sending is correct).
    other = ctx.title("by name, renamed again")
    stale = bn.apply_edits(api, bn.plan_term_rename(scan, key, other, ""))[0]
    H.expect(stale and not stale[0].ok and "changed on the site" in stale[0].words, "no conflict")
    still = api.get(f"wp/v2/tags/{tag['id']}", context="edit")["name"]
    H.expect(still == renamed, f"the stale send changed the name to {still!r}")
    undo = bn.undo_edits(lambda _site: api, sent)
    back = api.get(f"wp/v2/tags/{tag['id']}", context="edit")
    H.expect(back["name"] == tag["name"], f"after undo it is {back['name']!r}")
    return f"{said} A second send from the old scan was left alone as a conflict. {undo}"


def _by_name_split(ctx: Any) -> str:
    from quill.core.wordpress import workbench_across as wa
    from quill.core.wordpress import workbench_by_name as bn

    tag, post_id = ctx.state.get("wb_tag"), ctx.state.get("wb_tag_post")
    if not tag:
        raise H.NotRun("needs test 71's tag")
    api = ctx.api(H.EDITOR)
    key = f"post_tag:{tag['id']}"
    scan = wa.scan_site(api, H.SITE_NAME, pages=3)
    new_id, edits = bn.split_term(api, scan, key, ctx.title("by name, split"), [post_id])
    ctx.later(f"delete tag {new_id}", lambda: api.delete(f"wp/v2/tags/{new_id}", force=True))
    outcomes, _sent = bn.apply_edits(api, edits)
    H.expect(all(o.ok for o in outcomes), bn.outcome_report(outcomes)[0])
    tags = api.get(f"wp/v2/posts/{post_id}", context="edit", _fields="tags")["tags"]
    H.expect(new_id in tags and int(tag["id"]) not in tags, f"after split the tags are {tags}")
    scan = wa.scan_site(api, H.SITE_NAME, pages=3)
    merge = bn.plan_term_move(scan, f"post_tag:{new_id}", int(tag["id"]), tag["name"])
    outcomes, _sent = bn.apply_edits(api, merge)
    H.expect(outcomes and all(o.ok for o in outcomes), bn.outcome_report(outcomes)[0])
    tags = api.get(f"wp/v2/posts/{post_id}", context="edit", _fields="tags")["tags"]
    H.expect(int(tag["id"]) in tags, f"after merge the tags are {tags}")
    return "split to a new tag and merged back; the split tag is deleted afterwards"


def _by_name_contributor(ctx: Any) -> str:
    from quill.core.wordpress import workbench_across as wa
    from quill.core.wordpress import workbench_by_name as bn

    tag = ctx.state.get("wb_tag")
    if not tag:
        raise H.NotRun("needs test 71's tag")
    scan = wa.scan_site(ctx.api(H.EDITOR), H.SITE_NAME, pages=3)
    edits = bn.plan_term_rename(scan, f"post_tag:{tag['id']}", ctx.title("contributor"), "")
    outcomes, sent = bn.apply_edits(ctx.api(H.CONTRIBUTOR), edits)
    if sent:
        bn.undo_edits(lambda _site: ctx.api(H.EDITOR), sent)
    H.expect(outcomes and not outcomes[0].ok, "the contributor renamed the tag")
    return f"refused: {outcomes[0].words}"


# =========================================================================== #
# Across Sites (15.12), the one site read twice


def _across_gather(ctx: Any) -> str:
    from quill.core.wordpress import workbench_across as wa

    sites = _two_views(ctx)
    names = [s for s, _ in sites]
    terms = wa.across_rows("terms", wa.gather_across("terms", sites), names)
    differ = [r.key for r in terms if r.cell("versions") != "1" or r.cell("missing")]
    H.expect(terms and not differ, f"the same site differs from itself: {differ[:5]}")
    plan = wa.same_everywhere_plan(terms[0], next(iter(terms[0].raw["variants"])))
    H.expect(all(w.startswith("already") for _s, w in plan), f"plan: {plan}")
    # A list the editor may not read is "not read" there, never "missing from" it.
    unread: dict[str, list[str]] = {}
    settings = wa.across_rows(
        "settings", wa.gather_across("settings", sites, unread), names, unread
    )
    H.expect(EDITOR_VIEW in unread, "an editor read the site's settings")
    H.expect(settings and settings[0].kind == "unread", "no row says the settings were not read")
    named = [r for r in settings if r.kind == "across"]
    H.expect(
        named and all(EDITOR_VIEW in r.raw["unread"] and not r.cell("missing") for r in named),
        "a setting is counted as missing from the editor's view",
    )
    plan = wa.same_everywhere_plan(named[0], next(iter(named[0].raw["variants"])))
    H.expect(dict(plan)[EDITOR_VIEW].startswith("not read"), f"plan: {plan}")
    users_unread: dict[str, list[str]] = {}
    found = wa.gather_across("users", sites, users_unread)
    users = wa.across_rows("users", found, names, users_unread)
    return (
        f"{len(terms)} terms the same in both views; {len(named)} settings not read on the "
        f"editor's view ({H.cell(unread[EDITOR_VIEW][0], 80)}); {len(found)} people, the "
        f"editor's list {'not read' if users_unread else 'read'}; {len(users)} rows"
    )


def _across_make_same(ctx: Any) -> str:
    from quill.core.wordpress import workbench_across as wa
    from quill.core.wordpress import workbench_across_ops as ops
    from quill.core.wordpress import workbench_by_name as bn

    sites = _two_views(ctx)
    apis = dict(sites)
    slug = _stamp_slug(ctx, "same")
    tag = _new_tag(ctx, H.ADMIN, "make the same", slug=slug)
    name = f"{tag['name']} (tag)"
    objects = wa.gather_across("terms", sites).get(name)
    H.expect(objects and len(objects) == 2, f"{name} not seen in both views")
    # Single-site limited: the winner is the same tag with another slug.
    winner = {**objects[ADMIN_VIEW], "slug": slug + "-b"}
    plan = [(EDITOR_VIEW, f"changes from slug {slug} to slug {slug}-b")]
    edits, refused = ops.make_same_edits("terms", name, plan, objects, winner)
    H.expect(len(edits) == 1 and not refused, f"edits {edits}, refused {refused}")
    outcomes, sent = ops.run_edits_by_site(apis.__getitem__, edits)
    H.expect(all(o.ok for o in outcomes), "; ".join(o.line for o in outcomes))
    now = apis[ADMIN_VIEW].get(f"wp/v2/tags/{tag['id']}", context="edit")["slug"]
    H.expect(now == slug + "-b", f"slug is {now}")
    undo = bn.undo_edits(apis.__getitem__, sent)
    now = apis[ADMIN_VIEW].get(f"wp/v2/tags/{tag['id']}", context="edit")["slug"]
    H.expect(now == slug, f"after undo the slug is {now}")
    _e, plugin_refusal = ops.make_same_edits(
        "plugins", "Made Up", [(EDITOR_VIEW, "changes")], {}, {"status": "active"}
    )
    H.expect(plugin_refusal and "not installed" in plugin_refusal[0].words, "no plugin refusal")
    return f"single-site limited: slug changed and {undo.lower()} A missing plugin is refused."


def _across_styles(ctx: Any) -> str:
    from quill.core.wordpress import workbench_across_ops as ops

    sites = _two_views(ctx)
    per = {site: ops.site_styles(api) for site, api in sites}
    summary, lines = ops.compare_styles(per)
    if isinstance(per[ADMIN_VIEW], str):
        raise H.NotRun(f"the active theme: {per[ADMIN_VIEW]}")
    if isinstance(per[EDITOR_VIEW], dict):
        H.expect(summary.startswith("0 of"), f"the same site differs from itself: {summary}")
    networks = {site: ops.network_status(api) for site, api in sites}
    H.expect(not any(networks.values()), f"a single site reads as a network: {networks}")
    refusal = ops.network_refusal(H.SITE_NAME, False, True)
    H.expect("not a multisite network" in refusal, refusal)
    return f"{summary} Promote to Network: {refusal}"


def _across_install(ctx: Any) -> str:
    from quill.core.wordpress import site_admin
    from quill.core.wordpress import workbench_across as wa

    sites = _two_views(ctx)
    unread: dict[str, list[str]] = {}
    found = wa.gather_across("plugins", sites, unread)
    rows = [
        r
        for r in wa.across_rows("plugins", found, [s for s, _ in sites], unread)
        if r.kind == "across"
    ]
    H.expect(rows, "no plugins read as quilladmin")
    H.expect(EDITOR_VIEW in unread, "the editor read the plugin list")
    H.expect(not any(r.cell("missing") for r in rows), "a plugin counted as missing, not unread")
    plan = wa.same_everywhere_plan(rows[0], next(iter(rows[0].raw["variants"])))
    H.expect(dict(plan)[EDITOR_VIEW].startswith("not read"), f"plan: {plan}")
    raw = rows[0].raw["objects"][ADMIN_VIEW]
    slug = str(raw.get("plugin", "")).split("/", 1)[0]
    H.expect(slug, "no plugin slug")
    # An installed plugin's slug: even if the refusal failed, nothing new would arrive.
    error = H.refused(lambda: site_admin.install_plugin(ctx.api(H.EDITOR), slug))
    H.expect(error.status in (401, 403), f"answered {error.status}")
    return (
        f"the plugin list is 'not read' on the editor's view; installing {slug} as the editor: "
        f"{error.status} {error.plain}"
    )


def _across_revoke(ctx: Any) -> str:
    from quill.core.wordpress import workbench_across as wa
    from quill.core.wordpress import workbench_across_ops as ops

    sites = _two_views(ctx)
    found = wa.gather_across("app_passwords", sites)
    mine = [n for n, by in found.items() if n.endswith(", you") and ADMIN_VIEW in by]
    others = [n for n, by in found.items() if ADMIN_VIEW in by and EDITOR_VIEW not in by]
    H.expect(mine, "quilladmin's own application passwords are not listed")
    H.expect(others, "the admin cannot see other people's passwords")
    name = others[0]
    plan, refused = ops.revoke_plan(
        name, found[name], {EDITOR_VIEW: "an editor cannot revoke another person's password"}
    )
    H.expect(plan and all("/application-passwords/" in route for _s, route in plan), f"{plan}")
    # Planned only: nothing is deleted (see the needs-Jeff row).
    return (
        f"{len(found)} passwords listed; {len(others)} visible only to the admin; the plan "
        f"names {len(plan)} route(s) and refuses {len(refused)} site(s); nothing sent"
    )


def _fleet(ctx: Any) -> str:
    from quill.core.wordpress import workbench_fleet as fleet

    version = ctx.state.get("wp_version", "")
    spaces = list(ctx.index.namespaces)
    facts = [(ADMIN_VIEW, fleet.fleet_fact(ctx.api(H.ADMIN), version, spaces))]
    H.expect(
        facts[0][1]["health"] in ("good", "should be improved", "critical"),
        f"admin health: {facts[0][1]['health']}",
    )
    if H.EDITOR in ctx.apis:
        facts.append((EDITOR_VIEW, fleet.fleet_fact(ctx.api(H.EDITOR), version, spaces)))
        said = facts[1][1]["health"]
        H.expect(said == "unavailable: Site Health needs an administrator", f"editor: {said}")
    merged = fleet.merge_fleet(dict(facts), {ADMIN_VIEW: {"error": "a made-up timeout"}})
    H.expect(merged[ADMIN_VIEW].get("stale") == "a made-up timeout", "a silent site lost its facts")
    rows = fleet.fleet_rows(list(merged.items()))
    H.expect(any("stale, as read" in r.detail for r in rows), "the stale row does not say so")
    return " ".join(r.detail for r in fleet.fleet_rows(facts))[:400]


# =========================================================================== #
# Copy to Site, Compare Sites and snapshots (15.2)


def _copy_preview(ctx: Any) -> str:
    from quill.core.wordpress import workbench_site_copy as sc

    api = ctx.api(H.EDITOR)
    about = api.get(f"wp/v2/pages/{_page_id(ctx, api, 'about')}", context="edit")
    fresh = {**about, "slug": _stamp_slug(ctx, "copy"), "title": {"raw": ctx.title("copy")}}
    rows = [("item", "page", about), ("item", "page", fresh), ("comment", "", {"id": 1})]
    plan = sc.plan_copy(
        api,
        rows,
        source_site=EDITOR_VIEW,
        target_site=EDITOR_VIEW,
        source_url=H.SITE_URL,
        source=api,
    )
    actions = [line.action for line in plan.lines]
    H.expect(actions == ["replace", "create", "skip"], f"the plan reads {actions}")
    link = sc.rewrite_links(f'<a href="{H.SITE_URL}/about/">', H.SITE_URL, "https://example.org")
    H.expect("https://example.org/about/" in link, f"link rewritten to {link}")
    return plan.summary


def _copy_run(ctx: Any) -> str:
    from quill.core.wordpress import site as wp
    from quill.core.wordpress import workbench_site_copy as sc

    api = ctx.api(H.EDITOR)
    source = H._new_post(ctx, H.EDITOR, "copy source")
    raw = api.get(f"wp/v2/posts/{source.id}", context="edit")
    slug = _stamp_slug(ctx, "copied")
    raw = {**raw, "slug": slug, "title": {"raw": ctx.title("copied")}}

    def trash_copies(kind: str, wanted: str) -> None:
        admin = ctx.api(H.ADMIN)
        for row in admin.get(wp.kind_route(kind), slug=wanted, status="any", context="edit"):
            wp.trash_item(admin, kind, int(row["id"]))

    ctx.later(f"trash the copy {slug}", lambda: trash_copies("post", slug))
    plan = sc.plan_copy(
        api,
        [("item", "post", raw)],
        source_site=EDITOR_VIEW,
        target_site=EDITOR_VIEW,
        source_url=H.SITE_URL,
        source=api,
    )
    failed = sc.run_copy(api, api, plan, source_url=H.SITE_URL, target_url=H.SITE_URL)
    H.expect(not failed, "; ".join(failed))
    made = api.get("wp/v2/posts", slug=slug, status="any", context="edit")
    H.expect(made and made[0]["status"] == "draft", f"the copy: {made[:1]}")
    said = f"{plan.outcomes[0]} It arrived as a draft."
    if H.CONTRIBUTOR in ctx.apis:
        page_slug = _stamp_slug(ctx, "copied-page")
        page = {**raw, "slug": page_slug, "type": "page", "title": {"raw": ctx.title("page")}}
        ctx.later(f"trash the page {page_slug}", lambda: trash_copies("page", page_slug))
        target = ctx.api(H.CONTRIBUTOR)
        plan = sc.plan_copy(
            target,
            [("item", "page", page)],
            source_site=EDITOR_VIEW,
            target_site="Test site as quill-contributor",
            source_url=H.SITE_URL,
            source=api,
        )
        failed = sc.run_copy(api, target, plan, source_url=H.SITE_URL, target_url=H.SITE_URL)
        H.expect(failed, "a contributor was given a copied page")
        said += f" To a contributor: {failed[0]}"
    return said


def _compare_sites(ctx: Any) -> str:
    from quill.core.wordpress import workbench_snapshot as snap

    sites = _two_views(ctx)
    found = snap.compare_sites(
        sites[0][1],
        sites[1][1],
        first_name=ADMIN_VIEW,
        second_name=EDITOR_VIEW,
        kinds=("post", "page", "pattern", "category", "tag"),
    )
    content = [d for d in found if "differ" in d.words or "here," in d.words]
    H.expect(not content, "; ".join(f"{d.kind} {d.slug}: {d.words}" for d in content[:5]))
    return f"{len(found)} differences between the two views, none in titles, text or status" + (
        ": " + "; ".join(f"{d.kind} {d.slug} {d.words}" for d in found[:4]) if found else ""
    )


def _snapshot(ctx: Any) -> str:
    from quill.core.wordpress import workbench_snapshot as snap

    api = ctx.api(H.ADMIN)
    folder = ctx.scratch / "snapshots"
    path, counts = snap.take_snapshot(api, folder, site=H.SITE_NAME)
    H.expect((path / "snapshot.json").is_file(), "no snapshot.json")
    unread = (H.json.loads((path / "snapshot.json").read_text(encoding="utf-8"))).get("unread")
    H.expect(not unread, f"the snapshot could not read: {'; '.join(unread or [])}")
    H.expect(counts.get("posts", 0) > 0 and counts.get("pages", 0) > 0, f"counts {counts}")
    H.expect(snap.snapshot_folders(folder)[:1] == [path], "the snapshot is not listed first")
    lines = snap.restore_plan(api, path)
    H.expect(not lines, "; ".join(line.sentence for line in lines[:3]))
    return f"{snap.snapshot_counts_words(counts)}; put back plans nothing straight after"


def _snapshot_put_back(ctx: Any) -> str:
    from quill.core.wordpress import workbench_snapshot as snap

    api = ctx.api(H.ADMIN)
    post = H._new_post(ctx, H.ADMIN, "snapshot")
    path, _counts = snap.take_snapshot(api, ctx.scratch / "snapshots-put-back", site=H.SITE_NAME)
    api.post(f"wp/v2/posts/{post.id}", {"title": ctx.title("snapshot, changed")})
    mine = [line for line in snap.restore_plan(api, path) if line.route.endswith(f"/{post.id}")]
    H.expect(len(mine) == 1 and mine[0].action == "put back", f"plan: {mine}")
    said = snap.run_restore(api, mine)
    title = api.get(f"wp/v2/posts/{post.id}", context="edit")["title"]["raw"]
    H.expect(title == post.title, f"after putting back the title is {title!r}")
    return " ".join(said)


# =========================================================================== #
# Read Site as Document, the editorial queue (15.3 to 15.5)


def _read_site_public(ctx: Any) -> str:
    from quill.core.wordpress.workbench_read_site import ReadScope, document_pages, site_document

    pages, notes = document_pages(ctx.anon, ReadScope(), site=H.SITE_NAME)
    titles = [H.cell((p.get("title") or {}).get("rendered", ""), 60) for p in pages]
    H.expect("About Us" in titles, f"pages read: {titles}")
    H.expect(titles.index("Meet the Team") > titles.index("About Us"), "child before parent")
    news = [c for c in ctx.anon.get("wp/v2/categories", slug="news") if c.get("slug") == "news"]
    H.expect(news, "no News category")
    scope = ReadScope("category", int(news[0]["id"]), "News")
    posts, more = document_pages(ctx.anon, scope, site=H.SITE_NAME)
    text = site_document(H.SITE_NAME, posts, address=H.SITE_URL, scope=scope.words, notes=more)
    H.expect("## Welcome to the test site" in text, "Welcome is not in the News document")
    return f"{len(pages)} pages in page order; News: {len(posts)} posts, {len(text)} characters"


def _read_menu(ctx: Any) -> str:
    from quill.core.wordpress.workbench_read_site import ReadScope, document_pages, site_document

    api = ctx.api(H.ADMIN)
    menus = api.get("wp/v2/menus", context="edit") or []
    if not menus:
        raise H.NotRun("no menu on the site")
    menu = menus[0]
    scope = ReadScope("menu", int(menu["id"]), str(menu.get("name", "")))
    pages, notes = document_pages(api, scope, site=H.SITE_NAME)
    text = site_document(H.SITE_NAME, pages, scope=scope.words, notes=notes)
    said = H.cell(" ".join(notes), 120)
    return f"menu {scope.name}: {len(pages)} pages read; {said}; {len(text)} characters"


def _editorial_times(ctx: Any) -> str:
    from quill.core.wordpress.schedule import ScheduleError
    from quill.core.wordpress.workbench_editorial import moment_words, site_moment

    settings = ctx.api(H.ADMIN).get("wp/v2/settings")
    zone = str(settings.get("timezone_string") or "") or "UTC"
    when = site_moment("2027-01-15", "9:00 AM", zone)
    H.expect((when.hour, when.minute) == (9, 0), f"9 AM read as {when}")
    said = moment_words(when, zone)
    traps = []
    for day, clock, word in (
        ("2027-03-14", "2:30 AM", "does not happen"),
        ("2027-11-07", "1:30 AM", "happens twice"),
        ("2020-01-01", "9:00", "in the future"),
    ):
        try:
            site_moment(day, clock, "America/New_York")
            raise H.CheckFailed(f"{day} {clock} was taken")
        except ScheduleError as exc:
            H.expect(word in str(exc), str(exc))
            traps.append(word)
    second = site_moment("2027-11-07", "1:30 AM second", "America/New_York")
    H.expect(second.fold == 1, "second did not choose the later 1:30")
    return f"site zone {zone}: {said}; traps named: {', '.join(traps)}"


def _editorial_queue(ctx: Any) -> str:
    from quill.core.wordpress import workbench_editorial as ed
    from quill.core.wordpress.workbench_load import load_items

    made = H._new_post(ctx, H.CONTRIBUTOR, "for review", status="pending")
    H.expect(made.status == "pending", f"status {made.status}")
    editor = _site_ctx(ctx, H.EDITOR, H.SITE_NAME)
    rows = load_items(editor, "post", {"status": "pending"}, {})
    places = ed.queue_positions(rows)
    mine = places.get((H.SITE_NAME, str(made.id)), "")
    H.expect(mine.endswith(f"waiting on {H.SITE_NAME}"), f"place: {mine!r}")
    own = load_items(_site_ctx(ctx, H.CONTRIBUTOR, H.SITE_NAME), "post", {"status": "pending"}, {})
    H.expect(str(made.id) in {r.key for r in own}, "the contributor cannot see their own")
    review = ed.Review(H.SITE_NAME, made.id, f"wp/v2/posts/{made.id}", made.title, H.EDITOR)
    ed.assign_reviewer(ctx.scratch, review)
    H.expect([r.item_id for r in ed.load_reviews(ctx.scratch)] == [made.id], "not kept")
    status = ed.queue_status(ctx.api(H.EDITOR), review)
    H.expect(status == "pending", f"queue status {status}")
    return f"{mine}; the contributor sees {len(own)} of {len(rows)}; reviewer kept locally"


# =========================================================================== #
# REST Console, Watches, lists in and out (15.7, 15.9, 15.10)


def _rest_console(ctx: Any) -> str:
    from quill.core.wordpress import workbench_io as io
    from quill.core.wordpress import workbench_rest_routes as rr

    routes = ctx.index.routes
    shapes = rr.templates(routes)
    H.expect("wp/v2/posts/{id}" in shapes, "wp/v2/posts/{id} is not a template")
    route, left = rr.fill_route("wp/v2/posts/{id}", {"id": 1, "context": "view"})
    H.expect(route == "wp/v2/posts/1" and left == {"context": "view"}, f"{route} {left}")
    entry = rr.find_entry(routes, route)
    methods = rr.methods_for(entry)
    H.expect({"GET", "POST", "DELETE"} <= set(methods), f"methods {methods}")
    args = rr.arguments(entry, "POST")
    problems = rr.argument_problems(args, {"status": "nonsense", "made_up": 1})
    H.expect(len(problems) >= 2, f"problems found: {problems}")
    H.expect("wp/v2/posts" in io.complete_route("wp/v2/pos", routes), "no completion")
    H.expect(io.needed_capability("GET", "wp/v2/settings") == "manage_options", "settings need")
    params = io.parse_params("context=edit\nper_page=5")
    H.expect(set(params) == {"context", "per_page"}, f"params read as {params}")
    schema = ctx.anon.request("OPTIONS", "wp/v2/posts").payload.get("schema") or {}
    lines = rr.schema_lines(schema)
    H.expect(lines, "OPTIONS gave no schema")
    return (
        f"{len(shapes)} route shapes; posts/{{id}} takes {', '.join(methods)}; "
        f"{len(rr.argument_lines(args))} POST arguments; {len(lines)} schema lines"
    )


def _rest_console_editor(ctx: Any) -> str:
    from quill.core.wordpress import workbench_io as io

    need = io.needed_capability("GET", "wp/v2/settings")
    error = H.refused(lambda: ctx.api(H.EDITOR).get("wp/v2/settings"))
    H.expect(error.status in (401, 403), f"answered {error.status}")
    return f"needs {need}; the site said {error.status}: {error.plain}"


def _watches(ctx: Any) -> str:
    from quill.core.wordpress import workbench_watches as wt

    state = wt.WatchState()
    sites = [(H.SITE_NAME, ctx.api(H.ADMIN), list(ctx.index.namespaces))]
    kinds = list(wt.KINDS)
    first = wt.check(sites, state, kinds, unreachable=["QUILL live test, gone"], now=lambda: 1e9)
    H.expect(first == [], f"the first look spoke: {first}")
    again = wt.check(sites, state, kinds, now=lambda: 1e9 + 60)
    H.expect(again == [], f"nothing changed, yet: {again}")
    H.expect(not wt.due(state, 15, now=lambda: 1e9 + 60), "due again after a minute")
    said = ""
    waiting = state.waiting.get(H.SITE_NAME) or []
    if waiting:
        state.waiting[H.SITE_NAME] = waiting[1:]
        news = wt.check(sites, state, ["comment"], now=lambda: 1e9 + 1000)
        H.expect(any("1 new comment" in s for s in news), f"after forgetting one: {news}")
        said = f"; then: {news[0]}"
    wt.save_state(state, ctx.scratch)
    H.expect(wt.load_state(ctx.scratch).waiting == state.waiting, "the state did not round-trip")
    return f"first look and second round silent{said}"


def _lists_local(ctx: Any) -> str:
    from quill.core.wordpress import workbench_io as io
    from quill.core.wordpress.workbench_load import load_items

    rows = load_items(_site_ctx(ctx, H.EDITOR, H.SITE_NAME), "post", {}, {})
    H.expect(rows, "no posts read")
    table = [(r.title, r.status, "") for r in rows]
    heads = ("Title", "Status", "Content")
    said = []
    for suffix in ("csv", "xlsx", "md"):
        path = ctx.scratch / f"export.{suffix}"
        try:
            count = io.export_rows(path, heads, table)
        except ImportError as exc:
            said.append(f"{suffix}: {exc}")
            continue
        H.expect(count == len(rows) and path.stat().st_size, f"{suffix} wrote {count}")
        said.append(f"{suffix} {count}")
    back = io.read_spreadsheet(ctx.scratch / "export.csv")
    plan = io.import_plan(back)
    H.expect(len(plan) == len(rows), f"{len(plan)} import rows for {len(rows)}")
    noted = [p for p in plan if p.note]
    H.expect(noted, "a published row was not turned into a draft with a note")
    folder = ctx.scratch / "documents"
    folder.mkdir()
    (folder / "one.md").write_text("# A heading\n\nText.\n", encoding="utf-8")
    (folder / "two.md").write_text("", encoding="utf-8")
    docs = io.folder_plan(folder, lambda p: p.read_text(encoding="utf-8"))
    H.expect([d.problem for d in docs] == ["", "it is empty"], f"{[d.sentence for d in docs]}")
    return f"exported {', '.join(said)}; read back {len(plan)} rows; {noted[0].sentence}"


def _lists_import(ctx: Any) -> str:
    from quill.core.wordpress import site as wp
    from quill.core.wordpress import workbench_io as io

    api = ctx.api(H.EDITOR)
    rows = [
        {"Title": ctx.title("import"), "Content": "Imported.", "Status": "publish"},
        {"Title": ctx.title("import, bad status"), "Content": "x", "Status": "nonsense"},
        {"Title": "", "Content": "", "Status": ""},
    ]
    plan = io.import_plan(rows)
    said = io.send_import_results(api, "post", plan)

    def trash_imports() -> None:
        admin = ctx.api(H.ADMIN)
        for row in wp.list_items(admin, "post", search=ctx.title("import")):
            if H.TAG in row.title:
                wp.trash_item(admin, "post", row.id)

    ctx.later("trash the imported posts", trash_imports)
    H.expect(said[0].startswith("Made") and said[1].startswith("Skipped"), "; ".join(said))
    H.expect(said[2].startswith("Skipped"), said[2])
    number = int(re.search(r"number (\d+)", said[0]).group(1))
    status = api.get(f"wp/v2/posts/{number}", context="edit")["status"]
    H.expect(status == "draft", f"the imported row is {status}")
    out = " ".join(said)
    if H.CONTRIBUTOR in ctx.apis:
        page = io.import_plan([{"Title": ctx.title("import page"), "Content": "x"}])
        refused = io.send_import_results(ctx.api(H.CONTRIBUTOR), "page", page)
        if refused[0].startswith("Made"):
            trash_imports()
        H.expect(refused[0].startswith("Not made"), f"a contributor made a page: {refused[0]}")
        out += f" Contributor, a page: {refused[0]}"
    return out


# =========================================================================== #
# Redirects, upkeep, the sweep, Site Health, REST limits (15.11, 10B.3)


def _redirects(ctx: Any) -> str:
    from quill.core.wordpress import workbench_redirects as rd
    from quill.core.wordpress import workbench_sweep as sw

    spaces = list(ctx.index.namespaces)
    H.expect(
        sw.redirect_offered(spaces) == (rd.NAMESPACE in spaces),
        "redirect_offered disagrees with the index",
    )
    _need(ctx, rd.NAMESPACE, "Redirection")
    api = ctx.api(H.ADMIN)
    items = rd.read_pages(api, "redirect")
    missing = rd.read_pages(api, "404", max_pages=1)
    rows = [rd.redirect_row(H.SITE_NAME, r, H.SITE_URL) for r in items]
    said = rd.trace_address("/quill-live-test-nowhere/", items, H.SITE_URL)
    H.expect(said.startswith("No redirect"), said)
    return f"{len(rows)} redirects, {len(missing)} not-found rows read; {H.cell(said, 80)}"


def _redirects_write(ctx: Any) -> str:
    from quill.core.wordpress import workbench_redirects as rd

    _need(ctx, rd.NAMESPACE, "Redirection")
    api = ctx.api(H.ADMIN)
    source = "/" + _stamp_slug(ctx, "redirect") + "/"
    group = rd.default_group(rd.read_groups(api))
    if not group:  # setup never finished on the site: make the group its setup makes
        try:
            group = rd.make_first_group(api)
        except Exception as exc:  # noqa: BLE001 - the plugin's tables are missing
            raise H.NeedsJeff(
                "Redirection has no groups and cannot make one; finish its setup under "
                f"Tools > Redirection in wp-admin ({exc})"
            ) from exc
        H.expect(group, "the Redirection plugin did not make a group")
        ctx.later(
            f"delete redirect group {group}",
            lambda: api.post(f"{rd.NAMESPACE}/bulk/group/delete", {"items": [group]}),
        )
    api.post(
        f"{rd.NAMESPACE}/redirect",
        rd.edit_body(source, H.SITE_URL + "/about/", group_id=group),
    )
    made = [
        r
        for r in rd.read_pages(api, "redirect")
        if str(r.get("url", "")).rstrip("/") == source.rstrip("/")
    ]
    H.expect(made, "the redirect is not listed")
    ident = int(made[0]["id"])
    ctx.later(
        f"delete redirect {ident}",
        lambda: api.post(f"{rd.NAMESPACE}/bulk/redirect/delete", {"items": [ident]}),
    )
    said = rd.trace_address(source, made, H.SITE_URL)
    H.expect("leads to" in said, said)
    out = H.cell(said, 120)
    if H.CONTRIBUTOR in ctx.apis:
        error = H.refused(lambda: ctx.api(H.CONTRIBUTOR).get(f"{rd.NAMESPACE}/redirect"))
        out += f"; a contributor: {error.status}"
    return out


def _upkeep_public(ctx: Any) -> str:
    from quill.core.wordpress import workbench_upkeep as up

    status, _headers, body = H.fetch(H.site_url("wp-sitemap.xml"))
    found = status == 200
    sitemap = up.sitemap_row(H.SITE_NAME, H.SITE_URL, body if found else None)
    seen = up.visibility_row(H.SITE_NAME, H.SITE_URL, None, found)
    cert = up.read_certificate(ctx.anon)
    H.expect(cert, "the certificate could not be read from QUILL's own connection")
    expiry = up.certificate_row(H.SITE_NAME, H.SITE_URL, cert)
    return " ".join(H.cell(r.detail, 110) for r in (sitemap, seen, expiry))


def _upkeep_signed(ctx: Any) -> str:
    from quill.core.wordpress import workbench_upkeep as up

    api = ctx.api(H.ADMIN)
    future = list(api.get("wp/v2/posts", status="future", context="edit") or [])
    H.expect(
        any(H.cell(p["title"]["raw"]) == "Scheduled for next month" for p in future),
        "no seeded scheduled post",
    )
    overdue = up.overdue_rows(H.SITE_NAME, future)
    H.expect(
        not any("Scheduled for next month" in r.detail for r in overdue), "next month is overdue"
    )
    recent = list(api.get("wp/v2/posts", status="any", context="edit", per_page=20) or [])
    me = ctx.accounts.get(H.ADMIN)
    locks = up.lock_rows(H.SITE_NAME, recent, me=me.id if me else 0)
    return f"{len(future)} scheduled, {len(overdue)} overdue; {len(locks)} lock rows"


def _sweep(ctx: Any) -> str:
    from quill.core.wordpress import workbench_across as wa
    from quill.core.wordpress import workbench_sweep as sw

    scan = wa.scan_site(ctx.api(H.ADMIN), H.SITE_NAME, pages=3)
    audit = sw.content_audit(scan)
    media = sw.media_housekeeping(scan)
    H.expect(audit or media, "the sweep found nothing at all on a seeded site")
    summary, places = sw.trash_preview((audit or media)[0])
    H.expect(summary, "no Move to Trash preview")
    privacy = sw.privacy_rows(
        H.SITE_NAME, H.SITE_URL, list(ctx.index.routes), ctx.state.get("wp_version", "")
    )
    H.expect(privacy, "no privacy rows")
    return (
        f"{len(audit)} content findings, {len(media)} media findings; preview: "
        f"{H.cell(summary, 90)}; {len(privacy)} privacy rows"
    )


def _health_info(ctx: Any) -> str:
    from quill.core.wordpress.workbench_health_info import info_rows

    rows = info_rows(_site_ctx(ctx, H.ADMIN, H.SITE_NAME))
    H.expect(rows and rows[0].link.endswith("site-health.php?tab=debug"), "no Info tab row")
    return f"{len(rows)} rows: " + "; ".join(r.title for r in rows[:6])


def _xmlrpc(ctx: Any) -> str:
    from quill.core.wordpress.workbench_health_info import xmlrpc_check

    found = xmlrpc_check(ctx.anon)
    H.expect(found.state in ("answers", "blocked", "unknown"), found.state)
    if found.state == "unknown":
        raise H.NeedsJeff(f"the probe could not tell: {found.sentence}")
    return f"{found.state}: {H.cell(found.sentence, 160)}"


def _rest_limits(ctx: Any) -> str:
    from quill.core.wordpress import workbench_no_rest as nr

    gone = []
    for key in nr.ADMIN_SCREENS:
        if key.startswith("pmpro") and "pmpro/v1" not in set(ctx.index.namespaces):
            continue
        status = H.fetch(nr.admin_link(H.SITE_URL, key), limit=2000)[0]
        if status == 404:
            gone.append(key)
    H.expect(not gone, f"wp-admin screens that are not there: {gone}")
    H.expect(nr.screen_for_row("across", "plugins") == "plugin_auto_updates", "row screen")
    H.expect("only reads" in nr.REST_CANNOT, nr.REST_CANNOT)
    return f"{len(nr.ADMIN_SCREENS)} wp-admin screens named, every one there (sign-in asked)"


# =========================================================================== #
# Plugins: Paid Memberships Pro, Gravity Forms; WordPress.org


def _pmpro(ctx: Any) -> str:
    from quill.core.wordpress import workbench_pmpro_rest as pm

    _need(ctx, pm.PMPRO_NAMESPACE, "Paid Memberships Pro")
    api = ctx.api(H.ADMIN)
    site = _site_ctx(ctx, H.ADMIN, H.SITE_NAME)
    me = site.account
    levels = pm.member_levels(api, me.id)
    about = _page_id(ctx, api, "about")
    access = pm.has_access(api, me.id, about).sentence(me.name, "About Us", H.SITE_NAME)
    codes = pm.load_discount_codes(site)
    preview = pm.discount_preview(pm.DiscountSpec("QUILLLIVETEST", (1,)), H.SITE_NAME, {})
    return f"{len(levels)} levels for quilladmin; {access} {len(codes)} code rows; {preview[0]}"


def _pmpro_contributor(ctx: Any) -> str:
    from quill.core.wordpress import workbench_pmpro_rest as pm

    _need(ctx, pm.PMPRO_NAMESPACE, "Paid Memberships Pro")
    api = ctx.api(H.CONTRIBUTOR)
    about = _page_id(ctx, api, "about")
    error = H.refused(lambda: pm.has_access(api, 1, about))
    return f"{error.status}: {error.plain}"


def _gravity_entry(ctx: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    from quill.core.wordpress.workbench_gravity import NS

    api = ctx.api(H.ADMIN)
    answer = api.get(f"{NS}/entries", **{"paging[page_size]": 1})
    entries = answer.get("entries", []) if isinstance(answer, dict) else answer or []
    if not entries:
        raise H.NotRun("Gravity Forms has no entries on the site")
    entry = entries[0]
    form = api.get(f"{NS}/forms/{entry['form_id']}")
    return entry, form


def _gravity(ctx: Any) -> str:
    from quill.core.wordpress import workbench_gravity as gf

    _need(ctx, gf.NS, "Gravity Forms")
    site = _site_ctx(ctx, H.ADMIN, H.SITE_NAME)
    forms = gf.gravity_forms(site.api)
    if not forms:
        raise H.NotRun("Gravity Forms has no forms on the site")
    feeds = gf.load_feeds(site)
    results = gf.load_results(site)
    filters = gf.field_filters(site.api, next(iter(forms)))
    preview = gf.feed_body(feeds[0].raw, active=True)[1][0] if feeds else "no feeds"
    return (
        f"{len(forms)} forms, {len(feeds)} feeds ({preview}), {len(results)} result rows, "
        f"{len(filters)} field filters"
    )


def _gravity_notes(ctx: Any) -> str:
    from quill.core.wordpress import workbench_gravity as gf

    _need(ctx, gf.NS, "Gravity Forms")
    entry, form = _gravity_entry(ctx)
    notes = gf.read_notes(ctx.api(H.ADMIN), int(entry["id"]))
    lines = gf.note_lines(notes)
    sends = gf.entry_notifications(form, entry)
    # Resend is never run here: it emails real people (needs Jeff).
    return f"{len(notes)} notes ({H.cell(lines[0], 60)}); {len(sends)} notifications previewed"


def _gravity_star(ctx: Any) -> str:
    from quill.core.wordpress import workbench_gravity as gf

    _need(ctx, gf.NS, "Gravity Forms")
    entry, _form = _gravity_entry(ctx)
    api = ctx.api(H.ADMIN)
    route = f"{gf.NS}/entries/{entry['id']}"
    was = gf.set_entry_flag(api, route, "is_starred", True)
    ctx.later("put back the entry's star", lambda: gf.set_entry_flag(api, route, "is_starred", was))
    now = gf.truthy(api.get(route).get("is_starred"))
    H.expect(now, "the entry is not starred")
    return f"starred (was {'starred' if was else 'not starred'}); put back afterwards"


def _gravity_validate(ctx: Any) -> str:
    from quill.core.wordpress import workbench_gravity as gf
    from quill.core.wordpress import workbench_gravity_submit as gs

    _need(ctx, gf.NS, "Gravity Forms")
    api = ctx.api(H.ADMIN)
    forms = gf.gravity_forms(api)
    if not forms:
        raise H.NotRun("Gravity Forms has no forms on the site")
    form_id = next(iter(forms))
    form = api.get(f"{gf.NS}/forms/{form_id}")
    inputs, skipped = gs.sample_inputs(form)
    answer = gs.submit(api, form_id, {i.name: i.value for i in inputs}, validate_only=True)
    H.expect(not gs.is_practice_site(H.SITE_URL, H.SITE_NAME), "the test site reads as practice")
    said = "valid" if answer.valid else "; ".join(answer.lines({}))[:120]
    return (
        f"{forms[form_id]}: {len(inputs)} filled, {len(skipped)} skipped; validation only: "
        f"{said}. A real submission is offered only on a practice site"
    )


def _gravity_contributor(ctx: Any) -> str:
    from quill.core.wordpress import workbench_gravity as gf
    from quill.core.wordpress.site import load_account

    _need(ctx, gf.NS, "Gravity Forms")
    api = ctx.api(H.CONTRIBUTOR)
    error = H.refused(lambda: gf.gravity_forms(api))
    account = ctx.accounts.get(H.CONTRIBUTOR) or load_account(api)
    H.expect(not gf.gravity_can(account, gf.CAPABILITIES["edit_forms"][0]), "can edit forms")
    return f"{error.status}: {error.plain}"


def _dotorg(ctx: Any) -> str:
    from quill.core.wordpress import dotorg

    version = ctx.state.get("wp_version", "")
    if not version:
        raise H.NotRun("the site's WordPress version is not known")
    themes = dotorg.search_themes("accessibility ready")
    H.expect(themes, "WordPress.org found no themes")
    said = dotorg.site_languages([
        (H.SITE_NAME, "en_US", version),
        ("A made-up French site", "fr_FR", version),
    ])
    H.expect("needs no language pack" in said[0][1], said[0][1])
    H.expect("French" in said[1][1] or "fr_FR" in said[1][1], said[1][1])
    return f"{len(themes)} themes, first {themes[0].name}; {H.cell(said[1][1], 120)}"


# =========================================================================== #
# The list, in order: (area, test, name, function, who, writes)

_A, _E, _U, _C = "quilladmin", "quill-editor", "quill-author", "quill-contributor"

_TESTS: tuple[tuple[str, str, str, Any, str, bool], ...] = (
    (
        AREA_SITE,
        "70",
        "By Name: where a term, shortcode, author, part is used",
        _by_name_read,
        _E,
        False,
    ),
    (
        AREA_SITE,
        "71",
        "By Name: rename a tag everywhere, undo, conflict",
        _by_name_rename,
        _E,
        True,
    ),
    (AREA_SITE, "72", "By Name: split a tag, then merge it back", _by_name_split, _E, True),
    (AREA_SITE, "73", "By Name: a contributor's rename is refused", _by_name_contributor, _C, True),
    (
        AREA_ACROSS,
        "74",
        "Across Sites: terms, settings, people in two views",
        _across_gather,
        _A,
        False,
    ),
    (
        AREA_ACROSS,
        "75",
        "Make Them the Same, then undo (single-site limited)",
        _across_make_same,
        _A,
        True,
    ),
    (
        AREA_ACROSS,
        "76",
        "Compare global styles; Promote to Network detection",
        _across_styles,
        _A,
        False,
    ),
    (
        AREA_ACROSS,
        "77",
        "Install on Sites Missing It: the editor is refused",
        _across_install,
        _A,
        True,
    ),
    (
        AREA_ACROSS,
        "78",
        "Revoke application passwords everywhere: the plan",
        _across_revoke,
        _A,
        False,
    ),
    (AREA_ACROSS, "79", "Fleet: every aspect, a stale site kept", _fleet, _A, False),
    (AREA_ACROSS, "80", "Copy to Site: the preview", _copy_preview, _E, False),
    (AREA_ACROSS, "81", "Copy to Site: a draft copied; a contributor refused", _copy_run, _E, True),
    (AREA_ACROSS, "82", "Compare Sites (two views of one site)", _compare_sites, _A, False),
    (AREA_ACROSS, "83", "Take a Snapshot; put back plans nothing", _snapshot, _A, False),
    (AREA_ACROSS, "84", "Put Back from a Snapshot", _snapshot_put_back, _A, True),
    (AREA_SITE, "85", "Read Site as Document: pages and a category", _read_site_public, "", False),
    (AREA_SITE, "86", "Read a menu as a document", _read_menu, _A, False),
    (
        AREA_SITE,
        "87",
        "Times on the site's clock, and the clock-change traps",
        _editorial_times,
        _A,
        False,
    ),
    (
        AREA_SITE,
        "88",
        "Editorial queue: place in line, reviewer, status",
        _editorial_queue,
        _C,
        True,
    ),
    (
        AREA_SITE,
        "89",
        "REST Console: routes, arguments, schema from the index",
        _rest_console,
        "",
        False,
    ),
    (
        AREA_SITE,
        "90",
        "REST Console: an editor's settings read refused",
        _rest_console_editor,
        _E,
        False,
    ),
    (AREA_SITE, "91", "Watches: the first look is silent", _watches, _A, False),
    (
        AREA_SITE,
        "92",
        "Lists: export, read back, import preview, a folder",
        _lists_local,
        _E,
        False,
    ),
    (
        AREA_SITE,
        "93",
        "Lists: import as drafts; a contributor's page refused",
        _lists_import,
        _E,
        True,
    ),
    (AREA_PLUGINS, "94", "Redirects and the 404 log; Test an Address", _redirects, _A, False),
    (AREA_PLUGINS, "95", "Redirects: make one, trace it, delete it", _redirects_write, _A, True),
    (
        AREA_SITE,
        "96",
        "Search and Upkeep: sitemap, visibility, certificate",
        _upkeep_public,
        "",
        False,
    ),
    (
        AREA_SITE,
        "97",
        "Search and Upkeep: overdue schedules, editing locks",
        _upkeep_signed,
        _A,
        False,
    ),
    (AREA_SITE, "98", "Sweep: content audit, media, Trash preview, privacy", _sweep, _A, False),
    (AREA_SITE, "99", "Site Health Information rows", _health_info, _A, False),
    (AREA_SITE, "100", "XML-RPC probe, unsigned", _xmlrpc, "", False),
    (
        AREA_SITE,
        "101",
        "What REST cannot do: every wp-admin screen named is there",
        _rest_limits,
        "",
        False,
    ),
    (AREA_PLUGINS, "102", "Paid Memberships Pro: levels, Has Access, codes", _pmpro, _A, False),
    (
        AREA_PLUGINS,
        "103",
        "Paid Memberships Pro: a contributor is refused",
        _pmpro_contributor,
        _C,
        False,
    ),
    (AREA_PLUGINS, "104", "Gravity Forms: feeds, results, field filters", _gravity, _A, False),
    (
        AREA_PLUGINS,
        "105",
        "Gravity Forms: notes, notifications previewed",
        _gravity_notes,
        _A,
        False,
    ),
    (AREA_PLUGINS, "106", "Gravity Forms: star an entry, put it back", _gravity_star, _A, True),
    (
        AREA_PLUGINS,
        "107",
        "Gravity Forms: test submission, validation only",
        _gravity_validate,
        _A,
        False,
    ),
    (
        AREA_PLUGINS,
        "108",
        "Gravity Forms: a contributor is refused",
        _gravity_contributor,
        _C,
        False,
    ),
    (AREA_PLUGINS, "109", "WordPress.org: theme search and language packs", _dotorg, "", False),
)
