"""W7 in the real frame on a fake site: calendar, watches, practice, console, lists, the queue."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.core.wordpress.workbench_actions import WINDOW_MENU, command  # noqa: E402
from quill.core.workbench.menus import problems  # noqa: E402
from quill.ui import wordpress_dialogs as dlg  # noqa: E402
from quill.ui.workbench_frame import NodeRef  # noqa: E402
from tests.unit.ui.wordpress.test_wp_workbench_lists import bench as _bench  # noqa: E402
from tests.unit.ui.wordpress.test_wp_workbench_window import SITE, _go, _select  # noqa: E402

bench = _bench


def test_the_bar_still_keeps_its_rules() -> None:
    assert problems(WINDOW_MENU) == []


def test_the_calendar_lists_days_and_a_day_lists_its_items(bench) -> None:
    bench.api.posts.append({
        "id": 9,
        "title": {"raw": "Soon", "rendered": "Soon"},
        "status": "future",
        "date": "2030-01-02T09:00:00",
        "author": 3,
        "type": "post",
    })
    _go(bench, NodeRef("", "calendar"))
    days = [r.key for r in bench.rows]
    assert "2030-01-02" in days
    bench.provider._days_changed()
    _go(bench, NodeRef("", "calendar_day", "2030-01-02"))
    assert [r.title for r in bench.rows] == ["Soon"]


def test_watches_and_the_practice_site_say_where_they_stand(bench) -> None:
    _go(bench, NodeRef("", "watches"))
    assert any(r.cell("fact") == "New comments waiting" for r in bench.rows)
    _go(bench, NodeRef("", "practice"))
    assert any(r.cell("fact") == "Running" for r in bench.rows)


def test_the_rest_console_reads_and_draws_a_tree(bench) -> None:
    from quill.ui.wordpress_rest_console import RestConsole

    bench.provider.discover(SITE)
    ctx = bench.provider.ctx(SITE)

    class _Response:
        payload = {"id": 1, "title": {"rendered": "Hello"}}

    bench.api.request = lambda method, route, **kw: _Response()  # type: ignore[method-assign]
    console = RestConsole(bench.provider, SITE, ctx)
    try:
        console.route.ChangeValue("wp/v2/posts/1")
        console.send()
        root = console.tree.GetRootItem()
        top, _cookie = console.tree.GetFirstChild(root)
        assert console.tree.GetItemText(top) == "Answer (2 fields)"
    finally:
        console.dialog.Destroy()


def test_export_list_writes_what_the_list_shows(bench, tmp_path, monkeypatch) -> None:
    _go(bench, NodeRef("site", "posts", SITE))
    out = tmp_path / "posts.csv"
    monkeypatch.setattr(type(bench.provider), "_file", lambda self, *a, **k: out)
    bench.run(command("export_list"))
    text = out.read_text(encoding="utf-8-sig")
    assert text.splitlines()[0] == "Title,Status,Author,Modified" and "Hello" in text


def test_send_back_leaves_a_note_and_returns_the_draft(bench, monkeypatch) -> None:
    from quill.core.wordpress import block_notes

    notes: list[Any] = []
    monkeypatch.setattr(
        block_notes, "add_note", lambda api, ident, text: notes.append((ident, text))
    )
    monkeypatch.setattr(dlg, "ask_text", lambda *a, **k: "Needs a photo")
    _go(bench, NodeRef("site", "posts", SITE))
    _select(bench, 1)
    bench.run(command("send_back"))
    assert notes == [(2, "Needs a photo")]
    assert ("POST", "wp/v2/posts/2", {"status": "draft"}) in bench.api.writes


def test_read_site_as_document_opens_it_in_the_editor(bench, monkeypatch) -> None:
    opened: list[Path] = []
    bench.commands.host.open_path = opened.append  # type: ignore[attr-defined]
    _go(bench, NodeRef("site", "overview", SITE))
    bench.run(command("read_site"))
    assert opened and opened[0].read_text(encoding="utf-8").startswith(f"# {SITE}")
