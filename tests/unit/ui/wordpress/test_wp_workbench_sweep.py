"""WP-G, the site administration sweep, in the real frame on a fake site.

Redirects and the 404 log through the Redirection plugin's namespace, the
slug-change offer, Search and Upkeep, Administration Areas, privacy screens
and the audit's usage-before-trash. Every handler here is called.
"""

from __future__ import annotations

from typing import Any
from urllib.error import HTTPError

import pytest

wx = pytest.importorskip("wx")

from quill.core.wordpress import site_taxonomies as tx  # noqa: E402
from quill.core.wordpress.api import WordPressApiError  # noqa: E402
from quill.core.wordpress.workbench_actions import command  # noqa: E402
from quill.core.wordpress.workbench_coverage import THIRD_SWEEP  # noqa: E402
from quill.core.wordpress.workbench_rows import WbRow  # noqa: E402
from quill.ui import wordpress_dialogs as dlg  # noqa: E402
from quill.ui import wordpress_workbench_dialogs as wdlg  # noqa: E402
from quill.ui.wordpress_workbench_window import WordPressWorkbenchProvider  # noqa: E402
from quill.ui.workbench_frame import NodeRef, WorkbenchFrame  # noqa: E402
from tests.unit.ui.wordpress.test_wp_workbench_lists import PagedApi  # noqa: E402
from tests.unit.ui.wordpress.test_wp_workbench_window import (  # noqa: E402
    SITE,
    _Commands,
    _go,
    _inline,
)

_SITEMAP = (
    b"<sitemapindex><sitemap><loc>https://radio.example/wp-sitemap-posts-post-1.xml</loc>"
    b"</sitemap></sitemapindex>"
)


class _Response:
    def __init__(self, body: bytes) -> None:
        self.body = body

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_a: Any) -> None:
        return None

    def read(self) -> bytes:
        return self.body


class RedirectApi(PagedApi):
    """A site with the Redirection plugin, a sitemap and one overdue post."""

    timeout = 5.0

    def __init__(self, *, redirection: bool = True) -> None:
        super().__init__()
        self.role = "administrator"
        self.redirection = redirection
        self.redirects = [
            {
                "id": 4,
                "url": "/old/",
                "action_code": 301,
                "action_data": {"url": "/new/"},
                "hits": 3,
                "enabled": True,
                "group_id": 1,
            }
        ]
        self.posts.append({
            "id": 9,
            "title": {"raw": "Late show", "rendered": "Late show"},
            "status": "future",
            "date_gmt": "2020-01-01T00:00:00",
            "modified_gmt": "2020-01-01T00:00:00",
            "link": "https://radio.example/?p=9",
            "type": "post",
        })

    def _opener(self, request: Any, **_kw: Any) -> _Response:
        if request.full_url.endswith("/wp-sitemap.xml"):
            return _Response(_SITEMAP)
        raise HTTPError(request.full_url, 404, "Not Found", None, None)  # type: ignore[arg-type]

    def get(self, route: str, **params: Any) -> Any:
        if route == "" and self.redirection:
            answer = dict(super().get(route, **params))
            answer["namespaces"] = ["wp/v2", "redirection/v1", "wordfence/v1"]
            return answer
        if route == "redirection/v1/redirect":
            return {"items": list(self.redirects), "total": len(self.redirects)}
        if route == "redirection/v1/group":
            # 5.10.1 refuses group 1 here ("Invalid group"): the site's groups start at 2.
            return {
                "items": [
                    {"id": 2, "name": "Redirections", "module_id": 1, "enabled": True},
                    {"id": 6, "name": "Moved posts", "module_id": 1, "enabled": True},
                ],
                "total": 2,
            }
        if route == "redirection/v1/404":
            return {"items": [{"id": 1, "url": "/lost/", "created": "2026-11-12T10:00:00"}]}
        if route == "wp/v2/settings":
            return {"title": SITE}
        return super().get(route, **params)

    def delete(self, route: str, **params: Any) -> Any:
        if route.startswith("wp/v2/media/"):
            self.writes.append(("DELETE", route, params))
            raise WordPressApiError(
                "The site does not trash media.", status=501, wp_code="rest_trash_not_supported"
            )
        return super().delete(route, **params)


def _bench(api: RedirectApi, tmp_path: Any) -> WorkbenchFrame:
    said: list[str] = []
    commands = _Commands(said)
    provider = WordPressWorkbenchProvider(
        commands, announce=said.append, data_dir=tmp_path, api_for=lambda _p: api
    )
    frame = WorkbenchFrame(provider, announce=said.append, run_background=_inline)
    frame.said = said  # type: ignore[attr-defined]
    frame.api = api  # type: ignore[attr-defined]
    frame.commands = commands  # type: ignore[attr-defined]
    return frame


@pytest.fixture
def bench(wx_session_app, tmp_path):
    tx.clear_cache()
    frame = _bench(RedirectApi(), tmp_path)
    yield frame
    frame.frame.Destroy()
    tx.clear_cache()


@pytest.fixture
def plain(wx_session_app, tmp_path):
    tx.clear_cache()
    frame = _bench(RedirectApi(redirection=False), tmp_path)
    yield frame
    frame.frame.Destroy()
    tx.clear_cache()


def _answers(monkeypatch: pytest.MonkeyPatch, *texts: str) -> None:
    queue = list(texts)
    monkeypatch.setattr(dlg, "ask_text", lambda *a, **k: queue.pop(0))
    monkeypatch.setattr(dlg, "ask_choice", lambda *a, **k: 0)
    monkeypatch.setattr(wdlg, "ask_preview", lambda *a, **k: True)


def _posts_to(api: RedirectApi, route: str) -> list[Any]:
    return [body for method, r, body in api.writes if method == "POST" and r == route]


# -- redirects ----------------------------------------------------------------------


def test_redirects_list_and_add_through_new_here(bench, monkeypatch) -> None:
    _go(bench, NodeRef("site", "redirects", SITE))
    assert [(r.kind, r.cell("source")) for r in bench.rows] == [("redirect", "/old/")]
    _answers(monkeypatch, "/older/", "/newest/")
    bench.run(command("new_here"))
    (body,) = _posts_to(bench.api, "redirection/v1/redirect")
    assert body["url"] == "/older/" and body["action_data"] == {"url": "/newest/"}
    assert body["group_id"] == 2
    assert any("now leads to /newest/" in s for s in bench.said)


def test_change_turn_off_and_delete_a_redirect(bench, monkeypatch) -> None:
    _go(bench, NodeRef("site", "redirects", SITE))
    row = bench.rows[0]
    provider = bench.provider
    _answers(monkeypatch, "/old/", "/elsewhere/")
    provider.do_edit_redirect(None, row)
    (body,) = _posts_to(bench.api, "redirection/v1/redirect/4")
    assert body["action_data"] == {"url": "/elsewhere/"} and body["group_id"] == 1
    monkeypatch.setattr(dlg, "confirm", lambda *a, **k: True)
    provider.do_toggle_redirect(None, row)
    assert _posts_to(bench.api, "redirection/v1/bulk/redirect/disable") == [{"items": [4]}]
    provider.do_delete_redirect(None, row)
    assert _posts_to(bench.api, "redirection/v1/bulk/redirect/delete") == [{"items": [4]}]


def test_cancelling_a_delete_sends_nothing(bench, monkeypatch) -> None:
    _go(bench, NodeRef("site", "redirects", SITE))
    monkeypatch.setattr(dlg, "confirm", lambda *a, **k: False)
    bench.provider.do_delete_redirect(None, bench.rows[0])
    assert not bench.api.writes


def test_test_an_address_follows_the_list_and_sends_nothing(bench, monkeypatch) -> None:
    _go(bench, NodeRef("site", "redirects", SITE))
    shown: list[str] = []
    monkeypatch.setattr(dlg, "ask_text", lambda *a, **k: k["value"])
    monkeypatch.setattr(dlg, "show_report", lambda *a, **k: shown.append(k["text"]))
    bench.provider.do_test_address(None, bench.rows[0])
    assert shown and shown[0].startswith("/old/ leads to /new/")
    assert not bench.api.writes


def test_the_404_log_lists_and_redirects_an_address(bench, monkeypatch) -> None:
    _go(bench, NodeRef("site", "not_found_log", SITE))
    assert [(r.kind, r.cell("address")) for r in bench.rows] == [("not_found", "/lost/")]
    _answers(monkeypatch, "/lost/", "/found/")
    monkeypatch.setattr(dlg, "ask_choice", lambda *a, **k: 1 if "Group" in k["prompt"] else 0)
    bench.provider.do_redirect_not_found(None, bench.rows[0])
    (body,) = _posts_to(bench.api, "redirection/v1/redirect")
    assert body["url"] == "/lost/" and body["action_data"] == {"url": "/found/"}
    assert body["group_id"] == 6


def test_without_the_plugin_redirects_say_where_they_are(plain) -> None:
    _go(plain, NodeRef("site", "redirects", SITE))
    (row,) = plain.rows
    assert row.kind == "sweep_area" and "in wp-admin only" in row.cell("where")
    plain.provider.do_add_redirect(NodeRef("site", "redirects", SITE), None)
    assert any("does not have the Redirection plugin" in s for s in plain.said)
    assert not plain.api.writes


def test_a_new_slug_offers_a_redirect_where_the_plugin_is(bench, monkeypatch) -> None:
    _go(bench, NodeRef("site", "posts", SITE))
    monkeypatch.setattr(dlg, "confirm", lambda *a, **k: True)
    row = WbRow("item", SITE, "2", {"title": "News"}, "", route="wp/v2/posts/2")
    bench.provider.offer_redirect(row, "https://radio.example/old-news")
    (body,) = _posts_to(bench.api, "redirection/v1/redirect")
    assert body["url"] == "/old-news" and body["action_data"] == {
        "url": "https://radio.example/news"
    }
    assert body["group_id"] == 2


# -- upkeep, areas, privacy ------------------------------------------------------------


def test_search_and_upkeep_lists_each_check_with_its_source(bench) -> None:
    _go(bench, NodeRef("site", "site_upkeep", SITE))
    states = {r.key: r.cell("state") for r in bench.rows}
    assert states["visibility"] == "probably visible"
    assert states["sitemap"] == "found"
    assert states["overdue:9"] == "overdue"
    assert states["certificate"] == "valid now"
    assert all("Where this comes from:" in r.detail for r in bench.rows)


def test_administration_areas_have_every_row_and_go_there(bench) -> None:
    _go(bench, NodeRef("site", "admin_areas", SITE))
    rows = {r.key: r for r in bench.rows}
    assert set(rows) == {a.area for a in THIRD_SWEEP}
    assert rows["Security, sign-ins and two-factor"].status == "schema_built"
    assert rows["Backups"].status == "wp_admin_only"
    bench.provider.do_open_area(None, rows["Backups"])
    assert bench.commands.host.opened[-1].endswith("/wp-admin/plugins.php?plugin_status=active")
    bench.provider.do_open_area(None, rows["Redirects"])
    assert bench.current == NodeRef("site", "redirects", SITE)


def test_opening_a_privacy_screen_never_claims_the_request_was_done(bench) -> None:
    _go(bench, NodeRef("site", "privacy_requests", SITE))
    export = bench.rows[0]
    bench.provider.do_open_privacy(None, export)
    assert bench.commands.host.opened == [export.link]
    assert "QUILL cannot see whether they were" in bench.said[-1]


# -- usage before trash -------------------------------------------------------------


def test_a_finding_shows_its_usage_then_trashes_after_the_preview(bench, monkeypatch) -> None:
    _go(bench, NodeRef("site", "content_audit", SITE))
    row = next(r for r in bench.rows if r.cell("problem") == "Very short")
    assert row.kind == "finding"
    shown: list[str] = []
    monkeypatch.setattr(dlg, "show_report", lambda *a, **k: shown.append(k["text"]))
    bench.provider.do_show_usage(None, row)
    assert shown == ["Nothing in the posts and pages read links to it."]
    previews: list[Any] = []
    monkeypatch.setattr(wdlg, "ask_preview", lambda *a, **k: (previews.append(k), False)[1])
    bench.provider.do_trash_finding(None, row)
    assert previews and not bench.api.writes
    monkeypatch.setattr(wdlg, "ask_preview", lambda *a, **k: True)
    bench.provider.do_trash_finding(None, row)
    assert ("DELETE", row.raw["route"], {}) in bench.api.writes


def test_media_is_never_deleted_for_good_from_housekeeping(bench, monkeypatch) -> None:
    monkeypatch.setattr(wdlg, "ask_preview", lambda *a, **k: True)
    row = WbRow(
        "finding",
        SITE,
        "10:unused",
        {"problem": "Used nowhere"},
        "",
        raw={"route": "wp/v2/media/10", "title": "logo.png", "media": True, "places": []},
    )
    bench.provider.do_trash_finding(None, row)
    assert bench.api.writes == [("DELETE", "wp/v2/media/10", {})]
    assert "keeps no Trash for media, so logo.png was not deleted" in bench.said[-1]


class _NoGroupApi(RedirectApi):
    """A site whose Redirection setup never ran: no group until one is made."""

    def __init__(self) -> None:
        super().__init__()
        self.groups: list[dict[str, Any]] = []

    def get(self, route: str, **params: Any) -> Any:
        if route == "redirection/v1/group":
            return {"items": list(self.groups), "total": len(self.groups)}
        return super().get(route, **params)

    def post(self, route: str, body: Any = None, **params: Any) -> Any:
        if route == "redirection/v1/group":
            self.writes.append(("POST", route, body))
            self.groups.append({"id": 3, "name": body["name"], "module_id": 1, "enabled": True})
            return {"items": list(self.groups), "total": 1}
        return super().post(route, body, **params)


def test_no_group_offers_to_make_redirections_then_adds_the_redirect(
    wx_session_app, tmp_path, monkeypatch
) -> None:
    frame = _bench(_NoGroupApi(), tmp_path)
    try:
        _go(frame, NodeRef("site", "redirects", SITE))
        asked: list[str] = []
        monkeypatch.setattr(dlg, "confirm", lambda *a, **k: (asked.append(k["message"]), True)[1])
        _answers(monkeypatch, "/older/", "/newest/")
        frame.run(command("new_here"))
        assert asked and "has no group yet" in asked[0]
        (group,) = _posts_to(frame.api, "redirection/v1/group")
        assert group == {"name": "Redirections", "moduleId": 1}
        (body,) = _posts_to(frame.api, "redirection/v1/redirect")
        assert body["group_id"] == 3
        assert any("Made the Redirections group" in s for s in frame.said)
    finally:
        frame.frame.Destroy()


def test_no_group_and_no_thanks_sends_nothing(wx_session_app, tmp_path, monkeypatch) -> None:
    frame = _bench(_NoGroupApi(), tmp_path)
    try:
        _go(frame, NodeRef("site", "redirects", SITE))
        monkeypatch.setattr(dlg, "confirm", lambda *a, **k: False)
        _answers(monkeypatch, "/older/", "/newest/")
        frame.run(command("new_here"))
        assert not _posts_to(frame.api, "redirection/v1/group")
        assert not _posts_to(frame.api, "redirection/v1/redirect")
    finally:
        frame.frame.Destroy()


class _NoTablesApi(_NoGroupApi):
    """Redirection's setup never ran: it refuses to make a group too."""

    def post(self, route: str, body: Any = None, **params: Any) -> Any:
        if route == "redirection/v1/group":
            raise WordPressApiError("Invalid group or parameters", status=400)
        return super().post(route, body, **params)


def test_a_plugin_that_cannot_make_a_group_says_to_finish_its_setup(
    wx_session_app, tmp_path, monkeypatch
) -> None:
    frame = _bench(_NoTablesApi(), tmp_path)
    try:
        _go(frame, NodeRef("site", "redirects", SITE))
        monkeypatch.setattr(dlg, "confirm", lambda *a, **k: True)
        _answers(monkeypatch, "/older/", "/newest/")
        frame.run(command("new_here"))
        assert not _posts_to(frame.api, "redirection/v1/redirect")
        assert any("setup was never finished" in s for s in frame.said)
    finally:
        frame.frame.Destroy()
