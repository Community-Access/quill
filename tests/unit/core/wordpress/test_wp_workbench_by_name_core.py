"""By Name operations, Across Sites operations, the Fleet's states, and the scope matrix (15.12)."""

from __future__ import annotations

from typing import Any

import pytest

from quill.core.wordpress import workbench_across_ops as ops
from quill.core.wordpress import workbench_by_name as bn
from quill.core.wordpress.api import WordPressApiError
from quill.core.wordpress.workbench_across import (
    SiteScan,
    across_rows,
    kind_rows,
    same_everywhere_plan,
    scan_site,
)
from quill.core.wordpress.workbench_fleet import fleet_fact, fleet_rows, merge_fleet
from quill.core.wordpress.workbench_scope_matrix import (
    ACROSS_MATRIX_KINDS,
    ACROSS_OPS,
    BY_NAME_KINDS,
    BY_NAME_OPS,
    SCOPES,
    classify,
    matrix,
)


class Api:
    """Answers reads from a table; records every write; can fail a route."""

    def __init__(self, reads: dict[str, Any] | None = None) -> None:
        self.reads = reads or {}
        self.writes: list[tuple[str, str, Any]] = []
        self.fail: dict[str, int] = {}
        self.made = 100

    def _check(self, route: str) -> None:
        if route in self.fail:
            raise WordPressApiError("refused", status=self.fail[route])

    def get(self, route: str, **_params: Any) -> Any:
        self._check(route)
        return self.reads.get(route, {})

    def iter_collection(self, route: str, params: Any = None, **_kw: Any):
        self._check(route)
        yield from self.reads.get(route, [])

    def post(self, route: str, body: Any = None, **_params: Any) -> Any:
        self._check(route)
        self.writes.append(("POST", route, body))
        self.made += 1
        return {"id": self.made, **(body or {})}

    def delete(self, route: str, **params: Any) -> Any:
        self.writes.append(("DELETE", route, params))
        return {}

    def request(self, method: str, route: str, **_kw: Any) -> Any:
        class _R:
            payload = self.reads.get(f"{method} {route}", {})

        return _R()


def _scan() -> SiteScan:
    scan = SiteScan("Radio")
    scan.term_bases = {"category": "categories", "post_tag": "tags", "genre": "genres"}
    scan.items = [
        {
            "id": 1,
            "type": "post",
            "title": {"raw": "One"},
            "content": {
                "raw": '<a href="https://old.example">x</a> [gallery ids="1"][/gallery]'
                '<!-- wp:block {"ref":7} /--><!-- wp:qaf/form {"formId":4} /-->'
                '<img src="https://r.example/up/logo.png">'
            },
            "author": 3,
            "meta": {"venue": "Main Hall"},
            "categories": [5, 6],
            "genres": [9],
            "featured_media": 10,
            "modified_gmt": "2026-11-01T00:00:00",
        },
        {
            "id": 2,
            "type": "page",
            "title": {"raw": "Two"},
            "content": {"raw": "plain"},
            "author": 3,
            "meta": {"venue": "Main Hall"},
            "categories": [5],
            "modified_gmt": "2026-11-02T00:00:00",
        },
        {
            "id": 3,
            "type": "post",
            "title": {"raw": "Three"},
            "content": {"raw": ""},
            "author": 4,
            "meta": {},
            "modified_gmt": "x",
        },
    ]
    scan.terms = [
        ("category", {"id": 5, "name": "News", "slug": "news", "count": 2}),
        ("category", {"id": 6, "name": "Shows", "slug": "shows", "count": 1}),
        ("genre", {"id": 9, "name": "Jazz", "slug": "jazz", "count": 1}),
    ]
    scan.media = [
        {"id": 10, "source_url": "https://r.example/up/logo.png"},
        {"id": 11, "source_url": "https://r.example/up/new.png"},
    ]
    scan.users = {3: "Sam", 4: "Ann"}
    scan.patterns = {7: "Footer", 8: "Footer 2"}
    return scan


# -- By Name ------------------------------------------------------------------------


def test_the_scan_reads_custom_taxonomies_and_term_rows_say_where_used() -> None:
    api = Api({
        "wp/v2/taxonomies": {
            "genre": {"rest_base": "genres", "types": ["post"]},
            "kind": {"rest_base": "kinds", "types": ["event"]},
        },
        "wp/v2/genres": [{"id": 9, "name": "Jazz", "count": 1}],
        "wp/v2/posts": [{"id": 1, "title": {"raw": "One"}, "genres": [9]}],
    })
    scan = scan_site(api, "Radio")
    assert scan.term_bases == {"category": "categories", "post_tag": "tags", "genre": "genres"}
    row = next(r for r in kind_rows(scan, "terms") if r.key == "genre:9")
    assert row.cell("value") == "Jazz (genre)" and row.raw["places"] == ["One"]


def test_a_term_is_renamed_and_its_items_found_in_every_taxonomy() -> None:
    scan = _scan()
    assert [bn._title(r) for r in bn.term_uses(scan, "category:5")] == ["One", "Two"]
    assert [bn._title(r) for r in bn.term_uses(scan, "genre:9")] == ["One"]
    (edit,) = bn.plan_term_rename(scan, "category:5", "Updates", "updates")
    assert edit.route == "wp/v2/categories/5"
    assert edit.body == {"name": "Updates", "slug": "updates"}
    assert edit.before == {"name": "News", "slug": "news"}
    assert edit.stamp_field == "name" and edit.stamp == "News"


def test_reassign_merge_and_split_move_items_between_terms() -> None:
    scan = _scan()
    edits = bn.plan_term_move(scan, "category:5", 6, "Shows")
    assert [(e.route, e.body, e.before) for e in edits] == [
        ("wp/v2/posts/1", {"categories": [6]}, {"categories": [5, 6]}),
        ("wp/v2/pages/2", {"categories": [6]}, {"categories": [5]}),
    ]
    api = Api()
    new_id, split = bn.split_term(api, scan, "category:5", "Archive", [2])
    assert api.writes[0] == ("POST", "wp/v2/categories", {"name": "Archive"})
    assert [(e.route, e.body) for e in split] == [("wp/v2/pages/2", {"categories": [new_id]})]


def test_field_values_change_everywhere_or_on_chosen_items_and_missing_ones_are_found() -> None:
    scan = _scan()
    edits = bn.plan_field(scan, "venue: Main Hall", "Studio")
    assert [e.body for e in edits] == [{"meta": {"venue": "Studio"}}] * 2
    assert edits[0].before == {"meta": {"venue": "Main Hall"}}
    assert [e.route for e in bn.plan_field(scan, "venue: Main Hall", "Studio", [2])] == [
        "wp/v2/pages/2"
    ]
    assert bn.items_missing_field(scan, "venue") == ["Three"]


def test_authors_are_reassigned_wholly_or_in_part() -> None:
    scan = _scan()
    edits = bn.plan_author(scan, 3, 4)
    assert [(e.route, e.body, e.before) for e in edits] == [
        ("wp/v2/posts/1", {"author": 4}, {"author": 3}),
        ("wp/v2/pages/2", {"author": 4}, {"author": 3}),
    ]
    assert len(bn.plan_author(scan, 3, 4, [1])) == 1
    assert "from Sam to Ann" in edits[0].words


@pytest.mark.parametrize(
    ("kind", "old", "new", "expect"),
    [
        ("links", "https://old.example", "https://new.example", "https://new.example"),
        ("patterns", "Footer", "Footer 2", '"ref":8'),
        ("forms", "Form 4", "Form 7", '"formId":7'),
        ("blocks", "[gallery] shortcode", "slider", '[slider ids="1"][/slider]'),
        ("media_usage", "logo.png", "new.png", "https://r.example/up/new.png"),
    ],
)
def test_replace_rewrites_the_content_of_every_item_using_it(kind, old, new, expect) -> None:
    edits, reason = bn.plan_replace(_scan(), kind, old, new)
    assert reason == "" and len(edits) == 1
    assert expect in edits[0].body["content"] and old not in edits[0].body["content"].replace(
        "Footer 2", ""
    )
    assert edits[0].before is not None and "content" in edits[0].before
    if kind == "media_usage":
        assert edits[0].body["featured_media"] == 11


def test_a_block_is_not_rewritten_by_name_and_says_why() -> None:
    edits, reason = bn.plan_replace(_scan(), "blocks", "paragraph block", "heading")
    assert edits == [] and "markup" in reason


def test_a_conflict_leaves_the_item_alone_and_undo_puts_back_what_was_sent() -> None:
    scan = _scan()
    api = Api({
        "wp/v2/posts/1": {"modified_gmt": "2026-11-01T00:00:00"},
        "wp/v2/pages/2": {"modified_gmt": "changed by someone"},
    })
    outcomes, sent = bn.apply_edits(api, bn.plan_author(scan, 3, 4))
    assert [o.ok for o in outcomes] == [True, False]
    assert "changed on the site since QUILL read it" in outcomes[1].words
    assert [w[1] for w in api.writes] == ["wp/v2/posts/1"]
    said = bn.undo_edits(lambda _s: api, sent)
    assert api.writes[-1] == ("POST", "wp/v2/posts/1", {"author": 3})
    assert said == "Put 1 back as they were."
    summary, report = bn.outcome_report(outcomes)
    assert summary.startswith("1 of 2 changed. 1 not: Radio: Two:")
    assert report.splitlines()[0].startswith("Done. Radio: One")


def test_a_refusal_from_the_site_is_that_items_outcome() -> None:
    api = Api({"wp/v2/posts/1": {"modified_gmt": "2026-11-01T00:00:00"}})
    api.fail["wp/v2/pages/2"] = 403
    outcomes, sent = bn.apply_edits(api, bn.plan_author(_scan(), 3, 4))
    assert [o.ok for o in outcomes] == [True, False] and len(sent) == 1


# -- Across Sites -------------------------------------------------------------------


def _row(kind: str, found: dict[str, dict[str, Any]], every: list[str]):
    return across_rows(kind, found, every)[0]


def test_make_them_the_same_for_people_changes_roles_and_says_who_is_missing() -> None:
    row = _row(
        "users",
        {"sam@x": {"A": {"id": 3, "roles": ["editor"]}, "B": {"id": 8, "roles": ["author"]}}},
        ["A", "B", "C"],
    )
    plan = same_everywhere_plan(row, "editor")
    edits, refused = ops.make_same_edits(
        "users", "sam@x", plan, row.raw["objects"], row.raw["objects"]["A"]
    )
    assert [(e.site, e.route, e.body, e.before) for e in edits] == [
        ("B", "wp/v2/users/8", {"roles": ["editor"]}, {"roles": ["author"]})
    ]
    assert refused[0].site == "C" and "email and a password" in refused[0].words


def test_make_them_the_same_for_terms_plugins_settings_and_patterns() -> None:
    plan = [("A", "already matches"), ("B", "changes"), ("C", "gets it")]
    objects = {"B": {"id": 2, "slug": "events-2", "name": "Events"}}
    edits, _ = ops.make_same_edits(
        "terms", "Events (category)", plan, objects, {"name": "Events", "slug": "events"}
    )
    assert [(e.site, e.route, e.before is None) for e in edits] == [
        ("B", "wp/v2/categories/2", False),
        ("C", "wp/v2/categories", True),
    ]
    edits, refused = ops.make_same_edits(
        "plugins",
        "Yoast",
        plan,
        {"B": {"plugin": "y/y", "status": "inactive"}},
        {"status": "active"},
    )
    assert edits[0].body == {"status": "active"} and edits[0].before == {"status": "inactive"}
    assert "Install on Sites Missing It" in refused[0].words
    edits, _ = ops.make_same_edits(
        "settings", "timezone", plan[:2], {"B": {"value": "UTC"}}, {"value": "Europe/London"}
    )
    assert edits[0].body == {"timezone": "Europe/London"} and edits[0].before == {"timezone": "UTC"}
    edits, _ = ops.make_same_edits(
        "patterns", "Footer", plan, {"B": {"id": 4, "content": "old"}}, {"content": "new"}
    )
    assert [(e.route, e.body.get("content")) for e in edits] == [
        ("wp/v2/blocks/4", "new"),
        ("wp/v2/blocks", "new"),
    ]


def test_themes_open_wp_admin_because_rest_cannot_activate_them() -> None:
    open_on, refused = ops.theme_screens(
        [("A", "already"), ("B", "changes"), ("C", "gets")], {"B": {}}, "twentyfive"
    )
    assert open_on == ["B"] and "Install on Sites Missing It" in refused[0].words


def test_menus_are_gathered_by_name_and_copied_as_links_to_each_site() -> None:
    class Address:
        site_url = "https://a.example"

    source = Api({
        "wp/v2/menus": [{"id": 2, "name": "Footer"}],
        "wp/v2/menu-items": [
            {
                "id": 21,
                "title": {"raw": "About"},
                "url": "https://a.example/about/",
                "menu_order": 1,
            },
            {
                "id": 22,
                "title": {"raw": "Team"},
                "url": "https://a.example/about/team/",
                "menu_order": 2,
                "parent": 21,
            },
        ],
    })
    source.address = Address()  # type: ignore[attr-defined]
    found = ops.gather_more("menus", "A", source)
    winner = found["Footer"]
    assert winner["value"] == "2 items: About, Team"
    target = Api()
    outcome = ops.menu_copy(
        target, "B", "Footer", winner, {"id": 5, "items": [{"id": 51}]}, "https://b.example/blog"
    )
    assert outcome.ok and target.writes[0] == ("DELETE", "wp/v2/menu-items/51", {"force": True})
    made = [w[2] for w in target.writes if w[0] == "POST"]
    assert made[0]["url"] == "https://b.example/blog/about/" and made[0]["menus"] == 5
    assert made[1]["parent"] == 101  # the copy of About on the target
    assert ops.rehost("https://elsewhere.org/x", "https://a.example", "https://b.example") == (
        "https://elsewhere.org/x"
    )


def test_global_styles_are_compared_site_by_site() -> None:
    summary, lines = ops.compare_styles({
        "A": {"Theme": "TT5", "Colour Base": "#fff", "Font size Small": "13px"},
        "B": {"Theme": "TT5", "Colour Base": "#000", "Font size Small": "13px"},
        "C": "its active theme does not use global styles",
    })
    assert summary == "1 of 3 styles differ across 2 sites; 2 are the same."
    assert lines == [
        "C: its active theme does not use global styles",
        "Colour Base: A #fff; B #000",
    ]


def test_promote_to_network_only_where_the_plugin_schema_offers_network_active() -> None:
    multi = Api({
        "OPTIONS wp/v2/plugins": {
            "schema": {"properties": {"status": {"enum": ["inactive", "active", "network-active"]}}}
        }
    })
    single = Api({
        "OPTIONS wp/v2/plugins": {"schema": {"properties": {"status": {"enum": ["active"]}}}}
    })
    assert ops.network_status(multi) and not ops.network_status(single)
    assert "not a multisite network" in ops.network_refusal("A", False, True)
    assert "super admin" in ops.network_refusal("A", True, False)
    assert ops.network_refusal("A", True, True) == ""


def test_edits_run_site_by_site_and_one_site_failing_does_not_stop_the_rest() -> None:
    good, bad = Api(), Api()
    bad.fail["wp/v2/settings"] = 500
    edits = [
        bn.Edit("A", "wp/v2/settings", "x", {"x": 1}, {"x": 0}),
        bn.Edit("B", "wp/v2/settings", "x", {"x": 1}, {"x": 0}),
    ]
    outcomes, sent = ops.run_edits_by_site(lambda s: good if s == "A" else bad, edits)
    assert [o.ok for o in outcomes] == [True, False] and [e.site for e in sent] == ["A"]


# -- the Fleet ----------------------------------------------------------------------


def test_the_fleet_keeps_unavailable_unknown_and_stale_states_per_site() -> None:
    api = Api({
        "wp/v2/comments": [{"id": 1}],
        "wp-site-health/v1/tests/https-status": {"status": "critical"},
        "wp-site-health/v1/tests/background-updates": {"status": "good"},
    })
    fact = fleet_fact(api, "6.9", ["wp/v2", "wp-site-health/v1", "updraftplus/v1"], now=1000.0)
    assert fact["health"] == "critical" and fact["waiting"] == 1
    assert fact["backups"].startswith("unknown: updraftplus/v1 is on the site")
    assert fact["security"] == "unavailable: WordPress has no security API"
    assert fact["updates"].startswith("unavailable:")
    assert fleet_fact(Api(), "6.9", ["wp/v2"])["health"].startswith("unavailable: this site has")
    locked = Api()
    locked.fail["wp-site-health/v1/tests/background-updates"] = 403
    assert "administrator" in fleet_fact(locked, "6.9", ["wp-site-health/v1"])["health"]
    merged = merge_fleet({"A": fact}, {"A": {"error": "timed out"}, "B": {"error": "no"}})
    assert merged["A"]["stale"] == "timed out" and merged["B"] == {"error": "no"}
    rows = fleet_rows(list(merged.items()), now=1000.0 + 600)
    assert rows[0].cell("state").startswith("stale, as read 10 minutes ago; not answering now")
    assert rows[0].cell("health") == "critical"
    assert rows[1].cell("backups") == "unknown: the site did not answer"


# -- kind x scope x operation -------------------------------------------------------


def test_every_kind_scope_and_operation_is_classified_with_a_reason() -> None:
    cells = matrix()
    by_name = len(BY_NAME_KINDS) * len(SCOPES) * len(BY_NAME_OPS)
    across = len(ACROSS_MATRIX_KINDS) * len(SCOPES) * len(ACROSS_OPS)
    assert len(cells) == by_name + across
    for key, cell in cells.items():
        assert cell.reason.strip().endswith("."), key
        assert bool(cell.handler) == cell.supported, key


@pytest.mark.parametrize(
    ("cell", "supported", "words"),
    [
        (("by_name", "terms", "site", "split"), True, "new term"),
        (("by_name", "terms", "all_sites", "rename"), False, "inside one site"),
        (("by_name", "authors", "site", "merge"), False, "deleted"),
        (("by_name", "blocks", "site", "replace"), True, "Shortcodes only"),
        (("across", "themes", "all_sites", "make_same"), True, "cannot activate"),
        (("across", "themes", "site_set", "compare_styles"), True, "font sizes"),
        (("across", "plugins", "network", "promote_network"), True, "super admin"),
        (("across", "plugins", "all_sites", "promote_network"), False, "network scope"),
        (("across", "plugins", "all_sites", "update"), False, "cannot run updates"),
        (("across", "users", "all_sites", "fill_missing"), False, "password"),
        (("across", "menus", "site_set", "make_same"), True, "final"),
        (("across", "terms", "site", "variants"), False, "two or more sites"),
        (("across", "terms", "network", "make_same"), False, "no network-wide form"),
        (("across", "redirects", "all_sites", "variants"), False, "Redirection"),
        (("across", "spam_senders", "all_sites", "remove"), False, "disallowed_keys"),
        (("across", "fleet", "all_sites", "variants"), True, "health"),
    ],
)
def test_the_decided_cells(cell, supported, words) -> None:
    got = classify(*cell)
    assert got.supported is supported and words in got.reason


# -- the two leftovers: template parts and application passwords --------------------


def test_template_parts_are_listed_with_their_uses_and_renamed_by_title_only() -> None:
    scan = _scan()
    scan.template_parts = [
        {"id": "tt5//header", "slug": "header", "title": {"raw": "Header"}, "area": "header"},
        {"id": "tt5//spare", "slug": "spare", "title": {"raw": "Spare"}},
    ]
    scan.templates = [
        {
            "title": {"raw": "Home"},
            "content": {"raw": '<!-- wp:template-part {"slug":"header"} /-->'},
        }
    ]
    rows = {r.key: r for r in kind_rows(scan, "template_parts")}
    assert rows["tt5//header"].cell("used") == "used by 1 templates and pages, header area"
    assert rows["tt5//header"].raw["places"] == ["template Home"]
    assert rows["tt5//spare"].cell("used") == "not placed"
    (edit,) = bn.plan_part_rename(scan, "tt5//header", "Site Header")
    assert edit.route == "wp/v2/template-parts/tt5//header"
    assert edit.body == {"title": "Site Header"} and edit.before == {"title": "Header"}
    assert "slug header stays" in edit.words
    assert bn.plan_part_rename(scan, "nope", "x") == []


def test_application_passwords_are_gathered_for_you_and_whom_you_may_edit() -> None:
    api = Api({
        "wp/v2/users/me/application-passwords": [{"uuid": "u1", "name": "Phone"}],
        "wp/v2/users/me": {"id": 3},
        "wp/v2/users": [
            {"id": 3, "username": "jeff"},
            {"id": 4, "username": "ann"},
            {"id": 5, "username": "bob"},
        ],
        "wp/v2/users/4/application-passwords": [
            {"uuid": "u2", "name": "Phone", "last_used": "2026-11-01T00:00:00"}
        ],
    })
    api.fail["wp/v2/users/5/application-passwords"] = 403
    found = ops.gather_more("app_passwords", "A", api)
    assert set(found) == {"Phone, you", "Phone, ann"}
    assert found["Phone, you"]["route"] == "wp/v2/users/me/application-passwords/u1"
    assert found["Phone, ann"]["value"] == "last used 2026-11-01"
    plan, refused = ops.revoke_plan(
        "Phone, ann", {"A": found["Phone, ann"], "B": {"route": "r"}}, {"B": "needs edit_users."}
    )
    assert plan == [("A", "wp/v2/users/4/application-passwords/u2")]
    assert refused[0].site == "B" and refused[0].words == "needs edit_users."


@pytest.mark.parametrize(
    ("cell", "supported", "words"),
    [
        (("by_name", "template_parts", "site", "rename"), True, "slug stays"),
        (("by_name", "template_parts", "site", "replace"), False, "by slug"),
        (("across", "app_passwords", "all_sites", "remove"), True, "no undo"),
        (("across", "app_passwords", "site_set", "make_same"), False, "shown once"),
    ],
)
def test_the_leftover_cells(cell, supported, words) -> None:
    got = classify(*cell)
    assert got.supported is supported and words in got.reason
