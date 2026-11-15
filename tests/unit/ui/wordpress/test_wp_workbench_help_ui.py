"""WordPress PRD Part D in the real Workbench frame: the help keys, Help and Learning,
problems with Explain, Fix..., Take Me There and Open in Editor, What Depends on It,
and the settings REST does not share (WP-R-046 to WP-R-048).

Each test calls the handler a key or a context-menu row reaches, with a fake site
and the dialogs answered by patching the helpers the commands import."""

from __future__ import annotations

from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.core.wordpress import site_taxonomies as tx  # noqa: E402
from quill.core.wordpress.workbench_help_actions import command  # noqa: E402
from quill.core.wordpress.workbench_rows import WbRow  # noqa: E402
from quill.ui import wordpress_dialogs as dlg  # noqa: E402
from quill.ui import wordpress_workbench_dialogs as wdlg  # noqa: E402
from quill.ui import wordpress_workbench_problems as problems  # noqa: E402
from quill.ui import workbench_frame_help as frame_help  # noqa: E402
from quill.ui.wordpress_workbench_window import WordPressWorkbenchProvider  # noqa: E402
from quill.ui.workbench_frame import NodeRef, WorkbenchFrame  # noqa: E402
from tests.unit.ui.wordpress.test_wp_workbench_window import (  # noqa: E402
    SITE,
    FakeApi,
    _Commands,
    _inline,
)


class HelpApi(FakeApi):
    def __init__(self) -> None:
        super().__init__()
        self.role = "administrator"
        self.posts[1]["content"] = {"raw": 'Listen <a href="https://gone.example">here</a>.'}
        self.posts[1]["slug"] = "news"
        self.settings = {"timezone": ""}

    def get(self, route: str, **params: Any) -> Any:
        if route == "wp/v2/plugins":
            return [
                {"plugin": "akismet/akismet", "name": "Akismet", "status": "active"},
                {"plugin": "spam-extra/extra", "name": "Spam Extra", "status": "active",
                 "requires_plugins": "akismet"},
            ]  # fmt: skip
        if route == "wp/v2/block-types":
            return [{"name": "akismet/form"}]
        if route == "wp/v2/pages" and params.get("search") == "wp:akismet/":
            return [{"id": 9, "title": {"rendered": "Contact"}}]
        if route == "wp/v2/settings":
            return dict(self.settings)
        return super().get(route, **params)

    def post(self, route: str, body: Any = None, **params: Any) -> Any:
        if route == "wp/v2/settings":
            self.writes.append(("POST", route, body))
            self.settings.update(body)
            return dict(self.settings)
        return super().post(route, body, **params)


@pytest.fixture
def bench(wx_session_app, tmp_path):
    tx.clear_cache()
    said: list[str] = []
    api = HelpApi()
    commands = _Commands(said)
    provider = WordPressWorkbenchProvider(
        commands, announce=said.append, data_dir=tmp_path, api_for=lambda _p: api
    )
    frame = WorkbenchFrame(provider, announce=said.append, run_background=_inline)
    frame.said, frame.api, frame.commands = said, api, commands  # type: ignore[attr-defined]
    yield frame
    frame.frame.Destroy()
    tx.clear_cache()


@pytest.fixture
def shown(monkeypatch) -> list[tuple[str, str]]:
    """Every help window opened, as (title, text), instead of showing it."""
    seen: list[tuple[str, str]] = []

    class _Dialog:
        def __init__(self, _parent: Any, title: str, text: str) -> None:
            seen.append((title, text))

        def show(self) -> None:
            pass

    monkeypatch.setattr(frame_help, "HelpTextDialog", _Dialog)
    monkeypatch.setattr(problems, "HelpTextDialog", _Dialog)
    return seen


def _go(frame: WorkbenchFrame, ref: NodeRef) -> None:
    assert frame.select(ref), ref
    if frame.current != ref:
        frame._show_node(ref, remember=True)


def _pick(frame: WorkbenchFrame, title: str) -> WbRow:
    index = next(i for i, r in enumerate(frame.rows) if r.title == title)
    frame.focus_row(index)
    return frame.rows[index]


# -- the help keys (WP-R-046) ---------------------------------------------------------


def test_alt_f1_explains_the_wordpress_word_with_this_sites_example(bench, shown) -> None:
    _go(bench, NodeRef("site", "posts", SITE))
    _pick(bench, "News")
    bench.what_is_this()
    title, text = shown[-1]
    assert title == "What Is This" and text.startswith("Post\n\nA dated piece of writing")
    assert f'On {SITE}, "News" is a post.' in text


def test_alt_f1_with_no_word_is_provider_neutral(bench, shown, monkeypatch) -> None:
    monkeypatch.setattr(bench.provider, "glossary_for", lambda _kind: ("", ""))
    bench.what_is_this()
    assert bench.said[-1] == "There is no glossary word for this." and not shown


def test_ctrl_f1_opens_the_guide_at_this_places_chapter(bench) -> None:
    _go(bench, NodeRef("site", "plugins", SITE))
    bench.guide_chapter()
    opened = bench.commands.host.opened[-1]
    assert opened.startswith("file:") and "wordpress-forms-08-running-your-site" in opened


def test_search_help_and_the_keys_window_answer_in_wordpress(bench, shown) -> None:
    hits = bench.provider.search_help("approve", {})
    assert any(h.kind == "task" and h.target == ":waiting" for h in hits)
    assert any(h.kind == "node" for h in bench.provider.search_help("drafts", {}))
    bench.show_keys()
    title, text = shown[-1]
    assert title == "WordPress Workbench Keys"
    assert "What Is This?: Alt+F1" in text and "Explain That: Shift+F9" in text


def test_f9_repeats_and_shift_f9_explains_what_the_workbench_said(bench) -> None:
    bench.provider.say("Akismet is now inactive on Community Radio.")
    bench.repeat_result()
    assert bench.said[-1] == "Akismet is now inactive on Community Radio."
    bench.explain_result()
    assert "settings stay" in bench.said[-1]


def test_an_empty_list_says_what_would_be_there(bench) -> None:
    node = bench.node(NodeRef("", "waiting"))
    assert "No comments are waiting" in bench.provider.empty_text(None, node)


# -- Help and Learning ---------------------------------------------------------------


def test_do_something_takes_you_there_and_the_guide_opens_its_chapter(bench) -> None:
    _go(bench, NodeRef("", "help_tasks"))
    task = _pick(bench, "Update plugins safely")
    assert task.kind == "help_topic"
    bench.provider.do_take_me_there(None, task)
    assert bench.current == NodeRef("site", "plugins", SITE)
    _go(bench, NodeRef("", "help_guide"))
    bench.provider.do_open_topic(None, _pick(bench, "Chapter 7: Checking before you publish"))
    assert "wordpress-forms-07-checking" in bench.commands.host.opened[-1]


def test_ask_a_person_opens_only_a_blank_message(bench) -> None:
    _go(bench, NodeRef("", "help_ask"))
    bench.provider.do_open_topic(None, _pick(bench, "Write to support"))
    assert bench.commands.host.opened == ["mailto:support@community-access.org"]
    assert bench.api.writes == []


def test_the_words_node_shows_a_word_on_your_own_site_once_loaded(bench) -> None:
    _go(bench, NodeRef("site", "posts", SITE))
    _go(bench, NodeRef("", "words"))
    words = {r.cell("word"): r.cell("meaning") for r in bench.rows}
    assert '"Hello" is a post' in words["Post"]
    assert len(words) >= 60


# -- problems (WP-R-048) ---------------------------------------------------------------


def _health(text: str, test: str, status: str = "recommended") -> WbRow:
    return WbRow("problem", SITE, "0", {"says": text}, text, status=status,
                 raw={"test": test, "description": "From WordPress."})  # fmt: skip


def _broken() -> WbRow:
    return WbRow(
        "problem", SITE, "broken:2:https://gone.example",
        {"problem": "Broken link", "test": "News", "target": "https://gone.example"},
        "News links to https://gone.example.", link="https://radio.example/news",
        raw={"source_id": 2, "source_type": "post", "source_url": "https://radio.example/news",
             "target_url": "https://gone.example"},
    )  # fmt: skip


def test_explain_opens_what_a_problem_means_in_plain_words(bench, shown) -> None:
    bench.provider.do_explain_problem(None, _health("Page cache is not detected.", "page-cache"))
    title, text = shown[-1]
    assert title == "Explain" and "What it means for visitors" in text
    assert "WordPress says: From WordPress." in text


def test_fix_changes_a_broken_link_after_a_preview_and_ctrl_z_puts_it_back(
    bench, monkeypatch
) -> None:
    previews: list[Any] = []
    monkeypatch.setattr(dlg, "ask_text", lambda *_a, **_k: "https://found.example")
    monkeypatch.setattr(wdlg, "ask_preview", lambda *_a, **k: previews.append(k["lines"]) or True)
    bench.provider.do_fix_problem(None, _broken())
    assert previews == [["https://gone.example becomes https://found.example, 1 time."]]
    assert bench.api.posts[1]["content"] == 'Listen <a href="https://found.example">here</a>.'
    assert bench.said[-1] == f"Changed the link in News on {SITE}."
    bench.provider.do_undo(None, None)
    assert str(bench.api.posts[1]["content"]).count("https://gone.example") >= 1


def test_fix_sends_nothing_when_the_preview_is_cancelled(bench, monkeypatch) -> None:
    monkeypatch.setattr(dlg, "ask_text", lambda *_a, **_k: "https://found.example")
    monkeypatch.setattr(wdlg, "ask_preview", lambda *_a, **_k: False)
    bench.provider.do_fix_problem(None, _broken())
    assert bench.api.writes == []


def test_fix_sets_a_city_time_zone_and_refuses_what_is_not_one(bench, monkeypatch) -> None:
    row = _health("Time zone: a fixed offset of 1 hours.", "timezone")
    monkeypatch.setattr(wdlg, "ask_preview", lambda *_a, **_k: True)
    monkeypatch.setattr(dlg, "ask_text", lambda *_a, **_k: "plus one")
    bench.provider.do_fix_problem(None, row)
    assert bench.api.writes == [] and "is not a city time zone" in bench.said[-1]
    monkeypatch.setattr(dlg, "ask_text", lambda *_a, **_k: "Europe/London")
    bench.provider.do_fix_problem(None, row)
    assert bench.api.writes[-1] == ("POST", "wp/v2/settings", {"timezone": "Europe/London"})
    bench.provider.do_undo(None, None)
    assert bench.api.settings["timezone"] == ""


def test_fix_where_only_wp_admin_can_says_why_and_opens_that_screen(bench) -> None:
    bench.provider.do_fix_problem(None, _health("Permalinks: plain (?p=123).", "permalinks"))
    assert bench.commands.host.opened[-1] == "https://radio.example/wp-admin/options-permalink.php"
    assert "does not share or change how addresses look" in bench.said[-1]


def test_problem_commands_are_greyed_with_why_where_they_cannot_work(bench) -> None:
    header = _health("The authorization header is missing.", "authorization-header")
    refusal = bench.provider.refusal_for
    assert "cannot fix this from here" in refusal(command("fix_problem"), header)
    assert "whole site" in refusal(command("problem_in_editor"), header)
    assert refusal(command("problem_in_editor"), _broken()) == ""
    passed = _health("HTTPS: the site's address uses HTTPS.", "https-status", "good")
    assert "nothing to fix" in refusal(command("fix_problem"), passed)


def test_take_me_there_and_open_in_editor(bench) -> None:
    bench.provider.do_problem_there(None, _health("Permalinks: plain.", "permalinks"))
    assert bench.current == NodeRef("site", "settings", SITE)
    bench.provider.do_problem_in_editor(None, _broken())
    assert bench.commands.opened == [("post", 2)]


# -- plugins: what depends on one ----------------------------------------------------


def test_turning_a_plugin_off_first_says_what_depends_on_it(bench, monkeypatch) -> None:
    asked: list[str] = []
    monkeypatch.setattr(
        type(bench.provider), "_confirm", lambda _s, _t, message, _y: asked.append(message) or True
    )
    row = WbRow("plugin", SITE, "akismet/akismet", {"plugin": "Akismet"}, "", status="active",
                route="wp/v2/plugins/akismet/akismet")  # fmt: skip
    bench.provider.do_toggle_plugin(None, row)
    assert "Spam Extra requires it" in asked[0] and '"Contact" (its akismet blocks)' in asked[0]
    assert bench.api.writes[-1] == ("POST", "wp/v2/plugins/akismet/akismet", {"status": "inactive"})
    bench.provider.do_what_depends(None, row)
    assert bench.said[-1].startswith("What depends on Akismet: Spam Extra requires it")


# -- the settings REST does not share ---------------------------------------------------


def test_settings_explains_permalinks_and_links_plugin_documentation(bench) -> None:
    _go(bench, NodeRef("site", "settings", SITE))
    explained = [r for r in bench.rows if r.kind == "setting_help"]
    names = [r.cell("setting") for r in explained]
    assert "Permalinks" in names and "Search engine visibility" in names
    permalinks = next(r for r in explained if r.cell("setting") == "Permalinks")
    bench.provider.do_setting_screen(None, permalinks)
    assert bench.commands.host.opened[-1].endswith("/wp-admin/options-permalink.php")
    docs = WbRow("setting_help", SITE, "more:20", {"setting": "WooCommerce settings"}, "",
                 link="https://woocommerce.com/documentation/woocommerce/")  # fmt: skip
    bench.provider.do_open_docs(None, docs)
    assert bench.commands.host.opened[-1] == "https://woocommerce.com/documentation/woocommerce/"
