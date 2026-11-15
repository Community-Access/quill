"""WP-G in the real frame: Check on WordPress.org, Find a Plugin on WordPress.org, and the
directory's words in Install on Sites Missing It -- each after consent, each install
previewed with the update and rollback limits. Work runs inline; WordPress.org is faked."""

from __future__ import annotations

from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.core.wordpress import dotorg  # noqa: E402
from quill.core.wordpress import site_taxonomies as tx  # noqa: E402
from quill.core.wordpress.workbench_rows import WbRow  # noqa: E402
from quill.ui import wordpress_dialogs as dlg  # noqa: E402
from quill.ui import wordpress_workbench_dialogs as wdlg  # noqa: E402
from quill.ui.wordpress_workbench_window import WordPressWorkbenchProvider  # noqa: E402
from quill.ui.workbench_frame import NodeRef, WorkbenchFrame  # noqa: E402
from tests.unit.ui.wordpress.test_wp_workbench_rest_limits import SiteApi  # noqa: E402
from tests.unit.ui.wordpress.test_wp_workbench_window import (  # noqa: E402
    SITE,
    _Commands,
    _go,
    _inline,
)

OLD = dotorg.DotorgPlugin("old-forms", "Old Forms", "1.0", last_updated="2020-01-01")
GONE = dotorg.DotorgPlugin("gone", "Gone", closed=True, closed_reason="Security Issue")


class PluginSite(SiteApi):
    def get(self, route: str, **params: Any) -> Any:
        if route == "wp/v2/plugins":
            return [
                {"plugin": "old-forms/forms", "name": "Old Forms", "status": "active"},
                {"plugin": "custom/custom", "name": "Custom", "status": "inactive"},
            ]
        return super().get(route, **params)

    def iter_collection(self, route: str, params: Any = None, **kw: Any):
        if route == "wp/v2/plugins":  # what Across Sites reads
            yield from self.get(route)
            return
        yield from super().iter_collection(route, params, **kw)


@pytest.fixture
def bench(wx_session_app, tmp_path):
    tx.clear_cache()
    said: list[str] = []
    api = PluginSite()
    commands = _Commands(said)
    provider = WordPressWorkbenchProvider(
        commands, announce=said.append, data_dir=tmp_path, api_for=lambda _p: api
    )
    frame = WorkbenchFrame(provider, announce=said.append, run_background=_inline)
    frame.said = said  # type: ignore[attr-defined]
    frame.api = api  # type: ignore[attr-defined]
    yield frame
    frame.frame.Destroy()
    tx.clear_cache()


def _plugin_row() -> WbRow:
    return WbRow("plugin", SITE, "old-forms/forms", {"plugin": "Old Forms"}, "Old Forms.")


def test_check_on_wordpress_org_sends_nothing_without_consent(bench, monkeypatch) -> None:
    monkeypatch.setattr(dlg, "confirm", lambda *_a, **_k: False)
    monkeypatch.setattr(dotorg, "plugin_details", lambda *_a, **_k: pytest.fail("sent"))
    bench.provider.do_plugin_directory(NodeRef("site", "plugins", SITE), _plugin_row())
    assert bench.said[-1] == "Nothing was sent to WordPress.org."


def test_check_on_wordpress_org_reports_each_plugin_and_marks_the_rows(bench, monkeypatch) -> None:
    asked: list[str] = []
    monkeypatch.setattr(dlg, "confirm", lambda *_a, **k: asked.append(k["message"]) or True)
    reports: list[str] = []
    monkeypatch.setattr(dlg, "show_report", lambda *_a, **k: reports.append(k["text"]))
    sent: list[list[str]] = []
    monkeypatch.setattr(
        dotorg,
        "plugin_details",
        lambda slugs, **_k: sent.append(list(slugs)) or {"old-forms": OLD, "custom": None},
    )
    bench.provider.do_plugin_directory(NodeRef("site", "plugins", SITE), _plugin_row())
    assert "slugs" in asked[0] and "No site address" in asked[0]
    assert [sorted(s) for s in sent] == [["custom", "old-forms"]]
    text = reports[0]
    assert "Old Forms: Old Forms, version 1.0" in text and "may be abandoned" in text
    assert "Custom: Custom is not in the WordPress.org directory" in text
    assert "cannot update a plugin" in text and "no rollback" in text
    _go(bench, NodeRef("site", "plugins", SITE))
    old = next(r for r in bench.rows if r.key == "old-forms/forms")
    assert "WordPress.org: " in old.detail and "may be abandoned" in old.detail


def test_find_plugin_installs_the_chosen_one_inactive_after_a_preview_with_limits(
    bench, monkeypatch
) -> None:
    monkeypatch.setattr(dlg, "ask_text", lambda *_a, **_k: "forms")
    monkeypatch.setattr(dlg, "confirm", lambda *_a, **_k: True)
    choices: list[list[str]] = []
    monkeypatch.setattr(dlg, "ask_choice", lambda *_a, **k: choices.append(k["rows"]) or 0)
    previews: list[dict[str, Any]] = []
    monkeypatch.setattr(wdlg, "ask_preview", lambda *_a, **k: previews.append(k) or True)
    monkeypatch.setattr(dotorg, "search_plugins", lambda words: [OLD] if words == "forms" else [])
    bench.provider.do_find_plugin(NodeRef("site", "plugins", SITE), _plugin_row())
    assert "may be abandoned" in choices[0][0]
    preview = previews[0]
    assert preview["lines"][0] == f"{SITE}: installs old-forms, left inactive"
    assert "no rollback" in preview["summary"] and "cannot update a plugin" in preview["summary"]
    assert ("POST", "wp/v2/plugins", {"slug": "old-forms", "status": "inactive"}) in (
        bench.api.writes
    )
    assert bench.said[-1].startswith("Old Forms installed on 1 of 1 sites, inactive")


def test_find_plugin_cancelled_at_the_preview_installs_nothing(bench, monkeypatch) -> None:
    monkeypatch.setattr(dlg, "ask_text", lambda *_a, **_k: "gone")
    monkeypatch.setattr(dlg, "confirm", lambda *_a, **_k: True)
    monkeypatch.setattr(dlg, "ask_choice", lambda *_a, **_k: 0)
    monkeypatch.setattr(wdlg, "ask_preview", lambda *_a, **_k: False)
    monkeypatch.setattr(dotorg, "search_plugins", lambda _w: [GONE])
    bench.provider.do_find_plugin(NodeRef("site", "plugins", SITE), _plugin_row())
    assert not bench.api.writes


def test_install_missing_preview_carries_the_directory_words(bench, monkeypatch) -> None:
    monkeypatch.setattr(dlg, "confirm", lambda *_a, **_k: True)
    previews: list[list[str]] = []
    monkeypatch.setattr(wdlg, "ask_preview", lambda *_a, **k: previews.append(k["lines"]) or False)
    monkeypatch.setattr(dotorg, "plugin_details", lambda slugs, **_k: {"gone": GONE})
    row = WbRow(
        "across",
        "",
        "Gone",
        {},
        "",
        subkind="plugins",
        raw={"missing": [SITE], "objects": {"Other": {"plugin": "gone/gone"}}},
    )
    bench.provider.do_install_missing(None, row)
    assert previews[0][0] == f"{SITE}: installs gone, left inactive"
    assert "WordPress.org closed Gone (Security Issue)" in previews[0][1]
    assert not bench.api.writes


def _across_rows(bench) -> list[WbRow]:
    return [r for r in bench.provider.across_list("plugins") if r.kind == "across"]


def test_across_sites_plugin_rows_get_the_directory_facts_behind_the_same_consent(
    bench, monkeypatch
) -> None:
    sent: list[list[str]] = []
    monkeypatch.setattr(
        dotorg,
        "plugin_details",
        lambda slugs, **_k: sent.append(list(slugs)) or {"old-forms": OLD, "custom": None},
    )
    before = {r.title: r.detail for r in _across_rows(bench)}
    assert sent == []  # no consent yet: nothing asked, nothing added
    assert "WordPress.org:" not in before["Old Forms"]
    monkeypatch.setattr(dlg, "confirm", lambda *_a, **_k: True)
    monkeypatch.setattr(dlg, "show_report", lambda *_a, **_k: None)
    bench.provider.do_plugin_directory(NodeRef("site", "plugins", SITE), _plugin_row())
    rows = {r.title: r.detail for r in _across_rows(bench)}
    assert len(sent) == 1  # already known: Across Sites asks nothing again
    assert "WordPress.org: Old Forms, version 1.0" in rows["Old Forms"]
    assert "may be abandoned" in rows["Old Forms"]
    assert "Custom is not in the WordPress.org directory" in rows["Custom"]


def test_across_sites_asks_the_directory_for_plugins_it_has_not_heard_of(
    bench, monkeypatch
) -> None:
    sent: list[list[str]] = []
    monkeypatch.setattr(
        dotorg, "plugin_details", lambda slugs, **_k: sent.append(list(slugs)) or {}
    )
    bench.provider.__dict__["_dotorg_consents"] = {"plugins"}  # agreed earlier in the window
    _across_rows(bench)
    assert [sorted(s) for s in sent] == [["custom", "old-forms"]]
