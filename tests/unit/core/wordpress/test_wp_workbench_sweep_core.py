"""WP-G, the site administration sweep, in the core: redirects, upkeep, areas, audit."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from quill.core.wordpress.workbench_across import SiteScan
from quill.core.wordpress.workbench_actions import WORDPRESS_ACTIONS
from quill.core.wordpress.workbench_coverage import (
    STATUSES,
    THIRD_SWEEP,
    classify,
    sweep_disposition,
)
from quill.core.wordpress.workbench_redirects import (
    default_group,
    edit_body,
    group_label,
    not_found_row,
    read_groups,
    read_pages,
    redirect_row,
    trace_address,
)
from quill.core.wordpress.workbench_sweep import (
    content_audit,
    media_housekeeping,
    privacy_rows,
    privacy_screens,
    trash_preview,
)
from quill.core.wordpress.workbench_sweep_places import KEYLESS, SWEEP_ROW_HELP
from quill.core.wordpress.workbench_upkeep import (
    certificate_row,
    lock_rows,
    overdue_rows,
    peer_certificate,
    sitemap_row,
    visibility_row,
)
from quill.core.wordpress.workbench_window_menu import WORDPRESS_KEYS

NOW = datetime(2026, 11, 13, 12, 0, tzinfo=UTC)
URL = "https://r.example"

# -- every third-sweep row is accounted for ---------------------------------------

_PRD_AREAS = {
    "Redirects",
    "Backups",
    "Security, sign-ins and two-factor",
    "Caching and speed",
    "Multilingual sites",
    "Privacy requests",
    "Consent and cookies",
    "Email delivery",
    "Newsletters and subscribers",
    "Courses",
    "Event tickets and attendance",
    "Stats and analytics",
    "Search and sitemaps",
    "Social sharing",
    "Scheduled tasks",
    "Someone else is editing",
    "Content audit",
    "Media housekeeping",
    "SSL and the address",
    "Shop, orders and catalogue",
    "SEO",
}


def test_every_third_sweep_row_has_a_disposition_and_a_boundary() -> None:
    assert {a.area for a in THIRD_SWEEP} == _PRD_AREAS
    for area in THIRD_SWEEP:
        assert area.boundary.strip() and area.screen and area.plugins, area.area
        for listed in ((), area.namespaces):
            place = sweep_disposition(area, listed)
            assert place.status in STATUSES and place.home, (area.area, listed)
        if not area.built:
            assert sweep_disposition(area, ()).status == "wp_admin_only"
            assert sweep_disposition(area, area.namespaces).status == "schema_built"
            assert "Open in Dashboard: wp-admin/" in sweep_disposition(area, ()).home


def test_redirects_are_covered_only_where_the_plugin_is() -> None:
    redirects = THIRD_SWEEP[0]
    assert sweep_disposition(redirects, ["wp/v2"]).status == "wp_admin_only"
    assert sweep_disposition(redirects, ["redirection/v1"]).status == "covered"
    assert classify("/redirection/v1/redirect").status == "covered"
    assert classify("/redirection/v1/404").status == "covered"
    assert classify("/redirection/v1/group").status == "planned"


def test_every_sweep_command_has_help_and_a_key_or_a_reason() -> None:
    for kind in SWEEP_ROW_HELP:
        rows = WORDPRESS_ACTIONS.rows_for(kind)
        assert rows, kind
        for action in rows:
            assert action.help, (kind, action.label)
            verb = action.command_id
            assert (
                WORDPRESS_KEYS.get(verb)
                or KEYLESS.get(verb)
                or verb.endswith((".read", ".sheet", ".open_on_site"))
            ), verb


# -- redirects ----------------------------------------------------------------------


class _Pages:
    def __init__(self, items: list[dict[str, Any]]) -> None:
        self.items = items
        self.asked: list[tuple[str, dict[str, Any]]] = []

    def get(self, route: str, **params: Any) -> Any:
        self.asked.append((route, params))
        start = int(params["page"]) * int(params["per_page"])
        return {"items": self.items[start : start + int(params["per_page"])], "total": 250}


def test_redirect_lists_are_read_page_by_page_from_zero() -> None:
    api = _Pages([{"id": n, "url": f"/p{n}"} for n in range(250)])
    items = read_pages(api, "redirect")
    assert len(items) == 250
    assert [p["page"] for _r, p in api.asked] == [0, 1]
    assert api.asked[0][0] == "redirection/v1/redirect"


def test_a_redirect_row_and_a_404_row_say_what_they_are() -> None:
    row = redirect_row(
        "Radio",
        {
            "id": 4,
            "url": "/old/",
            "action_code": 301,
            "action_data": {"url": "/new/"},
            "hits": 12,
            "enabled": False,
        },
        URL,
    )
    assert row.kind == "redirect" and row.status == "disabled"
    assert row.cell("state") == "off" and row.link == "https://r.example/old/"
    assert "/old/ leads to /new/ with a 301 redirect, turned off; used 12 times" in row.detail
    lost = not_found_row("Radio", {"id": 9, "url": "/gone", "referrer": "https://x.org"}, URL)
    assert lost.kind == "not_found" and "from https://x.org" in lost.detail


def test_edit_body_keeps_a_path_and_the_code() -> None:
    body = edit_body("https://r.example/old/?a=1", "https://r.example/new/", 302, group_id=4)
    assert body["url"] == "/old/?a=1" and body["action_code"] == 302
    assert body["action_data"] == {"url": "https://r.example/new/"}
    assert body["group_id"] == 4
    assert edit_body("^/blog/(.*)$", "/news/$1", regex=True, group_id=4)["url"] == "^/blog/(.*)$"


class _Groups:
    """The Redirection plugin's ``group`` list as 5.10.1 answers it."""

    def __init__(self, items: list[dict[str, Any]]) -> None:
        self.items = items
        self.asked: list[str] = []

    def get(self, route: str, **params: Any) -> dict[str, Any]:
        self.asked.append(route)
        return {"items": self.items if params.get("page", 0) == 0 else [], "total": len(self.items)}


def test_a_new_redirect_goes_in_a_group_the_site_has() -> None:
    api = _Groups([
        {"id": 3, "name": "Old imports", "module_id": 1, "enabled": False},
        {"id": 5, "name": "Apache", "module_id": 2, "enabled": True},
        {"id": 7, "name": "Redirections", "module_id": 1, "enabled": True},
    ])
    groups = read_groups(api)
    assert api.asked == ["redirection/v1/group"]
    assert [g["id"] for g in groups] == [5, 7, 3]
    assert default_group(groups) == 7
    assert group_label(groups[2]) == "Old imports (turned off)"
    assert default_group([{"id": 9, "name": "Mine", "module_id": 1}]) == 9
    assert default_group([]) == 0
    body = edit_body("/old/", "/new/", group_id=default_group(groups))
    assert body["group_id"] == 7


def test_test_an_address_follows_chains_and_names_loops() -> None:
    rules = [
        {"url": "/a/", "action_data": {"url": "/b/"}, "action_code": 301, "enabled": True},
        {"url": "/b", "action_data": {"url": "/c/"}, "action_code": 301, "enabled": True},
        {"url": "/x/", "action_data": {"url": "/y/"}, "action_code": 301, "enabled": False},
        {"url": "/l1/", "action_data": {"url": "/l2/"}, "action_code": 302, "enabled": True},
        {"url": "/l2/", "action_data": {"url": "/l1/"}, "action_code": 302, "enabled": True},
    ]
    said = trace_address("/a/", rules, URL)
    assert said.startswith("/a/ leads to /c/: /a/ to /b/ (301) then /b to /c/ (301). A chain")
    assert "decide in the end" in said
    assert trace_address("/x/", rules, URL).startswith("No redirect read")
    assert "loop" in trace_address("https://r.example/l1/", rules, URL)


# -- privacy ------------------------------------------------------------------------


def test_privacy_rows_point_to_the_exact_screens_and_claim_nothing() -> None:
    assert privacy_screens(URL, "5.2.4") == (
        "https://r.example/wp-admin/tools.php?page=export_personal_data",
        "https://r.example/wp-admin/tools.php?page=remove_personal_data",
    )
    rows = privacy_rows("Radio", URL + "/", ["/wp/v2/posts"], "6.9")
    assert [r.link for r in rows] == [
        "https://r.example/wp-admin/export-personal-data.php",
        "https://r.example/wp-admin/erase-personal-data.php",
    ]
    assert all(r.kind == "privacy" for r in rows)
    assert all("cannot tell afterwards whether they were done" in r.detail for r in rows)


# -- content audit and housekeeping ---------------------------------------------------

_HARD = (
    "<p>Notwithstanding considerable organizational interdependencies, institutional "
    "accountability mechanisms necessitate comprehensive reconsideration of administrative "
    "responsibilities. </p>"
) * 10


def test_the_audit_finds_copies_and_hard_reading_and_keeps_usage() -> None:
    scan = SiteScan("Radio")
    scan.items = [
        {
            "id": n,
            "type": "post",
            "status": "publish",
            "title": {"raw": f"Post {n}"},
            "content": {"raw": _HARD},
            "link": f"https://r.example/post-{n}",
            "modified_gmt": "2026-11-01T00:00:00",
        }
        for n in (1, 2)
    ]
    rows = content_audit(scan, now=NOW)
    problems = {(r.key, r.cell("problem")) for r in rows}
    assert ("1:copy", "Same text as another") in problems
    assert ("1:reading", "Hard to read") in problems
    assert all(r.kind == "finding" and r.raw["route"].startswith("wp/v2/posts/") for r in rows)


def test_housekeeping_finds_copies_and_previews_usage_before_the_trash() -> None:
    scan = SiteScan("Radio")
    scan.items = [
        {
            "id": 1,
            "title": {"raw": "Home"},
            "content": {"raw": '<img src="https://r.example/u/logo.png">'},
            "featured_media": 0,
        }
    ]
    scan.media = [
        {
            "id": 10,
            "source_url": "https://r.example/u/logo.png",
            "mime_type": "image/png",
            "media_details": {"filesize": 3 * 1024 * 1024},
        },
        {"id": 11, "source_url": "https://r.example/u/logo-1.png", "mime_type": "image/png"},
    ]
    rows = {r.key: r for r in media_housekeeping(scan)}
    assert rows["11:copy"].cell("problem") == "Looks uploaded twice"
    assert "11:unused" in rows and "10:unused" not in rows
    summary, lines = trash_preview(rows["11:copy"])
    assert "nothing is deleted" in summary
    assert lines == ["Nothing in the posts and pages read uses it."]
    used = next(r for r in media_housekeeping(scan) if r.raw["item_id"] == 10)
    assert used.raw["places"] == ["Home"]


# -- upkeep -------------------------------------------------------------------------


def test_visibility_says_where_its_answer_comes_from() -> None:
    told = visibility_row("Radio", URL, {"blog_public": 0}, None)
    assert told.cell("state") == "asks not to be indexed"
    guessed = visibility_row("Radio", URL, {"title": "R"}, False)
    assert guessed.cell("state") == "maybe hidden"
    assert "does not include the Search engine visibility setting" in guessed.detail
    assert guessed.link.endswith("/wp-admin/options-reading.php")


def test_the_sitemap_row_counts_its_sitemaps() -> None:
    body = (
        b"<sitemapindex><sitemap><loc>https://r.example/wp-sitemap-posts-post-1.xml</loc>"
        b"</sitemap><sitemap><loc>https://r.example/wp-sitemap-users-1.xml</loc></sitemap>"
        b"</sitemapindex>"
    )
    row = sitemap_row("Radio", URL, body)
    assert "lists 2 sitemaps: wp-sitemap-posts-post-1.xml, wp-sitemap-users-1.xml" in row.detail
    assert sitemap_row("Radio", URL, None, "it answered 404").cell("state") == "not found"


def test_overdue_schedules_are_named_and_others_are_not() -> None:
    items = [
        {"id": 1, "status": "future", "title": {"raw": "Late"}, "date_gmt": "2026-11-12T08:00:00"},
        {"id": 2, "status": "future", "title": {"raw": "Soon"}, "date_gmt": "2026-11-20T08:00:00"},
    ]
    rows = overdue_rows("Radio", items, now=NOW)
    assert [r.key for r in rows] == ["overdue:1"]
    assert "WP-Cron" in rows[0].detail
    assert overdue_rows("Radio", items[1:], now=NOW)[0].cell("state") == "none"


def test_the_certificate_warns_inside_thirty_days_and_admits_what_it_cannot_read() -> None:
    soon = certificate_row("Radio", URL, {"notAfter": "Dec  1 00:00:00 2026 GMT"}, now=NOW)
    assert soon.cell("state") == "expires soon" and "17 days" in soon.detail
    unknown = certificate_row("Radio", URL, None, now=NOW)
    assert unknown.cell("state") == "valid now" and "not handed over" in unknown.detail
    plain = certificate_row("Radio", "http://r.example", None, now=NOW)
    assert plain.cell("state") == "no HTTPS"

    class _Sock:
        def getpeercert(self) -> dict[str, Any]:
            return {"notAfter": "Dec  1 00:00:00 2026 GMT"}

    class _Raw:
        _sock = _Sock()

    class _Fp:
        raw = _Raw()

    class _Response:
        fp = _Fp()

    assert peer_certificate(_Response()) == {"notAfter": "Dec  1 00:00:00 2026 GMT"}
    assert peer_certificate(object()) is None


def test_editing_locks_use_the_lock_where_exposed_and_say_so_where_not() -> None:
    stamp = int(NOW.timestamp()) - 30
    locked = [{"id": 5, "title": {"raw": "Draft"}, "meta": {"_edit_lock": f"{stamp}:7"}}]
    rows = lock_rows("Radio", locked, me=3, people={7: "Ann"}, now=NOW)
    assert rows[0].cell("state") == "locked" and "Ann has Draft open" in rows[0].detail
    assert lock_rows("Radio", locked, me=7, now=NOW)[0].cell("state") == "none seen"
    recent = [{"id": 6, "title": {"raw": "News"}, "modified_gmt": "2026-11-13T11:55:00"}]
    rows = lock_rows("Radio", recent, now=NOW)
    assert rows[0].cell("state") == "maybe open"
    assert "keeps its editing lock out of REST" in rows[0].detail
