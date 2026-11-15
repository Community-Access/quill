"""Shortcodes to blocks, synced patterns, a plugin's blocks, and the six Across Sites kinds.

WP-R-043 and WP-R-044 (PRD 15.12): every operation planned from fake answers,
with no site and no network.
"""

from __future__ import annotations

from typing import Any

from quill.core.wordpress import workbench_across_more as more
from quill.core.wordpress import workbench_across_ops as ops
from quill.core.wordpress import workbench_by_name_blocks as bb
from quill.core.wordpress.workbench_across import (
    SiteScan,
    across_rows,
    gather_across,
    same_everywhere_plan,
)
from tests.unit.core.wordpress.test_wp_workbench_by_name_core import Api


def _scan() -> SiteScan:
    scan = SiteScan("Radio")
    scan.items = [
        {
            "id": 1,
            "type": "post",
            "title": {"raw": "Pictures"},
            "content": {
                "raw": '<!-- wp:shortcode -->\n[gallery ids="10,11" columns="2" link="file"]\n'
                "<!-- /wp:shortcode -->\n"
                '[caption id="attachment_10" align="alignright" width="300"]'
                '<a href="https://r.example/up/a.jpg"><img src="https://r.example/up/a.jpg" '
                'alt="A tower" /></a> The tower[/caption]'
            },
            "modified_gmt": "2026-11-01T00:00:00",
        },
        {
            "id": 2,
            "type": "page",
            "title": {"raw": "Sounds"},
            "content": {
                "raw": '[audio mp3="https://r.example/up/a.mp3"] [audio] [playlist ids="3"]'
                '<!-- wp:block {"ref":7} /--><!-- wp:jetpack/slideshow {"ids":[1]} /-->'
            },
            "modified_gmt": "2026-11-02T00:00:00",
        },
        {
            "id": 3,
            "type": "post",
            "title": {"raw": "Watch"},
            "content": {
                "raw": '[video mp4="https://r.example/v.mp4" poster="https://r.example/p.jpg"]'
                "[embed]https://video.example/watch?v=1[/embed]"
                '<!-- wp:block {"ref":7} /--><!-- wp:jetpack/map /-->'
            },
            "modified_gmt": "2026-11-03T00:00:00",
        },
    ]
    scan.media = [
        {"id": 10, "source_url": "https://r.example/up/a.jpg", "alt_text": "A tower"},
        {"id": 11, "source_url": "https://r.example/up/b.jpg", "alt_text": "B & C"},
    ]
    scan.patterns = {7: "Footer"}
    return scan


# -- WP-R-043: shortcodes, patterns, a plugin's blocks ----------------------------------


def test_a_gallery_becomes_a_gallery_of_image_blocks_and_drops_its_shortcode_block() -> None:
    edits, left = bb.plan_convert(_scan(), "[gallery] shortcode")
    assert left == []
    (edit,) = edits
    text = edit.body["content"]
    assert "wp:shortcode" not in text and "[gallery" not in text
    assert '<!-- wp:gallery {"columns":2,"linkTo":"media"} -->' in text
    assert 'class="wp-image-11"' in text and 'alt="B &amp; C"' in text
    assert edit.before["content"].startswith("<!-- wp:shortcode -->")
    assert (
        edit.stamp == "2026-11-01T00:00:00"
        and edit.words == "1 [gallery] use becomes the gallery block"
    )


def test_a_caption_becomes_an_image_with_its_caption_and_link() -> None:
    (edit,), _left = bb.plan_convert(_scan(), "[caption] shortcode")
    text = edit.body["content"]
    assert '<!-- wp:image {"id":10,"align":"right"} -->' in text
    assert '<figure class="wp-block-image alignright"><a href="https://r.example/up/a.jpg">' in text
    assert '<figcaption class="wp-element-caption">The tower</figcaption>' in text


def test_audio_video_and_embed_convert_and_what_cannot_is_said() -> None:
    edits, left = bb.plan_convert(_scan(), "[audio] shortcode")
    assert edits[0].title == "Sounds"
    assert '<audio controls src="https://r.example/up/a.mp3"></audio>' in edits[0].body["content"]
    assert "[audio]" in edits[0].body["content"]  # the one with no file stays
    assert left == ["Radio: Sounds: one [audio] stays, because it names no audio file"]
    (video,), _ = bb.plan_convert(_scan(), "[video] shortcode")
    assert 'poster="https://r.example/p.jpg"' in video.body["content"]
    (embed,), _ = bb.plan_convert(_scan(), "[embed] shortcode")
    assert '<!-- wp:embed {"url":"https://video.example/watch?v=1"} -->' in embed.body["content"]
    assert bb.plan_convert(_scan(), "[playlist] shortcode") == (
        [],
        ["WordPress has no core playlist block, so [playlist] stays a shortcode."],
    )
    assert bb.plan_convert(_scan(), "paragraph block")[0] == []


def test_only_the_checked_items_are_converted() -> None:
    edits, _ = bb.plan_convert(_scan(), "[audio] shortcode", item_ids=[3])
    assert edits == []


def test_a_gallery_whose_pictures_were_not_read_stays_and_says_so() -> None:
    scan = _scan()
    scan.media = scan.media[:1]
    edits, left = bb.plan_convert(scan, "[gallery] shortcode")
    assert edits == [] and "11 are not in the Media Library" in left[0]


def test_a_pattern_updates_once_and_detaches_on_the_chosen_pages() -> None:
    scan = _scan()
    pattern = {"id": 7, "title": {"raw": "Footer"}, "content": {"raw": "<p>old</p>"}}
    pattern["modified_gmt"] = "2026-10-01T00:00:00"
    edit = bb.pattern_update_edit("Radio", pattern, "<p>new</p>", 2)
    assert edit is not None and edit.route == "wp/v2/blocks/7"
    assert edit.body == {"content": "<p>new</p>"} and edit.before == {"content": "<p>old</p>"}
    assert "the 2 pages placing it show the change" in edit.words
    assert bb.pattern_update_edit("Radio", pattern, "<p>old</p>", 2) is None
    assert [r["id"] for r in bb.pattern_items(scan, 7)] == [2, 3]
    (detached,) = bb.plan_detach(scan, 7, "<p>new</p>", item_ids=[3])
    assert detached.route == "wp/v2/posts/3"
    assert "wp:block" not in detached.body["content"] and "<p>new</p>" in detached.body["content"]
    assert "Footer becomes its own blocks here" in detached.words


def test_the_pages_using_a_plugins_blocks_are_found_before_it_is_removed() -> None:
    scan = _scan()
    assert bb.block_namespace("jetpack/slideshow block") == "jetpack"
    assert bb.block_namespace("paragraph block") == "core"
    assert bb.plugin_namespaces({"plugin": "jetpack/jetpack", "textdomain": "jetpack"}) == [
        "jetpack"
    ]
    assert bb.namespace_uses(scan, ["jetpack"]) == [
        ("Sounds", ["jetpack/slideshow"]),
        ("Watch", ["jetpack/map"]),
    ]
    assert bb.namespace_uses(scan, ["woocommerce"]) == []


# -- WP-R-044: the six kinds Across Sites declined ---------------------------------------

_QAF = {"namespaces": ["wp/v2", "qaf/v1", "redirection/v1"]}


def _model(*labels: str) -> dict[str, Any]:
    items = [{"id": f"q{i}", "type": "text", "label": label} for i, label in enumerate(labels)]
    return {"version": 1, "title": "Contact", "pages": [{"id": "page_1", "items": items}]}


def _site(**reads: Any) -> Api:
    return Api({"": _QAF, **reads})


def test_starter_pages_and_content_types_are_compared_and_never_copied() -> None:
    a = _site(**{
        "wp/v2/block-patterns/patterns": [
            {
                "name": "t/about",
                "title": "About",
                "content": "x",
                "blockTypes": ["core/post-content"],
            },
            {"name": "t/hero", "title": "Hero", "content": "y", "blockTypes": []},
        ],
        "wp/v2/types": {
            "event": {"name": "Events", "hierarchical": False, "taxonomies": ["genre"]}
        },
    })
    b = _site(**{"wp/v2/block-patterns/patterns": [], "wp/v2/types": {}})
    found = gather_across("starter_pages", [("A", a), ("B", b)])
    assert list(found) == ["About"]
    (row,) = across_rows("starter_pages", found, ["A", "B"])
    assert row.raw["missing"] == ["B"]
    types = gather_across("content_types", [("A", a), ("B", b)])
    assert types["Events (event)"]["A"]["value"].startswith("without parents; taxonomies genre")
    plan = same_everywhere_plan(row, next(iter(row.raw["variants"])))
    edits, refused = ops.make_same_edits("starter_pages", "About", plan, {}, {})
    assert edits == [] and "cannot register one" in refused[0].words


def test_forms_are_compared_by_questions_and_made_as_drafts_where_missing() -> None:
    a = _site(**{
        "qaf/v1/forms": [{"id": 4, "title": "Contact"}],
        "qaf/v1/forms/4": {
            "id": 4,
            "title": "Contact",
            "status": "active",
            "model": _model("Name"),
        },
    })
    b = _site(**{
        "qaf/v1/forms": [{"id": 9, "title": "Contact"}],
        "qaf/v1/forms/9": {
            "id": 9,
            "title": "Contact",
            "status": "active",
            "updated_at": "2026-10-01",
            "config": {"notify": "office@b.example"},
            "model": _model("Name", "Email"),
        },
    })
    c = Api({"": {"namespaces": ["wp/v2"]}})
    unread: dict[str, list[str]] = {}
    found = gather_across("forms", [("A", a), ("B", b), ("C", c)], unread)
    assert "does not run QUILL Accessible Forms" in unread["C"][0]
    (row,) = [r for r in across_rows("forms", found, ["A", "B", "C"], unread) if r.kind == "across"]
    assert row.raw["missing"] == [] and row.cell("versions") == "2"
    winner = next(w for w, s in row.raw["variants"].items() if s == ["A"])
    plan = same_everywhere_plan(row, winner)
    edits, refused = ops.make_same_edits(
        "forms", "Contact", plan, row.raw["objects"], found["Contact"]["A"]
    )
    (edit,) = edits
    assert edit.route == "qaf/v1/forms/9" and edit.stamp == "2026-10-01"
    assert edit.body["config"]["notify"] == "office@b.example"  # the site's own settings stay
    assert edit.body["model"]["pages"][0]["items"][0]["label"] == "Name"
    assert len(edit.before["model"]["pages"][0]["items"]) == 2
    assert refused[0].site == "C" and refused[0].words.startswith("not read")
    made = more.edit_for_more("forms", "D", "Contact", found["Contact"]["A"], None)
    assert made.route == "qaf/v1/forms" and made.body["status"] == "draft" and made.before is None


def test_pages_with_a_role_update_from_the_chosen_one() -> None:
    page = {
        "id": 3,
        "title": {"raw": "Privacy"},
        "content": {"raw": "new text"},
        "modified_gmt": "2026-11-01",
    }
    a = _site(**{
        "wp/v2/settings": {"show_on_front": "posts"},
        "wp/v2/pages": [{"id": 3}],
        "wp/v2/pages/3": page,
    })
    old = {
        "id": 8,
        "title": {"raw": "Privacy"},
        "content": {"raw": "old"},
        "modified_gmt": "2024-01-01",
    }
    b = _site(**{
        "wp/v2/settings": {"show_on_front": "page", "page_on_front": 2},
        "wp/v2/pages": [{"id": 8}],
        "wp/v2/pages/8": old,
        "wp/v2/pages/2": {"id": 2, "title": {"raw": "Home"}, "content": {"raw": "hi"}},
    })
    found = gather_across("role_pages", [("A", a), ("B", b)])
    name = "Privacy policy page (the privacy-policy address)"
    assert set(found) == {name, "Front page"}
    assert found[name]["B"]["value"].startswith("last updated 2024-01-01")
    row = next(r for r in across_rows("role_pages", found, ["A", "B"]) if r.key == name)
    plan = same_everywhere_plan(row, found[name]["A"]["value"])
    (edit,), _ = ops.make_same_edits("role_pages", name, plan, row.raw["objects"], found[name]["A"])
    assert edit.route == "wp/v2/pages/8" and edit.body == {"content": "new text"}
    assert edit.before == {"content": "old"} and edit.stamp == "2024-01-01"
    front = next(r for r in across_rows("role_pages", found, ["A", "B"]) if r.key == "Front page")
    plan = same_everywhere_plan(front, found["Front page"]["B"]["value"])
    _, refused = ops.make_same_edits("role_pages", "Front page", plan, front.raw["objects"], {})
    assert "Settings > Reading" in refused[0].words


def test_redirects_are_made_the_same_in_each_sites_group_and_removed_everywhere() -> None:
    redirect = {
        "id": 5,
        "url": "/old",
        "action_code": 301,
        "action_data": {"url": "/new"},
        "group_id": 2,
    }
    a = _site(**{"redirection/v1/redirect": {"items": [redirect], "total": 1}})
    b = _site(**{
        "redirection/v1/redirect": {"items": [], "total": 0},
        "redirection/v1/group": {"items": [{"id": 4, "name": "Redirections"}], "total": 1},
    })
    c = Api({"": {"namespaces": ["wp/v2"]}})
    unread: dict[str, list[str]] = {}
    found = gather_across("redirects", [("A", a), ("B", b), ("C", c)], unread)
    assert "does not run the Redirection plugin" in unread["C"][0]
    row = next(
        r for r in across_rows("redirects", found, ["A", "B", "C"], unread) if r.key == "/old"
    )
    assert row.raw["missing"] == ["B"]
    plan = same_everywhere_plan(row, "to /new, code 301")
    edits, _ = ops.make_same_edits(
        "redirects", "/old", plan, row.raw["objects"], found["/old"]["A"]
    )
    (edit,) = edits
    assert edit.route == "redirection/v1/redirect" and edit.body["group_id"] == 0
    outcomes, sent = ops.run_edits_by_site({"B": b}.__getitem__, edits)
    assert outcomes[0].ok and b.writes[-1][2]["group_id"] == 4  # the site's own default group
    removals, refused = more.removal_plan("redirects", "/old", row.raw["objects"])
    assert refused == [] and removals[0].route == "redirection/v1/bulk/redirect/delete"
    more.run_removals({"A": a}.__getitem__, removals)
    assert a.writes[-1] == ("POST", "redirection/v1/bulk/redirect/delete", {"items": [5]})


def test_spam_senders_are_blocked_where_missing_and_a_site_without_the_route_is_not_read() -> None:
    a = _site(**{
        more.BLOCKLIST_ROUTE: {"items": [{"id": 2, "value": "bad@x.example", "kind": "email"}]}
    })
    b = _site(**{more.BLOCKLIST_ROUTE: []})
    c = _site()
    c.fail[more.BLOCKLIST_ROUTE] = 404
    unread: dict[str, list[str]] = {}
    found = gather_across("spam_senders", [("A", a), ("B", b), ("C", c)], unread)
    assert "needs a version that offers this route" in unread["C"][0]
    row = next(
        r for r in across_rows("spam_senders", found, ["A", "B", "C"], unread) if r.kind == "across"
    )
    assert row.raw["missing"] == ["B"]
    plan = same_everywhere_plan(row, "blocked email")
    edits, refused = ops.make_same_edits(
        "spam_senders", "bad@x.example", plan, row.raw["objects"], found["bad@x.example"]["A"]
    )
    assert [(e.site, e.route, e.body) for e in edits] == [
        ("B", more.BLOCKLIST_ROUTE, {"value": "bad@x.example", "kind": "email"})
    ]
    assert refused[0].site == "C"
    removals, _ = more.removal_plan("spam_senders", "bad@x.example", row.raw["objects"])
    assert [(r.method, r.route) for r in removals] == [("DELETE", f"{more.BLOCKLIST_ROUTE}/2")]


def test_a_term_is_merged_into_another_by_name_and_removed_everywhere() -> None:
    api = Api({
        "wp/v2/categories": [{"id": 6, "name": "Shows"}],
        "wp/v2/posts": [
            {"id": 1, "title": {"raw": "One"}, "categories": [5, 9], "modified_gmt": "m1"},
            {"id": 2, "title": {"raw": "Two"}, "categories": [5, 6], "modified_gmt": "m2"},
        ],
    })
    edits, source, why = more.term_merge_plan(api, "A", "News (category)", {"id": 5}, "shows")
    assert why == "" and source == 5
    assert [(e.route, e.body, e.before) for e in edits] == [
        ("wp/v2/posts/1", {"categories": [9, 6]}, {"categories": [5, 9]}),
        ("wp/v2/posts/2", {"categories": [6]}, {"categories": [5, 6]}),
    ]
    _e, _s, why = more.term_merge_plan(api, "A", "News (category)", {"id": 5}, "Sport")
    assert why == "has no category named Sport"
    removals, refused = more.removal_plan(
        "terms", "News (category)", {"A": {"id": 5, "count": 2}, "B": {"name": "News"}}
    )
    assert removals[0].route == "wp/v2/categories/5" and "from 2 posts" in removals[0].words
    assert refused[0].site == "B"
    assert more.run_removals({"A": api}.__getitem__, removals)[0].ok
    assert api.writes[-1] == ("DELETE", "wp/v2/categories/5", {"force": True})
