"""wp_missing.md's five small gaps, wx-free: Earlier Versions on an item, the update check
against WordPress.org, Check Every Link, a Gravity Forms response's answers, and the
plugin rows of the wp-admin map."""

from __future__ import annotations

import io
import json
import threading
from typing import Any
from urllib.error import HTTPError

import pytest

from quill.core.wordpress import workbench_gravity_answers as gfa
from quill.core.wordpress import workbench_item_versions as iv
from quill.core.wordpress import workbench_link_check as lk
from quill.core.wordpress import workbench_update_check as uc
from quill.core.wordpress.api import WordPressApiError
from quill.core.wordpress.workbench_actions import WORDPRESS_ACTIONS
from quill.core.wordpress.workbench_admin_map import ADMIN_MAP, map_rows, screens_for
from quill.core.wordpress.workbench_edit import EditConflict
from quill.core.wordpress.workbench_gap_actions import (
    CHECK_LINKS,
    ITEM_VERSIONS,
    KEYLESS,
    UPDATE_CHECK,
)
from quill.core.wordpress.workbench_rows import WbRow
from quill.core.wordpress.workbench_tree import WORDPRESS_TREE

SITE = "Community Radio"

# -- Earlier Versions on an item ------------------------------------------------------


class ItemSite:
    def __init__(self) -> None:
        self.item = {
            "id": 9,
            "title": {"raw": "Schedule"},
            "content": {"raw": "Monday\nTuesday"},
            "modified_gmt": "2026-11-10T10:00:00",
        }
        self.revisions = [
            {
                "id": 101,
                "modified_gmt": "2026-11-09T09:00:00",
                "title": {"raw": "Schedule"},
                "content": {"raw": "Monday"},
            },
            {
                "id": 100,
                "modified_gmt": "2026-11-10T10:00:00",
                "title": {"raw": "Schedule"},
                "content": {"raw": "Monday\nTuesday"},
            },
        ]
        self.writes: list[tuple[str, Any]] = []

    def get(self, route: str, **_params: Any) -> Any:
        if route == "wp/v2/posts/9":
            return json.loads(json.dumps(self.item))
        if route == "wp/v2/posts/9/revisions":
            return self.revisions
        if route == "wp/v2/posts/9/autosaves":
            return []
        raise AssertionError(route)

    def post(self, route: str, body: Any = None, **_params: Any) -> Any:
        self.writes.append((route, body))
        self.post_body(body)
        return dict(self.item)

    def post_body(self, body: dict[str, Any]) -> None:
        self.item = {
            **self.item,
            "title": {"raw": body["title"]},
            "content": {"raw": body["content"]},
            "modified_gmt": f"2026-11-14T0{len(self.writes)}:00:00",
        }


def test_earlier_versions_leave_out_the_one_that_is_current_and_compare_in_words() -> None:
    api = ItemSite()
    now = iv.load_item(api, "wp/v2/posts/9")
    versions = iv.earlier_versions(api, "post", 9, now)
    assert [v.id for v in versions] == [101]
    assert iv.version_label(versions[0]).startswith("Saved ")
    assert iv.version_label(versions[0]).endswith("Schedule, a revision")
    assert iv.compare_lines(now, versions[0]) == ["Line 2 removed: Tuesday"]


def test_restore_reads_again_first_and_its_undo_puts_the_item_back() -> None:
    api = ItemSite()
    now = iv.load_item(api, "wp/v2/posts/9")
    chosen = iv.earlier_versions(api, "post", 9, now)[0]
    saved = iv.restore_version(api, now, chosen)
    assert api.writes == [("wp/v2/posts/9", {"title": "Schedule", "content": "Monday"})]
    assert saved.content == "Monday"
    iv.put_back(api, saved, now)
    assert api.item["content"] == {"raw": "Monday\nTuesday"}


def test_a_restore_after_somebody_else_changed_the_item_sends_nothing() -> None:
    api = ItemSite()
    now = iv.load_item(api, "wp/v2/posts/9")
    chosen = iv.earlier_versions(api, "post", 9, now)[0]
    api.item["modified_gmt"] = "2026-11-12T08:00:00"
    with pytest.raises(EditConflict):
        iv.restore_version(api, now, chosen)
    assert api.writes == []
    saved = iv.ItemText("wp/v2/posts/9", "Schedule", "Monday", "")
    with pytest.raises(EditConflict):  # the undo will not overwrite a later change either
        iv.put_back(api, saved, now)


# -- Check for Updates on WordPress.org ------------------------------------------------


class _Answer(io.BytesIO):
    def __enter__(self) -> _Answer:
        return self

    def __exit__(self, *_a: Any) -> None:
        self.close()


def _door(answers: dict[str, Any], asked: list[str]) -> Any:
    def door(request: Any, timeout: float = 0) -> Any:
        url = request.full_url
        asked.append(url)
        for needle, answer in answers.items():
            if needle in url:
                if answer == 404:
                    body = io.BytesIO(b'{"error":"Theme not found"}')
                    raise HTTPError(url, 404, "Not Found", None, body)  # type: ignore[arg-type]
                return _Answer(json.dumps(answer).encode())
        raise AssertionError(url)

    return door


def test_versions_compare_as_numbers() -> None:
    assert uc.is_newer("6.8.1", "6.9")
    assert uc.is_newer("5.3", "5.3.1")
    assert not uc.is_newer("6.9", "6.9.0")
    assert not uc.is_newer("10.0", "9.9")
    assert not uc.is_newer("", "1.0")
    assert uc.update_word("1.0", "1.1") == "Update waiting: version 1.1"
    assert uc.update_word("1.1", "1.1") == uc.UP_TO_DATE
    assert uc.update_word("1.1", None) == uc.UNKNOWN


def test_wordpress_org_is_asked_only_short_names_and_nothing_for_wordpress() -> None:
    asked: list[str] = []
    door = _door(
        {
            "version-check": {"offers": [{"response": "upgrade", "current": "6.9"}]},
            "slug%5D=twentytwentyfive": {"slug": "twentytwentyfive", "version": "1.3"},
            "slug%5D=premium-theme": 404,
            "slug%5D=akismet": {"slug": "akismet", "name": "Akismet", "version": "5.4"},
            "slug%5D=gravityforms": {"error": "Plugin not found."},
        },
        asked,
    )
    assert uc.latest_core(opener=door) == "6.9"
    assert asked[-1] == "https://api.wordpress.org/core/version-check/1.7/"
    themes = uc.latest_themes(["twentytwentyfive", "premium-theme"], opener=door)
    assert themes == {"twentytwentyfive": "1.3", "premium-theme": None}
    plugins = uc.latest_plugins(["akismet", "gravityforms"], opener=door)
    assert plugins == {"akismet": "5.4", "gravityforms": None}
    assert all(url.startswith("https://api.wordpress.org/") for url in asked)
    assert not any("radio.example" in url for url in asked)


def test_rows_are_marked_waiting_up_to_date_or_unknown() -> None:
    latest = uc.Latest("6.9", {"akismet": "5.4", "gravityforms": None}, {"twentytwentyfive": "1.3"})
    rows = [
        WbRow("update", SITE, "update:core", {"what": "WordPress", "installed": "6.8.1"}, "."),
        WbRow("plugin", SITE, "akismet/akismet", {"plugin": "Akismet", "version": "5.3"}, "."),
        WbRow("plugin", SITE, "gravityforms/gravityforms", {"version": "2.9"}, "."),
        WbRow("theme", SITE, "twentytwentyfive", {"theme": "TT5", "version": "1.3"}, "."),
        WbRow("update", SITE, "update:automatic", {"what": "Automatic updates"}, "."),
    ]
    marked = uc.mark_rows(rows, latest)
    assert marked[0].cell("update") == "Update waiting: version 6.9"
    assert marked[1].cell("version") == "5.3, update waiting: 5.4"
    assert "so an update waits" in marked[1].detail
    assert marked[2].cell("update") == uc.UNKNOWN and "unknown" in marked[2].detail
    assert marked[3].cell("update") == uc.UP_TO_DATE
    assert marked[4] is rows[4]
    assert uc.waiting_count(marked) == (2, 1)
    assert uc.mark_rows(rows, uc.Latest()) == rows  # nothing asked, nothing said


# -- Check Every Link ----------------------------------------------------------------------


class LinkSite:
    def __init__(self) -> None:
        self.asked: list[str] = []

    def get(self, route: str, **params: Any) -> Any:
        if route == "":
            return {"routes": {"/wp-block-editor/v1/url-details": {}}}
        if route == "wp-block-editor/v1/url-details":
            self.asked.append(params["url"])
            if "gone" in params["url"]:
                raise WordPressApiError("No response", status=404, wp_code="no_response")
            return {"title": "Fine"}
        raise AssertionError(route)

    def iter_collection(self, route: str, params: Any = None, **_kw: Any) -> Any:
        if route == "wp/v2/posts":
            yield {
                "id": 1,
                "title": {"raw": "News"},
                "content": {
                    "raw": '<a href="https://ok.example">a</a> <a href="https://gone.example">b</a>'
                },
                "link": "https://radio.example/news",
            }
        elif route == "wp/v2/pages":
            yield {
                "id": 2,
                "title": {"raw": "About"},
                "content": {
                    "raw": '<a href="https://gone.example">again</a> <a href="/local">x</a>'
                },
                "link": "https://radio.example/about",
            }
        elif route == "wp/v2/shows":
            raise WordPressApiError("Forbidden", status=403)


def test_every_link_is_checked_once_with_every_item_that_holds_it() -> None:
    api = LinkSite()
    assert lk.has_link_route(api)
    found, items = lk.collect_links(api, lk.kinds_for(["post", "shows"]))
    assert items == 2 and list(found) == ["https://ok.example", "https://gone.example"]
    ticks: list[tuple[int, int, int]] = []
    result = lk.check_links(api, found, items=items, progress=lambda *t: ticks.append(t))
    assert api.asked == ["https://ok.example", "https://gone.example"]
    assert ticks == [(1, 2, 0), (2, 2, 1)]
    [broken] = result.broken
    assert [h.title for h in broken.holders] == ["News", "About"]
    assert broken.spoken() == (
        "https://gone.example, in News (post), About (page): the page is not there."
    )
    assert lk.outcome(SITE, result) == "1 of 2 links on Community Radio lead nowhere."


def test_a_stopped_check_keeps_what_it_found() -> None:
    api = LinkSite()
    found, items = lk.collect_links(api, ["post", "page"])
    stop = threading.Event()
    result = lk.check_links(api, found, items=items, stop=stop, progress=lambda *_t: stop.set())
    assert result.stopped and result.checked == 1
    assert lk.outcome(SITE, result).startswith("Stopped after 1 of 2 links")


# -- A Gravity Forms response's answers ------------------------------------------------


class EntrySite:
    def __init__(self) -> None:
        self.entry = {
            "id": "5",
            "form_id": "1",
            "date_updated": "2026-11-09 10:00:00",
            "is_starred": "0",
            "1.3": "Ann",
            "1.6": "Lee",
            "10": "x",
            "2": "ann@example.com",
        }
        self.puts: list[dict[str, Any]] = []

    def get(self, route: str, **_params: Any) -> Any:
        return dict(self.entry)

    def request(self, method: str, route: str, **kw: Any) -> Any:
        assert method == "PUT" and route == "gf/v2/entries/5"
        self.puts.append(kw["json_body"])
        self.entry = {**kw["json_body"], "date_updated": "2026-11-14 09:00:00"}


def test_answers_are_found_in_field_order_with_their_labels() -> None:
    entry = EntrySite().entry
    assert gfa.answer_ids(entry) == ["1.3", "1.6", "2", "10"]
    form = {
        "fields": [
            {"id": 1, "label": "Name", "inputs": [{"id": "1.3", "label": "First"}]},
            {"id": 2, "label": "Email", "adminLabel": "Reply to"},
        ]
    }
    labels = gfa.answer_labels(form)
    assert labels["1.3"] == "Name, First" and labels["2"] == "Reply to"
    assert gfa.field_of(gfa.answer_key("1.3")) == "1.3" and gfa.field_of("is_read") == ""


def test_changed_answers_go_as_the_whole_entry_and_can_be_put_back() -> None:
    api = EntrySite()
    was = gfa.set_answers(
        api,
        "gf/v2/entries/5",
        seen={"1.3": "Ann"},
        changed={"1.3": "Anne"},
        seen_updated="2026-11-09 10:00:00",
    )
    assert was == {"1.3": "Ann"}
    sent = api.puts[0]
    assert sent["1.3"] == "Anne" and sent["2"] == "ann@example.com" and sent["is_starred"] == "0"
    gfa.set_answers(api, "gf/v2/entries/5", seen={"1.3": "Anne"}, changed=was)
    assert api.entry["1.3"] == "Ann"


def test_a_response_changed_meanwhile_is_left_alone() -> None:
    api = EntrySite()
    with pytest.raises(EditConflict):  # date_updated moved on
        gfa.set_answers(
            api,
            "gf/v2/entries/5",
            seen={"2": "ann@example.com"},
            changed={"2": "a@b.example"},
            seen_updated="2026-11-01 00:00:00",
        )
    with pytest.raises(EditConflict):  # the answer itself changed
        gfa.set_answers(api, "gf/v2/entries/5", seen={"2": "old@b.example"}, changed={"2": "x"})
    with pytest.raises(ValueError):
        gfa.set_answers(api, "gf/v2/entries/5", seen={}, changed={"is_read": "1"})
    assert api.puts == []


# -- the wp-admin map's plugin rows -----------------------------------------------------


def test_plugin_screens_reach_each_place_on_sites_that_have_the_plugin() -> None:
    site_nodes = {n.key for n in WORDPRESS_TREE.template("site")}
    for screen in ADMIN_MAP:
        assert screen.node in site_nodes, screen.key
    every = ["gf/v2", "qaf/v1", "redirection/v1", "wc/v3", "tribe/events/v1", "pmpro/v1"]
    wanted = {
        "forms": {"gf_forms", "gf_settings", "qaf_forms"},
        "form_entries": {"gf_entries"},
        "redirects": {"redirection"},
        "not_found_log": {"redirection_404s"},
        "shop": {"wc_products", "wc_status", "wc_extensions"},
        "shop_orders": {"wc_orders"},
        "shop_reports": {"wc_reports"},
        "shop_settings": {"wc_settings"},
        "events_venues": {"events_venues"},
        "membership_levels": {"pmpro_levels"},
        "membership_orders": {"pmpro_orders"},
        "membership_discount_codes": {"pmpro_discount_codes"},
    }
    for node, keys in wanted.items():
        assert {s.key for s in screens_for(node, every)} == keys, node
    members = {s.key for s in screens_for("memberships", every)}
    assert {"pmpro_members", "pmpro_reports", "pmpro_settings"} <= members
    assert screens_for("redirects", ["wp/v2"]) == []


def test_store_settings_no_longer_claims_settings_change_only_in_wp_admin() -> None:
    [row] = [
        r for r in map_rows(SITE, "https://r.example", ("wc/v3",), {}) if r.key == "wc_settings"
    ]
    assert row.status == "both" and "Change Setting" in row.raw["why"]
    assert row.link == "https://r.example/wp-admin/admin.php?page=wc-settings"


# -- the rows that offer them ---------------------------------------------------------


def test_each_command_is_offered_where_it_belongs_with_help_and_a_reason() -> None:
    offered = {
        kind: {r.command_id for r in WORDPRESS_ACTIONS.rows_for(kind)}
        for kind in ("item", "plugin", "theme", "update", "value")
    }
    assert ITEM_VERSIONS.command_id in offered["item"]
    for kind in ("plugin", "theme", "update"):
        assert UPDATE_CHECK.command_id in offered[kind], kind
    assert CHECK_LINKS.command_id in offered["value"]
    for row in (ITEM_VERSIONS, UPDATE_CHECK, CHECK_LINKS):
        assert row.help and KEYLESS[row.command_id], row.command_id
