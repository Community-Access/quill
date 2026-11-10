"""The WordPress Workbench's W1 to W4 leftovers in the real frame, on a fake site.

Load More and Load All, Columns, Group By as child nodes, New Here, Empty
Spam, Allow This Sender, Send Password Reset, Roles, F1 per node and row,
and File > WordPress > Properties built from the Workbench's item sheet.
"""

from __future__ import annotations

from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.core.wordpress import site_taxonomies as tx  # noqa: E402
from quill.core.wordpress.workbench_actions import command  # noqa: E402
from quill.ui import wordpress_dialogs as dlg  # noqa: E402
from quill.ui import wordpress_workbench_dialogs as wdlg  # noqa: E402
from quill.ui.wordpress_workbench_window import SEP, WordPressWorkbenchProvider  # noqa: E402
from quill.ui.workbench_frame import NodeRef, WorkbenchFrame  # noqa: E402
from tests.unit.ui.wordpress.test_wp_workbench_window import (  # noqa: E402
    SITE,
    FakeApi,
    _Commands,
    _go,
    _inline,
    _labels,
    _select,
)


class PagedApi(FakeApi):
    """Records the page limit each collection read used."""

    def __init__(self) -> None:
        super().__init__()
        self.max_pages: list[int] = []

    def get(self, route: str, **params: Any) -> Any:
        answer = super().get(route, **params)
        if route == "wp/v2/users/me" and self.role == "administrator":
            answer["capabilities"]["edit_users"] = True
        return answer

    def iter_collection(self, route: str, params: Any = None, **kw: Any):
        self.max_pages.append(int(kw.get("max_pages", 0)))
        yield from super().iter_collection(route, params, **kw)


@pytest.fixture
def bench(wx_session_app, tmp_path):
    tx.clear_cache()
    said: list[str] = []
    api = PagedApi()
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


def _posts(frame: WorkbenchFrame) -> NodeRef:
    ref = NodeRef("site", "posts", SITE)
    _go(frame, ref)
    return ref


def test_load_more_and_load_all_raise_the_page_limit(bench) -> None:
    _posts(bench)
    assert bench.api.max_pages[-1] == 3
    bench.run(command("load_more"))
    assert bench.api.max_pages[-1] == 6
    bench.run(command("load_all"))
    assert bench.api.max_pages[-1] == 100


def test_columns_choose_what_the_list_shows(bench, monkeypatch) -> None:
    _posts(bench)
    monkeypatch.setattr(wdlg, "ask_checks", lambda *a, **k: [0, 4])
    bench.run(command("columns"))
    assert bench.list.GetColumnCount() == 2
    assert bench.list.GetColumn(1).GetText() == "Date"


def test_group_by_adds_a_child_node_per_value(bench, monkeypatch) -> None:
    _posts(bench)
    monkeypatch.setattr(dlg, "ask_choice", lambda *a, **k: 2)  # the second column: status
    bench.run(command("group_by"))
    posts = bench._items[NodeRef("site", "posts", SITE)]
    labels = _labels(bench.tree, posts)
    assert "Draft (1)" in labels and "Published (1)" in labels
    group = NodeRef("site", "posts_group", f"{SITE}{SEP}group=status=Draft")
    _go(bench, group)
    assert [r.title for r in bench.rows] == ["Hello"]


def test_new_here_makes_a_draft_post(bench, monkeypatch) -> None:
    _posts(bench)
    monkeypatch.setattr(dlg, "ask_text", lambda *a, **k: "Fresh")
    bench.run(command("new_here"))
    assert ("POST", "wp/v2/posts", {"title": "Fresh", "status": "draft"}) in bench.api.writes
    assert any("as a draft" in s for s in bench.said)


def test_empty_spam_asks_then_deletes_every_spam_comment(bench, monkeypatch) -> None:
    _go(bench, NodeRef("site", "comments_spam", SITE))
    monkeypatch.setattr(dlg, "confirm", lambda *a, **k: True)
    bench.api.role = "administrator"
    bench.run(command("empty_spam"))
    deletes = [w for w in bench.api.writes if w[0] == "DELETE"]
    assert deletes == [("DELETE", "wp/v2/comments/8", {"force": True})]


def test_allow_this_sender_approves_and_explains(bench) -> None:
    _go(bench, NodeRef("site", "comments_spam", SITE))
    _select(bench, 0)
    bench.run(command("allow_sender"))
    assert ("POST", "wp/v2/comments/8", {"status": "approve"}) in bench.api.writes
    assert any("next comments" in s or "will wait" in s for s in bench.said)


def test_password_reset_opens_wp_admin_and_roles_read_in_words(bench, monkeypatch) -> None:
    bench.api.role = "administrator"
    _go(bench, NodeRef("site", "users", SITE))
    _select(bench, 1)
    bench.run(command("send_password_reset"))
    assert bench.commands.host.opened == ["https://radio.example/wp-admin/user-edit.php?user_id=4"]
    shown: list[str] = []
    monkeypatch.setattr(dlg, "show_report", lambda *a, **k: shown.append(k["text"]))
    bench.run(command("roles"))
    assert "Administrator:" in shown[0] and "cannot change" in shown[0]


def test_f1_on_the_tree_and_list_is_the_node_and_row_help(bench) -> None:
    from quill.ui.app_context_help import ensure_help_provider

    ensure_help_provider(wx)
    _posts(bench)
    assert "posts" in bench.tree.GetHelpText().lower()
    _select(bench, 0)
    bench._on_row_selected(None)
    assert "Enter opens it in the editor" in bench.list.GetHelpText()


def test_the_editor_properties_use_the_workbench_sheet(wx_session_app, monkeypatch) -> None:
    from quill.ui import wordpress_item_dialogs as idlg
    from quill.ui import workbench_sheet_editor as editor_module

    class _Editor:
        def __init__(self, parent, sheet, values, **kw) -> None:
            self.sheet, self.values, self.kw = sheet, values, kw
            self.dialog = wx.Dialog(None)

        def show(self) -> int:
            from quill.core.workbench.properties import SheetState

            state = SheetState(self.sheet, loaded=dict(self.values))
            state.edited["format"] = "aside"
            state.edited["tags"] = ("Live (9)",)
            self.kw["on_save"](state)
            self.dialog.Destroy()
            return wx.ID_OK

    monkeypatch.setattr(editor_module, "WorkbenchSheetEditor", _Editor)
    answer = idlg.ask_properties(
        None,
        lambda *_a: wx.ID_OK,
        kind="post",
        title="Hi",
        slug="hi",
        status="draft",
        excerpt="",
        categories=[(5, "News")],
        tags=[(9, "Live")],
        chosen_categories=[5],
        chosen_tags=[],
        comments_open=True,
        sticky=False,
        facts="Site: Radio",
    )
    assert answer is not None
    assert answer.tag_ids == [9] and answer.category_ids == [5]
    assert answer.extra == {"format": "aside"}


# -- W5 -------------------------------------------------------------------------

_ABILITY = {
    "name": "acme/count",
    "label": "Count Things",
    "description": "Counts things.",
    "meta": {"annotations": {"readonly": True}},
    "input_schema": {"properties": {"limit": {"type": "integer", "default": 5}}},
}


def test_more_from_this_site_lists_a_namespace_and_its_routes(bench) -> None:
    bench.provider.discover(SITE)
    bench.rebuild_tree()
    _go(bench, NodeRef("site", "more", SITE))
    assert [r.key for r in bench.rows] == ["wp/v2"]
    ref = NodeRef("site", "more_namespace", f"{SITE}{SEP}wp/v2")
    _go(bench, ref)
    assert [r.key for r in bench.rows] == ["/wp/v2/posts"]
    assert bench.rows[0].cell("coverage") == "covered"


def test_the_content_model_lists_types_with_who_registered_them(bench) -> None:
    _go(bench, NodeRef("site", "content_model", SITE))
    owners = {r.key: r.cell("registered_by") for r in bench.rows}
    assert owners["post"] == "WordPress"
    assert owners["event"] == "a plugin or the theme"


def test_an_ability_runs_after_its_sheet_and_preview(bench, monkeypatch) -> None:
    from quill.ui import workbench_sheet_editor as editor_module

    ran: list[Any] = []
    bench.api.get_original = bench.api.get

    def get(route: str, **params: Any) -> Any:
        if route == "wp-abilities/v1/abilities/acme/count":
            return dict(_ABILITY)
        return bench.api.get_original(route, **params)

    monkeypatch.setattr(bench.api, "get", get)

    class _Response:
        payload = {"count": 3}

    monkeypatch.setattr(
        bench.api,
        "request",
        lambda method, route, **kw: (ran.append((method, route, kw)), _Response())[1],
    )

    class _Editor:
        def __init__(self, parent, sheet, values, **kw) -> None:
            self.sheet, self.values, self.kw = sheet, values, kw

        def show(self) -> int:
            from quill.core.workbench.properties import SheetState

            state = SheetState(self.sheet, loaded=dict(self.values))
            state.edited["limit"] = "9"
            self.kw["on_save"](state)
            return wx.ID_OK

    monkeypatch.setattr(editor_module, "WorkbenchSheetEditor", _Editor)
    previews: list[Any] = []
    monkeypatch.setattr(wdlg, "ask_preview", lambda *a, **k: (previews.append(k), True)[1])
    reports: list[str] = []
    monkeypatch.setattr(dlg, "show_report", lambda *a, **k: reports.append(k["text"]))
    from quill.core.wordpress.workbench_rows import WbRow

    row = WbRow("ability", SITE, "acme/count", {"ability": "Count Things"}, "", raw={})
    bench.provider.do_run_ability(None, row)
    assert previews and previews[0]["lines"] == ["limit: 9"]
    assert ran and ran[0][1] == "wp-abilities/v1/abilities/acme/count/run"
    assert reports
