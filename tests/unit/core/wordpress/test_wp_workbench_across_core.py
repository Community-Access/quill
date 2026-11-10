"""W8 and the third sweep in the core: by name, across sites, fleet, audit, housekeeping."""

from __future__ import annotations

from datetime import UTC, datetime

from quill.core.wordpress.workbench_across import (
    SiteScan,
    across_rows,
    fleet_rows,
    kind_rows,
    same_everywhere_plan,
)
from quill.core.wordpress.workbench_sweep import (
    content_audit,
    media_housekeeping,
    privacy_rows,
    redirect_body,
    redirect_offered,
)

_TEXT = (
    '<!-- wp:paragraph --><p><a href="https://old.example.org">old</a></p>'
    '<!-- /wp:paragraph --><!-- wp:block {"ref":7} /-->[gallery ids="1"]'
    '<img src="https://r.example/wp-content/uploads/logo.png"><h2>A</h2><h4>B</h4>'
)


def _scan() -> SiteScan:
    scan = SiteScan("Radio")
    scan.items = [
        {
            "id": 1,
            "type": "page",
            "status": "publish",
            "title": {"raw": "About"},
            "content": {"raw": _TEXT},
            "link": "https://r.example/about",
            "author": 3,
            "meta": {"venue": "Main Hall"},
            "modified_gmt": "2024-01-01T00:00:00",
        },
        {
            "id": 2,
            "type": "post",
            "status": "draft",
            "title": {"raw": "About"},
            "content": {"raw": "short"},
            "author": 3,
            "meta": {"venue": "Main Hall"},
        },
    ]
    scan.terms = [("category", {"id": 5, "name": "News", "count": 12})]
    scan.media = [
        {"id": 10, "source_url": "https://r.example/wp-content/uploads/logo.png"},
        {
            "id": 11,
            "source_url": "https://r.example/wp-content/uploads/big.mp3",
            "mime_type": "audio/mpeg",
            "media_details": {"filesize": 5 * 1024 * 1024},
        },
    ]
    scan.users = {3: "Sam"}
    scan.patterns = {7: "Footer"}
    return scan


def test_every_kind_has_its_own_rows_with_where_it_is_used() -> None:
    scan = _scan()
    values = {
        kind: {r.key: r for r in kind_rows(scan, kind)}
        for kind in ("terms", "fields", "authors", "media_usage", "patterns", "links", "blocks")
    }
    assert values["terms"]["category:5"].cell("used") == "12 posts"
    assert values["fields"]["venue: Main Hall"].cell("count") == "2"
    assert "1 publish" in values["authors"]["3"].cell("used")
    assert values["media_usage"]["logo.png"].cell("used") == "used on 1 pages"
    assert values["media_usage"]["big.mp3"].cell("used") == "not used anywhere"
    assert "Footer" in values["patterns"]
    assert "https://old.example.org" in values["links"]
    assert "paragraph block" in values["blocks"] and "[gallery] shortcode" in values["blocks"]


def test_across_sites_names_variants_and_where_a_term_is_missing() -> None:
    found = {
        "Events (category)": {
            "A": {"name": "Events", "slug": "events"},
            "B": {"name": "Events", "slug": "events-2"},
        }
    }
    rows = across_rows("terms", found, ["A", "B", "C"])
    row = rows[0]
    assert row.detail.startswith("Events (category): on 2 sites, 2 versions, missing from 1")
    assert row.cell("missing") == "C"
    plan = dict(same_everywhere_plan(row, "slug events"))
    assert plan == {
        "A": "already matches; nothing to do",
        "B": "changes from slug events-2 to slug events",
        "C": "gets Events (category), as slug events",
    }


def test_the_fleet_reads_every_site_in_one_list() -> None:
    rows = fleet_rows([("A", {"version": "6.9", "waiting": 2}), ("B", {"error": "timed out"})])
    assert rows[0].detail == "A: WordPress 6.9, 2 comments waiting."
    assert rows[1].detail == "B: not answering: timed out."


def test_the_content_audit_and_media_housekeeping_find_their_problems() -> None:
    scan = _scan()
    problems = {
        r.cell("problem") for r in content_audit(scan, now=datetime(2026, 11, 10, tzinfo=UTC))
    }
    assert {"Nothing links to it", "Not changed in a year", "A heading skips a level"} <= problems
    house = {(r.key, r.cell("problem")) for r in media_housekeeping(scan)}
    assert ("11:unused", "Used nowhere") in house
    assert ("11:large", "Very large") in house
    assert ("11:transcript", "Audio without a transcript") in house


def test_privacy_points_to_wp_admin_and_redirects_wait_for_their_plugin() -> None:
    rows = privacy_rows("Radio", "https://r.example/", ["/wp/v2/posts"])
    assert [r.link for r in rows] == [
        "https://r.example/wp-admin/export-personal-data.php",
        "https://r.example/wp-admin/erase-personal-data.php",
    ]
    assert not redirect_offered(["wp/v2"]) and redirect_offered(["redirection/v1"])
    body = redirect_body("https://r.example/old-name/", "https://r.example/new-name/")
    assert body["url"] == "/old-name/" and body["action_data"] == {
        "url": "https://r.example/new-name/"
    }
