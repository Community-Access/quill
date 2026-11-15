"""Self-lockout guards, ACF, QUILL Site Types, stale claims and return context (complete.md WP-A/B).

The real provider and shared frame over a fake site; background work runs
inline and dialogs are answered by replacing the helpers the commands import.
"""

from __future__ import annotations

from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.core.wordpress import site_taxonomies as tx  # noqa: E402
from quill.core.wordpress.site_types_plugin import NAMESPACE as QST  # noqa: E402
from quill.core.wordpress.sites import SiteProfile, SiteStore  # noqa: E402
from quill.core.wordpress.workbench_actions import WORDPRESS_ACTIONS, command  # noqa: E402
from quill.core.wordpress.workbench_admin_actions import KEYLESS  # noqa: E402
from quill.core.wordpress.workbench_rows import WbRow  # noqa: E402
from quill.ui import wordpress_dialogs as dlg  # noqa: E402
from quill.ui import wordpress_workbench_dialogs as wdlg  # noqa: E402
from quill.ui import wordpress_workbench_window as window  # noqa: E402
from quill.ui.wordpress_workbench_window import SEP, WordPressWorkbenchProvider  # noqa: E402
from quill.ui.workbench_frame import NodeRef, WorkbenchFrame  # noqa: E402

SITE = "Community Radio"


class _Address:
    is_wpcom = False
    wpcom_site = ""
    site_url = "https://radio.example"


class _Auth:
    kind = "app_password"
    username = "jeff"


class Api:
    def __init__(self) -> None:
        self.address, self.auth = _Address(), _Auth()
        self.site_name = SITE
        self.writes: list[tuple[str, str, Any]] = []
        self.namespaces = ["wp/v2", QST]
        self.role = "administrator"
        self.posts = [
            {"id": n, "title": {"raw": t, "rendered": t}, "status": "draft", "author": 3,
             "modified_gmt": "2026-11-01T10:00:00", "link": f"https://radio.example/?p={n}",
             "type": "post", "acf": {"venue": "Hall"}}
            for n, t in ((1, "Alpha"), (2, "Beta"), (3, "Gamma"))
        ]  # fmt: skip
        self.events = [{"id": 9, "title": {"raw": "Fair", "rendered": "Fair"}, "status": "draft",
                        "type": "event", "modified_gmt": "2026-11-01T10:00:00"}]  # fmt: skip

    def get(self, route: str, **params: Any) -> Any:
        if route == "wp/v2/users/me":
            caps = {"edit_posts", "publish_posts", "delete_posts", "edit_pages", "list_users"}
            if self.role == "administrator":
                caps |= {"promote_users", "manage_options", "activate_plugins", "delete_users",
                         "edit_users", "moderate_comments", "upload_files"}  # fmt: skip
            return {"id": 3, "name": "Jeff", "username": "jeff", "roles": [self.role],
                    "capabilities": dict.fromkeys(caps, True)}  # fmt: skip
        if route == "":
            return {"name": SITE, "home": "https://radio.example", "namespaces": self.namespaces,
                    "routes": {"/wp/v2/posts": {}}}  # fmt: skip
        if route == "wp/v2/types":
            return {"post": {"name": "Posts", "rest_base": "posts"},
                    "event": {"name": "Events", "rest_base": "events"},
                    "book": {"name": "Books", "rest_base": "book"}}  # fmt: skip
        if route == "wp/v2/taxonomies":
            return {"category": {"name": "Categories", "rest_base": "categories",
                                 "types": ["post"]}}  # fmt: skip
        if route == "wp/v2/settings":
            return {"title": "Radio", "posts_per_page": 10, "show_on_front": "page",
                    "page_on_front": 0, "page_for_posts": 7}  # fmt: skip
        if route == "wp/v2/pages":
            return [{"id": 7, "title": {"rendered": "News"}, "link": "https://radio.example/news/"}]
        if route == f"{QST}/field-groups":
            return [{"id": "facts", "title": "Facts", "attach": {"post_types": ["book"]},
                     "fields": [{"name": "isbn", "label": "ISBN", "kind": "text",
                                 "required": False, "choices": []}]}]  # fmt: skip
        if route.startswith("wp/v2/posts/"):
            return dict(next(p for p in self.posts if p["id"] == int(route.rsplit("/", 1)[1])))
        if route.startswith("wp/v2/users/"):
            return {"id": int(route.rsplit("/", 1)[1]), "name": "Jeff", "roles": [self.role]}
        if route == f"{QST}/types":
            return [{"slug": "book", "name": "Books"}]
        if route == f"{QST}/kinds":
            return [{"kind": "text"}, {"kind": "picture"}]
        if route == f"{QST}/export":
            return {"filename": "quill-site-types-export.php", "content": "<?php\n// book\n"}
        if route.startswith(QST):
            return []
        return []

    def request(self, method: str, route: str, **kw: Any) -> Any:
        class _R:
            payload: Any = {}
            total = 0

        if method == "OPTIONS" and route == "wp/v2/posts":
            _R.payload = {"schema": {"properties": {"acf": {"type": "object", "properties": {
                "venue": {"type": "string"}, "seats": {"type": "integer"}}}}}}  # fmt: skip
        return _R()

    def iter_collection(self, route: str, params: Any = None, **_kw: Any):
        if route == "wp/v2/posts":
            yield from (dict(p) for p in self.posts)
        elif route == "wp/v2/events":
            yield from (dict(e) for e in self.events)
        elif route == "wp/v2/users":
            yield {"id": 3, "name": "Jeff", "roles": [self.role]}
            yield {"id": 4, "name": "Ann", "roles": ["author"]}
            yield {"id": 5, "name": "Bo", "roles": ["administrator"]}

    def post(self, route: str, body: Any = None, **_p: Any) -> Any:
        self.writes.append(("POST", route, body))
        if route.startswith("wp/v2/posts/"):
            post = next(p for p in self.posts if p["id"] == int(route.rsplit("/", 1)[1]))
            for key, value in (body or {}).items():
                post[key] = {**post.get(key, {}), **value} if key == "acf" else value
            return dict(post)
        return dict(body or {})

    def delete(self, route: str, **params: Any) -> Any:
        self.writes.append(("DELETE", route, params))
        if route.startswith(QST):
            return {"deleted": True, "previous": {"slug": "book", "name": "Books"}}
        return {}


class _Host:
    def __init__(self, said: list[str]) -> None:
        self.said, self.parent, self.opened = said, None, []

    def announce(self, text: str) -> None:
        self.said.append(text)

    def open_in_browser(self, url: str) -> None:
        pass

    def open_path(self, path: Any) -> None:
        self.opened.append(path)


class _Commands:
    def __init__(self, said: list[str]) -> None:
        self.host = _Host(said)
        self.items: list[tuple[str, int]] = []

    def sites(self) -> SiteStore:
        return SiteStore([SiteProfile("s1", SITE, "https://radio.example", "jeff")], "s1")

    def open_item(self, _profile: SiteProfile, kind: str, item_id: int) -> None:
        self.items.append((kind, item_id))

    def review(self, profile: SiteProfile, url: str, **_kw: Any) -> None:
        self.reviewed = (profile.name, url)


def _inline(_name: str, work: Any, done: Any, failed: Any) -> None:
    try:
        result = work()
    except Exception as exc:  # noqa: BLE001
        failed(exc)
        return
    done(result)


@pytest.fixture
def bench(wx_session_app, tmp_path):
    tx.clear_cache()
    said: list[str] = []
    api = Api()
    commands = _Commands(said)
    provider = WordPressWorkbenchProvider(
        commands, announce=said.append, data_dir=tmp_path, api_for=lambda _p: api
    )
    frame = WorkbenchFrame(provider, announce=said.append, run_background=_inline)
    frame.said, frame.api, frame.commands = said, api, commands  # type: ignore[attr-defined]
    yield frame
    window._OPEN.pop("wordpress", None)
    frame.frame.Destroy()
    tx.clear_cache()


@pytest.fixture
def answers(monkeypatch):
    """Previews and choices, recorded and answered from a queue (yes and the first row)."""
    seen: dict[str, list[Any]] = {"previews": [], "texts": [], "choices": []}
    replies: dict[str, list[Any]] = {"preview": [], "text": [], "choice": []}

    def preview(*_a: Any, **kw: Any) -> bool:
        seen["previews"].append(kw)
        return replies["preview"].pop(0) if replies["preview"] else True

    def text(*_a: Any, **kw: Any) -> Any:
        seen["texts"].append(kw)
        return replies["text"].pop(0) if replies["text"] else ""

    def choice(*_a: Any, **kw: Any) -> Any:
        seen["choices"].append(kw)
        return replies["choice"].pop(0) if replies["choice"] else 0

    monkeypatch.setattr(wdlg, "ask_preview", preview)
    monkeypatch.setattr(dlg, "ask_text", text)
    monkeypatch.setattr(dlg, "ask_choice", choice)
    monkeypatch.setattr(dlg, "confirm", lambda *a, **k: True)
    return seen, replies


@pytest.fixture
def sheets(monkeypatch):
    from quill.ui import workbench_sheet_editor as editor

    opened: list[Any] = []
    monkeypatch.setattr(editor.WorkbenchSheetEditor, "show", lambda self: opened.append(self) or 0)
    return opened


def _go(frame: WorkbenchFrame, ref: NodeRef) -> None:
    assert frame.select(ref), ref
    if frame.current != ref:
        frame._show_node(ref, remember=True)


def _pick(frame: WorkbenchFrame, title: str) -> WbRow:
    index = next(i for i, r in enumerate(frame.rows) if r.title == title)
    frame.focus_row(index)
    return frame.rows[index]


# -- self-lockout -------------------------------------------------------------------------


def test_revoking_the_password_quill_signs_in_with_is_refused(bench, answers) -> None:
    row = WbRow("app_password", SITE, "u1", {"name": "QUILL"}, "", status="current",
                route="wp/v2/users/me/application-passwords/u1")  # fmt: skip
    bench.provider.do_revoke(None, row)
    assert bench.api.writes == []
    assert "lock the Workbench out" in bench.said[-1]
    other = WbRow("app_password", SITE, "u2", {"name": "Phone"}, "",
                  route="wp/v2/users/me/application-passwords/u2")  # fmt: skip
    bench.provider.do_revoke(None, other)
    assert bench.api.writes[-1][:2] == ("DELETE", "wp/v2/users/me/application-passwords/u2")


def test_turning_off_the_connection_plugin_is_refused(bench, answers) -> None:
    row = WbRow("plugin", SITE, "application-passwords/ap.php", {"name": "AP"}, "",
                status="active", route="wp/v2/plugins/application-passwords/ap")  # fmt: skip
    bench.provider.do_toggle_plugin(None, row)
    assert bench.api.writes == [] and "through this plugin" in bench.said[-1]


def test_turning_a_plugin_off_forgets_the_site_claims_and_reads_them_again(bench, answers) -> None:
    _go(bench, NodeRef("site", "posts", SITE))
    ctx = bench.provider.ctx(SITE)
    old_account = ctx.account
    row = WbRow("plugin", SITE, "akismet/akismet.php", {"name": "Akismet"}, "",
                status="active", route="wp/v2/plugins/akismet/akismet")  # fmt: skip
    bench.provider.do_toggle_plugin(None, row)
    assert bench.api.writes[-1] == ("POST", "wp/v2/plugins/akismet/akismet", {"status": "inactive"})
    assert ctx.account is not None and ctx.account is not old_account  # read again, not reused


def test_your_own_role_is_refused_before_any_dialog_and_others_are_previewed(
    bench, answers
) -> None:
    seen, replies = answers
    _go(bench, NodeRef("site", "users", SITE))
    me = _pick(bench, "Jeff")
    bench.provider.do_change_role(None, me)
    assert seen["choices"] == [] and "your own Administrator role" in bench.said[-1]
    ann = _pick(bench, "Ann")
    replies["choice"].append(3)  # Editor
    replies["preview"].append(False)
    bench.provider.do_change_role(None, ann)
    preview = seen["previews"][-1]
    assert preview["lines"][0] == "Ann: Author becomes Editor"
    assert not [w for w in bench.api.writes if w[1] == "wp/v2/users/4"]  # cancelled: nothing sent
    replies["choice"].append(3)
    bench.provider.do_change_role(None, ann)
    assert ("POST", "wp/v2/users/4", {"roles": ["editor"]}) in bench.api.writes


def test_removing_yourself_is_refused_before_any_dialog(bench, answers) -> None:
    seen, _replies = answers
    _go(bench, NodeRef("site", "users", SITE))
    bench.provider.do_remove_user(None, _pick(bench, "Jeff"))
    assert seen["choices"] == [] and "your own account" in bench.said[-1]


def test_a_role_saved_from_your_own_sheet_meets_the_same_guard(bench, sheets, answers) -> None:
    _go(bench, NodeRef("site", "users", SITE))
    _pick(bench, "Jeff")
    bench.run(command("sheet"))
    sheet = sheets[-1]
    sheet.controls["roles"].SetStringSelection(
        next(c for c in sheet.controls["roles"].GetStrings() if "ditor" in c)
    )
    sheet.collect()
    sheet._on_save(sheet.state)
    assert not [w for w in bench.api.writes if w[1] == "wp/v2/users/3"]
    assert "your own Administrator role" in bench.said[-1]


def test_a_setting_is_previewed_and_cancel_sends_nothing(bench, sheets, answers) -> None:
    seen, replies = answers
    _go(bench, NodeRef("site", "settings", SITE))
    bench.focus_row(next(i for i, r in enumerate(bench.rows) if r.key == "title"))
    bench.run(command("sheet"))
    sheet = sheets[-1]
    sheet.controls["value"].ChangeValue("Community Radio")
    sheet.collect()
    replies["preview"].append(False)
    sheet._on_save(sheet.state)
    assert seen["previews"][-1]["lines"] == ["Site title (title): Radio becomes Community Radio"]
    assert bench.api.writes == []
    sheet._on_save(sheet.state)
    assert ("POST", "wp/v2/settings", {"title": "Community Radio"}) in bench.api.writes


# -- Advanced Custom Fields --------------------------------------------------------------


def test_acf_fields_show_on_properties_and_save_as_acf(bench, sheets, answers) -> None:
    _go(bench, NodeRef("site", "posts", SITE))
    _pick(bench, "Alpha")
    bench.run(command("sheet"))
    sheet = sheets[-1]
    assert sheet.sheet.pages[-1].title == "Advanced Custom Fields"
    assert sheet.controls["acf.venue"].GetValue() == "Hall"
    sheet.controls["acf.venue"].ChangeValue("Barn")
    sheet.collect()
    sheet._on_save(sheet.state)
    assert bench.api.writes[-1] == ("POST", "wp/v2/posts/1", {"acf": {"venue": "Barn"}})
    assert bench.said[-1].startswith("Saved 1 change to Alpha")
    bench.run(command("undo"))
    assert bench.api.writes[-1] == ("POST", "wp/v2/posts/1", {"acf": {"venue": "Hall"}})


# -- QUILL Site Types --------------------------------------------------------------------


def test_site_types_commands_have_help_a_reason_for_no_chord_and_a_handler(bench) -> None:
    offered = {a.command_id: a for a in WORDPRESS_ACTIONS.rows_for("model")}
    for verb in ("define_site_type", "stop_defining", "export_as_code"):
        assert offered[command(verb)].help and KEYLESS[command(verb)]
        assert callable(getattr(bench.provider, f"do_{verb}"))


def test_ctrl_n_on_content_model_defines_a_type_after_a_preview(bench, answers) -> None:
    seen, replies = answers
    _go(bench, NodeRef("site", "content_model", SITE))
    book = next(r for r in bench.rows if r.key == "book")
    assert book.cell("definition").startswith("Editable") and book.raw["editable_definition"]
    replies["choice"].append(0)  # a post type
    replies["text"] += ["film", "Films"]
    bench.provider.do_new_here(NodeRef("site", "content_model", SITE), None)
    assert "Define the post type Films" in seen["previews"][-1]["summary"]
    assert (
        "POST",
        f"{QST}/types",
        {"slug": "film", "name": "Films", "singular_name": "Films"},
    ) in (bench.api.writes)
    bench.run(command("undo"))
    assert bench.api.writes[-1][:2] == ("DELETE", f"{QST}/types/film")


def test_a_field_group_with_a_kind_the_site_lacks_is_refused_unsent(bench, answers) -> None:
    _seen, replies = answers
    _go(bench, NodeRef("site", "content_model", SITE))
    replies["choice"].append(2)  # a field group
    replies["text"] += ["facts", "Facts", "book", "isbn: text, tint: colourwheel"]
    bench.provider.do_define_site_type(NodeRef("site", "content_model", SITE), None)
    assert "no field kind called colourwheel" in bench.said[-1]
    assert not [w for w in bench.api.writes if w[1].startswith(QST)]


def test_stop_defining_only_what_site_types_defines_and_export_as_code(bench, answers) -> None:
    _go(bench, NodeRef("site", "content_model", SITE))
    post = next(r for r in bench.rows if r.key == "post")
    bench.provider.do_stop_defining(None, post)
    assert "not defined through QUILL Site Types" in bench.said[-1] and bench.api.writes == []
    book = next(r for r in bench.rows if r.key == "book")
    bench.provider.do_stop_defining(None, book)
    assert bench.api.writes[-1][:2] == ("DELETE", f"{QST}/types/book")
    bench.run(command("undo"))
    assert bench.api.writes[-1] == ("POST", f"{QST}/types", {"slug": "book", "name": "Books"})
    bench.provider.do_export_as_code(NodeRef("site", "content_model", SITE), None)
    path = bench.commands.host.opened[-1]
    assert path.name == "quill-site-types-export.php"
    assert path.read_bytes() == b"<?php\n// book\n"


def test_a_site_without_site_types_is_told_so(bench, answers) -> None:
    bench.api.namespaces = ["wp/v2"]
    _go(bench, NodeRef("site", "content_model", SITE))
    bench.provider.do_define_site_type(NodeRef("site", "content_model", SITE), None)
    assert "does not have the QUILL Site Types plugin" in bench.said[-1]


# -- stale claims ------------------------------------------------------------------------


def test_a_site_that_changed_is_read_again_and_said_once(bench, monkeypatch) -> None:
    monkeypatch.setattr(type(bench.provider), "_after_ui", staticmethod(lambda job: job()))
    _go(bench, NodeRef("site", "posts", SITE))
    ctx = bench.provider.ctx(SITE)
    assert bench.provider.recheck(ctx, now=1e9 - 1) == []  # nothing moved
    bench.api.namespaces = ["wp/v2", QST, "acf/v3"]
    bench.api.role = "editor"
    said = bench.provider.recheck(ctx, now=2e9)
    assert "the site's REST namespaces changed" in said and "your role is now editor" in said
    assert ctx.account.roles == ("editor",) and "acf/v3" in ctx.info.namespaces
    assert "changed since QUILL last looked" in bench.said[-1]
    assert bench.provider.recheck(ctx, now=2e9 + 1) == []  # not due again yet


# -- writing, custom types and context on return ------------------------------------------


def test_a_custom_type_opens_in_the_editor_under_its_own_route(bench) -> None:
    bench.provider.start()
    _go(bench, NodeRef("site", "custom_type", f"{SITE}{SEP}events"))
    _pick(bench, "Fair")
    bench.default_action()
    assert bench.commands.items == [("events", 9)]  # the REST base, which a save goes back to


def test_coming_back_to_the_workbench_keeps_node_row_and_filter(bench, monkeypatch) -> None:
    monkeypatch.setattr(window, "_OPEN", {"wordpress": bench})
    posts = NodeRef("site", "posts", SITE)
    _go(bench, posts)
    bench.filter.ChangeValue("a")
    bench.apply_filter()
    _pick(bench, "Gamma")
    bench.rebuild_tree()
    assert (bench.current, bench.filter.GetValue()) == (posts, "a"), bench.said
    window.open_workbench(bench.commands)  # Tools > WordPress Workbench again, no node asked
    assert bench.current == posts
    assert bench.filter.GetValue() == "a"
    assert bench.selected_row().title == "Gamma"
    window.open_workbench(bench.commands, node="comments")  # a door that names a node moves
    assert bench.current == NodeRef("site", "comments", SITE)


def test_the_status_bar_has_the_wordpress_cells(bench) -> None:
    """WP-R-002a: site, role, items, filter, loading and access, read live from the frame."""
    _go(bench, NodeRef("site", "posts", SITE))
    bench.filter.ChangeValue("a")
    bench.apply_filter()
    cells = {c.key: c for c in bench.provider.status_cells(bench)}
    assert {"site", "role", "items", "filter", "loading", "waiting", "access"} <= set(cells)
    assert cells["site"].text() == SITE
    assert cells["role"].text() == f"Administrator on {SITE}"
    assert cells["items"].text() == "3 shown"
    assert cells["filter"].text() and cells["loading"].text().startswith("Up to date")
    assert cells["access"].text() == "Full"
    assert all(c.help for c in cells.values())


# -- the buildable remainder: settings examples, Visual Review, fields and kinds -------------


def test_each_setting_is_explained_with_the_sites_own_example(bench) -> None:
    _go(bench, NodeRef("site", "settings", SITE))
    rows = {r.key: r for r in bench.rows}
    assert rows["page_for_posts"].cell("value") == "News"
    assert rows["page_for_posts"].detail.endswith(
        "News, so visitors see your latest posts at https://radio.example/news/."
    )
    assert "show 10 posts" in rows["posts_per_page"].detail
    settings = [r for r in bench.rows if r.kind == "setting"]
    assert all(len(r.detail.split(". ")) > 1 for r in settings)  # value, then the why


def test_visual_review_runs_the_editors_review_on_a_published_row(bench) -> None:
    offered = [a.command_id for a in WORDPRESS_ACTIONS.rows_for("item")]
    assert command("visual_review") in offered and KEYLESS[command("visual_review")]
    draft = WbRow("item", SITE, "1", {"title": "Alpha"}, "", status="draft",
                  link="https://radio.example/?p=1", subkind="post")  # fmt: skip
    bench.provider.do_visual_review(None, draft)
    assert "not published" in bench.said[-1] and not hasattr(bench.commands, "reviewed")
    live = WbRow("item", SITE, "2", {"title": "Beta"}, "", status="publish",
                 link="https://radio.example/beta/", subkind="post")  # fmt: skip
    bench.provider.do_visual_review(None, live)
    assert bench.commands.reviewed == (SITE, "https://radio.example/beta/")


def test_a_fields_own_sheet_saves_the_whole_group_after_a_preview(bench, sheets, answers) -> None:
    seen, replies = answers
    _go(bench, NodeRef("site", "content_model", SITE))
    group = next(r for r in bench.rows if r.key == "facts")
    replies["choice"].append(0)  # isbn
    bench.provider.do_edit_site_type_fields(None, group)
    sheet = sheets[-1]
    assert sheet.controls["label"].GetValue() == "ISBN"
    sheet.controls["help"].ChangeValue("The 13-digit number on the back.")
    sheet.controls["required"].SetValue(True)
    sheet.collect()
    sheet._on_save(sheet.state)
    assert "required: False becomes True" in seen["previews"][-1]["lines"]
    route, body = bench.api.writes[-1][1:]
    assert route == f"{QST}/field-groups/facts"
    assert body["fields"][0]["required"] is True and body["attach"] == {"post_types": ["book"]}
    bench.run(command("undo"))
    assert bench.api.writes[-1][2]["fields"][0]["required"] is False


def test_add_a_field_and_a_kind_the_site_defines(bench, sheets, answers) -> None:
    seen, replies = answers
    _go(bench, NodeRef("site", "content_model", SITE))
    group = next(r for r in bench.rows if r.key == "facts")
    replies["choice"].append(1)  # Add a field
    bench.provider.do_edit_site_type_fields(None, group)
    sheet = sheets[-1]
    sheet.controls["name"].ChangeValue("cover")
    sheet.controls["kind"].SetStringSelection("picture")
    sheet.collect()
    sheet._on_save(sheet.state)
    fields = bench.api.writes[-1][2]["fields"]
    assert [f["name"] for f in fields] == ["isbn", "cover"] and fields[1]["kind"] == "picture"
    replies["text"] += ["isbn13", "ISBN-13", "^[0-9]{13}$"]
    replies["choice"].append(0)  # string
    bench.provider.do_add_field_kind(NodeRef("site", "content_model", SITE), None)
    assert "cannot be undone from here" in seen["previews"][-1]["summary"]
    assert bench.api.writes[-1] == ("POST", f"{QST}/kinds", {
        "kind": "isbn13", "label": "ISBN-13", "schema": {"type": "string", "pattern": "^[0-9]{13}$"}
    })  # fmt: skip
