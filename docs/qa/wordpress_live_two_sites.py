"""Tests 110 onward of the live WordPress run: Across Sites between two real sites.

Loaded by ``docs/qa/wordpress-live-run.py`` (``_load_workbench_checks``), which
passes itself to :func:`register`. Tests 74 to 84 read the one test site twice;
these run between the test site (as quilladmin) and the **Practice Site**, the
WordPress Playground site on 127.0.0.1:9400 that the Workbench starts
(``quill/core/wordpress/workbench_practice.py``). The harness starts it, or
reuses one it started before, only with ``--second-site practice``; without
that every test here is "not run: no second site", never a failure.

The Practice Site is the run's own: it lives in ``build/live-run/practice-site``
(``QUILL_LIVE_PRACTICE_BASE`` moves the parent folder), not in QUILL's data
folder, so a Practice Site the person uses in QUILL is never touched. Its
one-time application password is read from that folder's handoff file and held
in memory only: never printed, never stored in Credential Manager. Deleting the
folder makes the next run build a new site (about three minutes).

Writes to the test site are only "QUILL live test" items the run makes and
removes, as everywhere else in the harness. Content goes from the test site to
the Practice Site, never the other way.

``--second-site practice-alone`` checks this file itself without the test site:
the Practice Site stands in for both sites, what the "first site" would have had
is made up in memory, and anything that needs two different sites says so in
its detail.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

#: The harness module, set by :func:`register`.
H: Any = None

AREA = "Workbench, two sites (15.2, 15.12)"
AREA_ACROSS = "Workbench, across sites (15.2, 15.12)"
PRACTICE = "Practice Site"
STAND_IN = "Practice Site, standing in for the test site"
PLUGIN = "hello-dolly"

#: "needs Jeff" rows of wordpress_live_workbench.py these tests do with a second site.
COVERS = frozenset({(AREA_ACROSS, ref) for ref in ("75", "77", "78", "81")})


def register(harness: Any) -> None:
    """Put tests 110 onward on the harness's list, and the second site's start and stop."""
    global H
    H = harness
    areas = list(harness.AREAS)
    if AREA not in areas:
        areas.insert(areas.index("Clean-up") if "Clean-up" in areas else len(areas), AREA)
        harness.AREAS = tuple(areas)
    for ref, name, fn, writes in _TESTS:
        harness.check(AREA, ref, name, who=harness.ADMIN, writes=writes, second_site=True)(fn)
    harness.SECOND_SITE_HOOKS = (attach, detach)
    harness.SECOND_SITE_COVERS = COVERS


# =========================================================================== #
# The second site: start or reuse, sign in, stop


@dataclass
class SecondSite:
    name: str
    url: str
    api: Any
    username: str
    folder: Path
    process: Any  # the server the run started, or None when it reused one
    alone: bool
    started_here: bool


def _folder() -> Path:
    from quill.core.wordpress.workbench_practice import practice_dir

    base = os.environ.get("QUILL_LIVE_PRACTICE_BASE", "").strip()
    return practice_dir(Path(base) if base else H.ROOT / "build" / "live-run")


def _answers_as_practice() -> bool:
    """Whether 127.0.0.1:9400 is a Practice Site already (any other answer is not)."""
    import json
    from http.client import HTTPConnection

    from quill.core.wordpress.workbench_practice import LOOPBACK_HOST, PORT, PRACTICE_NAME

    connection = HTTPConnection(LOOPBACK_HOST, PORT, timeout=20.0)
    try:
        connection.request("GET", "/wp-json/?_fields=name,namespaces")
        response = connection.getresponse()
        index = json.loads(response.read().decode("utf-8")) if response.status == 200 else {}
        return isinstance(index, dict) and index.get("name") == PRACTICE_NAME
    except (OSError, ValueError):
        return False
    finally:
        connection.close()


def _start(folder: Path) -> Any:
    from quill.core.wordpress import workbench_practice as wp_p

    tools = wp_p.find_cli()
    missing = wp_p.missing_words(tools)
    if missing:
        raise RuntimeError(missing)
    process = wp_p.start_process(tools, folder)
    try:
        wp_p.wait_for_site(process, folder)
    except BaseException:
        wp_p.stop_process(process)
        raise
    return process


def attach(ctx: Any, *, alone: bool = False) -> None:
    """Start (or reuse) the Practice Site and sign in to it; on failure say why, once."""
    from quill.core.wordpress import workbench_practice as wp_p
    from quill.core.wordpress.api import SiteAddress, SiteAuth, WordPressApi

    folder = _folder()
    process = None
    try:
        if wp_p.port_problem():
            if not _answers_as_practice():
                raise RuntimeError(wp_p.port_problem())
            print("A Practice Site is already running on 127.0.0.1:9400; the run uses it.")
        else:
            print("Starting the Practice Site (a first start installs WordPress: minutes).")
            process = _start(folder)
        found = wp_p.read_password(folder)
        if found is None:
            raise RuntimeError(
                "the running Practice Site handed the run no application password (one "
                "started by QUILL keeps its own); stop it there, or delete "
                f"{folder} so the run builds its own"
            )
        username, secret = found
        ctx.secrets += H.secret_forms(username, secret)
        api = WordPressApi(
            SiteAddress(wp_p.site_url()),
            SiteAuth("app_password", username, secret),
            site_name=PRACTICE,
            timeout=90.0,
        )
        del secret, found
        me = api.get("wp/v2/users/me", context="edit")
        if "administrator" not in (me.get("roles") or []):
            raise RuntimeError(f"the Practice Site's {username} is not an administrator")
    except Exception as exc:  # noqa: BLE001 - every test says why, as "not run"
        if process is not None:
            wp_p.stop_process(process)
        ctx.second_why = f"no second site: {ctx.mask(getattr(exc, 'plain', '') or exc)}"
        print(ctx.second_why)
        return
    ctx.second = SecondSite(
        PRACTICE, wp_p.site_url(), api, username, folder, process, alone, process is not None
    )
    print(f"Second site: {PRACTICE} at {wp_p.site_url()}, signed in as {username}.")


def detach(ctx: Any) -> None:
    """After the clean-up: sweep the Practice Site, then stop it if the run started it."""
    second = ctx.second
    if second is None:
        return
    from quill.core.wordpress import workbench_practice as wp_p

    try:
        left = _practice_leftovers(second.api)
        ctx.results.add(
            "Clean-up",
            "-",
            f"Nothing titled '{H.TAG}' left on the Practice Site",
            H.FAIL if left else H.PASS,
            ", ".join(left) or "none",
            second.username,
        )
    except Exception as exc:  # noqa: BLE001 - a stopped site cannot be swept; say so
        ctx.results.add("Clean-up", "-", "Practice Site sweep", H.FAIL, ctx.mask(exc), "-")
    if second.started_here and second.process is not None:
        wp_p.stop_process(second.process)
        second.process = None
        print("Stopped the Practice Site the run started.")


def _practice_leftovers(api: Any) -> list[str]:
    left: list[str] = []
    for route in ("wp/v2/posts", "wp/v2/pages", "wp/v2/blocks"):
        for raw in api.get(route, search=H.TAG, status="any", context="edit", per_page=100):
            left.append(f"{route.rsplit('/', 1)[1]} {raw['id']}")
    for route in ("wp/v2/tags", "wp/v2/categories"):
        left += [f"term {t['id']}" for t in api.get(route, search=H.TAG, per_page=100)]
    left += [
        f"menu {m['id']}"
        for m in api.get("wp/v2/menus", context="edit", per_page=100)
        if H.TAG in str(m.get("name", ""))
    ]
    left += [f"media {m['id']}" for m in _run_media(api)]
    left += [
        f"plugin {p['plugin']}"
        for p in api.get("wp/v2/plugins", context="edit")
        if str(p.get("plugin", "")).startswith(PLUGIN + "/")
    ]
    return left


def _run_media(api: Any) -> list[dict[str, Any]]:
    """Media on the Practice Site uploaded by the run (its file is quill-live-test*.png)."""
    found = api.get("wp/v2/media", search="quill-live-test", context="edit", per_page=100)
    return [
        m
        for m in found
        if str(m.get("source_url", "")).rsplit("/", 1)[-1].startswith("quill-live-test")
    ]


# =========================================================================== #
# The pair of sites the tests run between


@dataclass
class Pair:
    first: str
    first_url: str
    first_api: Any
    second: str
    second_url: str
    second_api: Any
    alone: bool

    def api(self, site: str) -> Any:
        return self.first_api if site == self.first else self.second_api

    @property
    def names(self) -> list[str]:
        return [self.first, self.second]

    @property
    def reading(self) -> list[tuple[str, Any]]:
        """The sites read for real: both, or only the Practice Site when it stands alone."""
        pair = [(self.second, self.second_api)]
        return pair if self.alone else [(self.first, self.first_api), *pair]


def _pair(ctx: Any) -> Pair:
    second = ctx.second
    if second is None:
        raise H.NotRun(ctx.second_why)
    if second.alone:
        first = (STAND_IN, second.url, second.api)
    else:
        first = (H.SITE_NAME, H.SITE_URL, ctx.api(H.ADMIN))
    return Pair(*first, second.name, second.url, second.api, second.alone)


def _slug(ctx: Any, words: str) -> str:
    return "quill-live-test-" + words + "-" + re.sub(r"\D", "", ctx.stamp)


def _quietly(call: Any) -> None:
    """A clean-up step that is done when the thing is already gone."""
    from quill.core.wordpress.api import WordPressApiError

    try:
        call()
    except WordPressApiError as exc:
        if exc.status not in (404, 410):
            raise


def _make(ctx: Any, api: Any, site: str, route: str, body: dict[str, Any]) -> dict[str, Any]:
    """Make something on *site*, removed afterwards: posts and pages trashed on the test
    site (as the harness does everywhere), anything on the Practice Site deleted."""
    made = api.post(route, body)
    ident = int(made["id"])
    trash = route in ("wp/v2/posts", "wp/v2/pages") and site == H.SITE_NAME
    ctx.later(
        f"{'trash' if trash else 'delete'} {route} {ident} on {site}",
        lambda: _quietly(
            lambda: (
                api.delete(f"{route}/{ident}")
                if trash
                else api.delete(f"{route}/{ident}", force=True)
            )
        ),
    )
    return made


def _make_first(ctx: Any, pair: Pair, route: str, body: dict[str, Any]) -> dict[str, Any]:
    """Made on the test site; when the Practice Site stands alone, only imagined."""
    if pair.alone:
        return {**body, "id": 0}
    return _make(ctx, pair.first_api, pair.first, route, body)


def _gather(pair: Pair, kind: str, imagined: dict[str, Any]) -> tuple[dict[str, Any], dict]:
    """Across Sites rows of *kind*, by key, and what was not read."""
    from quill.core.wordpress import workbench_across as wa

    unread: dict[str, list[str]] = {}
    found = wa.gather_across(kind, pair.reading, unread)
    if pair.alone:
        for name, raw in imagined.items():
            found.setdefault(name, {})[pair.first] = raw
    rows = wa.across_rows(kind, found, pair.names, unread)
    return {r.key: r for r in rows if r.kind == "across"}, unread


def _same_then_undo(
    pair: Pair, kind: str, row: Any, winner_site: str, value_of: Any
) -> tuple[str, str]:
    """Make *row* the same as *winner_site*'s copy, read it back, undo, read it back.

    Returns (the site that changed, the undo sentence)."""
    from quill.core.wordpress import workbench_across as wa
    from quill.core.wordpress import workbench_across_ops as ops
    from quill.core.wordpress import workbench_by_name as bn

    objects = row.raw["objects"]
    variant = next(w for w, sites in row.raw["variants"].items() if winner_site in sites)
    plan = wa.same_everywhere_plan(row, variant)
    edits, refused = ops.make_same_edits(kind, row.key, plan, objects, objects[winner_site])
    H.expect(len(edits) == 1 and not refused, f"edits {[e.line for e in edits]}, refused {refused}")
    target = edits[0].site
    H.expect(target != winner_site, f"the winner {winner_site} would be changed")
    before = value_of(target)
    want = value_of(winner_site)
    outcomes, sent = ops.run_edits_by_site(pair.api, edits)
    H.expect(outcomes and all(o.ok for o in outcomes), "; ".join(o.line for o in outcomes))
    now = value_of(target)
    H.expect(now == want, f"{kind} on {target} is {H.cell(now, 80)!r}, not the winner's")
    H.expect(now != before, f"{kind} on {target} did not change")
    undo = bn.undo_edits(pair.api, sent)
    back = value_of(target)
    H.expect(back == before, f"after undo {kind} on {target} is {H.cell(back, 80)!r}")
    return target, undo


# =========================================================================== #
# 110 to 118


def _make_same(ctx: Any) -> str:
    """A tag (the test site changes), a setting and a synced pattern (the Practice Site changes)."""
    pair = _pair(ctx)
    papi = pair.second_api
    said: list[str] = []

    # A tag on both, with different slugs. The Practice Site's wins, so the
    # test site's "QUILL live test" tag is the one that changes.
    name = ctx.title("make the same, tag")
    slug = _slug(ctx, "same-tag")
    tags = {
        pair.first: _make_first(ctx, pair, "wp/v2/tags", {"name": name, "slug": slug}),
        pair.second: _make(
            ctx, papi, pair.second, "wp/v2/tags", {"name": name, "slug": slug + "-practice"}
        ),
    }
    rows, _u = _gather(pair, "terms", {f"{name} (tag)": tags[pair.first]})
    row = rows.get(f"{name} (tag)")
    H.expect(row is not None and row.cell("versions") == "2", f"the tag reads {row and row.detail}")
    winner = pair.first if pair.alone else pair.second

    def tag_slug(site: str) -> str:
        if not tags[site]["id"]:  # imagined: the Practice Site stands alone
            return str(tags[site]["slug"])
        return str(pair.api(site).get(f"wp/v2/tags/{tags[site]['id']}", context="edit")["slug"])

    target, undo = _same_then_undo(pair, "terms", row, winner, tag_slug)
    said.append(f"tag: {target} took {winner}'s slug; {undo.lower()}")

    # A setting: the Practice Site's tagline, set to something of the run's own
    # first (put back afterwards), is made the test site's.
    settings = papi.get("wp/v2/settings")
    original = settings.get("description", "")
    ctx.later(
        "put back the Practice Site's tagline",
        lambda: papi.post("wp/v2/settings", {"description": original}),
    )
    papi.post("wp/v2/settings", {"description": ctx.title("tagline")})
    imagined = {"description": {"value": ctx.title("the winning tagline")}}
    rows, unread = _gather(pair, "settings", imagined)
    H.expect(not unread, f"settings not read: {unread}")
    row = rows.get("description")
    H.expect(row is not None and row.cell("versions") == "2", f"tagline: {row and row.detail}")

    def tagline(site: str) -> str:
        if pair.alone and site == pair.first:
            return str(imagined["description"]["value"])
        return str(pair.api(site).get("wp/v2/settings").get("description", ""))

    target, undo = _same_then_undo(pair, "settings", row, pair.first, tagline)
    said.append(f"setting: {target}'s tagline took the test site's; {undo.lower()}")

    # A synced pattern on both, with different words; the test site's wins.
    title = ctx.title("make the same, pattern")
    words = {
        pair.first: "QUILL live test: the words on the test site, which win.",
        pair.second: "QUILL live test: the Practice Site's words.",
    }
    patterns = {}
    for site in pair.names:
        body = {
            "title": title,
            "content": f"<!-- wp:paragraph --><p>{words[site]}</p><!-- /wp:paragraph -->",
            "status": "publish",
            "slug": _slug(ctx, "same-pattern"),
        }
        patterns[site] = (
            _make_first(ctx, pair, "wp/v2/blocks", body)
            if site == pair.first
            else _make(ctx, papi, site, "wp/v2/blocks", body)
        )
    first_raw = {
        "id": 0,
        "content": patterns[pair.first]["content"],
        "value": f"{len(patterns[pair.first]['content'])} characters, imagined",
    }
    rows, _u = _gather(pair, "patterns", {title: first_raw})
    row = rows.get(title)
    H.expect(row is not None and row.cell("versions") == "2", f"the pattern: {row and row.detail}")

    def content(site: str) -> str:
        if pair.alone and site == pair.first:
            return str(first_raw["content"])
        raw = pair.api(site).get(f"wp/v2/blocks/{patterns[site]['id']}", context="edit")
        return str(raw["content"]["raw"])

    target, undo = _same_then_undo(pair, "patterns", row, pair.first, content)
    said.append(f"pattern: {target} took the test site's words; {undo.lower()}")
    return "; ".join(said)


def _missing_and_variants(ctx: Any) -> str:
    from quill.core.wordpress import workbench_across as wa
    from quill.core.wordpress import workbench_across_ops as ops

    pair = _pair(ctx)
    papi = pair.second_api
    # Only on the test site: missing from the Practice Site.
    name = ctx.title("missing from")
    slug = _slug(ctx, "missing")
    only = _make_first(ctx, pair, "wp/v2/tags", {"name": name, "slug": slug})
    # On both, two slugs: two variants.
    both = ctx.title("variants")
    vslug = _slug(ctx, "variants")
    _make_first(ctx, pair, "wp/v2/tags", {"name": both, "slug": vslug})
    _make(ctx, papi, pair.second, "wp/v2/tags", {"name": both, "slug": vslug + "-practice"})
    rows, _u = _gather(
        pair,
        "terms",
        {f"{name} (tag)": only, f"{both} (tag)": {"name": both, "slug": vslug, "id": 0}},
    )
    row = rows.get(f"{name} (tag)")
    H.expect(row is not None, f"{name} is not listed")
    H.expect(row.cell("missing") == pair.second, f"missing from {row.cell('missing')!r}")
    H.expect(f"Missing from: {pair.second}" in row.detail, row.detail)
    plan = dict(wa.same_everywhere_plan(row, f"slug {slug}"))
    H.expect(plan[pair.second].startswith("gets"), f"plan: {plan}")
    variants = rows.get(f"{both} (tag)")
    H.expect(variants is not None and variants.cell("versions") == "2", "not two variants")
    H.expect(not variants.cell("missing"), f"missing from {variants.cell('missing')}")
    H.expect(all(site in variants.detail for site in pair.names), f"variants: {variants.detail}")
    # Make Them the Same fills the gap: the tag is made on the Practice Site.
    edits, refused = ops.make_same_edits(
        "terms", row.key, list(plan.items()), row.raw["objects"], only
    )
    H.expect(len(edits) == 1 and edits[0].before is None and not refused, f"{edits} {refused}")
    outcomes, _sent = ops.run_edits_by_site(pair.api, edits)
    H.expect(all(o.ok for o in outcomes), "; ".join(o.line for o in outcomes))
    made = [t for t in papi.get("wp/v2/tags", slug=slug, context="edit") if t["slug"] == slug]
    H.expect(made, "the tag did not arrive on the Practice Site")
    ident = int(made[0]["id"])
    ctx.later(
        f"delete tag {ident} on the Practice Site",
        lambda: _quietly(lambda: papi.delete(f"wp/v2/tags/{ident}", force=True)),
    )
    papi.delete(f"wp/v2/tags/{ident}", force=True)
    rows, _u = _gather(pair, "terms", {f"{name} (tag)": only})
    H.expect(rows[f"{name} (tag)"].cell("missing") == pair.second, "deleting it did not show")
    return (
        f"{H.cell(row.detail, 120)} Made on {pair.second} as missing (made, so no undo), then "
        f"deleted there. {H.cell(variants.detail, 120)}"
    )


def _install_missing(ctx: Any) -> str:
    from quill.core.wordpress import dotorg, site_admin

    pair = _pair(ctx)
    papi = pair.second_api
    if any(p.plugin.startswith(PLUGIN + "/") for p in site_admin.list_plugins(papi)):
        raise H.CheckFailed(f"{PLUGIN} is on the Practice Site before the run; delete it there")
    rows, unread = _gather(pair, "plugins", {})
    H.expect(pair.second not in unread, f"the Practice Site's plugins: {unread.get(pair.second)}")
    gap = [r for r in rows.values() if pair.second in (r.raw.get("missing") or [])]

    def slug_of(row: Any) -> str:
        source = next(iter(row.raw["objects"].values()), {})
        return dotorg.plugin_slug(str(source.get("plugin") or ""))

    ours = next((r for r in gap if slug_of(r) == PLUGIN), None)
    found = (
        f"Across Sites lists {ours.key} as missing from {pair.second}"
        if ours
        else f"{len(gap)} plugins missing from {pair.second}; the test site has no {PLUGIN}, so "
        "it is installed by its WordPress.org name as the command does"
    )

    def remove() -> None:
        for plugin in site_admin.list_plugins(papi):
            if plugin.plugin.startswith(PLUGIN + "/"):
                site_admin.delete_plugin(papi, plugin)

    ctx.later(f"delete {PLUGIN} on the Practice Site", remove)
    # What Install on Sites Missing It sends to each site missing it.
    made = site_admin.install_plugin(papi, PLUGIN)
    H.expect(not made.active, f"{made.name} arrived active")
    listed = [p for p in site_admin.list_plugins(papi) if p.plugin.startswith(PLUGIN + "/")]
    H.expect(listed and not listed[0].active, f"after installing the list has {listed}")
    if ours:
        rows, _u = _gather(pair, "plugins", {})
        now = rows.get(ours.key)
        H.expect(now is not None and not now.cell("missing"), f"{ours.key}: {now and now.detail}")
    remove()
    left = [p.plugin for p in site_admin.list_plugins(papi) if p.plugin.startswith(PLUGIN + "/")]
    H.expect(not left, f"{left} is still there after deleting")
    return f"{found}; installed {made.name} {made.version}, inactive, then deleted"


def _copy_to_practice(ctx: Any) -> str:
    """A post with a picture and links, a page, a menu and a term: test site to Practice Site."""
    from quill.core.wordpress import site_media as sm
    from quill.core.wordpress import workbench_site_copy as sc

    pair = _pair(ctx)
    src, dst = pair.first_api, pair.second_api
    where = pair.first if not pair.alone else pair.second
    base = pair.first_url.rstrip("/")

    picture = sm.upload_media(
        src,
        "quill-live-test.png",
        H.tiny_png(),
        "image/png",
        title=ctx.title("copy, picture"),
        alt_text=f"{H.TAG} picture",
    )
    ctx.later(
        f"delete media {picture.id} on {where}",
        lambda: _quietly(lambda: sm.delete_media(src, picture.id)),
    )
    tag = _make(
        ctx,
        src,
        where,
        "wp/v2/tags",
        {"name": ctx.title("copy, term"), "slug": _slug(ctx, "copy-term")},
    )
    page_slug = _slug(ctx, "copy-page")
    page = _make(
        ctx,
        src,
        where,
        "wp/v2/pages",
        {"title": ctx.title("copy, page"), "slug": page_slug, "status": "draft", "content": "x"},
    )
    post_slug = _slug(ctx, "copy-post")
    content = (
        f'<!-- wp:image --><figure class="wp-block-image"><img src="{picture.source_url}" '
        f'alt="{H.TAG} picture"/></figure><!-- /wp:image -->'
        f'<!-- wp:paragraph --><p>See <a href="{base}/{page_slug}/">the page</a> and '
        f'<a href="{base}/about/">About Us</a>.</p><!-- /wp:paragraph -->'
    )
    post = _make(
        ctx,
        src,
        where,
        "wp/v2/posts",
        {
            "title": ctx.title("copy, post"),
            "slug": post_slug,
            "status": "draft",
            "content": content,
            "tags": [int(tag["id"])],
        },
    )
    menu = _make(ctx, src, where, "wp/v2/menus", {"name": ctx.title("copy, menu")})
    for body in (
        {"title": "The page", "type": "post_type", "object": "page", "object_id": int(page["id"])},
        {"title": "Home", "type": "custom", "url": base + "/"},
    ):
        src.post("wp/v2/menu-items", {**body, "menus": int(menu["id"]), "status": "publish"})

    # Chosen in the worst order -- the menu before the page it links to, the
    # post before its own term -- which Copy to Site must put right itself.
    raws = [
        ("menu", "", src.get(f"wp/v2/menus/{menu['id']}", context="edit")),
        ("item", "post", src.get(f"wp/v2/posts/{post['id']}", context="edit")),
        ("item", "page", src.get(f"wp/v2/pages/{page['id']}", context="edit")),
        ("term", "post_tag", src.get(f"wp/v2/tags/{tag['id']}", context="edit")),
    ]
    if pair.alone:  # copying a site to itself: new addresses and names, so each is made
        raws = [
            (
                k,
                s,
                {
                    **r,
                    "slug": f"{r['slug']}-copy",
                    **({"name": f"{r['name']} copy"} if "name" in r else {}),
                },
            )
            for k, s, r in raws
        ]
    slugs = {sub or kind: raw["slug"] for kind, sub, raw in raws}

    def delete_copies() -> None:
        for route, key in (("wp/v2/posts", "post"), ("wp/v2/pages", "page")):
            for raw in dst.get(route, slug=slugs[key], status="any", context="edit"):
                _quietly(
                    lambda raw=raw, route=route: dst.delete(f"{route}/{raw['id']}", force=True)
                )
        for raw in dst.get("wp/v2/tags", slug=slugs["post_tag"]):
            _quietly(lambda raw=raw: dst.delete(f"wp/v2/tags/{raw['id']}", force=True))
        for raw in dst.get("wp/v2/menus", context="edit", per_page=100):
            if raw.get("slug") == slugs["menu"]:
                _quietly(lambda raw=raw: dst.delete(f"wp/v2/menus/{raw['id']}", force=True))
        for raw in _run_media(dst):
            if pair.alone and int(raw["id"]) == picture.id:
                continue
            _quietly(lambda raw=raw: dst.delete(f"wp/v2/media/{raw['id']}", force=True))

    ctx.later("delete the copies on the Practice Site", delete_copies)
    plan = sc.plan_copy(
        dst, raws, source_site=pair.first, target_site=pair.second, source_url=base, source=src
    )
    actions = [line.action for line in plan.lines]
    H.expect(actions == ["create"] * 4, f"the plan reads {[line.sentence for line in plan.lines]}")
    H.expect(
        picture.source_url in plan.pictures, f"the picture is not in the plan: {plan.pictures}"
    )
    failed = sc.run_copy(
        src,
        dst,
        plan,
        source_url=base,
        target_url=pair.second_url,
        fetch=lambda url: sc.fetch_site_file(src, url),
    )
    H.expect(not failed, "; ".join(failed))
    kinds = [o.split(" ", 2)[1] for o in plan.outcomes]
    H.expect(kinds == ["term", "item", "item", "menu"], f"copied in the order {kinds}")

    copied = dst.get("wp/v2/posts", slug=slugs["post"], status="any", context="edit")
    H.expect(copied and copied[0]["status"] == "draft", f"the post: {copied[:1]}")
    text = copied[0]["content"]["raw"]
    images = re.findall(r'<img[^>]+src="([^"]+)"', text)
    H.expect(images and images[0] != picture.source_url, f"the picture is still {images}")
    H.expect(images[0].startswith(pair.second_url), f"the picture points at {images[0]}")
    if not pair.alone:
        H.expect(base not in text, "a link still points at the test site")
        H.expect(
            f'{pair.second_url}/about/"' in text, "About Us is not pointed at the Practice Site"
        )
    term = dst.get("wp/v2/tags", slug=slugs["post_tag"])
    H.expect(term, "the term did not arrive")
    # Copied to itself, the post keeps the tag it had (found there by name).
    want_tag = int(tag["id"]) if pair.alone else int(term[0]["id"])
    H.expect(copied[0]["tags"] == [want_tag], f"the post's tags are {copied[0]['tags']}")
    pages = dst.get("wp/v2/pages", slug=slugs["page"], status="any", context="edit")
    H.expect(pages and pages[0]["status"] == "draft", f"the page: {pages[:1]}")
    menus = [
        m
        for m in dst.get("wp/v2/menus", context="edit", per_page=100)
        if m.get("slug") == slugs["menu"]
    ]
    H.expect(menus, "the menu did not arrive")
    items = dst.get("wp/v2/menu-items", menus=int(menus[0]["id"]), context="edit")
    linked = [i for i in items if i.get("type") == "post_type"]
    H.expect(len(items) == 2, f"the menu has {len(items)} items")
    # The page link is matched by address: the copied page, or (copied to
    # itself) the page it already links to.
    want_page = int(page["id"]) if pair.alone else int(pages[0]["id"])
    H.expect(linked and int(linked[0]["object_id"]) == want_page, f"the page link: {linked[:1]}")
    custom = [i for i in items if i.get("type") == "custom"]
    H.expect(
        custom and custom[0]["url"].startswith(pair.second_url), f"the menu link: {custom[:1]}"
    )
    delete_copies()
    H.expect(
        not dst.get("wp/v2/posts", slug=slugs["post"], status="any", context="edit"),
        "the copied post is still on the Practice Site",
    )
    done = " ".join(plan.outcomes)
    return f"{done} Picture re-hosted, links pointed at {pair.second}; deleted there."


def _compare_sites(ctx: Any) -> str:
    from quill.core.wordpress import workbench_snapshot as snap

    pair = _pair(ctx)
    found = snap.compare_sites(
        pair.first_api,
        pair.second_api,
        first_name=pair.first,
        second_name=pair.second,
        kinds=("post", "page", "pattern", "category", "tag"),
    )
    unread = [d for d in found if d.words.startswith("not compared")]
    H.expect(not unread, "; ".join(d.words for d in unread))
    if pair.alone:
        H.expect(not found, f"a site differs from itself: {[d.words for d in found[:3]]}")
        return "the Practice Site compared with itself: no differences"
    words = {(d.kind, d.slug): d.words for d in found}
    H.expect(
        words.get(("page", "about")) == f"only on {pair.first}", "About Us is not test-site-only"
    )
    welcome = ("page", "welcome-to-your-practice-site")
    H.expect(words.get(welcome) == f"only on {pair.second}", "the Practice Site's welcome page")
    only_first = sum(1 for d in found if d.words == f"only on {pair.first}")
    only_second = sum(1 for d in found if d.words == f"only on {pair.second}")
    differ = len(found) - only_first - only_second
    return (
        f"{only_first} only on the test site, {only_second} only on the Practice Site, "
        f"{differ} differ"
    )


def _compare_styles(ctx: Any) -> str:
    from quill.core.wordpress import workbench_across_ops as ops

    pair = _pair(ctx)
    per = {site: ops.site_styles(pair.api(site)) for site in pair.names}
    H.expect(isinstance(per[pair.second], dict), f"the Practice Site's styles: {per[pair.second]}")
    summary, lines = ops.compare_styles(per)
    readable = sum(1 for v in per.values() if isinstance(v, dict))
    H.expect(f"across {readable} sites" in summary, summary)
    if pair.alone:
        H.expect(summary.startswith("0 of"), f"a site differs from itself: {summary}")
    networks = {site: ops.network_status(pair.api(site)) for site in pair.names}
    H.expect(not any(networks.values()), f"a single site reads as a network: {networks}")
    first = lines[0] if lines else "nothing differs"
    return f"{summary} First line: {H.cell(first, 120)}"


def _revoke_everywhere(ctx: Any) -> str:
    from quill.core.wordpress import workbench_across_ops as ops
    from quill.core.wordpress.api import SiteAddress, SiteAuth, WordPressApi

    pair = _pair(ctx)
    papi = pair.second_api
    user = ctx.second.username
    name = ctx.title("throwaway password")
    made = papi.post("wp/v2/users/me/application-passwords", {"name": name})
    uuid = str(made["uuid"])
    ctx.secrets += H.secret_forms(user, str(made["password"]))
    route = f"wp/v2/users/me/application-passwords/{uuid}"
    ctx.later("revoke the throwaway password", lambda: _quietly(lambda: papi.delete(route)))
    throwaway = WordPressApi(
        SiteAddress(pair.second_url),
        SiteAuth("app_password", user, str(made.pop("password"))),
        site_name=f"{PRACTICE}, throwaway password",
        timeout=90.0,
    )
    del made
    H.expect(throwaway.get("wp/v2/users/me").get("id"), "the throwaway password did not sign in")
    rows, _u = _gather(pair, "app_passwords", {})
    key = f"{name}, you"
    row = rows.get(key)
    H.expect(row is not None, f"{key} is not listed")
    H.expect(set(row.raw["objects"]) == {pair.second}, f"it is on {sorted(row.raw['objects'])}")
    if not pair.alone:
        H.expect(row.cell("missing") == pair.first, f"missing from {row.cell('missing')!r}")
    plan, refused = ops.revoke_plan(key, row.raw["objects"], {})
    H.expect(plan == [(pair.second, route)] and not refused, f"plan {plan}, refused {refused}")
    for site, where in plan:  # what Revoke Everywhere sends, site by site
        pair.api(site).delete(where)
    error = H.refused(lambda: throwaway.get("wp/v2/users/me"))
    H.expect(error.status == 401, f"after revoking it answered {error.status}")
    rows, _u = _gather(pair, "app_passwords", {})
    H.expect(key not in rows, "still listed after revoking")
    return (
        f"made on {pair.second} only, signed in with it, revoked by the plan; "
        f"then {error.status} ({error.plain})"
    )


def _by_name_both(ctx: Any) -> str:
    from quill.core.wordpress import workbench_across as wa
    from quill.core.wordpress import workbench_across_ops as ops
    from quill.core.wordpress import workbench_by_name as bn

    pair = _pair(ctx)
    name = ctx.title("by name, both sites")
    renamed = ctx.title("by name, both sites, renamed")
    ids: dict[str, int] = {}
    for site, api in pair.reading:
        tag = _make(
            ctx, api, site, "wp/v2/tags", {"name": name, "slug": _slug(ctx, "by-name-both")}
        )
        ids[site] = int(tag["id"])
        _make(
            ctx,
            api,
            site,
            "wp/v2/posts",
            {
                "title": ctx.title("by name, both sites, post"),
                "slug": _slug(ctx, "by-name-both-post"),
                "status": "draft",
                "tags": [ids[site]],
            },
        )
    edits = []
    uses = []
    for site, api in pair.reading:
        scan = wa.scan_site(api, site, pages=3)
        key = f"post_tag:{ids[site]}"
        found = bn.term_uses(scan, key)
        H.expect(len(found) == 1, f"{site}: the tag is used {len(found)} times")
        uses.append(f"{site} 1")
        edits += bn.plan_term_rename(scan, key, renamed, "")
    H.expect(len(edits) == len(pair.reading), f"{len(edits)} renames planned")
    outcomes, sent = ops.run_edits_by_site(pair.api, edits)
    H.expect(all(o.ok for o in outcomes), "; ".join(o.line for o in outcomes))

    def names() -> set[str]:
        return {
            str(api.get(f"wp/v2/tags/{ids[site]}", context="edit")["name"])
            for site, api in pair.reading
        }

    H.expect(names() == {renamed}, f"after renaming: {names()}")
    undo = bn.undo_edits(pair.api, sent)
    H.expect(names() == {name}, f"after undo: {names()}")
    return f"used on {', '.join(uses)}; renamed on {len(sent)} sites at once; {undo.lower()}"


def _fleet(ctx: Any) -> str:
    from quill.core.wordpress import workbench_fleet as fleet
    from quill.core.wordpress import workbench_practice as wp_p
    from quill.core.wordpress.site import load_site_info

    pair = _pair(ctx)
    second = ctx.second

    def read(sites: list[tuple[str, Any]]) -> dict[str, dict[str, Any]]:
        latest: dict[str, dict[str, Any]] = {}
        for site, api in sites:  # as the Workbench's Fleet reads each site
            try:
                info = load_site_info(api)
                latest[site] = fleet.fleet_fact(api, info.wp_version, info.namespaces)
            except Exception as exc:  # noqa: BLE001 - the row says the site did not answer
                latest[site] = {"error": getattr(exc, "plain", "") or str(exc)}
        return latest

    kept = fleet.merge_fleet({}, read(pair.reading))
    for site, fact in kept.items():
        H.expect(not fact.get("error"), f"{site}: {fact.get('error')}")
        H.expect(
            fact["health"] in ("good", "should be improved", "critical"),
            f"{site} health: {fact['health']}",
        )
    fresh = "; ".join(f"{s} health {f['health']}" for s, f in kept.items())
    if not second.started_here or second.process is None:
        raise H.NotRun(
            f"read fresh ({fresh}); the Practice Site was running before the run, so the "
            "run does not stop it"
        )
    wp_p.stop_process(second.process)
    second.process = None
    try:
        merged = fleet.merge_fleet(kept, read(pair.reading))
        H.expect(merged[pair.second].get("stale"), f"the stopped site: {merged[pair.second]}")
        rows = {r.site: r for r in fleet.fleet_rows(list(merged.items()))}
        stale = rows[pair.second].detail
        H.expect("stale, as read" in stale, f"the stopped site's row: {stale}")
        if not pair.alone:
            H.expect("stale" not in rows[pair.first].detail, "the test site reads as stale")
    finally:
        second.process = _start(second.folder)  # the clean-up still needs it
    H.expect(second.api.get("wp/v2/users/me").get("id"), "the Practice Site did not come back")
    return f"{fresh}. Stopped: {H.cell(stale, 160)} Started again for the clean-up."


# =========================================================================== #
# The list, in order: (test, name, function, writes)

_TESTS: tuple[tuple[str, str, Any, bool], ...] = (
    ("110", "Make Them the Same, two sites: a tag, a setting, a pattern; undo", _make_same, True),
    ("111", "Missing From and Variants, two sites; the gap filled", _missing_and_variants, True),
    ("112", f"Install on Sites Missing It: {PLUGIN} on the Practice Site", _install_missing, True),
    ("113", "Copy to Site: post, picture, links, page, menu, term", _copy_to_practice, True),
    ("114", "Compare Sites: the test site and the Practice Site", _compare_sites, False),
    ("115", "Compare Global Styles across two sites", _compare_styles, False),
    ("116", "Revoke Everywhere: a throwaway Practice Site password", _revoke_everywhere, True),
    ("117", "By Name across both sites: rename a tag, undo", _by_name_both, True),
    ("118", "Fleet: the Practice Site stopped reads as stale", _fleet, False),
)
