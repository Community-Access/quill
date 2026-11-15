"""wp_missing.md's gaps in the real Workbench frame: Earlier Versions on an item's row,
Check for Updates on WordPress.org, Check Every Link under By Name > Links, and changing
a Gravity Forms response's answers from its Properties. Each test calls the handler a
person reaches from the context menu, with the dialogs answered by patching the helpers."""

from __future__ import annotations

from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.core.wordpress import site_taxonomies as tx  # noqa: E402
from quill.core.wordpress import workbench_gravity_answers as gfa  # noqa: E402
from quill.core.wordpress import workbench_link_check as lk  # noqa: E402
from quill.core.wordpress import workbench_update_check as uc  # noqa: E402
from quill.core.wordpress.workbench_rows import WbRow, item_row  # noqa: E402
from quill.core.workbench.properties import SheetState  # noqa: E402
from quill.ui import wordpress_dialogs as dlg  # noqa: E402
from quill.ui import wordpress_workbench_dialogs as wdlg  # noqa: E402
from quill.ui.wordpress_workbench_window import WordPressWorkbenchProvider  # noqa: E402
from quill.ui.workbench_frame import WorkbenchFrame  # noqa: E402
from tests.unit.ui.wordpress.test_wp_workbench_gravity_ui import GravityApi  # noqa: E402
from tests.unit.ui.wordpress.test_wp_workbench_gravity_ui import _Commands as _GfCommands  # noqa: E402
from tests.unit.ui.wordpress.test_wp_workbench_gravity_ui import _row as _gf_row  # noqa: E402
from tests.unit.ui.wordpress.test_wp_workbench_window import (  # noqa: E402
    SITE,
    FakeApi,
    _Commands,
    _inline,
)


class GapApi(FakeApi):
    def __init__(self) -> None:
        super().__init__()
        self.posts[0]["content"] = {"raw": "Monday\nTuesday"}
        self.posts[1]["content"] = {
            "raw": '<a href="https://ok.example">ok</a> <a href="https://gone.example">gone</a>'
        }
        self.revisions = [
            {
                "id": 50,
                "modified_gmt": "2026-10-30T09:00:00",
                "title": {"raw": "Hello there"},
                "content": {"raw": "Monday"},
            }
        ]
        self.asked: list[str] = []

    def get(self, route: str, **params: Any) -> Any:
        if route == "wp/v2/posts/1/revisions":
            return list(self.revisions)
        if route.endswith("/autosaves"):
            return []
        if route == "":
            index = super().get(route, **params)
            index["routes"]["/wp-block-editor/v1/url-details"] = {}
            return index
        if route == "wp-block-editor/v1/url-details":
            self.asked.append(params["url"])
            if "gone" in params["url"]:
                from quill.core.wordpress.api import WordPressApiError

                raise WordPressApiError("No response", status=404, wp_code="no_response")
            return {"title": "Fine"}
        if route == "wp/v2/plugins":
            return [{"plugin": "akismet/akismet", "name": "Akismet", "version": "5.3"}]
        if route == "wp/v2/themes":
            return [{"stylesheet": "twentytwentyfive", "name": "TT5", "version": "1.3"}]
        return super().get(route, **params)


@pytest.fixture
def bench(wx_session_app, tmp_path):
    tx.clear_cache()
    said: list[str] = []
    api = GapApi()
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


def _previews(monkeypatch: Any, answer: bool = True) -> list[Any]:
    seen: list[Any] = []
    monkeypatch.setattr(
        wdlg, "ask_preview", lambda *_a, **k: seen.append((k["summary"], k["lines"])) or answer
    )
    return seen


def _post(bench: Any) -> WbRow:
    return item_row(bench.api.posts[0], "post", SITE)


# -- Earlier Versions ------------------------------------------------------------------


def test_earlier_versions_compares_then_restores_and_ctrl_z_puts_it_back(
    bench, monkeypatch
) -> None:
    previews = _previews(monkeypatch)
    asked: list[list[str]] = []
    monkeypatch.setattr(dlg, "ask_choice", lambda *_a, **k: asked.append(k["rows"]) or 0)
    bench.provider.do_item_versions(None, _post(bench))
    assert asked[0][0].endswith("Hello there, a revision")
    assert previews[0][1] == ["Title: Hello becomes Hello there.", "Line 2 removed: Tuesday"]
    sent = [w for w in bench.api.writes if w[1] == "wp/v2/posts/1"]
    assert sent == [("POST", "wp/v2/posts/1", {"title": "Hello there", "content": "Monday"})]
    assert bench.said[-1].startswith("Restored Hello to its version of ")
    bench.provider.do_undo(None, None)
    assert bench.api.posts[0]["title"] == "Hello" and bench.api.posts[0]["content"] == (
        "Monday\nTuesday"
    )


def test_earlier_versions_sends_nothing_when_the_preview_is_cancelled(bench, monkeypatch) -> None:
    _previews(monkeypatch, answer=False)
    monkeypatch.setattr(dlg, "ask_choice", lambda *_a, **_k: 0)
    bench.provider.do_item_versions(None, _post(bench))
    assert not bench.api.writes
    bench.api.revisions = []
    bench.provider.do_item_versions(None, _post(bench))
    assert bench.said[-1] == f"Hello has no earlier versions on {SITE}."


# -- Check for Updates on WordPress.org -----------------------------------------------


def test_check_for_updates_asks_first_then_marks_the_rows(bench, monkeypatch) -> None:
    sent: list[Any] = []
    monkeypatch.setattr(uc, "latest_core", lambda: sent.append("core") or "")
    monkeypatch.setattr(
        uc, "latest_plugins", lambda slugs, **_k: sent.append(list(slugs)) or {"akismet": "5.4"}
    )
    monkeypatch.setattr(
        uc, "latest_themes", lambda slugs: sent.append(list(slugs)) or {"twentytwentyfive": "1.3"}
    )
    plugin = WbRow("plugin", SITE, "akismet/akismet", {"plugin": "Akismet", "version": "5.3"}, ".")
    monkeypatch.setattr(dlg, "confirm", lambda *_a, **_k: False)
    bench.provider.do_check_updates(None, plugin)
    assert sent == [] and bench.said[-1] == "Nothing was sent to WordPress.org."
    monkeypatch.setattr(dlg, "confirm", lambda *_a, **_k: True)
    bench.provider.do_check_updates(None, plugin)
    assert sent == ["core", ["akismet"], ["twentytwentyfive"]]
    assert bench.said[-1] == f"1 update waiting on {SITE}: Akismet."
    [marked] = bench.provider.with_update_facts([plugin])
    assert marked.cell("version") == "5.3, update waiting: 5.4"


# -- Check Every Link ------------------------------------------------------------------


def _links_row() -> WbRow:
    return WbRow("value", SITE, "https://gone.example", {"value": "gone"}, "", subkind="links")


def test_check_every_link_lists_what_is_broken_and_who_holds_it(bench, monkeypatch) -> None:
    monkeypatch.setattr(dlg, "confirm", lambda *_a, **_k: True)
    shown: list[dict[str, Any]] = []

    class _Window:
        def Destroy(self) -> None:  # noqa: N802 - wx's name
            pass

    monkeypatch.setattr(dlg, "show_list_window", lambda *_a, **k: shown.append(k) or _Window())
    bench.provider.do_check_every_link(None, _links_row())
    assert bench.api.asked == ["https://ok.example", "https://gone.example"]
    assert bench.said[-1] == f"1 of 2 links on {SITE} lead nowhere."
    assert shown[0]["rows"] == ["https://gone.example, in News (post): the page is not there."]
    shown[0]["actions"][0].run(0)
    assert bench.commands.opened == [("post", 2)]
    assert bench.provider.link_check_status() == ""


def test_choosing_it_again_while_it_runs_stops_it(bench, monkeypatch) -> None:
    monkeypatch.setattr(dlg, "confirm", lambda *_a, **_k: True)
    monkeypatch.setattr(dlg, "show_list_window", lambda *_a, **_k: pytest.fail("none broken"))
    real = lk.read_target

    def first_then_stop(api: Any, url: str) -> Any:
        assert "Reading" not in bench.provider.link_check_status()
        bench.provider.do_check_every_link(None, _links_row())  # the second choice stops it
        return real(api, url)

    monkeypatch.setattr(lk, "read_target", first_then_stop)
    bench.provider.do_check_every_link(None, _links_row())
    assert bench.said[-2] == "Stopping the link check; what it found so far is kept."
    assert bench.said[-1].startswith("Stopped after 1 of 2 links")
    bench.provider.stop_link_check()
    assert bench.said[-1] == "No link check is running."


def test_check_every_link_is_only_for_links(bench) -> None:
    row = WbRow("value", SITE, "Shows", {"value": "Shows"}, "", subkind="terms")
    bench.provider.do_check_every_link(None, row)
    assert bench.said[-1] == "Check Every Link works on a row of By Name > Links."


# -- a Gravity Forms response's answers ------------------------------------------------


@pytest.fixture
def gf_bench(wx_session_app, tmp_path):
    tx.clear_cache()
    said: list[str] = []
    api = GravityApi()
    provider = WordPressWorkbenchProvider(
        _GfCommands(said), announce=said.append, data_dir=tmp_path, api_for=lambda _p: api
    )
    frame = WorkbenchFrame(provider, announce=said.append, run_background=_inline)
    frame.said = said  # type: ignore[attr-defined]
    frame.api = api  # type: ignore[attr-defined]
    yield frame
    frame.frame.Destroy()
    tx.clear_cache()


def test_a_responses_answers_change_after_a_preview_and_ctrl_z_restores_them(
    gf_bench, monkeypatch
) -> None:
    previews = _previews(monkeypatch)
    entry = _gf_row(gf_bench, "form_entries")
    sheet, values, _fresh, _names, _meta = gf_bench.provider._load_sheet(entry)
    key = gfa.answer_key("1")
    assert sheet.field(key).label == "Name" and not sheet.field(key).readonly
    state = SheetState(sheet, dict(values))
    state.set(key, "Anne")
    assert gf_bench.provider.gravity_entry_save(entry, state) is True
    assert previews[0][1] == ["Name: Ann becomes Anne"]
    assert gf_bench.api.entry["1"] == "Anne" and gf_bench.api.entry["2"] == "ann@example.com"
    gf_bench.provider.do_undo(None, None)
    assert gf_bench.api.entry["1"] == "Ann"


def test_an_answer_changed_in_gravity_forms_meanwhile_is_left_alone(gf_bench, monkeypatch) -> None:
    _previews(monkeypatch)
    entry = _gf_row(gf_bench, "form_entries")
    sheet, values, _fresh, _names, _meta = gf_bench.provider._load_sheet(entry)
    state = SheetState(sheet, dict(values))
    state.set(gfa.answer_key("1"), "Anne")
    gf_bench.api.entry["1"] = "Annie"  # somebody else, after the sheet loaded
    gf_bench.provider.gravity_entry_save(entry, state)
    assert not [w for w in gf_bench.api.writes if w[0] == "PUT"]
    assert gf_bench.said[-1].startswith("This response was changed in Gravity Forms")
