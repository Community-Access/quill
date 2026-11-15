"""wordpress.md 9.18 packages 6, 7 and 14 in the real frame: the Overview's children, Edit
Block Markup, Earlier Versions, Reset, New Template, Additional CSS, and wp-admin by place.
Reuses the fake site of ``test_wp_workbench_window``; work runs inline."""

from __future__ import annotations

from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.core.wordpress import site_taxonomies as tx  # noqa: E402
from quill.core.wordpress.workbench_rows import WbRow  # noqa: E402
from quill.ui import wordpress_dialogs as dlg  # noqa: E402
from quill.ui import wordpress_workbench_dialogs as wdlg  # noqa: E402
from quill.ui.wordpress_workbench_window import WordPressWorkbenchProvider  # noqa: E402
from quill.ui.workbench_frame import NodeRef, WorkbenchFrame  # noqa: E402
from tests.unit.ui.wordpress.test_wp_workbench_window import (  # noqa: E402
    SITE,
    FakeApi,
    _Commands,
    _go,
    _inline,
)

ROUTE = "wp/v2/templates/tt5//single"


class EditorApi(FakeApi):
    def __init__(self) -> None:
        super().__init__()
        self.role = "administrator"
        self.template: dict[str, Any] = {
            "id": "tt5//single",
            "slug": "single",
            "type": "wp_template",
            "title": {"rendered": "Single Posts"},
            "content": {"raw": "<!-- wp:post-title /-->"},
            "source": "theme",
            "has_theme_file": True,
        }
        self.css = "a { color: red; }"

    def get(self, route: str, **params: Any) -> Any:
        if route == "wp/v2/users/me":
            me = super().get(route, **params)
            if self.role == "administrator":
                me["capabilities"]["edit_theme_options"] = True
            return me
        if route == ROUTE:
            if params.get("source") == "theme":
                return {**self.template, "content": {"raw": "<!-- wp:post-title /-->"}}
            return dict(self.template)
        if route == f"{ROUTE}/revisions":
            return [{"id": 40, "modified_gmt": "2026-10-01T10:00:00", "content": {"raw": "old"}}]
        if route == "wp/v2/templates/lookup":
            return {**self.template, "id": "tt5//single", "title": {"rendered": "Single Posts"}}
        if route == "wp/v2/themes":
            href = "https://radio.example/wp-json/wp/v2/global-styles/9"
            return [
                {
                    "name": {"raw": "TT5"},
                    "stylesheet": "tt5",
                    "is_block_theme": True,
                    "_links": {"wp:user-global-styles": [{"href": href}]},
                }
            ]
        if route == "wp/v2/global-styles/9":
            return {"id": 9, "styles": {"css": self.css}}
        return super().get(route, **params)

    def post(self, route: str, body: Any = None, **params: Any) -> Any:
        self.writes.append(("POST", route, body))
        if route == ROUTE:
            self.template.update(content={"raw": body["content"]}, source="custom")
            return dict(self.template)
        if route == "wp/v2/global-styles/9":
            self.css = body["styles"]["css"]
            return {"id": 9}
        if route == "wp/v2/templates":
            return {**body, "id": "tt5//single-post-news", "type": "wp_template"}
        return dict(body or {})

    def delete(self, route: str, **params: Any) -> Any:
        self.writes.append(("DELETE", route, params))
        if route == ROUTE:
            self.template.update(source="theme")
        return {}


@pytest.fixture
def bench(wx_session_app, tmp_path):
    tx.clear_cache()
    said: list[str] = []
    api = EditorApi()
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


def _template_row() -> WbRow:
    return WbRow(
        "template",
        SITE,
        "tt5//single",
        {"title": "Single Posts"},
        "",
        route=ROUTE,
        subkind="wp_template",
    )


def _ref() -> NodeRef:
    return NodeRef("site", "templates", SITE)


def _answer(monkeypatch: Any, text: str | None, *, preview: bool = True) -> list[Any]:
    previews: list[Any] = []
    monkeypatch.setattr(dlg, "ask_text", lambda *_a, **_k: text)
    monkeypatch.setattr(
        wdlg, "ask_preview", lambda *_a, **k: previews.append((k["summary"], k["lines"])) or preview
    )
    return previews


# -- package 6 and 14: the Overview's children ---------------------------------------


def test_overview_has_at_a_glance_activity_and_the_wp_admin_screens(bench) -> None:
    _go(bench, NodeRef("site", "at_a_glance", SITE))
    facts = {r.cell("fact") for r in bench.rows}
    assert {"Posts", "Pages", "Comments", "WordPress", "Theme"} <= facts
    _go(bench, NodeRef("site", "activity", SITE))
    assert {r.cell("group") for r in bench.rows} == {
        "Publishing soon",
        "Recently published",
        "Recent comments",
    }
    _go(bench, NodeRef("site", "admin_screens", SITE))
    permalinks = next(r for r in bench.rows if r.key == "permalinks")
    bench.provider.do_open_admin_screen(None, permalinks)
    assert bench.commands.host.opened == ["https://radio.example/wp-admin/options-permalink.php"]
    assert "permalink structure is not in REST" in bench.said[-1]
    bench.provider.do_go_to_place(None, permalinks)
    assert bench.current == NodeRef("site", "settings", SITE)


def test_wp_admin_for_this_place_opens_the_chosen_screen_after_its_reason(
    bench, monkeypatch
) -> None:
    rows: list[list[str]] = []
    monkeypatch.setattr(dlg, "ask_choice", lambda *_a, **k: rows.append(k["rows"]) or 1)
    bench.provider.do_admin_here(NodeRef("site", "comments_waiting", SITE), None)
    assert rows[0] == [
        "Comments: All of it in the Workbench",
        "Settings > Discussion: Part in the Workbench, the rest in wp-admin",
    ]
    assert bench.commands.host.opened == ["https://radio.example/wp-admin/options-discussion.php"]
    assert "avatars" in bench.said[-1]
    bench.provider.do_admin_here(NodeRef("site", "content_model", SITE), None)
    assert "No wp-admin screen is nearer" in bench.said[-1]


# -- package 7: templates ------------------------------------------------------------


def test_edit_template_previews_saves_and_ctrl_z_resets_a_theme_template(
    bench, monkeypatch
) -> None:
    previews = _answer(monkeypatch, "<!-- wp:post-content /-->")
    bench.provider.do_edit_template(_ref(), _template_row())
    summary, lines = previews[0]
    assert "comes from the theme" in summary
    assert lines == [
        "Line 1 removed: <!-- wp:post-title /-->",
        "Line 1 added: <!-- wp:post-content /-->",
    ]
    assert ("POST", ROUTE, {"content": "<!-- wp:post-content /-->"}) in bench.api.writes
    assert bench.said[-1] == f"Saved the template Single Posts on {SITE}."
    bench.provider.do_undo(None, None)
    assert bench.api.writes[-1] == ("DELETE", ROUTE, {"force": True})


def test_edit_template_cancelled_or_unchanged_sends_nothing(bench, monkeypatch) -> None:
    _answer(monkeypatch, "<!-- wp:post-content /-->", preview=False)
    bench.provider.do_edit_template(_ref(), _template_row())
    _answer(monkeypatch, "<!-- wp:post-title /-->")
    bench.provider.do_edit_template(_ref(), _template_row())
    assert not bench.api.writes
    assert "unchanged" in bench.said[-1]


def test_earlier_versions_and_reset_on_a_customized_template(bench, monkeypatch) -> None:
    bench.api.template["source"] = "custom"
    previews = _answer(monkeypatch, None)
    monkeypatch.setattr(dlg, "ask_choice", lambda *_a, **_k: 0)
    bench.provider.do_template_revisions(_ref(), _template_row())
    assert previews[0][1] == ["Line 1 removed: <!-- wp:post-title /-->", "Line 1 added: old"]
    assert bench.api.writes[-1] == ("POST", ROUTE, {"content": "old"})
    bench.provider.do_reset_template(_ref(), _template_row())
    assert "to the theme's version" in previews[-1][0]
    assert bench.api.writes[-1] == ("DELETE", ROUTE, {"force": True})
    assert "is the theme's version again" in bench.said[-1]
    bench.provider.do_undo(None, None)
    assert bench.api.writes[-1] == ("POST", ROUTE, {"content": "old"})


def test_reset_of_a_theme_template_says_there_is_nothing_to_reset(bench) -> None:
    bench.provider.do_reset_template(_ref(), _template_row())
    assert "already is the theme's version" in bench.said[-1]
    assert not bench.api.writes


def test_new_template_starts_from_the_lookup_and_undo_deletes_it(bench, monkeypatch) -> None:
    previews = _answer(monkeypatch, "single-post-news")
    bench.provider.do_new_template(_ref(), _template_row())
    assert "starts as a copy of Single Posts" in previews[0][0]
    assert bench.api.writes[-1] == (
        "POST",
        "wp/v2/templates",
        {
            "slug": "single-post-news",
            "title": "single-post-news",
            "content": "<!-- wp:post-title /-->",
        },
    )
    bench.provider.do_undo(None, None)
    assert bench.api.writes[-1] == (
        "DELETE",
        "wp/v2/templates/tt5//single-post-news",
        {"force": True},
    )


def test_open_in_the_site_editor_opens_that_template(bench) -> None:
    bench.provider.do_open_site_editor(_ref(), _template_row())
    assert bench.commands.host.opened == [
        "https://radio.example/wp-admin/site-editor.php?postType=wp_template&postId=tt5%2F%2Fsingle"
    ]


# -- package 7: Additional CSS -----------------------------------------------------


def test_additional_css_previews_saves_and_ctrl_z_puts_it_back(bench, monkeypatch) -> None:
    _go(bench, NodeRef("site", "additional_css", SITE))
    row = bench.rows[0]
    assert row.kind == "custom_css"
    previews = _answer(monkeypatch, "a { color: blue; }")
    bench.provider.do_edit_css(None, row)
    assert "every page" in previews[0][0]
    assert bench.api.css == "a { color: blue; }"
    bench.provider.do_undo(None, None)
    assert bench.api.css == "a { color: red; }"


def test_css_with_markup_is_refused_before_any_preview(bench, monkeypatch) -> None:
    row = WbRow("custom_css", SITE, "9", {}, "", raw={"styles_id": 9})
    previews = _answer(monkeypatch, "<style>a{}</style>")
    bench.provider.do_edit_css(None, row)
    assert not previews and not bench.api.writes
    assert bench.said[-1].startswith("Nothing was sent. WordPress refuses markup")


def test_a_subscriber_is_refused_before_any_dialog(bench) -> None:
    bench.api.role = "subscriber"
    bench.provider.ensure(bench.provider.ctx(SITE))
    command = "wordpress.workbench.edit_template"
    assert "Administrator" in bench.provider.refusal_for(command, _template_row())
