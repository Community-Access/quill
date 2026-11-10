"""The WordPress Workbench window (PRD W1 to W4): tree, lists, commands, sheets, permissions.

Built on the real shared frame with a fake site and a background runner that
runs work inline, so loading and saving are deterministic without a network.
Dialogs are answered by replacing the WordPress dialog helpers the commands
import, the way ``tests/unit/apps/conftest.py`` patches a module-scope import.
"""

from __future__ import annotations

from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.core.wordpress import site_taxonomies as tx  # noqa: E402
from quill.core.wordpress.sites import SiteProfile, SiteStore  # noqa: E402
from quill.core.wordpress.workbench_actions import WINDOW_MENU, command  # noqa: E402
from quill.core.workbench.menus import problems  # noqa: E402
from quill.ui import wordpress_dialogs as dlg  # noqa: E402
from quill.ui.wordpress_workbench_window import (  # noqa: E402
    SEP,
    WordPressWorkbenchProvider,
)
from quill.ui.workbench_frame import NodeRef, WorkbenchFrame  # noqa: E402

SITE = "Community Radio"


class _Address:
    is_wpcom = False
    wpcom_site = ""
    site_url = "https://radio.example"


class _Auth:
    kind = "app_password"
    username = "jeff"


class FakeApi:
    """Answers the routes the Workbench asks; records every write."""

    def __init__(self) -> None:
        self.address = _Address()
        self.auth = _Auth()
        self.site_name = SITE
        self.writes: list[tuple[str, str, Any]] = []
        self.batches: list[list[dict[str, Any]]] = []
        self.posts = [
            {
                "id": 1,
                "title": {"raw": "Hello", "rendered": "Hello"},
                "status": "draft",
                "author": 3,
                "modified_gmt": "2026-11-01T10:00:00",
                "link": "https://radio.example/?p=1",
                "categories": [5],
                "tags": [],
                "type": "post",
            },
            {
                "id": 2,
                "title": {"raw": "News", "rendered": "News"},
                "status": "publish",
                "author": 3,
                "modified_gmt": "2026-11-02T10:00:00",
                "link": "https://radio.example/news",
                "categories": [],
                "tags": [],
                "type": "post",
            },
        ]
        self.comments = [
            {
                "id": 7,
                "post": 2,
                "author_name": "Ann",
                "status": "hold",
                "date_gmt": "2026-11-03T09:00:00",
                "content": {"rendered": "<p>Nice show</p>"},
            },
            {
                "id": 8,
                "post": 2,
                "author_name": "Bot",
                "status": "spam",
                "date_gmt": "2026-11-03T08:00:00",
                "content": {"rendered": "<p>Buy now</p>"},
            },
        ]
        self.role = "editor"

    # -- reads --------------------------------------------------------------------

    def get(self, route: str, **params: Any) -> Any:
        if route == "wp/v2/users/me":
            caps = {
                "edit_posts": True,
                "publish_posts": True,
                "moderate_comments": True,
                "upload_files": True,
                "delete_posts": True,
                "edit_pages": True,
                "manage_categories": True,
            }
            if self.role == "subscriber":
                caps = {"read": True}
            if self.role == "administrator":
                caps.update({
                    "list_users": True,
                    "promote_users": True,
                    "manage_options": True,
                    "delete_users": True,
                    "activate_plugins": True,
                })
            return {
                "id": 3,
                "name": "Jeff",
                "username": "jeff",
                "roles": [self.role],
                "capabilities": caps,
            }
        if route == "":
            return {
                "name": SITE,
                "home": "https://radio.example",
                "namespaces": ["wp/v2"],
                "routes": {"/wp/v2/posts": {}, "/batch/v1": {}},
            }
        if route == "wp/v2/types":
            return {
                "post": {},
                "page": {},
                "event": {"rest_base": "events", "name": "Events", "rest_namespace": "wp/v2"},
            }
        if route == "wp/v2/taxonomies":
            return {
                "category": {
                    "name": "Categories",
                    "rest_base": "categories",
                    "hierarchical": True,
                    "types": ["post"],
                },
                "genre": {"name": "Genres", "rest_base": "genres", "types": ["event"]},
            }
        if route == "wp/v2/statuses":
            return {}
        if route.startswith("wp/v2/posts/"):
            post_id = int(route.rsplit("/", 1)[1])
            return dict(next(p for p in self.posts if p["id"] == post_id))
        if route.startswith("wp/v2/users/"):
            return {"id": 3, "name": "Jeff"}
        if route == "wp/v2/categories":
            return [{"id": 5, "name": "Shows"}]
        return []

    def request(self, method: str, route: str, **kw: Any) -> Any:
        class _R:
            payload: Any = {}
            total = 0

        if method == "OPTIONS":
            return _R()
        response = _R()
        response.payload = []
        return response

    def iter_collection(self, route: str, params: Any = None, **_kw: Any):
        params = dict(params or {})
        if route == "wp/v2/posts":
            status = params.get("status", "any")
            wanted = status if isinstance(status, list) else [status]
            for post in self.posts:
                if "any" in wanted or post["status"] in wanted:
                    if params.get("search") and params["search"] not in post["title"]["raw"]:
                        continue
                    yield dict(post)
        elif route == "wp/v2/comments":
            for c in self.comments:
                if params.get("status") in (c["status"], "all"):
                    yield dict(c)
        elif route == "wp/v2/users":
            yield {"id": 3, "name": "Jeff", "roles": [self.role]}
            yield {"id": 4, "name": "Ann", "roles": ["author"]}

    # -- writes -------------------------------------------------------------------

    def post(self, route: str, body: Any = None, **params: Any) -> Any:
        self.writes.append(("POST", route, body))
        if route.startswith("wp/v2/comments/"):
            comment_id = int(route.rsplit("/", 1)[1])
            for c in self.comments:
                if c["id"] == comment_id:
                    c["status"] = {"approve": "approved"}.get(body["status"], body["status"])
            return {"id": comment_id, **body}
        if route.startswith("wp/v2/posts/"):
            post_id = int(route.rsplit("/", 1)[1])
            post = next(p for p in self.posts if p["id"] == post_id)
            post.update(body)
            post["modified_gmt"] = "2026-11-09T12:00:00"
            return dict(post)
        return dict(body or {})

    def delete(self, route: str, **params: Any) -> Any:
        self.writes.append(("DELETE", route, params))
        if route.startswith("wp/v2/posts/"):
            post_id = int(route.rsplit("/", 1)[1])
            post = next(p for p in self.posts if p["id"] == post_id)
            post["status"] = "trash"
            return dict(post)
        return {}

    def batch(self, requests: list[dict[str, Any]]) -> list[dict[str, Any]]:
        self.batches.append(requests)
        answers = []
        for request in requests:
            route = request["path"].lstrip("/")
            answers.append({"status": 200, "body": self.post(route, request["body"])})
        return answers


class _Host:
    def __init__(self, said: list[str]) -> None:
        self.said = said
        self.opened: list[str] = []
        self.parent = None

    def announce(self, text: str) -> None:
        self.said.append(text)

    def open_in_browser(self, url: str) -> None:
        self.opened.append(url)


class _Commands:
    def __init__(self, said: list[str]) -> None:
        self.host = _Host(said)
        self.opened: list[tuple[str, int]] = []

    def sites(self) -> SiteStore:
        return SiteStore([SiteProfile("s1", SITE, "https://radio.example", "jeff")], "s1")

    def open_item(self, profile: SiteProfile, kind: str, item_id: int) -> None:
        self.opened.append((kind, item_id))


def _inline(_name: str, work: Any, done: Any, failed: Any) -> None:
    try:
        result = work()
    except Exception as exc:  # noqa: BLE001
        failed(exc)
        return
    done(result)


@pytest.fixture
def bench(wx_session_app, tmp_path, monkeypatch):
    tx.clear_cache()
    said: list[str] = []
    api = FakeApi()
    commands = _Commands(said)
    provider = WordPressWorkbenchProvider(
        commands, announce=said.append, data_dir=tmp_path, api_for=lambda _p: api
    )
    frame = WorkbenchFrame(provider, announce=said.append, run_background=_inline)
    frame.said = said  # type: ignore[attr-defined]
    frame.api = api  # type: ignore[attr-defined]
    frame.commands = commands  # type: ignore[attr-defined]
    yield frame
    frame.frame.Destroy()
    tx.clear_cache()


def _go(frame: WorkbenchFrame, ref: NodeRef) -> None:
    assert frame.select(ref), ref
    if frame.current != ref:
        frame._show_node(ref, remember=True)


def _labels(tree: Any, parent: Any) -> list[str]:
    labels, (child, cookie) = [], tree.GetFirstChild(parent)
    while child.IsOk():
        labels.append(tree.GetItemText(child))
        child, cookie = tree.GetNextChild(parent, cookie)
    return labels


def _select(frame: WorkbenchFrame, *indices: int) -> None:
    for index in range(frame.list.GetItemCount()):
        frame.list.Select(index, on=index in indices)


def test_the_menu_bar_keeps_the_accelerator_and_access_key_rules() -> None:
    assert problems(WINDOW_MENU) == []


def test_the_tree_has_the_prd_places_and_the_site(bench) -> None:
    tree = bench.tree
    top = _labels(tree, tree.GetRootItem())
    assert top[:3] == ["Start Here", "Needs My Attention", "Sites"]
    sites = bench._items[NodeRef("", "sites")]
    assert _labels(tree, sites) == [SITE]
    site_item = bench._items[NodeRef("site", "site", SITE)]
    assert {"Overview", "Posts", "Pages", "Media", "Comments", "People", "Plugins"} <= set(
        _labels(tree, site_item)
    )


def test_discovery_adds_a_node_for_each_custom_type_and_taxonomy(bench) -> None:
    bench.provider.start()
    assert NodeRef("site", "custom_type", f"{SITE}{SEP}events") in bench._items
    assert NodeRef("site", "custom_taxonomy", f"{SITE}{SEP}genre") in bench._items


def test_posts_load_and_say_nothing(bench) -> None:
    _go(bench, NodeRef("site", "posts", SITE))
    assert [row.title for row in bench.rows] == ["Hello", "News"]
    assert bench.said == []  # GATE-13: the list says it


def test_needs_my_attention_gathers_waiting_comments(bench) -> None:
    _go(bench, NodeRef("", "waiting"))
    assert [row.cell("author") for row in bench.rows] == ["Ann"]
    _go(bench, NodeRef("", "held_as_spam"))
    assert [row.cell("author") for row in bench.rows] == ["Bot"]


def test_enter_on_a_post_opens_it_in_the_editor(bench) -> None:
    _go(bench, NodeRef("site", "posts", SITE))
    _select(bench, 0)
    bench.default_action()
    assert bench.commands.opened == [("post", 1)]


def test_delete_is_trash_and_ctrl_z_restores(bench) -> None:
    _go(bench, NodeRef("site", "posts", SITE))
    _select(bench, 0)
    bench.run(command("trash"))
    assert ("DELETE", "wp/v2/posts/1", {}) in bench.api.writes
    assert "Trash" in bench.said[-1]
    bench.run(command("undo"))
    assert bench.api.writes[-1] == ("POST", "wp/v2/posts/1", {"status": "draft"})


def test_not_spam_puts_a_held_comment_back_in_the_queue(bench) -> None:
    _go(bench, NodeRef("", "held_as_spam"))
    _select(bench, 0)
    bench.run(command("approve"))
    assert bench.api.writes[-1] == ("POST", "wp/v2/comments/8", {"status": "hold"})
    assert "Not spam" in bench.said[-1]


def test_a_filter_goes_to_the_site_as_rest_parameters(bench) -> None:
    _go(bench, NodeRef("site", "posts", SITE))
    bench.filter.ChangeValue("status:draft")
    bench.apply_filter()
    assert [row.title for row in bench.rows] == ["Hello"]


def test_publish_goes_through_the_batch_endpoint(bench, monkeypatch) -> None:
    monkeypatch.setattr(dlg, "confirm", lambda *a, **k: True)
    _go(bench, NodeRef("site", "posts", SITE))
    _select(bench, 0)
    bench.run(command("publish"))
    assert bench.api.batches[0][0]["path"] == "/wp/v2/posts/1"
    assert bench.api.batches[0][0]["body"] == {"status": "publish"}


def test_a_save_checks_for_conflicts_and_verifies(bench, monkeypatch) -> None:
    from quill.core.wordpress.workbench_edit import save
    from quill.core.wordpress.workbench_rows import item_row

    row = item_row(bench.api.posts[0], "post", SITE)
    result = save(bench.api, row, {"title": "Hi"}, loaded_modified="2026-11-01T10:00:00")
    assert result.not_kept == ()
    assert result.undo == {"title": "Hello"}
    from quill.core.wordpress.workbench_edit import EditConflict

    with pytest.raises(EditConflict):
        save(bench.api, row, {"title": "Again"}, loaded_modified="2026-11-01T10:00:00")


def test_read_only_access_greys_writes_with_a_reason(bench) -> None:
    from quill.core.wordpress.workbench_permissions import Access

    bench.provider.access_store.set("s1", Access.READ_ONLY)
    _go(bench, NodeRef("site", "posts", SITE))
    _select(bench, 0)
    assert not bench.provider.supports(command("trash"))
    bench.run(command("trash"))
    assert "Read Only" in bench.said[-1]
    assert not any(method == "DELETE" for method, _r, _b in bench.api.writes)


def test_view_as_role_is_read_only_and_explains(bench) -> None:
    bench.provider.view_as[SITE] = "contributor"
    _go(bench, NodeRef("site", "posts", SITE))
    _select(bench, 0)
    reason = bench.provider.refusal_for(command("publish"), bench.selected_row())
    assert "viewing" in reason.lower()


def test_an_editor_is_told_why_users_are_out_of_reach(bench) -> None:
    _go(bench, NodeRef("site", "posts", SITE))  # learns the role first
    node = bench.node(NodeRef("site", "users", SITE))
    reason = bench.provider.unavailable(NodeRef("site", "users", SITE), node)
    assert "Administrator role or higher" in reason and "Editor" in reason


def test_planned_nodes_say_where_the_feature_lives_today(bench) -> None:
    node = bench.node(NodeRef("", "accessibility"))
    assert "Check the Whole Site" in bench.provider.unavailable(NodeRef("", "accessibility"), node)


def test_the_door_opens_nothing_without_the_flag(monkeypatch) -> None:
    from quill.ui.wordpress_workbench_window import open_from_door

    monkeypatch.delenv("QUILL_WORDPRESS_WORKBENCH_WINDOW", raising=False)
    assert open_from_door(object(), "wordpress.comments") is False


@pytest.fixture
def sheets(monkeypatch):
    """Every sheet the Workbench opens, captured instead of shown."""
    from quill.ui import workbench_sheet_editor as editor

    opened: list[Any] = []
    monkeypatch.setattr(editor.WorkbenchSheetEditor, "show", lambda self: opened.append(self) or 0)
    return opened


def test_alt_enter_opens_the_post_sheet_and_ok_saves_with_verify(bench, sheets) -> None:
    _go(bench, NodeRef("site", "posts", SITE))
    _select(bench, 0)
    bench.run(command("sheet"))
    sheet = sheets[-1]
    assert sheet.sheet.pages[0].title == "General"
    assert sheet.controls["title"].GetValue() == "Hello"
    assert sheet.controls["categories"].GetValue() == "Shows (5)"
    sheet.controls["title"].ChangeValue("Hello again")
    sheet.collect()
    sheet._on_save(sheet.state)
    assert bench.api.writes[-1] == ("POST", "wp/v2/posts/1", {"title": "Hello again"})
    assert bench.said[-1].startswith("Saved 1 change to Hello")
    bench.run(command("undo"))
    assert bench.api.writes[-1] == ("POST", "wp/v2/posts/1", {"title": "Hello"})


def test_several_rows_get_the_batch_sheet_with_mixed_values(bench, sheets, monkeypatch) -> None:
    monkeypatch.setattr(dlg, "confirm", lambda *a, **k: True)
    _go(bench, NodeRef("site", "posts", SITE))
    _select(bench, 0, 1)
    bench.run(command("sheet"))
    sheet = sheets[-1]
    assert sheet.controls["status"].GetStringSelection() == "(Mixed: leave as it is)"
    sheet.controls["status"].SetStringSelection("private")
    sheet.controls["add_categories"].ChangeValue("9")
    sheet.collect()
    sheet._on_save(sheet.state)
    bodies = [r["body"] for r in bench.api.batches[-1]]
    assert bodies[0] == {"status": "private", "categories": [5, 9]}
    assert bodies[1] == {"status": "private", "categories": [9]}


def test_a_subscriber_gets_a_read_only_sheet_with_the_reason(bench, sheets) -> None:
    bench.api.role = "subscriber"
    _go(bench, NodeRef("site", "posts", SITE))
    _select(bench, 0)
    bench.run(command("sheet"))
    sheet = sheets[-1]
    assert sheet._on_save is None
    assert "Contributor role or higher" in sheet._help(sheet.sheet.field("title"))


def test_the_site_sheet_has_the_spam_page(bench, sheets) -> None:
    _go(bench, NodeRef("site", "overview", SITE))
    bench.run(command("site_sheet"))
    titles = [page.title for page in sheets[-1].sheet.pages]
    assert titles[0] == "General" and "Spam" in titles
