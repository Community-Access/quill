"""W8 and the third sweep in the real frame on a fake site."""

from __future__ import annotations

from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.core.wordpress.workbench_actions import WINDOW_MENU, command  # noqa: E402
from quill.core.wordpress.workbench_options import load_options  # noqa: E402
from quill.core.workbench.menus import problems  # noqa: E402
from quill.ui import wordpress_dialogs as dlg  # noqa: E402
from quill.ui import wordpress_workbench_dialogs as wdlg  # noqa: E402
from quill.ui.workbench_frame import NodeRef  # noqa: E402
from tests.unit.ui.wordpress.test_wp_workbench_lists import bench as _bench  # noqa: E402
from tests.unit.ui.wordpress.test_wp_workbench_window import SITE, _go  # noqa: E402

bench = _bench


def test_the_bar_keeps_its_rules_with_across_sites() -> None:
    assert problems(WINDOW_MENU) == []


def test_by_name_lists_values_with_where_they_are_used(bench) -> None:
    for post in bench.api.posts:
        post["content"] = {"raw": '<a href="https://old.example">x</a>'}
    _go(bench, NodeRef("site", "by_name_links", SITE))
    assert [r.key for r in bench.rows] == ["https://old.example"]
    assert bench.rows[0].cell("used") == "used on 2 pages"


def test_across_sites_and_the_fleet_list_every_site(bench) -> None:
    _go(bench, NodeRef("", "across_users"))
    names = [r.key for r in bench.rows]
    assert names and all(r.kind == "across" for r in bench.rows)
    _go(bench, NodeRef("", "fleet"))
    assert [r.site for r in bench.rows] == [SITE]


def test_a_site_set_is_kept_and_narrows_the_scope(bench, monkeypatch) -> None:
    bench.select(NodeRef("", "start"))
    monkeypatch.setattr(dlg, "ask_text", lambda *a, **k: "Family")
    monkeypatch.setattr(wdlg, "ask_checks", lambda *a, **k: [0])
    bench.run(command("site_sets"))
    assert load_options(bench.provider._data_dir).site_sets == {"Family": [SITE]}
    monkeypatch.setattr(dlg, "ask_choice", lambda *a, **k: 1)
    bench.run(command("scope"))
    assert bench.provider.scope == "Family" and bench.provider.scope_sites() == [SITE]


def test_make_them_the_same_previews_every_site_first(bench, monkeypatch) -> None:
    from quill.core.wordpress.workbench_rows import WbRow

    previews: list[Any] = []
    monkeypatch.setattr(dlg, "ask_choice", lambda *a, **k: 0)
    monkeypatch.setattr(wdlg, "ask_preview", lambda *a, **k: (previews.append(k), False)[1])
    row = WbRow(
        "across",
        "",
        "Shows (category)",
        {},
        "",
        subkind="terms",
        raw={"variants": {"slug shows": [SITE]}, "missing": [], "objects": {SITE: {}}},
    )
    bench.provider.do_make_same(None, row)
    assert previews and previews[0]["lines"] == [f"{SITE}: already matches; nothing to do"]
    assert not [w for w in bench.api.writes if "categories" in w[1]]
