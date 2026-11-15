"""complete.md 10B.3, wx-free: what REST cannot do, PMPro's pmpro/v1, Site Health
Information and Security (XML-RPC), WordPress.org's directories, and the coverage rows."""

from __future__ import annotations

import io
import json
from typing import Any
from urllib.error import HTTPError

import pytest

from quill.core.wordpress.site import SiteInfo
from quill.core.wordpress.workbench_load import SiteContext


class _Address:
    is_wpcom = False
    wpcom_site = ""
    site_url = "https://radio.example"


class _Answer(io.BytesIO):
    status = 200

    def __enter__(self) -> _Answer:
        return self

    def __exit__(self, *_a: Any) -> None:
        self.close()


class FakeApi:
    """Answers by route; records requests sent through the site's door."""

    def __init__(self, answers: dict[str, Any] | None = None, door: Any = None) -> None:
        self.address = _Address()
        self.site_name = "Radio"
        self.timeout = 5.0
        self.answers = answers or {}
        self.gets: list[tuple[str, dict[str, Any]]] = []
        self.posts: list[tuple[str, Any]] = []
        self.sent: list[Any] = []
        self._door = door

    def _opener(self, request: Any, timeout: float = 0, context: Any = None) -> Any:
        self.sent.append(request)
        return self._door(request)

    def get(self, route: str, **params: Any) -> Any:
        self.gets.append((route, params))
        answer = self.answers.get(route)
        if isinstance(answer, Exception):
            raise answer
        return answer

    def post(self, route: str, body: Any = None, **_p: Any) -> Any:
        self.posts.append((route, body))
        return {"id": 9, **(body or {})}

    def request(self, method: str, route: str, **kw: Any) -> Any:
        class _R:
            payload = self.answers.get(route)

        self.gets.append((route, dict(kw.get("params") or {})))
        return _R()

    def iter_collection(self, route: str, params: Any = None, **_kw: Any):
        yield from self.answers.get(route, [])


def _info(*namespaces: str, routes: tuple[str, ...] = ()) -> SiteInfo:
    return SiteInfo("Radio", "", "https://radio.example", "6.8", namespaces, "", routes)


def _ctx(api: FakeApi, info: SiteInfo | None = None) -> SiteContext:
    return SiteContext("Radio", api, url="https://radio.example", info=info)  # type: ignore[arg-type]


# -- 1. what REST cannot do --------------------------------------------------------------


def test_each_job_rest_cannot_do_has_an_exact_wp_admin_address() -> None:
    from quill.core.wordpress.workbench_no_rest import (
        REST_CANNOT,
        across_note,
        admin_link,
        screen_for_row,
    )

    base = "https://radio.example/"
    assert admin_link(base, "updates") == "https://radio.example/wp-admin/update-core.php"
    assert admin_link(base, "theme_activate", theme="twentyfive").endswith(
        "wp-admin/themes.php?theme=twentyfive"
    )
    assert admin_link(base, "site_health_info").endswith("site-health.php?tab=debug")
    assert admin_link("", "updates") == ""
    assert screen_for_row("plugin") == "plugin_auto_updates"
    assert screen_for_row("across", "themes") == "theme_activate"
    assert screen_for_row("item") == ""
    assert "only reads" in REST_CANNOT and "no route" in REST_CANNOT
    assert "Open in Dashboard" in across_note("plugins")
    assert "only reads themes" in across_note("themes")
    assert across_note("terms") == ""


def test_plugin_theme_and_across_rows_say_the_limit_before_anyone_acts() -> None:
    from quill.core.wordpress.workbench_across import across_rows
    from quill.core.wordpress.workbench_load import load_plugins, load_themes

    api = FakeApi({
        "wp/v2/plugins": [{"plugin": "akismet/akismet", "name": "Akismet", "version": "5.3"}],
        "wp/v2/themes": [{"stylesheet": "tt5", "name": {"rendered": "TT5"}, "status": "active"}],
    })
    ctx = _ctx(api)
    assert "Open in Dashboard" in load_plugins(ctx)[0].detail
    assert "REST only reads themes" in load_themes(ctx)[0].detail
    found = {"TT5": {"A": {"version": "1", "status": "active"}}}
    row = across_rows("themes", found, ["A", "B"])[0]
    assert "Missing from: B." in row.detail and "only reads themes" in row.detail
    assert row.detail.endswith(".") and ".." not in row.detail


def test_the_coverage_ledger_records_pmpro_mcp_and_the_jobs_with_no_route() -> None:
    from quill.core.wordpress.workbench_coverage import NO_ROUTE, classify

    assert classify("/pmpro/v1/discount_code").status == "covered"
    assert "Discount Codes" in classify("/pmpro/v1/discount_code").home
    assert classify("/pmpro/v1/has_membership_access").status == "covered"
    assert classify("/pmpro/v1/get_membership_levels_for_user").status == "covered"
    assert classify("/pmpro/v1/change_membership_level").status == "covered"  # WP-C
    assert classify("/pmpro/v1/checkout_levels").status == "out_of_scope"
    assert classify("/pmpro/v1/order").status == "planned"
    assert classify("/mcp/mcp-adapter-default-server").status == "out_of_scope"
    assert "Ask the Site" in classify("/mcp/mcp-adapter-default-server").home
    assert "wp-admin" in classify("/wp/v2/plugins").home
    assert NO_ROUTE["XML-RPC (xmlrpc.php)"].status == "out_of_scope"
    assert "site-health.php?tab=debug" in NO_ROUTE["Site Health Info tab"].home
    assert all(c.status in ("wp_admin_only", "out_of_scope") for c in NO_ROUTE.values())


# -- 2. PMPro pmpro/v1 -------------------------------------------------------------------


def test_has_access_reads_every_shape_pmpro_answers() -> None:
    from quill.core.wordpress.workbench_pmpro_rest import has_access

    api = FakeApi({"pmpro/v1/has_membership_access": [False, ["2"], ["Gold"]]})
    answer = has_access(api, 4, 12)  # type: ignore[arg-type]
    assert api.gets[-1] == ("pmpro/v1/has_membership_access", {"user_id": 4, "post_id": 12})
    assert answer.sentence("Ann", "News", "Radio") == (
        "Ann cannot see News on Radio. It needs one of these levels: Gold."
    )
    api.answers["pmpro/v1/has_membership_access"] = True
    assert has_access(api, 4, 12).allowed  # type: ignore[arg-type]


def test_a_discount_code_is_previewed_then_sent_as_pmpro_expects() -> None:
    from quill.core.wordpress.workbench_pmpro_rest import (
        DiscountSpec,
        create_discount_code,
        discount_preview,
    )

    spec = DiscountSpec("SPRING", (2,), "10.00", 5, expires="2026-12-31")
    lines = discount_preview(spec, "Radio", {2: "Gold"})
    assert lines[0] == "Code SPRING on Radio: 5 uses, starts today, expires 2026-12-31."
    assert lines[1].startswith("Gold (level 2): initial payment 10.00")
    api = FakeApi()
    create_discount_code(api, spec)  # type: ignore[arg-type]
    route, body = api.posts[-1]
    assert route == "pmpro/v1/discount_code"
    assert body["code"] == "SPRING" and body["levels"][0]["level"] == 2


def test_discount_codes_list_from_the_ability_or_say_where_the_list_is() -> None:
    from quill.core.wordpress.workbench_pmpro_rest import load_discount_codes

    ability = {
        "name": "pmpro/discount-codes-query",
        "meta": {"annotations": {"readonly": True}},
    }
    api = FakeApi({
        "wp-abilities/v1/abilities": [ability],
        "wp-abilities/v1/abilities/pmpro/discount-codes-query/run": {
            "items": [{"id": 3, "code": "FALL", "uses": 0, "expires": ""}]
        },
    })
    rows = load_discount_codes(_ctx(api, _info("wp-abilities/v1", "pmpro/v1")))
    assert [r.cell("code") for r in rows] == ["FALL"]
    assert rows[0].cell("uses") == "unlimited"
    note = load_discount_codes(_ctx(FakeApi(), _info("pmpro/v1")))[0]
    assert note.subkind == "discount_note"
    assert note.link.endswith("admin.php?page=pmpro-discountcodes")
    assert "one discount code at a time" in note.detail
    absent = load_discount_codes(_ctx(FakeApi(), _info("wp/v2")))[0]
    assert absent.kind == "fact" and "pmpro/v1" in absent.detail


def test_member_levels_fall_back_to_pmpro_v1() -> None:
    from quill.core.wordpress.workbench_pmpro_rest import member_levels

    api = FakeApi({"pmpro/v1/get_membership_levels_for_user": {"2": {"id": 2, "name": "Gold"}}})
    assert member_levels(api, 4) == [{"id": 2, "name": "Gold"}]  # type: ignore[arg-type]


# -- 3. Site Health Information ----------------------------------------------------------


def test_information_says_what_rest_covers_and_opens_the_info_tab_for_the_rest() -> None:
    from quill.core.wordpress.workbench_health_info import info_rows

    api = FakeApi({
        "wp-site-health/v1/directory-sizes": {
            "uploads_size": {"raw": 2048, "size": "2 KB"},
            "database_size": {"raw": 1024, "size": "1 KB"},
        }
    })
    routes = ("/wp-site-health/v1/tests/background-updates", "/wp-site-health/v1/tests/page-cache")
    rows = info_rows(_ctx(api, _info("wp-site-health/v1", routes=routes)))
    first = rows[0]
    assert first.kind == "dashboard"
    assert first.link == "https://radio.example/wp-admin/site-health.php?tab=debug"
    assert "no REST route" in first.detail
    assert "Background updates, Page cache" in rows[1].detail
    assert any(r.cell("test") == "Uploads" for r in rows)


def test_information_says_why_when_only_an_administrator_may_read_sizes() -> None:
    from quill.core.wordpress.api import WordPressApiError
    from quill.core.wordpress.workbench_health_info import info_rows

    api = FakeApi({"wp-site-health/v1/directory-sizes": WordPressApiError("no", status=403)})
    rows = info_rows(_ctx(api))
    assert rows[-1].detail == "Directory sizes: only an administrator can read them."


# -- 4. XML-RPC --------------------------------------------------------------------------


def _xml(methods: list[str]) -> bytes:
    values = "".join(f"<value><string>{m}</string></value>" for m in methods)
    return f"<methodResponse><params><param><value><array><data>{values}</data></array>".encode()


def test_xmlrpc_that_answers_is_a_warning_and_no_password_is_sent() -> None:
    from quill.core.wordpress.workbench_health_info import security_rows

    api = FakeApi(door=lambda _r: _Answer(_xml(["pingback.ping", "wp.getUsersBlogs"])))
    rows = security_rows(_ctx(api))
    request = api.sent[0]
    assert request.full_url == "https://radio.example/xmlrpc.php"
    assert request.get_method() == "POST"
    assert b"system.listMethods" in request.data
    assert not request.has_header("Authorization")
    assert rows[0].status == "recommended"
    assert "XML-RPC is on" in rows[0].detail and "pingbacks" in rows[0].detail
    assert "never uses XML-RPC" in rows[1].detail


def test_xmlrpc_that_is_blocked_is_good_and_a_failure_is_unknown() -> None:
    from quill.core.wordpress.workbench_health_info import xmlrpc_check

    def blocked(_r: Any) -> Any:
        raise HTTPError("u", 403, "Forbidden", {}, None)  # type: ignore[arg-type]

    assert xmlrpc_check(FakeApi(door=blocked)).state == "blocked"  # type: ignore[arg-type]

    def gone(_r: Any) -> Any:
        raise OSError("no route")

    assert xmlrpc_check(FakeApi(door=gone)).state == "unknown"  # type: ignore[arg-type]
    html = FakeApi(door=lambda _r: _Answer(b"<html>hi</html>"))
    assert xmlrpc_check(html).state == "blocked"  # type: ignore[arg-type]


# -- 5. WordPress.org --------------------------------------------------------------------


def test_theme_search_sends_only_the_words_and_reads_each_theme() -> None:
    from quill.core.wordpress.dotorg import search_themes

    asked: list[str] = []

    def door(request: Any, timeout: float = 0) -> Any:
        asked.append(request.full_url)
        payload = {
            "themes": [
                {
                    "slug": "calm",
                    "name": "Calm",
                    "version": "1.2",
                    "author": {"display_name": "Sam"},
                    "rating": 90,
                    "num_ratings": 12,
                    "requires": "6.5",
                    "description": "<p>A quiet theme.</p>",
                }
            ]
        }
        return _Answer(json.dumps(payload).encode())

    themes = search_themes("calm blog", opener=door)
    assert asked[0].startswith("https://api.wordpress.org/themes/info/1.2/?action=query_themes")
    assert "calm+blog" in asked[0] and "radio" not in asked[0]
    assert themes[0].sentence == (
        "Calm, version 1.2, by Sam, rated 4.5 of 5 by 12 people, needs WordPress 6.5. "
        "A quiet theme."
    )


def test_wordpress_org_refuses_any_other_host() -> None:
    from quill.core.wordpress import dotorg

    with pytest.raises(dotorg.DotorgError):
        dotorg._get("https://example.org/themes", lambda *_a, **_k: None)


def test_language_packs_ask_once_per_version_and_say_what_rest_cannot() -> None:
    from quill.core.wordpress.dotorg import site_languages

    asked: list[str] = []

    def door(request: Any, timeout: float = 0) -> Any:
        asked.append(request.full_url)
        payload = {
            "translations": [
                {
                    "language": "de_DE",
                    "english_name": "German",
                    "native_name": "Deutsch",
                    "version": "6.8",
                    "updated": "2026-10-01 10:00:00",
                }
            ]
        }
        return _Answer(json.dumps(payload).encode())

    said = dict(
        site_languages([("A", "de_DE", "6.8"), ("B", "fy", "6.8"), ("C", "", "6.8")], opener=door)
    )
    assert asked == ["https://api.wordpress.org/translations/core/1.0/?version=6.8"]
    assert "German (Deutsch)" in said["A"] and "updated 2026-10-01" in said["A"]
    assert "not on WordPress's REST API" in said["A"]
    assert "has no fy pack" in said["B"]
    assert "needs no language pack" in said["C"]


def test_every_new_command_has_help_and_a_written_reason_for_no_chord() -> None:
    from quill.core.wordpress.workbench_actions import WINDOW_MENU, WORDPRESS_ACTIONS
    from quill.core.wordpress.workbench_admin_actions import KEYLESS, command
    from quill.core.workbench.menus import rows

    bound = {row.command_id for _menu, row in rows(WINDOW_MENU)}
    verbs = (
        "open_dashboard",
        "find_theme",
        "install_missing",
        "language_packs",
        "check_access",
        "look_up_discount",
        "new_discount_code",
    )
    offered = {
        a.command_id: a for k in WORDPRESS_ACTIONS.row_types for a in WORDPRESS_ACTIONS.rows_for(k)
    }
    for verb in verbs:
        action = offered[command(verb)]
        assert action.help, verb
        assert command(verb) in bound or KEYLESS.get(command(verb)), verb
