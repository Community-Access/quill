"""The editor's doors into the Workbench (PRD 14), Shop, Podcast and People's rest, in the frame.

Reuses the fake site of ``test_wp_workbench_window``; work runs inline, so a
load or a write is finished when the call returns.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.core.wordpress import local as lc  # noqa: E402
from quill.core.wordpress import site_taxonomies as tx  # noqa: E402
from quill.core.wordpress.workbench_actions import command  # noqa: E402
from quill.ui import wordpress_dialogs as dlg  # noqa: E402
from quill.ui import wordpress_workbench_dialogs as wdlg  # noqa: E402
from quill.ui import wordpress_workbench_editor_side as side  # noqa: E402
from quill.ui.wordpress_workbench_window import SEP, WordPressWorkbenchProvider  # noqa: E402
from quill.ui.workbench_frame import NodeRef, WorkbenchFrame  # noqa: E402
from tests.unit.ui.wordpress.test_wp_workbench_window import (  # noqa: E402
    SITE,
    _Commands,
    _go,
    _inline,
    _select,
)
from tests.unit.ui.wordpress.test_wp_workbench_wpab import SiteApi  # noqa: E402

UPLOADS = "https://radio.example/wp-content/uploads/2026/11"


class EditorApi(SiteApi):
    """The fake site, with media, a shop, people's passwords and room for new people."""

    def __init__(self) -> None:
        super().__init__()
        self.namespaces = ["wp/v2", "wc/v3"]
        self.role = "administrator"
        self.posts[1]["content"] = {"raw": '<!-- wp:audio {"id":5} -->\n<figure></figure>'}

    def get(self, route: str, **params: Any) -> Any:
        if route == "wp/v2/users/me":
            me = super().get(route, **params)
            if self.role == "administrator":
                me["capabilities"].update({"edit_users": True, "create_users": True})
            return me
        if route == "":
            return {
                "name": SITE,
                "home": "https://radio.example",
                "namespaces": self.namespaces,
                "routes": {"/wp/v2/posts": {}},
            }
        if route == "wp/v2/users/4/application-passwords":
            return [{"uuid": "u-1", "name": "Ann's phone", "created": "2026-10-01T10:00:00"}]
        return super().get(route, **params)

    def iter_collection(self, route: str, params: Any = None, **kw: Any):
        if route == "wp/v2/media":
            self.reads.append((route, dict(params or {})))
            yield {
                "id": 5,
                "title": {"raw": "Fair"},
                "mime_type": "image/jpeg",
                "media_type": "image",
                "source_url": f"{UPLOADS}/fair.jpg",
                "alt_text": "Volunteers",
                "caption": {"raw": ""},
                "description": {"raw": ""},
                "media_details": {"width": 800, "height": 600, "filesize": 4000},
                "date_gmt": "2026-11-01T10:00:00",
                "post": 0,
            }
            return
        if route == "wc/v3/orders":
            yield {"id": 77, "number": "1077", "status": "processing", "total": "9.00"}
            return
        if route == "wp/v2/users" and (params or {}).get("_fields") == "id,email,username":
            yield {"id": 3, "email": "jeff@example.com", "username": "jeff"}
            return
        yield from super().iter_collection(route, params, **kw)

    def delete(self, route: str, **params: Any) -> Any:
        self.writes.append(("DELETE", route, params))
        return {}


def _frame(commands: Any, api: Any, said: list[str]) -> WorkbenchFrame:
    provider = WordPressWorkbenchProvider(
        commands, announce=said.append, data_dir=None, api_for=lambda _p: api
    )
    frame = WorkbenchFrame(provider, announce=said.append, run_background=_inline)
    frame.said = said  # type: ignore[attr-defined]
    frame.api = api  # type: ignore[attr-defined]
    frame.commands = commands  # type: ignore[attr-defined]
    return frame


@pytest.fixture
def bench(wx_session_app):
    tx.clear_cache()
    said: list[str] = []
    frame = _frame(_Commands(said), EditorApi(), said)
    yield frame
    frame.frame.Destroy()
    tx.clear_cache()


# -- This Post in the Workbench ---------------------------------------------------------


def test_this_post_selects_the_documents_post_in_its_list(bench) -> None:
    bench.provider.go_to_item(SITE, "post", 2, "News")
    assert bench.current == NodeRef("site", "posts", SITE)
    row = bench.selected_row()
    assert row is not None and row.key == "2"
    assert bench.details.GetValue() == row.detail


def test_a_post_past_the_rows_loaded_is_searched_for_once_then_said(bench) -> None:
    bench.provider.go_to_item(SITE, "post", 99, "Ghost")
    assert bench.api.reads[-1][1].get("search") == "Ghost"
    assert any("Ghost is not in this list" in words for words in bench.said)


def test_a_custom_types_item_waits_for_discovery_then_is_selected(bench) -> None:
    bench.provider.go_to_item(SITE, "events", 32, "Fair")
    assert bench.current != NodeRef("site", "custom_type", f"{SITE}{SEP}events")
    bench.provider.start()  # discovery adds the Events node, then selects the item
    assert bench.current == NodeRef("site", "custom_type", f"{SITE}{SEP}events")
    assert bench.selected_row().key == "32"


def test_open_on_document_opens_on_the_copys_site_and_post(bench, monkeypatch) -> None:
    monkeypatch.setattr(side, "_open", lambda _commands, _node="": bench)
    profile = bench.commands.sites().sites[0]
    copy = lc.WorkingCopy("s1", "post", "local", remote_id=1, title="Hello")
    assert side.open_on_document(bench.commands, copy, profile)
    assert bench.selected_row().key == "1"
    unsent = lc.WorkingCopy("s1", "post", "local2", title="Draft")
    assert not side.open_on_document(bench.commands, unsent, profile)
    assert "Save Draft to Site" in bench.said[-1]


def test_file_wordpress_this_post_runs_through_the_shared_commands(wp, monkeypatch) -> None:
    opened: list[tuple[str, int]] = []

    def record(_commands: Any, copy: Any, profile: Any) -> None:
        opened.append((profile.id, copy.remote_id))

    monkeypatch.setattr(side, "open_on_document", record)
    wp.cmd_this_post_in_workbench()
    assert "This Post in the Workbench works in a WordPress page or post" in wp.host.said
    copy = lc.WorkingCopy("radio", "page", lc.new_local_id(), remote_id=41, title="Schedule")
    wp.host.open_path(wp.local.write_document(copy))
    wp.cmd_this_post_in_workbench()
    assert opened == [("radio", 41)]


# -- picking mode -----------------------------------------------------------------------


class _Window:
    def __init__(self) -> None:
        self.raised = 0

    def Raise(self) -> None:  # noqa: N802 - wx's name
        self.raised += 1


def test_insert_from_the_library_picks_in_the_workbench_and_enter_inserts(
    wx_session_app, wp, wp_dialogs, monkeypatch
) -> None:
    from quill.ui import wordpress_item_dialogs as idlg

    copy = lc.WorkingCopy("radio", "page", lc.new_local_id(), remote_id=41, title="Schedule")
    copy.text_format = "html"
    wp.host.open_path(wp.local.write_document(copy))
    wp.host.parent = window = _Window()
    said: list[str] = []
    frame = _frame(wp, EditorApi(), said)
    try:
        monkeypatch.setattr(side, "_open", lambda _commands, _node="": frame)
        wp_dialogs.answer(
            "ask_image",
            idlg.ImageAnswer(
                alt="Volunteers", decorative=False, caption="", width=0, featured=False, link=""
            ),
        )
        wp.cmd_insert_from_library()
        assert frame.current is not None and frame.current.key == "media"
        assert frame.provider.picking
        _select(frame, 0)
        frame.default_action()  # Enter
        assert 'class="wp-image-5"' in wp.host.text
        assert window.raised == 1 and not frame.provider.picking
        frame.default_action()  # picking is over: Enter is View or Play again
        assert wp.host.text.count("wp-image-5") == 1
    finally:
        frame.frame.Destroy()


def test_insert_into_the_document_outside_picking_says_how(bench) -> None:
    _go(bench, NodeRef("site", "media", SITE))
    _select(bench, 0)
    bench.run(command("insert_picked"))
    assert "Insert > Picture from the Media Library" in bench.said[-1]


def test_picking_refuses_a_file_from_another_site(bench) -> None:
    inserted: list[Any] = []
    bench.provider.start_picking("Another Site", "Schedule", inserted.append)
    _go(bench, NodeRef("site", "media", SITE))
    _select(bench, 0)
    bench.default_action()
    assert not inserted and "Another Site's Media" in bench.said[-1]


# -- Shop and Podcast ---------------------------------------------------------------------


def test_shop_orders_load_in_the_frame_and_enter_opens_the_dashboard(bench) -> None:
    _go(bench, NodeRef("site", "shop_orders", SITE))
    assert [row.title for row in bench.rows] == ["Shop order 1077"]
    _select(bench, 0)
    bench.default_action()
    assert bench.commands.host.opened == [
        "https://radio.example/wp-admin/post.php?post=77&action=edit"
    ]


def test_shop_without_woocommerce_says_so_in_the_details(bench) -> None:
    bench.api.namespaces = ["wp/v2"]
    _go(bench, NodeRef("site", "shop", SITE))
    assert "does not list WooCommerce" in bench.details.GetValue()


def test_podcast_lists_the_episode_posts_and_enter_opens_one(bench) -> None:
    _go(bench, NodeRef("site", "podcast", SITE))
    assert [row.title for row in bench.rows] == ["News"]
    _select(bench, 0)
    bench.default_action()
    assert bench.commands.opened == [("post", 2)]


# -- People > Users, the rest ---------------------------------------------------------------


def test_their_application_passwords_read_and_revoke(bench, monkeypatch) -> None:
    _go(bench, NodeRef("site", "users", SITE))
    _select(bench, 1)  # Ann
    shown: list[list[str]] = []

    def choose(*_a: Any, rows: Any, **_k: Any) -> int:
        shown.append(list(rows))
        return 0

    monkeypatch.setattr(dlg, "ask_choice", choose)
    monkeypatch.setattr(dlg, "confirm", lambda *_a, **_k: True)
    bench.run(command("user_app_passwords"))
    assert shown[0][0].startswith("Ann's phone, made ")
    assert ("DELETE", "wp/v2/users/4/application-passwords/u-1", {}) in bench.api.writes
    assert bench.said[-1] == f"Revoked Ann's phone for Ann on {SITE}."


def test_an_editor_hears_why_others_passwords_are_closed(bench) -> None:
    bench.api.role = "editor"
    _go(bench, NodeRef("site", "users", SITE))
    _select(bench, 1)
    bench.run(command("user_app_passwords"))
    assert "(edit users) needs the Administrator role" in bench.said[-1]
    assert not bench.api.writes


def test_sign_out_everywhere_says_why_and_opens_their_wp_admin_screen(bench) -> None:
    _go(bench, NodeRef("site", "users", SITE))
    _select(bench, 1)
    bench.run(command("sign_out_everywhere"))
    assert "no route that lists them" in bench.said[-1]
    assert bench.commands.host.opened == ["https://radio.example/wp-admin/user-edit.php?user_id=4"]


def test_invite_from_a_spreadsheet_previews_then_adds_each_person(
    bench, monkeypatch, tmp_path: Path
) -> None:
    sheet = tmp_path / "people.csv"
    sheet.write_text(
        "email,role,name\nann.new@example.com,author,Ann New\njeff@example.com,editor,Jeff\n",
        encoding="utf-8",
    )
    previews: list[dict[str, Any]] = []
    monkeypatch.setattr(wdlg, "choose_spreadsheet", lambda *_a, **_k: sheet)
    monkeypatch.setattr(wdlg, "ask_preview", lambda *_a, **k: previews.append(k) or True)
    _go(bench, NodeRef("site", "users", SITE))
    _select(bench, 0)
    bench.run(command("invite_spreadsheet"))
    first = "Add Ann New as Author, signing in as ann.new, ann.new@example.com"
    assert previews[0]["lines"][0] == first
    assert "already has an account" in previews[0]["lines"][1]
    assert "sends no email" in previews[0]["summary"]
    posts = [w for w in bench.api.writes if w[:2] == ("POST", "wp/v2/users")]
    assert len(posts) == 1 and posts[0][2]["email"] == "ann.new@example.com"
    assert bench.said[-1] == f"Added 1 of 1 people to {SITE}."


def test_invite_cancelled_at_the_preview_sends_nothing(bench, monkeypatch, tmp_path) -> None:
    sheet = tmp_path / "people.csv"
    sheet.write_text("zed@example.com,author,Zed\n", encoding="utf-8")
    monkeypatch.setattr(wdlg, "choose_spreadsheet", lambda *_a, **_k: sheet)
    monkeypatch.setattr(wdlg, "ask_preview", lambda *_a, **_k: False)
    _go(bench, NodeRef("site", "users", SITE))
    _select(bench, 0)
    bench.run(command("invite_spreadsheet"))
    assert not [w for w in bench.api.writes if w[1] == "wp/v2/users"]
